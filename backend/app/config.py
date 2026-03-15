"""Centralized configuration — all values from environment variables."""
from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path

# .env lives one level up (LegalRAG/.env), resolve relative to this file
_ENV_FILE = Path(__file__).parent.parent.parent / ".env"


class Settings(BaseSettings):
    # AWS
    aws_region: str = "us-east-1"
    aws_account_id: str = ""

    # S3
    s3_bucket_name: str = "legal-rag-documents"

    # OpenSearch
    opensearch_endpoint: str = ""
    opensearch_index: str = "legal-docs"
    opensearch_master_user: str = "admin"
    opensearch_master_password: str = ""

    # Bedrock — Models
    bedrock_embedding_model_id: str = "cohere.embed-english-v3"
    bedrock_llm_model_id: str = "apac.amazon.nova-lite-v1:0"
    bedrock_llm_smart_model_id: str = "apac.amazon.nova-pro-v1:0"
    bedrock_llm_long_context_model_id: str = "apac.amazon.nova-pro-v1:0"

    # Embedding
    embed_dimensions: int = 1536
    embed_normalize: bool = True

    # Retrieval
    top_k_retrieve: int = 15
    top_n_final: int = 5
    semantic_weight: float = 0.6
    keyword_weight: float = 0.4

    # Cache
    elasticache_url: str = "redis://localhost:6379"
    cache_enabled: bool = True
    cache_similarity_threshold: float = 0.95
    cache_ttl_seconds: int = 3600

    # DynamoDB
    dedup_table: str = "legalrag-dedup"
    sessions_table: str = "legalrag-sessions"

    # Generation
    max_tokens: int = 2048
    temperature: float = 0.1

    # Vector DB — "opensearch" or "pinecone"
    vector_db: str = "opensearch"
    pinecone_api_key: str = ""
    pinecone_index_name: str = "legalrag"

    # Euri API (OpenAI-compatible fallback for embeddings + LLM)
    use_euri: bool = False
    euri_api_key: str = ""
    euri_base_url: str = "https://api.euron.one/api/v1/euri"
    euri_embedding_model: str = "text-embedding-3-small"
    euri_llm_model: str = "gpt-4o-mini"

    # App
    log_level: str = "INFO"
    enable_guardrails: bool = False

    model_config = {"env_file": str(_ENV_FILE), "case_sensitive": False, "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
