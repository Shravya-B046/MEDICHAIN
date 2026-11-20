from fastapi import APIRouter
from app.schemas.assistant import ChatRequest, ChatResponse
from app.services.ai_service import ai_service

router = APIRouter(prefix="/api/assistant", tags=["AI Health Assistant"])


@router.post("/chat", response_model=ChatResponse, summary="Send health or medicine question to AI assistant")
def chat_with_assistant(request: ChatRequest):
    """
    Submits a user health or medication inquiry to the MEDICHAIN AI Health Assistant.
    Adheres strictly to WHO, MedlinePlus, ICMR, and FDA healthcare information standards.
    Supports multi-turn conversation history, structured 8-part medicine information,
    emergency red-flag triage, and zero-hallucination guardrails.
    """
    history_dicts = [h.model_dump() for h in request.history] if request.history else []
    reply_text, source, is_emergency, is_medicine, sources = ai_service.get_health_guidance(
        question=request.message,
        history=history_dicts,
        context=request.context,
        language=request.language or "en",
    )

    return ChatResponse(
        reply=reply_text,
        source=source,
        is_emergency=is_emergency,
        is_medicine_query=is_medicine,
        verified_sources=sources,
    )
