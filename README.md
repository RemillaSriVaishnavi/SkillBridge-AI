# 🎯 SkillBridge AI — Resume & Job Description Matcher

An AI-powered screening engine that analyzes candidate resumes against job descriptions, identifies competency matches and skill gaps, and recommends targeted upskilling courses.

![Project Demo](assets/demo.gif)

## 🌟 Key Features
- **Multi-Format Parsing:** Supports `.pdf`, `.docx`, and `.txt` files.
- **Document Classification Guardrails:** Filters out non-resume/non-JD files automatically.
- **Dual Interfaces:** Web dashboard (Streamlit) and mobile chatbot (Telegram).
- **Competency Gap Analysis:** Pinpoints confirmed skills and missing qualifications.
- **Automated Upskilling:** Maps missing skills directly to verified learning courses.

## 🛠️ Tech Stack
- **AI Core:** Google Gemini (`gemini-2.0-flash` via `google-genai`)
- **Backend:** FastAPI, Pydantic
- **Frontend / Chat:** Streamlit, `python-telegram-bot`
- **Parsing:** `pdfplumber`, `python-docx`

## 🚀 Quick Start Guide

