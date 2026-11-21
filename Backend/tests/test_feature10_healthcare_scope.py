import io
import os
import pytest
from PIL import Image

from app.services.ai_service import HEALTHCARE_ONLY_REJECTION_MESSAGE, UNCLEAR_MEDICINE_MESSAGE
from tests.test_all_modules import client


def create_dummy_image_bytes(color: str = "blue") -> bytes:
    """Helper to generate in-memory dummy JPEG bytes."""
    # Handle non-standard color names
    rgb_map = {
        "amber": (255, 191, 0),
        "silver": (192, 192, 192),
    }
    c = rgb_map.get(color, color)
    img = Image.new("RGB", (100, 100), color=c)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


# =====================================================================
# ACCEPTANCE TEST 1: Upload a paracetamol packaging image -> Accept & identify
# =====================================================================
def test_acceptance_1_paracetamol_image_accepted():
    img_bytes = create_dummy_image_bytes("white")
    response = client.post(
        "/api/assistant/upload",
        files={"file": ("paracetamol_packaging.jpg", io.BytesIO(img_bytes), "image/jpeg")},
        data={"message": "Please identify this medicine packaging"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_healthcare_related"] is True
    assert data["is_medicine_query"] is True
    assert data["identification_confidence"] == "high"
    assert "paracetamol" in data["reply"].lower() or "acetaminophen" in data["reply"].lower()
    assert "### 1. Medicine Name & Generic Composition" in data["reply"]


# =====================================================================
# ACCEPTANCE TEST 2: Upload a syrup bottle -> Accept & analyze
# =====================================================================
def test_acceptance_2_syrup_bottle_image_accepted():
    img_bytes = create_dummy_image_bytes("amber")
    response = client.post(
        "/api/assistant/upload",
        files={"file": ("cough_syrup_bottle.jpg", io.BytesIO(img_bytes), "image/jpeg")},
        data={"message": "What is this syrup used for?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_healthcare_related"] is True
    assert data["is_medicine_query"] is True
    assert "cough" in data["reply"].lower() or "syrup" in data["reply"].lower()


# =====================================================================
# ACCEPTANCE TEST 3: Upload a medical report -> Accept & process
# =====================================================================
def test_acceptance_3_medical_report_accepted():
    pdf_content = b"%PDF-1.4 Mock Laboratory Diagnostic Lipid Profile & Hemoglobin Report"
    response = client.post(
        "/api/reports/upload",
        files={"file": ("medical_diagnostic_report.pdf", io.BytesIO(pdf_content), "application/pdf")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Completed"
    assert data["temporary_file_cleaned"] is True
    assert len(data["key_observations"]) > 0


# =====================================================================
# ACCEPTANCE TEST 4: Upload a spoon -> Reject with short healthcare-only message
# =====================================================================
def test_acceptance_4_spoon_image_rejected():
    img_bytes = create_dummy_image_bytes("gray")
    # 1. Test assistant image upload
    response = client.post(
        "/api/assistant/upload",
        files={"file": ("metal_spoon.jpg", io.BytesIO(img_bytes), "image/jpeg")},
        data={"message": "What is this object?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_healthcare_related"] is False
    assert data["is_medicine_query"] is False
    assert data["identification_confidence"] == "rejected"
    assert data["reply"] == HEALTHCARE_ONLY_REJECTION_MESSAGE

    # 2. Test reports upload rejection for unrelated image
    rep_resp = client.post(
        "/api/reports/upload",
        files={"file": ("spoon.jpg", io.BytesIO(img_bytes), "image/jpeg")},
    )
    assert rep_resp.status_code == 400
    assert rep_resp.json()["detail"] == HEALTHCARE_ONLY_REJECTION_MESSAGE


# =====================================================================
# ACCEPTANCE TEST 5: Upload a chair -> Reject
# =====================================================================
def test_acceptance_5_chair_image_rejected():
    img_bytes = create_dummy_image_bytes("brown")
    response = client.post(
        "/api/assistant/upload",
        files={"file": ("office_chair.jpg", io.BytesIO(img_bytes), "image/jpeg")},
        data={"message": "Can you describe this item?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_healthcare_related"] is False
    assert data["reply"] == HEALTHCARE_ONLY_REJECTION_MESSAGE

    # Reports upload rejection
    rep_resp = client.post(
        "/api/reports/upload",
        files={"file": ("wooden_chair.png", io.BytesIO(img_bytes), "image/png")},
    )
    assert rep_resp.status_code == 400
    assert rep_resp.json()["detail"] == HEALTHCARE_ONLY_REJECTION_MESSAGE


# =====================================================================
# ACCEPTANCE TEST 6: Ask "What is the capital of India?" -> Redirect to healthcare topics
# =====================================================================
def test_acceptance_6_unrelated_text_redirected():
    response = client.post(
        "/api/assistant/chat",
        json={"message": "What is the capital of India?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_healthcare_related"] is False
    assert data["reply"] == HEALTHCARE_ONLY_REJECTION_MESSAGE

    # Additional unrelated topics
    for unrelated_q in [
        "How to bake a chocolate cake?",
        "Who won the cricket match yesterday?",
        "Write python code to reverse a linked list",
        "Which is the best luxury car to buy?",
    ]:
        res = client.post("/api/assistant/chat", json={"message": unrelated_q})
        assert res.status_code == 200
        assert res.json()["is_healthcare_related"] is False
        assert res.json()["reply"] == HEALTHCARE_ONLY_REJECTION_MESSAGE


# =====================================================================
# ACCEPTANCE TEST 7: Ask "What is paracetamol used for?" -> Accept
# =====================================================================
def test_acceptance_7_paracetamol_query_accepted():
    response = client.post(
        "/api/assistant/chat",
        json={"message": "What is paracetamol used for?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_healthcare_related"] is True
    assert data["is_medicine_query"] is True
    assert "paracetamol" in data["reply"].lower() or "acetaminophen" in data["reply"].lower()
    assert "fever" in data["reply"].lower() or "pain" in data["reply"].lower()


# =====================================================================
# ACCEPTANCE TEST 8: Ask "What are the side effects of this medicine?" after identification -> Accept
# =====================================================================
def test_acceptance_8_followup_side_effects_accepted():
    history = [
        {"role": "user", "content": "Please identify this medicine: Paracetamol 650mg"},
        {
            "role": "assistant",
            "content": "### 1. Medicine Name: Paracetamol (Acetaminophen)\nCommon uses include fever reduction and pain relief.",
        },
    ]
    response = client.post(
        "/api/assistant/chat",
        json={
            "message": "What are the side effects of this medicine?",
            "history": history,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_healthcare_related"] is True
    assert data["is_medicine_query"] is True
    assert "side effect" in data["reply"].lower() or "liver" in data["reply"].lower() or "nausea" in data["reply"].lower()


def test_acceptance_8_followup_unrelated_rejected():
    """Verify that a user CANNOT bypass healthcare restrictions via follow-up messages."""
    history = [
        {"role": "user", "content": "What is Paracetamol used for?"},
        {"role": "assistant", "content": "Paracetamol is used for pain relief and fever."},
    ]
    response = client.post(
        "/api/assistant/chat",
        json={
            "message": "By the way, what is the capital of France?",
            "history": history,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_healthcare_related"] is False
    assert data["reply"] == HEALTHCARE_ONLY_REJECTION_MESSAGE


# =====================================================================
# ACCEPTANCE TEST 9: Upload an unclear medicine image -> Ask for clearer image; do not guess
# =====================================================================
def test_acceptance_9_unclear_medicine_image():
    img_bytes = create_dummy_image_bytes("gray")
    response = client.post(
        "/api/assistant/upload",
        files={"file": ("unclear_blurry_tablet_strip.jpg", io.BytesIO(img_bytes), "image/jpeg")},
        data={"message": "Can you identify this pill?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_healthcare_related"] is True
    assert data["identification_confidence"] == "unclear"
    assert "unclear or partially obscured" in data["reply"]
    assert "upload a clearer" in data["reply"] or "type the medicine name" in data["reply"]
    # Verify it does not guess a random drug name
    assert "I have diagnosed" not in data["reply"]


# =====================================================================
# ACCEPTANCE TEST 10: Upload a medical device -> Accept for healthcare analysis
# =====================================================================
def test_acceptance_10_medical_device_accepted():
    img_bytes = create_dummy_image_bytes("silver")
    response = client.post(
        "/api/assistant/upload",
        files={"file": ("digital_blood_pressure_monitor.jpg", io.BytesIO(img_bytes), "image/jpeg")},
        data={"message": "What is this medical device and how do I use it?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_healthcare_related"] is True
    assert data["identification_confidence"] == "high"
    assert "blood pressure" in data["reply"].lower() or "device" in data["reply"].lower()
    assert "normal" in data["reply"].lower() or "mmhg" in data["reply"].lower()
