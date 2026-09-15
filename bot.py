import os
import io
import html
import logging
import warnings
import asyncio

import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from google.genai.errors import APIError
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from google import genai
from google.genai import types

from parser import extract_text_from_file
from schemas import BatchEvaluationResponse
from course_catalog import get_courses_for_skills

# Suppress noisy client logs
warnings.filterwarnings("ignore", category=UserWarning, module="google.genai")
logging.getLogger("google.genai").setLevel(logging.ERROR)

load_dotenv()

# Verify API Keys
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is missing from .env")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is missing from .env")

client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-3.6-flash"

# Session state: chat_id -> {'jd': str, 'resumes': [{'filename': str, 'text': str}]}
USER_SESSIONS = {}


def get_session(chat_id: int):
    if chat_id not in USER_SESSIONS:
        USER_SESSIONS[chat_id] = {"jd": None, "resumes": []}
    return USER_SESSIONS[chat_id]


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    USER_SESSIONS[chat_id] = {"jd": None, "resumes": []}

    welcome_msg = (
        "👋 <b>Welcome to SkillBridge AI Bot!</b>\n\n"
        "Here is how to evaluate candidates:\n"
        "1️⃣ Send or paste the <b>Job Description</b> (as text or attach a PDF/DOCX).\n"
        "2️⃣ Send candidate <b>Resumes</b> as document attachments (up to 5+).\n"
        "3️⃣ Type <b>/evaluate</b> to run the analysis!\n\n"
        "Type <b>/reset</b> anytime to clear your uploaded files."
    )
    await update.message.reply_text(welcome_msg, parse_mode="HTML")


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    USER_SESSIONS[chat_id] = {"jd": None, "resumes": []}
    await update.message.reply_text("🔄 Session cleared! Please send a new Job Description.")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session = get_session(chat_id)
    text = update.message.text.strip()

    if not session["jd"]:
        session["jd"] = text
        await update.message.reply_text(
            "✅ <b>Job Description received!</b>\nNow attach candidate resumes (PDF, DOCX, or TXT).",
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text(
            "ℹ️ Job Description already saved. Please attach candidate resumes, or type <b>/evaluate</b> to process.",
            parse_mode="HTML",
        )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session = get_session(chat_id)
    doc = update.message.document
    filename = doc.file_name or "uploaded_document"

    tg_file = await context.bot.get_file(doc.file_id)
    file_bytes = io.BytesIO()
    await tg_file.download_to_memory(file_bytes)
    raw_data = file_bytes.getvalue()

    try:
        extracted_text = extract_text_from_file(raw_data, filename)
    except Exception as e:
        await update.message.reply_text(
            f"❌ Failed to parse <code>{html.escape(filename)}</code>: {html.escape(str(e))}",
            parse_mode="HTML",
        )
        return

    if not session["jd"]:
        session["jd"] = extracted_text
        await update.message.reply_text(
            f"📄 <b>Job Description saved from:</b> <code>{html.escape(filename)}</code>\nNow attach candidate resume files.",
            parse_mode="HTML",
        )
    else:
        session["resumes"].append({"filename": filename, "text": extracted_text})
        count = len(session["resumes"])
        await update.message.reply_text(
            f"📎 <b>Resume #{count} added:</b> <code>{html.escape(filename)}</code>\nSend more resumes or run <b>/evaluate</b>.",
            parse_mode="HTML",
        )


# Candidate models in order of priority
CANDIDATE_MODELS = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-1.5-flash"]

async def evaluate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session = get_session(chat_id)

    if not session["jd"]:
        await update.message.reply_text("⚠️ Please send a Job Description first.")
        return

    if not session["resumes"]:
        await update.message.reply_text("⚠️ Please upload at least one candidate resume.")
        return

    status_msg = await update.message.reply_text(
        "⏳ <b>Analyzing candidates and matching competencies...</b>",
        parse_mode="HTML",
    )

    resumes_formatted = ""
    for idx, r in enumerate(session["resumes"]):
        resumes_formatted += f"\n\n--- CANDIDATE FILE #{idx+1}: {r['filename']} ---\n{r['text'][:3500]}"

    prompt = f"""
    You are an automated technical recruitment auditor.
    
    1. VALIDATE JOB DESCRIPTION:
       - Check if the text describes a genuine job profile with tasks or qualifications.
       - If invalid, set is_valid_jd=false and describe in jd_rejection_reason.
    
    2. EVALUATE EACH CANDIDATE RESUME:
       - If not a resume (e.g., invoices, articles), set is_valid_resume=false and provide rejection_reason.
       - If valid:
         - Extract candidate_name (default: "Candidate").
         - Compute overall_score (0-100).
         - Extract matched_skills (concise, 1-3 words each).
         - Extract missing_skills (concise, 1-3 words each).

    === JOB DESCRIPTION ===
    {session["jd"][:4000]}

    === CANDIDATE RESUMES ===
    {resumes_formatted}
    """

    result = None
    last_error = None

    # Try models with automatic backoff retry on 503 / high demand
    for model_name in CANDIDATE_MODELS:
        for attempt in range(2):  # 2 attempts per model
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=BatchEvaluationResponse,
                        temperature=0.1,
                        tools=None,
                    ),
                )
                result = BatchEvaluationResponse.model_validate_json(response.text)
                break
            except Exception as e:
                last_error = str(e)
                if "503" in last_error or "UNAVAILABLE" in last_error or "429" in last_error:
                    await asyncio.sleep(3)  # Wait briefly for the spike to settle
                    continue
                break
        if result:
            break

    if not result:
        await status_msg.edit_text(
            f"❌ <b>Server Busy:</b> Google servers are experiencing high traffic. Please try sending /evaluate again in a few moments.\n\n<i>Detail: {html.escape(last_error or '')}</i>",
            parse_mode="HTML",
        )
        return

    if not result.is_valid_jd:
        await status_msg.edit_text(
            f"❌ <b>Invalid Job Description:</b> {html.escape(result.jd_rejection_reason or 'Not recognized.')}",
            parse_mode="HTML",
        )
        USER_SESSIONS[chat_id] = {"jd": None, "resumes": []}
        return

    # Delete progress message
    await status_msg.delete()
    result.results.sort(key=lambda x: x.overall_score, reverse=True)

    # Render candidate reports
    for cand in result.results:
        safe_fname = html.escape(cand.filename)
        if not cand.is_valid_resume:
            msg = f"⚠️ <b>{safe_fname}</b>\n<b>Status:</b> Rejected\n<b>Reason:</b> {html.escape(cand.rejection_reason or 'Invalid file format')}"
            await update.message.reply_text(msg, parse_mode="HTML")
            continue

        cand.recommended_courses = get_courses_for_skills(cand.missing_skills)

        matched = ", ".join([f"<code>{html.escape(s)}</code>" for s in cand.matched_skills]) or "<i>None identified</i>"
        missing = ", ".join([f"<code>{html.escape(s)}</code>" for s in cand.missing_skills]) or "<i>None identified</i>"

        report = (
            f"👤 <b>Candidate:</b> {html.escape(cand.candidate_name)}\n"
            f"📁 <b>File:</b> <code>{safe_fname}</code>\n"
            f"🎯 <b>Match Score:</b> <b>{cand.overall_score}%</b>\n\n"
            f"✅ <b>Confirmed Competencies:</b>\n{matched}\n\n"
            f"⚠️ <b>Skill Gaps:</b>\n{missing}\n"
        )

        if cand.recommended_courses:
            report += "\n📚 <b>Recommended Upskilling Courses:</b>\n"
            for c in cand.recommended_courses:
                course_title = html.escape(c["course_name"])
                platform = html.escape(c["platform"])
                report += f"• <a href=\"{c['url']}\">{course_title}</a> <i>({platform})</i>\n"

        await update.message.reply_text(
            report,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )

    # Automatically clear session for the next batch
    USER_SESSIONS[chat_id] = {"jd": None, "resumes": []}
    await update.message.reply_text(
        "✨ <b>Evaluation cycle complete!</b>\n\n"
        "Session has been automatically reset. You can now send a new <b>Job Description</b> to start another round.",
        parse_mode="HTML",
    )



# Dummy HTTP server to satisfy Render's free Web Service health checks
class RenderHealthCheck(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"SkillBridge Telegram Bot is Online!")

def start_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), RenderHealthCheck)
    server.serve_forever()

def main():
    # Start the dummy web server in a background thread
    threading.Thread(target=start_health_server, daemon=True).start()

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(CommandHandler("evaluate", evaluate_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    print("🤖 SkillBridge Mobile Telegram Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
