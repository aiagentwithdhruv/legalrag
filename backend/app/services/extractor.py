"""Document text extraction using Amazon Textract + Comprehend."""
import json
import time
from app.utils.aws_clients import get_textract, get_comprehend, get_s3
from app.utils.logger import get_logger
from app.config import get_settings

logger = get_logger(__name__)


def extract_text_from_s3(s3_key: str) -> list[dict]:
    """
    Extract text from S3 object. Returns list of page dicts:
    [{"page": 1, "text": "...", "tables": [...]}]
    """
    s = get_settings()
    key_lower = s3_key.lower()

    if key_lower.endswith(".pdf") or key_lower.endswith(".png") or key_lower.endswith(".jpg") or key_lower.endswith(".jpeg"):
        return _extract_with_textract(s.s3_bucket_name, s3_key)
    else:
        return _extract_plain_text(s.s3_bucket_name, s3_key)


def _extract_with_textract(bucket: str, key: str) -> list[dict]:
    textract = get_textract()

    # Start async job for PDFs (handles multi-page)
    response = textract.start_document_analysis(
        DocumentLocation={"S3Object": {"Bucket": bucket, "Name": key}},
        FeatureTypes=["TABLES", "FORMS"],
    )
    job_id = response["JobId"]
    logger.info(f"Textract job started: {job_id}")

    # Poll until complete
    while True:
        result = textract.get_document_analysis(JobId=job_id)
        status = result["JobStatus"]
        if status == "SUCCEEDED":
            break
        elif status == "FAILED":
            raise RuntimeError(f"Textract job failed: {result.get('StatusMessage', 'Unknown')}")
        logger.info(f"Textract job {job_id} status: {status}, waiting...")
        time.sleep(3)

    # Collect all pages (paginated)
    pages: dict[int, list[str]] = {}
    next_token = None
    while True:
        kwargs = {"JobId": job_id}
        if next_token:
            kwargs["NextToken"] = next_token
        result = textract.get_document_analysis(**kwargs)

        for block in result.get("Blocks", []):
            page_num = block.get("Page", 1)
            if block["BlockType"] == "LINE":
                pages.setdefault(page_num, []).append(block.get("Text", ""))

        next_token = result.get("NextToken")
        if not next_token:
            break

    page_list = [
        {"page": page_num, "text": " ".join(lines), "tables": []}
        for page_num, lines in sorted(pages.items())
    ]
    logger.info(f"Textract extracted {len(page_list)} pages from {key}")
    return page_list


def _extract_plain_text(bucket: str, key: str) -> list[dict]:
    s3 = get_s3()
    obj = s3.get_object(Bucket=bucket, Key=key)
    text = obj["Body"].read().decode("utf-8", errors="replace")
    # Split into ~2000 char pages for processing
    page_size = 2000
    pages = []
    for i, start in enumerate(range(0, len(text), page_size)):
        pages.append({"page": i + 1, "text": text[start : start + page_size], "tables": []})
    return pages


def extract_entities(text: str) -> list[str]:
    """Extract named entities using Amazon Comprehend."""
    if not text.strip():
        return []
    comprehend = get_comprehend()
    # Comprehend max 5000 chars per call
    snippet = text[:4900]
    try:
        response = comprehend.detect_entities(Text=snippet, LanguageCode="en")
        return list({
            e["Text"].strip()
            for e in response.get("Entities", [])
            if e["Score"] > 0.85 and e["Type"] in ("PERSON", "ORGANIZATION", "DATE", "LOCATION", "TITLE", "QUANTITY")
        })
    except Exception as e:
        logger.warning(f"Comprehend entity extraction failed: {e}")
        return []
