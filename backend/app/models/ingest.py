"""Pydantic models for ingestion API."""
from pydantic import BaseModel
from typing import Literal, Optional


class IngestRequest(BaseModel):
    s3_key: str
    filename: str
    doc_type: Literal["contract", "policy", "regulation", "case_law", "document"] = "document"
    department: str = "general"
    clearance_level: Literal["public", "internal", "confidential"] = "internal"


class IngestResponse(BaseModel):
    doc_id: str
    status: Literal["indexed", "skipped", "failed"]
    message: str
    chunks_indexed: int = 0
