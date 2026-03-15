"""Pydantic models for query API."""
from pydantic import BaseModel
from typing import Optional


class QueryRequest(BaseModel):
    query: str
    session_id: str = "default"
    department: str = ""
    clearance_level: str = ""
    doc_type: str = ""
    use_smart_model: bool = False  # True = Claude Sonnet 4.6, False = Claude Haiku 4.5


class UploadUrlRequest(BaseModel):
    filename: str
    content_type: str = "application/pdf"
