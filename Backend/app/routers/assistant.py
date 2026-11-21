import base64
import json
import logging
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile
from app.schemas.assistant import ChatRequest, ChatResponse
from app.services.ai_service import ai_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/assistant", tags=["AI Health Assistant"])


def _decode_base64_image(data_str: str) -> tuple[bytes, str]:
    """Helper to parse raw base64 or Data URI scheme base64 strings."""
    mime = "image/jpeg"
    clean_b64 = data_str.strip()
    if "," in clean_b64 and clean_b64.startswith("data:"):
        header, body = clean_b64.split(",", 1)
        clean_b64 = body.strip()
        if ";" in header:
            mime = header.split(";", 1)[0].replace("data:", "").strip()

    decoded_bytes = base64.b64decode(clean_b64)
    return decoded_bytes, mime


@router.post("/chat", response_model=ChatResponse, summary="Send health or medicine question to AI assistant")
def chat_with_assistant(request: ChatRequest):
    """
    Submits a user health or medication inquiry to the MEDICHAIN AI Health Assistant.
    Adheres strictly to WHO, MedlinePlus, ICMR, and FDA healthcare information standards.
    Strictly validates the input domain to ensure healthcare-only operation.
    Supports multi-turn conversation history, structured 8-part medicine information,
    emergency red-flag triage, and optional base64 image analysis.
    """
    history_dicts = [h.model_dump() for h in request.history] if request.history else []

    image_bytes = None
    image_mime = request.image_mime or "image/jpeg"

    if request.image_data:
        try:
            image_bytes, detected_mime = _decode_base64_image(request.image_data)
            if not request.image_mime:
                image_mime = detected_mime
        except Exception as e:
            logger.warning(f"Failed to decode base64 image in chat: {e}")

    (
        reply_text,
        source,
        is_emergency,
        is_medicine,
        is_healthcare,
        confidence,
        detected_entity,
        sources,
    ) = ai_service.get_health_guidance(
        question=request.message,
        history=history_dicts,
        context=request.context,
        image_bytes=image_bytes,
        image_mime=image_mime,
        image_filename=request.image_filename,
        language=request.language or "en",
    )

    return ChatResponse(
        reply=reply_text,
        source=source,
        is_emergency=is_emergency,
        is_medicine_query=is_medicine,
        is_healthcare_related=is_healthcare,
        identification_confidence=confidence,
        detected_entity=detected_entity,
        verified_sources=sources,
    )


@router.post("/upload", response_model=ChatResponse, summary="Upload medical image or document to AI assistant")
async def upload_assistant_image(
    file: UploadFile = File(..., description="Uploaded medical image or document (PNG, JPG, PDF)"),
    message: Optional[str] = Form(default=""),
    history: Optional[str] = Form(default="[]"),
    context: Optional[str] = Form(default=None),
    language: Optional[str] = Form(default="en"),
):
    """
    Uploads a medicine package, syrup bottle, medical device, prescription, or healthcare document.
    Strictly validates that the upload is healthcare-related. Unrelated images (spoons, chairs, etc.)
    are rejected without entering the medicine identification pipeline.
    """
    try:
        file_bytes = file.file.read()
        if not file_bytes:
            file.file.seek(0)
            file_bytes = file.file.read()
    except Exception:
        file_bytes = await file.read()
    mime = file.content_type or "image/jpeg"
    filename = file.filename or "upload.jpg"

    # Parse history if provided as JSON string
    history_dicts = []
    if history:
        try:
            history_dicts = json.loads(history)
            if not isinstance(history_dicts, list):
                history_dicts = []
        except Exception:
            history_dicts = []

    (
        reply_text,
        source,
        is_emergency,
        is_medicine,
        is_healthcare,
        confidence,
        detected_entity,
        sources,
    ) = ai_service.get_health_guidance(
        question=message or "",
        history=history_dicts,
        context=context,
        image_bytes=file_bytes,
        image_mime=mime,
        image_filename=filename,
        language=language or "en",
    )

    return ChatResponse(
        reply=reply_text,
        source=source,
        is_emergency=is_emergency,
        is_medicine_query=is_medicine,
        is_healthcare_related=is_healthcare,
        identification_confidence=confidence,
        detected_entity=detected_entity,
        verified_sources=sources,
    )
