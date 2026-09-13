import os
import json
from fastapi import FastAPI, UploadFile, File, Form
from typing import List, Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types

from parser import extract_text_from_file
from schemas import DocumentValidation, CandidateEvaluation, BatchEvaluationResponse
from course_catalog import get_courses_for_skills

load_dotenv()
app = FastAPI(title="Resume Matcher API")

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in environment!")

client = genai.Client(api_key=api_key)

# Using the active model requested by the Google API
MODEL_NAME = "gemini-3.6-flash"


@app.post("/analyze", response_model=BatchEvaluationResponse)
async def analyze_batch(
    jd_text_input: Optional[str] = Form(None),
    jd_file: Optional[UploadFile] = File(None),
    resumes: List[UploadFile] = File(...)
):
    # 1. Read JD text
    final_jd_text = ""
    if jd_file:
        file_bytes = await jd_file.read()
        final_jd_text = extract_text_from_file(file_bytes, jd_file.filename)
    elif jd_text_input:
        final_jd_text = jd_text_input.strip()

    if not final_jd_text:
        return BatchEvaluationResponse(
            is_valid_jd=False, 
            jd_rejection_reason="No Job Description supplied.", 
            results=[]
        )

    # 2. Read all resumes into memory
    resume_payloads = []
    for res_file in resumes:
        raw_bytes = await res_file.read()
        try:
            text = extract_text_from_file(raw_bytes, res_file.filename)
            resume_payloads.append({"filename": res_file.filename, "text": text[:3500]})
        except Exception as e:
            resume_payloads.append({"filename": res_file.filename, "text": f"Error reading file: {str(e)}"})

    # 3. Consolidate everything into a single prompt (Only 1 API Call)
    resumes_text_formatted = ""
    for idx, r in enumerate(resume_payloads):
        resumes_text_formatted += f"\n\n--- RESUME #{idx+1} (Filename: {r['filename']}) ---\n{r['text']}"

    prompt = f"""
    You are an expert HR recruitment auditor and parser. Perform the following evaluation:

    1. VALIDATE JOB DESCRIPTION:
       - Check if the provided text is a genuine Job Description (contains job title, duties, or technical requirements).
       - If invalid, set is_valid_jd=false and provide jd_rejection_reason.

    2. FOR EACH CANDIDATE RESUME:
       - Verify if it is a legitimate resume (mentions education, background, projects, or work history).
       - If not a resume (e.g. receipt, article, random notes), set is_valid_resume=false and provide rejection_reason.
       - If it IS a valid resume:
         - Extract candidate_name (use 'Candidate' if not found).
         - Compute compatibility score (overall_score) from 0 to 100.
         - Extract matched_skills (concise, 1 to 3 words each).
         - Extract missing_skills (concise, 1 to 3 words each).

    === JOB DESCRIPTION TEXT ===
    {final_jd_text[:4000]}

    === CANDIDATE RESUMES ===
    {resumes_text_formatted}
    """

    # 4. Generate structured response
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=BatchEvaluationResponse,
            temperature=0.1,
        ),
    )

    result = BatchEvaluationResponse.model_validate_json(response.text)

    # 5. Populate recommended courses locally from verified database
    for cand in result.results:
        if cand.is_valid_resume and cand.missing_skills:
            cand.recommended_courses = get_courses_for_skills(cand.missing_skills)

    result.results.sort(key=lambda x: x.overall_score, reverse=True)
    return result