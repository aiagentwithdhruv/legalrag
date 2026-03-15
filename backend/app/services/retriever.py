"""Hybrid retrieval — routes to Pinecone or OpenSearch based on VECTOR_DB config."""
from app.utils.logger import get_logger
from app.config import get_settings

logger = get_logger(__name__)


def hybrid_search(
    query_text: str,
    query_vector: list[float],
    department: str = "",
    clearance_level: str = "",
    doc_type: str = "",
    k: int = 15,
) -> list[dict]:
    """
    Hybrid BM25 + kNN search with optional metadata filters.
    Routes to Pinecone (vector-only) or OpenSearch (BM25 + kNN) based on VECTOR_DB.
    """
    s = get_settings()
    if s.vector_db == "pinecone":
        from app.services.pinecone_store import hybrid_search as pinecone_search
        return pinecone_search(query_text, query_vector, department, clearance_level, doc_type, k)

    from app.utils.aws_clients import get_opensearch_client
    client = get_opensearch_client()

    # Build metadata filters
    filters = [{"term": {"is_parent": False}}]  # only retrieve child chunks
    if department:
        filters.append({"term": {"metadata.department": department}})
    if clearance_level:
        filters.append({"term": {"metadata.clearance_level": clearance_level}})
    if doc_type:
        filters.append({"term": {"metadata.doc_type": doc_type}})

    filter_clause = {"bool": {"must": filters}} if filters else {"match_all": {}}

    query_body = {
        "size": k,
        "query": {
            "bool": {
                "must": [
                    {
                        "bool": {
                            "should": [
                                # BM25 keyword search
                                {"match": {"text": {"query": query_text, "boost": 0.3}}},
                                # kNN vector search
                                {
                                    "knn": {
                                        "embedding": {
                                            "vector": query_vector,
                                            "k": k,
                                            "boost": 0.7,
                                        }
                                    }
                                },
                            ]
                        }
                    }
                ],
                "filter": filters,
            }
        },
        "_source": True,
    }

    try:
        response = client.search(index=s.opensearch_index, body=query_body)
        hits = response["hits"]["hits"]

        results = []
        for hit in hits:
            source = hit["_source"]
            source["_score"] = hit["_score"]
            results.append(source)

        logger.info(f"Retrieved {len(results)} chunks for query: {query_text[:60]}...")
        return results
    except Exception as e:
        logger.error(f"OpenSearch search failed: {e}")
        return []


def get_parent_chunk(parent_chunk_id: str) -> dict | None:
    """Fetch the parent chunk for full context (OpenSearch only)."""
    from app.utils.aws_clients import get_opensearch_client
    s = get_settings()
    client = get_opensearch_client()
    try:
        resp = client.get(index=s.opensearch_index, id=parent_chunk_id)
        return resp["_source"]
    except Exception:
        return None


def enrich_with_parents(child_chunks: list[dict]) -> list[dict]:  # noqa: C901
    """
    Replace child chunk text with parent chunk text for richer LLM context.
    Deduplicates by parent_chunk_id.
    """
    seen_parents = set()
    enriched = []

    for chunk in child_chunks:
        parent_id = chunk.get("parent_chunk_id")
        if parent_id and parent_id not in seen_parents:
            parent = get_parent_chunk(parent_id)
            if parent:
                # Use parent text but keep child metadata (score, citation_id, etc.)
                chunk["text"] = parent["text"]
                seen_parents.add(parent_id)
        enriched.append(chunk)

    return enriched
