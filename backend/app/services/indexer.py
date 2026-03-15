"""Vector store indexing — routes to OpenSearch or Pinecone based on VECTOR_DB config."""
import hashlib
from app.utils.logger import get_logger
from app.config import get_settings
from app.services.chunker import Chunk

logger = get_logger(__name__)


def bulk_upsert(chunks: list[Chunk], embeddings: list[list[float]]) -> dict:
    """Route to Pinecone or OpenSearch based on VECTOR_DB setting."""
    s = get_settings()
    if s.vector_db == "pinecone":
        from app.services.pinecone_store import upsert_chunks
        return upsert_chunks(chunks, embeddings)
    return _opensearch_upsert(chunks, embeddings)


def delete_doc(doc_id: str) -> int:
    """Delete all chunks for a document."""
    s = get_settings()
    if s.vector_db == "pinecone":
        from app.services.pinecone_store import _get_index
        index = _get_index()
        index.delete(filter={"doc_id": {"$eq": doc_id}})
        return 0  # Pinecone doesn't return deleted count easily
    return _opensearch_delete(doc_id)


def _chunk_exists(client, index: str, chunk_id: str, text_hash: str) -> bool:
    """Check if chunk already exists with same content."""
    try:
        resp = client.get(index=index, id=chunk_id)
        existing_hash = resp["_source"].get("metadata", {}).get("text_hash", "")
        return existing_hash == text_hash
    except Exception:
        return False


def _opensearch_upsert(chunks: list[Chunk], embeddings: list[list[float]]) -> dict:
    """
    Bulk upsert chunks to OpenSearch with deduplication.
    Only child chunks are embedded (parents stored as context).
    Returns {"indexed": N, "skipped": N, "updated": N}
    """
    from app.utils.aws_clients import get_opensearch_client
    s = get_settings()
    client = get_opensearch_client()
    index = s.opensearch_index

    actions = []
    stats = {"indexed": 0, "skipped": 0, "updated": 0}

    embed_idx = 0
    for chunk in chunks:
        text_hash = hashlib.md5(chunk.text.encode()).hexdigest()

        if _chunk_exists(client, index, chunk.chunk_id, text_hash):
            stats["skipped"] += 1
            if not chunk.is_parent:
                embed_idx += 1
            continue

        doc = {
            "chunk_id":        chunk.chunk_id,
            "doc_id":          chunk.doc_id,
            "parent_chunk_id": chunk.parent_chunk_id,
            "is_parent":       chunk.is_parent,
            "text":            chunk.text,
            "metadata": {
                **chunk.metadata,
                "text_hash": text_hash,
                "citation_id": f"{chunk.doc_id}:p{chunk.page_number}:{chunk.chunk_id[:8]}",
            },
        }

        # Only child chunks get embeddings
        if not chunk.is_parent:
            if embed_idx < len(embeddings):
                doc["embedding"] = embeddings[embed_idx]
                embed_idx += 1
        else:
            # Parents: store a zero vector (won't be retrieved via kNN directly)
            doc["embedding"] = [0.0] * s.embed_dimensions

        actions.append({"index": {"_index": index, "_id": chunk.chunk_id}})
        actions.append(doc)

        if chunk.chunk_id in [c.chunk_id for c in chunks if c.chunk_id == chunk.chunk_id]:
            stats["indexed"] += 1

    if actions:
        response = client.bulk(body=actions)
        errors = [item for item in response.get("items", []) if item.get("index", {}).get("error")]
        if errors:
            logger.error(f"Bulk index errors: {errors[:3]}")
        else:
            logger.info(f"Bulk indexed {len(actions) // 2} chunks")

    return stats


def _opensearch_delete(doc_id: str) -> int:
    """Delete all chunks for a document from OpenSearch."""
    from app.utils.aws_clients import get_opensearch_client
    s = get_settings()
    client = get_opensearch_client()
    response = client.delete_by_query(
        index=s.opensearch_index,
        body={"query": {"term": {"doc_id": doc_id}}},
    )
    deleted = response.get("deleted", 0)
    logger.info(f"Deleted {deleted} chunks for doc_id={doc_id}")
    return deleted
