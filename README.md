# MEDICHAIN
AI-Powered Intelligent Healthcare Coordination & Prediction Platform

MEDICHAIN is an AI-powered healthcare coordination platform designed to improve access to healthcare information, hospital resource visibility, emergency coordination, and preliminary medical report understanding.

# Phase 1 – Core Modules

1. AI Health Assistant – Provides general health information and guidance.
2. Hospital Resource Dashboard – Displays hospital bed availability, medicine stock, equipment status, and other resources.
3. Emergency Coordination – Connects emergency requests with hospitals and ambulance availability.
4. AI Preliminary Report Analysis – Helps users understand information extracted from uploaded medical reports.

# Technology Stack

- Frontend: HTML5, CSS3, Vanilla JavaScript (no frameworks or build tools required)
- Backend: Python, FastAPI (planned)
- Database: PostgreSQL (planned)
- AI Integration: Gemini API (planned)
- Version Control: Git and GitHub

# Running the Frontend

The frontend requires no build step or package installation.
Open `Frontend/index.html` directly in a web browser, or serve the `Frontend` directory with any static file server:

```
python -m http.server 8080
```

Then visit `http://localhost:8080` in your browser.

> **Note:** All data displayed in the current frontend prototype is demonstration data only.
> No live hospital data, real emergency dispatch, or AI analysis is performed until the backend is connected.

# Disclaimer

MEDICHAIN provides informational assistance and is not a substitute for professional medical diagnosis or treatment.
