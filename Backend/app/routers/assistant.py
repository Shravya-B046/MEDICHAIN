from fastapi import APIRouter
from app.schemas.assistant import ChatRequest, ChatResponse
from app.services.ai_service import ai_service

router = APIRouter(prefix="/api/assistant", tags=["AI Health Assistant"])


@router.post("/chat", response_model=ChatResponse, summary="Send health question to AI assistant")
def chat_with_assistant(request: ChatRequest):
    """
    Submits a user health inquiry to the AI Health Assistant.
    Uses Gemini API when configured in backend environment; otherwise provides
    synthetic medical reference responses with clear safety disclaimers.
    """
    reply_text, source = ai_service.get_health_guidance(question=request.message)
    return ChatResponse(
        reply=reply_text,
        source=source,
    )

