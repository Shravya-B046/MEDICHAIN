from typing import List, Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'/'model'")
    content: str = Field(..., min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(default="", max_length=2000, description="User health or medicine question")
    context: Optional[str] = Field(None, max_length=500, description="Optional conversational context")
    history: Optional[List[ChatMessage]] = Field(default=[], description="Multi-turn conversation history")
    language: Optional[str] = Field(default="en", description="Target response language: en (English), kn (Kannada), hi (Hindi), mr (Marathi)")
    image_data: Optional[str] = Field(None, description="Base64 encoded image or document (data:image/...;base64,... or raw base64)")
    image_mime: Optional[str] = Field(None, description="MIME type of uploaded image (image/png, image/jpeg, etc.)")
    image_filename: Optional[str] = Field(None, description="Original filename of uploaded image")


class ChatResponse(BaseModel):
    reply: str = Field(..., description="Structured medical guidance or medicine explanation")
    source: str = Field(..., description="'gemini_api' | 'verified_medical_kb' | 'synthetic_demo' | 'domain_guardrail'")
    is_emergency: bool = Field(default=False, description="Whether query indicates acute emergency red flags")
    is_medicine_query: bool = Field(default=False, description="Whether query was classified as a medicine inquiry")
    is_healthcare_related: bool = Field(default=True, description="Whether input strictly pertains to the healthcare/medical domain")
    identification_confidence: Optional[str] = Field(None, description="'high' | 'medium' | 'unclear' | 'rejected'")
    detected_entity: Optional[str] = Field(None, description="Identified medicine name, device type, or clinical document")
    verified_sources: List[str] = Field(default_factory=list, description="Authoritative reference sources (WHO, MedlinePlus, FDA, ICMR, etc.)")
    disclaimer: str = (
        "MEDICHAIN provides AI-assisted health information and preliminary explanations. "
        "It does not replace professional medical diagnosis, treatment, or consultation, "
        "and is not a substitute for direct physician care."
    )


