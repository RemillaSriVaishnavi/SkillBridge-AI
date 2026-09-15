# 🎯 SkillBridge AI — Intelligent Resume Screening & Upskilling Engine

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://remillasrivaishnavi-skillbridge-ai-app-c2de8r.streamlit.app/)
[![Telegram Bot](https://img.shields.io/badge/Telegram-Try%20Bot-2CA5E0?logo=telegram&logoColor=white)](https://t.me/skillbridge_matcher_bot)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

SkillBridge AI is an end-to-end recruitment audit platform that screens candidate resumes against job descriptions, identifies skill gaps, calculates competency compatibility scores, and recommends targeted upskilling courses.

Available as both a **Web Dashboard** and a **Mobile Telegram Bot**.


## 🚀 Live Demos

* **🌐 Interactive Web App:** [Launch SkillBridge Web App](https://remillasrivaishnavi-skillbridge-ai-app-c2de8r.streamlit.app/)
* **📱 24/7 Telegram Bot:** [Chat with @skillbridge_matcher_bot](https://t.me/skillbridge_matcher_bot?start=hello)


## 🌟 Key Features

* **Multi-Format Extraction:** Seamlessly parses `.pdf`, `.docx`, and `.txt` files directly in memory.
* **Document Integrity Guardrails:** Rejects non-resume/non-JD files (e.g., invoices, articles, receipts) automatically.
* **Multi-Candidate Evaluation:** Compares up to 5+ candidate profiles simultaneously against a target Job Description.
* **Competency Gap Analysis:** Highlights confirmed technical capabilities and pinpoints missing qualifications with clean badge indicators.
* **Automated Course Recommendations:** Automatically provides verified educational courses (Coursera, Udemy) for identified skill gaps.


## 🛠️ Architecture & Tech Stack

* **LLM Engine:** Google Gemini (`gemini-2.0-flash` via `google-genai`)
* **Web UI:** Streamlit Cloud
* **Mobile Bot:** `python-telegram-bot` (Hosted on Render)
* **Schema Validation:** Pydantic v2
* **Parsing Engine:** `pdfplumber`, `python-docx`

## 📄 License
This project is open-source and licensed under the MIT License