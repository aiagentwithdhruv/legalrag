"""File-level SHA-256 deduplication via DynamoDB."""
import hashlib
import time
from typing import Optional
from app.utils.aws_clients import get_dynamodb
from app.utils.logger import get_logger
from app.config import get_settings

logger = get_logger(__name__)


def compute_file_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def check_and_register(file_hash: str, doc_id: str, filename: str) -> dict:
    """
    Check if file was already processed.
    Returns: {"status": "new"} or {"status": "duplicate", "doc_id": existing_doc_id}
    """
    s = get_settings()
    table = get_dynamodb().Table(s.dedup_table)

    response = table.get_item(Key={"file_hash": file_hash})
    existing = response.get("Item")

    if existing and existing.get("status") == "indexed":
        logger.info(f"Duplicate file detected: {filename} (hash={file_hash[:8]}...)")
        return {"status": "duplicate", "doc_id": existing["doc_id"], "filename": existing.get("original_filename", "")}

    # Register as processing
    ttl = int(time.time()) + (365 * 24 * 3600)  # 1 year
    table.put_item(Item={
        "file_hash": file_hash,
        "doc_id": doc_id,
        "original_filename": filename,
        "status": "processing",
        "created_at": int(time.time()),
        "expires_at": ttl,
    })
    logger.info(f"Registered new file: {filename} (hash={file_hash[:8]}...)")
    return {"status": "new"}


def mark_indexed(file_hash: str, chunk_count: int) -> None:
    s = get_settings()
    table = get_dynamodb().Table(s.dedup_table)
    table.update_item(
        Key={"file_hash": file_hash},
        UpdateExpression="SET #s = :s, chunk_count = :c, indexed_at = :t",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":s": "indexed", ":c": chunk_count, ":t": int(time.time())},
    )


def mark_failed(file_hash: str, error: str) -> None:
    """Mark as failed so re-upload is allowed."""
    s = get_settings()
    table = get_dynamodb().Table(s.dedup_table)
    table.delete_item(Key={"file_hash": file_hash})
    logger.error(f"Ingestion failed for hash={file_hash[:8]}...: {error}")
