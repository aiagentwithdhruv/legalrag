"""Custom hybrid re-ranker: semantic (kNN) + keyword (BM25) weighted scoring."""
import math
from app.utils.logger import get_logger
from app.config import get_settings

logger = get_logger(__name__)


def normalize_scores(chunks: list[dict]) -> list[dict]:
    """Min-max normalize _score to 0-1 range."""
    scores = [c.get("_score", 0.0) for c in chunks]
    min_s, max_s = min(scores, default=0), max(scores, default=1)
    if max_s == min_s:
        for c in chunks:
            c["normalized_score"] = 1.0
    else:
        for c in chunks:
            c["normalized_score"] = (c.get("_score", 0.0) - min_s) / (max_s - min_s)
    return chunks


def keyword_score(query: str, text: str) -> float:
    """
    BM25-inspired keyword overlap score.
    Counts unique query term matches weighted by IDF approximation.
    """
    query_terms = set(query.lower().split())
    text_lower = text.lower()
    text_words = text_lower.split()
    text_len = len(text_words)
    if text_len == 0 or not query_terms:
        return 0.0

    # TF-IDF approximation
    k1, b, avg_dl = 1.5, 0.75, 200
    score = 0.0
    for term in query_terms:
        tf = text_lower.count(term)
        if tf == 0:
            continue
        # BM25 TF normalization
        tf_norm = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * text_len / avg_dl))
        # Simple IDF — give more weight to longer/rarer terms
        idf = math.log(1 + len(term))
        score += tf_norm * idf

    # Normalize to 0-1 range
    return min(score / (len(query_terms) * 5), 1.0)


def rerank(query: str, chunks: list[dict], top_n: int = 5) -> list[dict]:
    """
    Custom hybrid re-ranker combining:
    - Semantic score (kNN cosine from OpenSearch, normalized)
    - Keyword score (BM25-inspired term overlap)

    Final score = semantic_weight * semantic + keyword_weight * keyword
    """
    s = get_settings()

    if not chunks:
        return []

    # Normalize semantic scores
    chunks = normalize_scores(chunks)

    for chunk in chunks:
        text = chunk.get("text", "")
        kw_score = keyword_score(query, text)
        semantic = chunk.get("normalized_score", 0.0)

        chunk["keyword_score"]  = kw_score
        chunk["semantic_score"] = semantic
        chunk["combined_score"] = (
            s.semantic_weight * semantic +
            s.keyword_weight  * kw_score
        )

    ranked = sorted(chunks, key=lambda x: x["combined_score"], reverse=True)
    top = ranked[:top_n]

    logger.info(
        f"Reranked {len(chunks)} → top {len(top)} | "
        f"scores: {[round(c['combined_score'], 3) for c in top]}"
    )
    return top
