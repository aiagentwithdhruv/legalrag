"""Hierarchical chunking: parent (1500 tokens) + child (512 tokens) strategy."""
import uuid
import hashlib
from dataclasses import dataclass, field
from app.utils.logger import get_logger

logger = get_logger(__name__)

PARENT_SIZE = 1500   # tokens (approx words)
CHILD_SIZE  = 512
OVERLAP     = 50


@dataclass
class Chunk:
    chunk_id: str
    parent_chunk_id: str
    is_parent: bool
    text: str
    doc_id: str
    page_number: int
    metadata: dict = field(default_factory=dict)


def _words(text: str) -> list[str]:
    return text.split()


def _make_id(doc_id: str, text: str, page: int, suffix: str = "") -> str:
    raw = f"{doc_id}:{page}:{text[:80]}:{suffix}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def chunk_pages(pages: list[dict], doc_id: str, base_metadata: dict) -> list[Chunk]:
    """
    Two-level chunking:
    1. Parent chunks (1500 tokens) — stored for context return
    2. Child chunks (512 tokens, 50 overlap) — embedded and stored for retrieval
    Both stored in OpenSearch; retrieval uses child embeddings, returns parent text.
    """
    all_chunks: list[Chunk] = []

    for page_dict in pages:
        page_num = page_dict["page"]
        text = page_dict["text"].strip()
        if not text:
            continue

        words = _words(text)

        # Parent chunks
        parent_starts = range(0, len(words), PARENT_SIZE - OVERLAP)
        for p_start in parent_starts:
            parent_words = words[p_start : p_start + PARENT_SIZE]
            parent_text = " ".join(parent_words)
            parent_id = _make_id(doc_id, parent_text, page_num, "parent")

            parent_chunk = Chunk(
                chunk_id=parent_id,
                parent_chunk_id=parent_id,
                is_parent=True,
                text=parent_text,
                doc_id=doc_id,
                page_number=page_num,
                metadata={**base_metadata, "page_number": page_num},
            )
            all_chunks.append(parent_chunk)

            # Child chunks within this parent
            child_starts = range(0, len(parent_words), CHILD_SIZE - OVERLAP)
            for c_idx, c_start in enumerate(child_starts):
                child_words = parent_words[c_start : c_start + CHILD_SIZE]
                if len(child_words) < 30:  # skip tiny trailing chunks
                    continue
                child_text = " ".join(child_words)
                child_id = _make_id(doc_id, child_text, page_num, f"child_{c_idx}")

                child_chunk = Chunk(
                    chunk_id=child_id,
                    parent_chunk_id=parent_id,
                    is_parent=False,
                    text=child_text,
                    doc_id=doc_id,
                    page_number=page_num,
                    metadata={**base_metadata, "page_number": page_num},
                )
                all_chunks.append(child_chunk)

    parent_count = sum(1 for c in all_chunks if c.is_parent)
    child_count = sum(1 for c in all_chunks if not c.is_parent)
    logger.info(f"Chunked doc {doc_id}: {parent_count} parents, {child_count} children")
    return all_chunks
