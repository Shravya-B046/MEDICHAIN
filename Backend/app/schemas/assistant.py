from typing import Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000, description="User health question")
    context: Optional[str] = Field(None, max_length=200, description="Optional conversational context")


class ChatResponse(BaseModel):
    reply: str
    source: str = Field(..., description="'gemini_api' or 'synthetic_demo'")
    disclaimer: str = (
        "This assistant provides general informational guidance only and is not a substitute "
        "for professional medical diagnosis, advice, or emergency services."
    )

