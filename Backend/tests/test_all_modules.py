import io
import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base
from app.dependencies import get_db
from app.main import app

# Setup in-memory test database using StaticPool so all connections share the same memory DB
TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

# Create tables in test db
Base.metadata.create_all(bind=test_engine)

client = TestClient(app)


@pytest.fixture(autouse=True)
def run_around_tests():
    # Setup fresh seed data before each test
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    from app.services.hospital_service import seed_sample_hospitals
    from app.services.resource_service import seed_default_resources
    from app.services.emergency_service import seed_default_emergencies

    db = TestingSessionLocal()
    seed_sample_hospitals(db)
    seed_default_resources(db)
    seed_default_emergencies(db)
    db.close()

    yield


def test_root_endpoint():
    """Verify root endpoint and documentation."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["platform"] == "MEDICHAIN"
    assert len(data["modules"]) == 5


def test_health_check_endpoint():
    """Verify health endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


# =====================================================================
# Module 1: AI Health Assistant Tests
# =====================================================================
def test_ai_health_assistant_dehydration():
    """Verify dehydration question produces relevant guidance with disclaimer."""
    response = client.post(
        "/api/assistant/chat",
        json={"message": "What are the common signs of dehydration?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data
    assert "dehydration" in data["reply"].lower() or "fluids" in data["reply"].lower()
    assert "disclaimer" in data
    assert "not a substitute" in data["disclaimer"].lower()


def test_ai_health_assistant_general():
    """Verify general query handling."""
    response = client.post(
        "/api/assistant/chat",
        json={"message": "Why is regular sleep important?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["reply"]) > 20
    assert data["source"] in ["synthetic_demo", "gemini_api"]


# =====================================================================
# Module 2: Hospital Resource Dashboard Tests
# =====================================================================
def test_resource_list_and_summary():
    """Verify hospital resources and overview counts."""
    # List endpoint
    res_list = client.get("/api/resources")
    assert res_list.status_code == 200
    items = res_list.json()
    assert len(items) >= 4
    types = [i["resource_type"] for i in items]
    assert "General Beds" in types
    assert "ICU Beds" in types

    # Summary endpoint
    res_summary = client.get("/api/resources/summary")
    assert res_summary.status_code == 200
    summary = res_summary.json()
    assert summary["available_beds"] > 0
    assert summary["icu_beds"] > 0
    assert summary["is_demo_data"] is True


def test_resource_update():
    """Verify updating a resource count."""
    res_list = client.get("/api/resources").json()
    first_id = res_list[0]["id"]

    update_resp = client.put(
        f"/api/resources/{first_id}",
        json={"available": 115, "occupied": 35},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["available"] == 115


# =====================================================================
# Module 3: Emergency Coordination Tests
# =====================================================================
def test_emergency_cases_and_summary():
    """Verify emergency tracking and metrics."""
    # List cases
    cases_resp = client.get("/api/emergency")
    assert cases_resp.status_code == 200
    cases = cases_resp.json()
    assert len(cases) >= 4
    case_ids = [c["case_id"] for c in cases]
    assert "EMG001" in case_ids

    # Summary metrics
    summary_resp = client.get("/api/emergency/summary")
    assert summary_resp.status_code == 200
    data = summary_resp.json()
    assert data["total_emergencies"] >= 4
    assert data["active_emergencies"] >= 1
    assert data["is_demo_data"] is True


def test_emergency_create_and_status_patch():
    """Verify logging a new emergency and updating status."""
    new_case = {
        "case_id": "EMG999",
        "emergency_type": "Respiratory Distress",
        "location": "Kankanady",
        "hospital_name": "City Hospital",
        "priority": "Critical",
        "status": "In Progress",
    }
    create_resp = client.post("/api/emergency", json=new_case)
    assert create_resp.status_code == 201
    assert create_resp.json()["case_id"] == "EMG999"

    # Update status to Resolved
    patch_resp = client.patch(
        "/api/emergency/EMG999/status",
        json={"status": "Resolved", "priority": "Medium"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "Resolved"


# =====================================================================
# Module 4: AI Preliminary Report Analysis Tests
# =====================================================================
def test_report_upload_and_temporary_cleanup():
    """Verify medical report upload, analysis generation, and temporary file deletion."""
    test_pdf_content = b"%PDF-1.4 Mock Laboratory Complete Blood Count Test Report"
    upload_dir = settings.upload_dir_path

    # Initial file count in uploads
    initial_files = list(upload_dir.glob("temp_*"))

    response = client.post(
        "/api/reports/upload",
        files={"file": ("cbc_test_report.pdf", io.BytesIO(test_pdf_content), "application/pdf")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "cbc_test_report.pdf"
    assert data["status"] == "Completed"
    assert data["temporary_file_cleaned"] is True
    assert len(data["key_observations"]) > 0
    assert len(data["suggested_questions_for_doctor"]) > 0

    # Guarantee no lingering temp files left in uploads dir
    final_files = list(upload_dir.glob("temp_*"))
    assert len(final_files) == len(initial_files)


def test_report_upload_unsupported_format_rejected():
    """Verify rejection of invalid file extensions (security validation)."""
    response = client.post(
        "/api/reports/upload",
        files={"file": ("malicious.exe", io.BytesIO(b"fake-binary"), "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]


# =====================================================================
# Module 5: Hospital Administration (Admin Panel) Tests
# =====================================================================
def test_hospital_crud():
    """Verify hospital directory listing, registration, and deletion."""
    # List initial sample
    hospitals = client.get("/api/hospitals").json()
    assert len(hospitals) >= 1
    assert hospitals[0]["name"] == "City Hospital"

    # Add new hospital
    new_hosp = {
        "name": "District General Hospital",
        "location": "Udupi",
        "contact": "0820-2520000",
    }
    create_resp = client.post("/api/hospitals", json=new_hosp)
    assert create_resp.status_code == 201
    created = create_resp.json()
    hosp_id = created["id"]
    assert created["name"] == "District General Hospital"

    # Delete hospital
    del_resp = client.delete(f"/api/hospitals/{hosp_id}")
    assert del_resp.status_code == 200

    # Verify not found
    get_resp = client.get(f"/api/hospitals/{hosp_id}")
    assert get_resp.status_code == 404
