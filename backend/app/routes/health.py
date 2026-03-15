"""Health check endpoint."""
from fastapi import APIRouter
from app.utils.aws_clients import get_opensearch_client
from app.config import get_settings

router = APIRouter()


@router.get("/health")
def health():
    s = get_settings()
    os_status = "unknown"
    try:
        client = get_opensearch_client()
        info = client.info()
        os_status = "ok"
    except Exception as e:
        os_status = f"error: {e}"

    return {
        "status": "ok",
        "region": s.aws_region,
        "opensearch": os_status,
        "embed_model": s.bedrock_embedding_model_id,
        "llm_model": s.bedrock_llm_model_id,
    }
