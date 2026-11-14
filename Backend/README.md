# MEDICHAIN — Backend API

Backend service for **MEDICHAIN: AI-Powered Intelligent Healthcare Coordination & Prediction Platform**, built with **FastAPI**, **Pydantic v2**, **SQLAlchemy 2.x**, **PostgreSQL**, and **Alembic**.

---

## Architecture Overview

```
Backend/
├── app/
│   ├── main.py             # FastAPI entrypoint, CORS configuration, router mounting, lifespan startup
│   ├── config.py           # Environment settings (Pydantic Settings)
│   ├── database.py         # SQLAlchemy 2.x synchronous engine & SessionLocal factory
│   ├── dependencies.py     # Request session dependency (get_db)
│   │
│   ├── models/             # SQLAlchemy ORM table definitions
│   │   ├── hospital.py     # hospitals table
│   │   ├── resource.py     # resources table (beds, ICU, staff)
│   │   ├── emergency.py    # emergencies table (EMG cases)
│   │   └── report.py       # report_audits table (privacy-compliant processing metadata)
│   │
│   ├── schemas/            # Pydantic v2 request and response contracts
│   │   ├── hospital.py
│   │   ├── resource.py
│   │   ├── emergency.py
│   │   ├── report.py
│   │   └── assistant.py
│   │
│   ├── routers/            # Feature endpoint routes (/api/...)
│   │   ├── hospitals.py    # CRUD for hospitals (/api/hospitals)
│   │   ├── resources.py    # Resource tables and summary (/api/resources)
│   │   ├── emergency.py    # Emergency coordination cases and metrics (/api/emergency)
│   │   ├── reports.py      # Temporary report processing (/api/reports/upload)
│   │   └── assistant.py    # AI Health Assistant chat (/api/assistant/chat)
│   │
│   └── services/           # Business logic & external integrations
│       ├── hospital_service.py   # Database queries for hospital administration
│       ├── resource_service.py   # Aggregation calculations for dashboard metrics
│       ├── emergency_service.py  # Emergency tracking and priority sorting
│       ├── report_service.py     # Temporary upload streaming, validation, immediate disk cleanup
│       └── ai_service.py         # Gemini API wrapper with medical safety synthetic fallback
│
├── alembic/                # Database migrations
│   ├── env.py              # Alembic runtime config
│   ├── script.py.mako      # Migration file template
│   └── versions/           # Migration revision history
│
├── uploads/                # Temporary processing directory (.gitignored, cleaned up after each request)
├── requirements.txt        # Pinned dependencies
├── .env.example            # Environment variables template
└── alembic.ini             # Alembic configuration
```

---

## Key Design Principles

1. **Synchronous SQLAlchemy 2.x Sessions**: Simple, robust session management via `SessionLocal` with clear transaction commit/rollback behavior.
2. **Temporary Report Processing**: Medical report uploads are handled strictly in `Backend/uploads/` (which is gitignored). Files are streamed, validated for allowed extensions (`.pdf`, `.png`, `.jpg`, `.jpeg`) and size (<= 10MB), processed for educational guidance, and **immediately deleted from the disk** in a `finally` block. Raw patient reports and medical text are **never permanently stored by default**.
3. **Environment Security**: All database credentials and the `GEMINI_API_KEY` are read exclusively from environment variables via `app/config.py`.
4. **Synthetic Demo Data**: The backend automatically pre-seeds realistic synthetic demonstration data on startup so that the entire platform is functional immediately even before live external feeds are connected.
5. **Clear Medical Safety Disclaimers**: Every response carries prominent educational disclaimers reminding users that the platform does not replace professional medical diagnosis or live emergency services (112 in India).

---

## Setup & Running Locally

### 1. Create a Virtual Environment

```bash
cd Backend
python -m venv venv

# Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Linux / macOS:
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` to configure your settings:
- `DATABASE_URL`: PostgreSQL connection string (defaults to SQLite fallback if PostgreSQL is not running locally).
- `GEMINI_API_KEY`: Your Google Gemini API key (optional; if left blank, high-quality synthetic demo guidance is used).
- `CORS_ORIGINS`: Allowed origins (defaults to frontend servers on ports 8080, 5500, 3000).

### 4. Database Migrations (Alembic)

```bash
alembic upgrade head
```

### 5. Start the Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Once running:
- **Interactive OpenAPI Documentation (Swagger UI)**: `http://localhost:8000/docs`
- **ReDoc API Documentation**: `http://localhost:8000/redoc`
- **Root Status**: `http://localhost:8000/`

---

## API Endpoints Reference

### 1. AI Health Assistant
- `POST /api/assistant/chat`: Submit general health questions. Returns AI explanation with medical disclaimer.

### 2. Hospital Resource Dashboard
- `GET /api/resources`: Tabular resource rows (General Beds, ICU Beds, Doctors, Ambulances).
- `GET /api/resources/summary`: Aggregated counts for the platform overview cards.
- `PUT /api/resources/{id}`: Update availability counts.

### 3. Emergency Coordination
- `GET /api/emergency`: List of emergency cases.
- `GET /api/emergency/summary`: Overview counts (active, dispatched, resolved).
- `GET /api/emergency/{case_id}`: Details for a specific emergency case.
- `POST /api/emergency`: Log a new emergency request.
- `PATCH /api/emergency/{case_id}/status`: Update case status or priority.

### 4. AI Preliminary Report Analysis
- `POST /api/reports/upload`: Multipart upload of medical report file (`.pdf`, `.png`, `.jpg`). Returns preliminary structured observations and doctor consultation questions, then purges the temporary file from disk.

### 5. Hospital Administration
- `GET /api/hospitals`: Directory of registered hospital facilities.
- `POST /api/hospitals`: Register a new hospital.
- `GET /api/hospitals/{id}`: Hospital facility details.
- `DELETE /api/hospitals/{id}`: Remove a hospital from the directory.

