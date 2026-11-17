# MEDICHAIN
### AI-Powered Intelligent Healthcare Coordination & Prediction Platform

MEDICHAIN is an enterprise-grade AI healthcare coordination platform designed to improve access to validated medical information, hospital resource visibility, emergency triage coordination, and cryptographic medical report auditing.

---

## 🏥 Core Modules

1. **Clinical AI Health Assistant (`/assistant.html`):**
   - General health, preventive care, and symptom guidance grounded in official **WHO, MedlinePlus, ICMR / MoHFW, NHS, and FDA** guidelines.
   - **8-Part Structured Medicine Information Engine:** Generic composition, approved uses, mechanism of action in simple terms, side effects, precautions/warnings, drug interactions, food/administration timing, and doctor consultation triggers.
   - **Multi-Turn Conversational Memory:** Preserves multi-turn context so follow-up queries (*"Can I take it before food?"*) retain reference to previous topics.
   - **Emergency Fast-Path:** Detects acute red-flag symptoms (chest pain, stroke signs, severe breathing distress) and immediately provides critical emergency guidance.
   - **Anti-Hallucination & Honest Abstention:** If a drug name or medical fact cannot be verified in authoritative medical repositories, the assistant abstains safely rather than inventing facts.

2. **Hospital Resource Dashboard (`/resources.html`):**
   - Real-time tracking of general beds, ICU beds, mechanical ventilators, oxygen cylinders, ambulances, doctors, and emergency antibiotics.
   - Live occupancy metrics and critical shortage threshold alerts.

3. **Emergency Coordination Module (`/emergency.html`):**
   - Emergency dispatch intake with automated clinical priority triage (`Critical`, `Urgent`, `Stable`).
   - Live case logs, status transitions, and emergency hospital routing.

4. **AI Preliminary Report Analysis & Verification (`/reports.html` & `/admin.html`):**
   - Ephemeral in-memory report parsing (PDF/image) using PyMuPDF.
   - Zero-retention memory processing: files are scrubbed immediately after processing to protect patient privacy.
   - SHA-256 cryptographic document verification hash for anti-tampering audits.

---

## 🛠️ Technology Stack

- **Frontend:** HTML5, CSS3 (Glassmorphism & CSS Variables), Vanilla ES6+ JavaScript.
- **Backend:** Python 3.12, FastAPI, Uvicorn, SQLAlchemy 2.0, Pydantic v2.
- **Database:** Serverless PostgreSQL on **Neon Cloud** (with automatic local SQLite fallback).
- **AI Integration:** Google Gemini 3.1 Flash-Lite API via REST transport.
- **Testing:** Pytest (14 test suites, 100% passing).
- **Deployment:** Render / Railway (Backend) + Netlify / Vercel (Frontend).

---

## 🚀 Quickstart Guide

### 1. Backend Setup
```bash
cd Backend
pip install -r requirements.txt
cp .env.example .env
# Configure DATABASE_URL and GEMINI_API_KEY in .env
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive Swagger API documentation: `http://localhost:8000/docs`

### 2. Frontend Setup
```bash
cd Frontend
python -m http.server 8081
```
Open your browser at: `http://localhost:8081/index.html`

---

## ☁️ Cloud Deployment

Refer to [`DEPLOYMENT.md`](DEPLOYMENT.md) for complete instructions on deploying the FastAPI backend to **Render/Railway** and the static frontend to **Netlify/Vercel**.

---

## ⚠️ Medical Safety & Privacy Disclaimer

MEDICHAIN provides AI-assisted health information and preliminary explanations. It does not replace professional medical diagnosis, treatment, or consultation. In case of acute medical emergencies, seek immediate care from local emergency medical services (Dial 112 / 911 / 108).
