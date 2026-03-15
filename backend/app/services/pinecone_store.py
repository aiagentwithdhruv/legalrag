"""Pinecone vector store — drop-in replacement for OpenSearch when VECTOR_DB=pinecone."""
from __future__ import annotations
from functools import lru_cache
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


@lru_cache
def _get_index():
    from pinecone import Pinecone
    s = get_settings()
    pc = Pinecone(api_key=s.pinecone_api_key)
    return pc.Index(s.pinecone_index_name)


def upsert_chunks(chunks, embeddings: list[list[float]]) -> dict:
    """Upsert child chunks into Pinecone. Returns {indexed, skipped, updated}."""
    index = _get_index()
    vectors = []
    child_idx = 0

    for chunk in chunks:
        if chunk.is_parent:
            continue
        emb = embeddings[child_idx]
        child_idx += 1

        meta = {**chunk.metadata}
        # Pinecone metadata values must be str/int/float/bool/list[str]
        meta["text"] = chunk.text[:4096]
        meta["chunk_id"] = chunk.chunk_id
        meta["doc_id"] = chunk.doc_id
        meta["parent_chunk_id"] = chunk.parent_chunk_id or ""
        meta["is_parent"] = False
        # Flatten list fields
        if isinstance(meta.get("entities"), list):
            meta["entities"] = meta["entities"][:50]  # keep top 50

        vectors.append({"id": chunk.chunk_id, "values": emb, "metadata": meta})

    if vectors:
        # Pinecone max 100 vectors per upsert
        for i in range(0, len(vectors), 100):
            index.upsert(vectors=vectors[i:i+100])

    logger.info(f"Pinecone upserted {len(vectors)} vectors")
    return {"indexed": len(vectors), "skipped": 0, "updated": 0}


def hybrid_search(
    query_text: str,
    query_vector: list[float],
    department: str = None,
    clearance_level: str = None,
    doc_type: str = None,
    k: int = 15,
) -> list[dict]:
    """Vector search in Pinecone with optional metadata filters."""
    index = _get_index()

    filters = {"is_parent": {"$eq": False}}
    if department:
        filters["department"] = {"$eq": department}
    if clearance_level:
        filters["clearance_level"] = {"$eq": clearance_level}
    if doc_type:
        filters["doc_type"] = {"$eq": doc_type}

    results = index.query(
        vector=query_vector,
        top_k=k,
        include_metadata=True,
        filter=filters,
    )

    chunks = []
    for match in results.get("matches", []):
        meta = dict(match["metadata"])
        text = meta.pop("text", "")
        chunk_id = meta.pop("chunk_id", match["id"])
        doc_id = meta.pop("doc_id", "")
        parent_chunk_id = meta.pop("parent_chunk_id", "")
        meta.pop("is_parent", None)

        chunks.append({
            "chunk_id": chunk_id,
            "doc_id": doc_id,
            "parent_chunk_id": parent_chunk_id,
            "is_parent": False,
            "text": text,
            "metadata": meta,
            "_score": match["score"],
        })

    logger.info(f"Pinecone retrieved {len(chunks)} chunks")
    return chunks


def enrich_with_parents(child_chunks: list[dict]) -> list[dict]:
    """Pinecone has no parent chunks — return child chunks as-is."""
    return child_chunks
