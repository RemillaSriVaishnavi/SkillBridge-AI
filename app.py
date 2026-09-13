import os
import io
import html
import asyncio
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

from parser import extract_text_from_file
from schemas import BatchEvaluationResponse
from course_catalog import get_courses_for_skills

load_dotenv()

# Read from Streamlit Secrets (Cloud) or .env (Local)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY and "GEMINI_API_KEY" in st.secrets:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

if not GEMINI_API_KEY:
    st.error("Missing GEMINI_API_KEY. Please set it in Streamlit Secrets or .env file.")
    st.stop()

client = genai.Client(api_key=GEMINI_API_KEY)
CANDIDATE_MODELS = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-1.5-flash"]

st.set_page_config(page_title="SkillBridge AI | Resume & JD Matcher", layout="wide")

# Custom Badges Styling
st.markdown("""
<style>
    .badge-match {
        display: inline-block;
        background-color: #E6F4EA;
        color: #137333;
        border: 1px solid #CEEAD6;
        padding: 4px 10px;
        margin: 3px 4px;
        border-radius: 14px;
        font-size: 13px;
        font-weight: 500;
    }
    .badge-missing {
        display: inline-block;
        background-color: #FCE8E6;
        color: #C5221F;
        border: 1px solid #FAD2CF;
        padding: 4px 10px;
        margin: 3px 4px;
        border-radius: 14px;
        font-size: 13px;
        font-weight: 500;
    }
    .skill-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 16px;
        border: 1px solid #e9ecef;
        min-height: 140px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🎯 SkillBridge AI")
st.caption("Intelligent Candidate Evaluation, Competency Matching & Gap Analysis")

with st.sidebar:
    st.header("1. Target Job Description")
    jd_choice = st.radio("Input Format:", ["Direct Text", "Upload Document"])
    jd_text = ""
    jd_file = None
    if jd_choice == "Direct Text":
        jd_text = st.text_area("Paste JD here:", height=200)
    else:
        jd_file = st.file_uploader("Upload JD (.pdf, .docx, .txt)", type=["pdf", "docx", "txt"])

    st.header("2. Candidate Resumes")
    resume_files = st.file_uploader(
        "Upload Resumes (Up to 5+ files)", 
        type=["pdf", "docx", "txt"], 
        accept_multiple_files=True
    )
    
    submit_button = st.button("Evaluate Candidates", type="primary", use_container_width=True)

if submit_button:
    if not jd_text and not jd_file:
        st.error("Please supply a Job Description.")
        st.stop()
    if not resume_files:
        st.error("Please upload at least one candidate resume.")
        st.stop()

    with st.spinner("Extracting content and analyzing competencies..."):
        # Resolve JD Text
        final_jd_text = ""
        if jd_file:
            final_jd_text = extract_text_from_file(jd_file.getvalue(), jd_file.name)
        elif jd_text:
            final_jd_text = jd_text.strip()

        # Extract Resumes
        resumes_formatted = ""
        for idx, rf in enumerate(resume_files):
            text = extract_text_from_file(rf.getvalue(), rf.name)
            resumes_formatted += f"\n\n--- CANDIDATE FILE #{idx+1}: {rf.name} ---\n{text[:3500]}"

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
        {final_jd_text[:4000]}

        === CANDIDATE RESUMES ===
        {resumes_formatted}
        """

        result = None
        for model_name in CANDIDATE_MODELS:
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
            except Exception:
                continue

        if not result:
            st.error("API high demand spike. Please try again in a few moments.")
            st.stop()

        if not result.is_valid_jd:
            st.error(f"❌ Invalid Job Description: {result.jd_rejection_reason}")
            st.stop()

        st.success("✅ Analysis Complete!")

        result.results.sort(key=lambda x: x.overall_score, reverse=True)

        for cand in result.results:
            with st.container():
                if not cand.is_valid_resume:
                    st.warning(f"⚠️ **{cand.filename}** — {cand.rejection_reason or 'Invalid file format'}")
                    st.divider()
                    continue

                col_score, col_meta = st.columns([1, 5])
                with col_score:
                    st.metric("Compatibility", f"{cand.overall_score}%")
                with col_meta:
                    st.subheader(f"{cand.candidate_name} (`{cand.filename}`)")

                col_matched, col_missing = st.columns(2)
                with col_matched:
                    st.markdown("#### ✅ Confirmed Competencies")
                    matched_badges = "".join([f'<span class="badge-match">{s}</span>' for s in cand.matched_skills])
                    st.markdown(f'<div class="skill-card">{matched_badges if matched_badges else "<i>None identified</i>"}</div>', unsafe_allow_html=True)

                with col_missing:
                    st.markdown("#### ⚠️ Skill Gaps Identified")
                    missing_badges = "".join([f'<span class="badge-missing">{s}</span>' for s in cand.missing_skills])
                    st.markdown(f'<div class="skill-card">{missing_badges if missing_badges else "<i>No critical gaps found</i>"}</div>', unsafe_allow_html=True)

                cand.recommended_courses = get_courses_for_skills(cand.missing_skills)
                if cand.recommended_courses:
                    st.write("")
                    with st.expander("📚 Recommended Courses to Bridge Missing Skills", expanded=True):
                        for course in cand.recommended_courses:
                            st.markdown(f"- **{course['skill'].title()}**: [{course['course_name']}]({course['url']}) · *{course['platform']}*")

                st.divider()