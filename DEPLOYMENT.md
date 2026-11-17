# MEDICHAIN Cloud Deployment & Team Collaboration Guide

This document outlines the step-by-step procedures for deploying MEDICHAIN online and collaborating across development branches.

---

## 1. Architecture Overview

- **Frontend:** HTML5, CSS3 (Glassmorphism), Vanilla ES6+ JavaScript.
- **Backend:** Python 3.12, FastAPI, Uvicorn, SQLAlchemy 2.0, Pydantic v2.
- **Database:** PostgreSQL (Neon Serverless PostgreSQL on AWS) with automated local SQLite fallback.
- **AI Integration:** Google Gemini 3.1 Flash-Lite API with clinical grounding (WHO, MedlinePlus, ICMR, FDA).
- **Report Verification:** Ephemeral zero-retention SHA-256 cryptographic document audit trail.

---

## 2. Deploying Backend Online (e.g. Render / Railway / Cloud Run)

### A. Deploy via Render Blueprint (Recommended)
1. Fork or push your code to GitHub: `https://github.com/Shravya-B046/MEDICHAIN`.
2. Log in to [Render.com](https://render.com) and click **New +** -> **Web Service**.
3. Select your GitHub repository: `Shravya-B046/MEDICHAIN`.
4. Configure service settings:
   - **Root Directory:** `Backend`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Under **Environment Variables**, add:
   - `DATABASE_URL`: Your Neon PostgreSQL connection string:
     `postgresql://neondb_owner:<password>@ep-orange-cloud-b37154fa-pooler.c-4.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&connect_timeout=45`
   - `GEMINI_API_KEY`: Your Google AI Studio API key.
   - `CORS_ORIGINS`: `*` (or your Netlify/Vercel URL).
   - `ENVIRONMENT`: `production`
   - `DEBUG`: `False`
6. Click **Create Web Service**. Your live backend URL will be:  
   `https://<your-service-name>.onrender.com`

---

## 3. Deploying Frontend Online (e.g. Netlify / Vercel)

### A. Deploy via Netlify
1. Log in to [Netlify.com](https://netlify.com) and select **Add new site** -> **Import an existing project**.
2. Select your repository `Shravya-B046/MEDICHAIN`.
3. Set **Base directory** to `Frontend` (or root if using `netlify.toml`).
4. Set **Publish directory** to `Frontend`.
5. Under **Environment Variables** or `Frontend/js/api.js`:
   Set `window.MEDICHAIN_API_BASE` to your deployed backend URL:
   `https://<your-service-name>.onrender.com`
6. Click **Deploy Site**. Your live frontend URL will be:  
   `https://<your-site-name>.netlify.app`

### B. Deploy via Vercel
1. Log in to [Vercel.com](https://vercel.com) and import `Shravya-B046/MEDICHAIN`.
2. Set **Root Directory** to `Frontend`.
3. Click **Deploy**.

---

## 4. Local Team Development Guide

Each teammate can clone and run MEDICHAIN on their local machine without interfering with production:

### Prerequisites
- Python 3.10+ installed
- Modern Web Browser (Chrome, Firefox, Edge)

### Step 1: Clone the Repository
```bash
git clone https://github.com/Shravya-B046/MEDICHAIN.git
cd MEDICHAIN
```

### Step 2: Setup Backend
```bash
cd Backend

# Create and activate virtual environment (optional but recommended)
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env from template
cp .env.example .env
# Edit .env with your DATABASE_URL and GEMINI_API_KEY

# Start backend server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation will be live at: `http://localhost:8000/docs`

### Step 3: Start Frontend
In a new terminal window:
```bash
cd Frontend

# Start lightweight HTTP server:
python -m http.server 8081
```
Open your browser at: `http://localhost:8081/index.html`

---

## 5. Branching Strategy for Teammates

- `main`: Stable production release.
- `shravya_backend`: Core backend, database, and AI service integration.
- `Anushka_backend`: Emergency triage and resource services.
- `Riya_frontend`: UI layouts, styles, and dashboard views.
- `ashwini_frontend`: Document reporting and admin views.

**Workflow for new features:**
1. Pull latest changes: `git checkout main && git pull origin main`
2. Create your feature branch: `git checkout -b feature/your-feature-name`
3. Commit small, clear updates: `git commit -m "Add: description"`
4. Push and open a Pull Request (PR) into `main`.
