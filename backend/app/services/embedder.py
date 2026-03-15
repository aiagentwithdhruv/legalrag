"""Bedrock embedding — supports Cohere Embed v3, Titan V2, and Euri (OpenAI-compatible)."""
import json
from typing import Generator
from app.utils.aws_clients import get_bedrock
from app.utils.logger import get_logger
from app.config import get_settings

logger = get_logger(__name__)

BATCH_SIZE = 96  # Cohere / OpenAI support up to 96-2048 texts per batch


def _is_cohere(model_id: str) -> bool:
    return "cohere" in model_id.lower()


def _get_euri_client():
    """Get OpenAI client pointed at Euri base URL."""
    from openai import OpenAI
    s = get_settings()
    return OpenAI(api_key=s.euri_api_key, base_url=s.euri_base_url)


def _embed_via_euri(texts: list[str]) -> list[list[float]]:
    """Embed texts using Euri API (OpenAI-compatible)."""
    s = get_settings()
    client = _get_euri_client()
    resp = client.embeddings.create(model=s.euri_embedding_model, input=texts)
    return [item.embedding for item in sorted(resp.data, key=lambda x: x.index)]


def embed_text(text: str, input_type: str = "search_query") -> list[float]:
    """Embed a single text string.

    input_type: 'search_query' for user queries, 'search_document' for doc chunks.
    """
    s = get_settings()
    if s.use_euri:
        try:
            return _embed_via_euri([text])[0]
        except Exception as e:
            logger.error(f"Euri embed_text failed: {e}")
            return [0.0] * s.embed_dimensions

    bedrock = get_bedrock()
    model_id = s.bedrock_embedding_model_id
    try:
        if _is_cohere(model_id):
            body = json.dumps({"texts": [text[:2048]], "input_type": input_type, "truncate": "END"})
            response = bedrock.invoke_model(modelId=model_id, body=body)
            return json.loads(response["body"].read())["embeddings"][0]
        else:
            body = json.dumps({"inputText": text[:8000], "dimensions": s.embed_dimensions, "normalize": s.embed_normalize})
            response = bedrock.invoke_model(modelId=model_id, body=body)
            return json.loads(response["body"].read())["embedding"]
    except Exception as e:
        logger.error(f"embed_text failed: {e}")
        return [0.0] * s.embed_dimensions


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts. Returns embeddings in same order."""
    s = get_settings()
    if s.use_euri:
        try:
            return _embed_via_euri(texts)
        except Exception as e:
            logger.error(f"Euri embed_batch failed: {e}")
            return [[0.0] * s.embed_dimensions] * len(texts)

    bedrock = get_bedrock()
    model_id = s.bedrock_embedding_model_id
    try:
        if _is_cohere(model_id):
            body = json.dumps({"texts": [t[:2048] for t in texts], "input_type": "search_document", "truncate": "END"})
            response = bedrock.invoke_model(modelId=model_id, body=body)
            return json.loads(response["body"].read())["embeddings"]
        else:
            embeddings = []
            for text in texts:
                body = json.dumps({"inputText": text[:8000], "dimensions": s.embed_dimensions, "normalize": s.embed_normalize})
                response = bedrock.invoke_model(modelId=model_id, body=body)
                embeddings.append(json.loads(response["body"].read())["embedding"])
            return embeddings
    except Exception as e:
        logger.error(f"Embedding batch failed: {e}")
        return [[0.0] * s.embed_dimensions] * len(texts)


def embed_chunks_in_batches(texts: list[str]) -> Generator[list[list[float]], None, None]:
    """Yield embedding batches for large doc sets."""
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        logger.info(f"Embedding batch {i // BATCH_SIZE + 1}: {len(batch)} chunks")
        yield embed_batch(batch)
