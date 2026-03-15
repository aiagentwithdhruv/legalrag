"""Ingestion pipeline route — upload presign + process."""
import hashlib
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from app.models.ingest import IngestRequest, IngestResponse
from app.models.query import UploadUrlRequest
from app.services import dedup, extractor, chunker, embedder, indexer
from app.utils.aws_clients import get_s3
from app.utils.logger import get_logger
from app.config import get_settings

router = APIRouter(prefix="/ingest", tags=["ingest"])
logger = get_logger(__name__)


@router.post("/upload-url")
def get_upload_url(req: UploadUrlRequest):
    """Get a presigned S3 PUT URL for direct frontend upload."""
    s = get_settings()
    s3 = get_s3()
    s3_key = f"documents/{req.filename}"
    url = s3.generate_presigned_url(
        "put_object",
        Params={"Bucket": s.s3_bucket_name, "Key": s3_key, "ContentType": req.content_type},
        ExpiresIn=300,
    )
    return {"upload_url": url, "s3_key": s3_key}


@router.post("/process", response_model=IngestResponse)
def process_document(req: IngestRequest):
    """
    Pipeline 1: Process a document already in S3.
    1. Download from S3 → compute hash → dedup check
    2. Extract text (Textract for PDF)
    3. Hierarchical chunking
    4. Embed child chunks (Titan V2)
    5. Bulk upsert to OpenSearch (with chunk-level dedup)
    """
    s = get_settings()
    s3 = get_s3()
    doc_id = req.s3_key

    # Step 1: Download + hash
    try:
        obj = s3.get_object(Bucket=s.s3_bucket_name, Key=req.s3_key)
        file_bytes = obj["Body"].read()
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"S3 object not found: {e}")

    file_hash = dedup.compute_file_hash(file_bytes)
    dedup_result = dedup.check_and_register(file_hash, doc_id, req.filename)

    if dedup_result["status"] == "duplicate":
        return IngestResponse(
            doc_id=dedup_result["doc_id"],
            status="skipped",
            message=f"File already indexed (originally: {dedup_result.get('filename', req.filename)})",
            chunks_indexed=0,
        )

    try:
        # Step 2: Extract text per page
        pages = extractor.extract_text_from_s3(req.s3_key)
        if not pages:
            raise ValueError("No text extracted from document")

        # Step 3: Extract entities from full text for metadata
        full_text = " ".join(p["text"] for p in pages)
        entities = extractor.extract_entities(full_text)

        base_metadata = {
            "source":          req.filename,
            "s3_key":          req.s3_key,
            "doc_type":        req.doc_type,
            "department":      req.department,
            "clearance_level": req.clearance_level,
            "entities":        entities,
            "file_hash":       file_hash,
        }

        # Step 4: Hierarchical chunking
        chunks = chunker.chunk_pages(pages, doc_id=req.s3_key, base_metadata=base_metadata)
        child_chunks = [c for c in chunks if not c.is_parent]

        # Step 5: Embed child chunks in batches
        all_embeddings: list[list[float]] = []
        child_texts = [c.text for c in child_chunks]
        for batch_embeddings in embedder.embed_chunks_in_batches(child_texts):
            all_embeddings.extend(batch_embeddings)

        # Step 6: Bulk upsert with dedup
        stats = indexer.bulk_upsert(chunks, all_embeddings)

        dedup.mark_indexed(file_hash, stats["indexed"])
        logger.info(f"Ingestion complete: {req.filename} → {stats}")

        return IngestResponse(
            doc_id=doc_id,
            status="indexed",
            message=f"Indexed {stats['indexed']} chunks ({stats['skipped']} skipped, {stats['updated']} updated)",
            chunks_indexed=stats["indexed"],
        )

    except Exception as e:
        dedup.mark_failed(file_hash, str(e))
        logger.error(f"Ingestion failed for {req.filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
