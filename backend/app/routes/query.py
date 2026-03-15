"""Query pipeline route — SSE streaming chat."""
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.models.query import QueryRequest
from app.services import embedder, retriever, reranker, generator, session
from app.utils.logger import get_logger

router = APIRouter(prefix="/query", tags=["query"])
logger = get_logger(__name__)


@router.post("")
def query_documents(req: QueryRequest):
    """
    Pipeline 2: Chat with indexed documents.
    1. Embed user query (Titan V2)
    2. Hybrid search OpenSearch (BM25 + kNN, k=15)
    3. Custom rerank → top 5 (semantic 0.6 + keyword 0.4)
    4. Enrich with parent chunks for full context
    5. Stream response from Bedrock LLM
    6. Save to session history
    """
    def stream():
        full_response = []
        sources = []

        try:
            # Step 1: Embed query
            query_vector = embedder.embed_text(req.query)

            # Step 2: Hybrid search
            raw_chunks = retriever.hybrid_search(
                query_text=req.query,
                query_vector=query_vector,
                department=req.department,
                clearance_level=req.clearance_level,
                doc_type=req.doc_type,
            )

            # Step 3: Re-rank
            ranked_chunks = reranker.rerank(req.query, raw_chunks, top_n=5)

            # Step 4: Enrich with parent chunks
            enriched = retriever.enrich_with_parents(ranked_chunks)

            # Load session history
            history = session.get_history(req.session_id)

            # Step 5: Stream generation
            for event in generator.stream_response(
                query=req.query,
                chunks=enriched,
                history=history,
                use_smart_model=req.use_smart_model,
            ):
                if event["type"] == "text":
                    full_response.append(event["content"])
                elif event["type"] == "sources":
                    sources = event["sources"]

                yield f"data: {json.dumps(event)}\n\n"

            # Step 6: Save to session
            session.save_message(req.session_id, "user", req.query)
            session.save_message(req.session_id, "assistant", "".join(full_response), sources)

        except Exception as e:
            logger.error(f"Query pipeline failed: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
