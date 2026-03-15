# LegalRAG — Production RAG on AWS
## AI Architect Mastery | Euron Bootcamp

> **STATUS: SPEC PHASE — DO NOT BUILD YET. Wait for explicit approval before writing any code.**

---

## What We Are Building

**LegalRAG** is a two-pipeline document intelligence system for legal teams, built entirely on AWS. Legal teams upload documents through a UI, which are processed and indexed into AWS OpenSearch. Anyone can then chat with the system and get cited, grounded answers retrieved from those documents.

**Two pipelines. Fully automated setup via AWS CLI + IAM. No manual intervention.**

---

## Pipeline 1: Data Ingestion

### Flow

```
[Legal Team] → [UI: Upload PDF / DOC / DOCX]
                          │
                          ▼
                   [Amazon S3 Bucket]
                          │
                          ▼
              ┌─────────────────────────────────┐
              │  MIDDLEWARE: Duplicate Checker   │
              │  ─────────────────────────────  │
              │  1. Compute SHA-256 hash of file │
              │  2. Check DynamoDB: hash exists? │
              │     YES → skip, return "already  │
              │           processed" status      │
              │     NO  → continue processing   │
              │  3. Store hash + metadata on     │
              │     success to prevent reprocess │
              └──────────────┬──────────────────┘
                             │ (new file only)
                             ▼
              ┌─────────────────────────────────┐
              │  DOCUMENT PROCESSOR             │
              │  ─────────────────────────────  │
              │  • Textract: PDF/image → text   │
              │  • Tables + Forms extraction    │
              │  • Hierarchical chunking        │
              │    (Parent: 1500t, Child: 512t) │
              │  • Comprehend: entity extract   │
              └──────────────┬──────────────────┘
                             │
                             ▼
              ┌─────────────────────────────────┐
              │  EMBEDDING (AWS Bedrock)        │
              │  ─────────────────────────────  │
              │  Choose from options below ↓    │
              └──────────────┬──────────────────┘
                             │
                             ▼
              ┌─────────────────────────────────┐
              │  METADATA + CITATIONS           │
              │  ─────────────────────────────  │
              │  Every chunk stores:            │
              │  • source filename + S3 path    │
              │  • page number                  │
              │  • doc_type (contract/policy)   │
              │  • department + clearance       │
              │  • entities (people, orgs, law) │
              │  • section / clause heading     │
              │  • citation_id (unique ref)     │
              │  • chunk_id + parent_chunk_id   │
              └──────────────┬──────────────────┘
                             │
                             ▼
              ┌─────────────────────────────────┐
              │  DEDUPLICATION MIDDLEWARE       │
              │  ─────────────────────────────  │
              │  Before OpenSearch upsert:      │
              │  • Check if chunk_id exists     │
              │  • If exists + same hash → skip │
              │  • If exists + diff hash → update│
              │  • If new → insert              │
              └──────────────┬──────────────────┘
                             │
                             ▼
                  [AWS OpenSearch Serverless]
                  knn_vector + BM25 hybrid index
```

### Embedding Model Options (Choose One)

| # | Model | Dimensions | Price | Best For |
|---|-------|------------|-------|----------|
| **Option A** | **Amazon Titan Text Embeddings V2** | 256 / 512 / **1024** | $0.02/1M tokens | English legal docs, cost-efficient, MRL support (reduce to 256 dims for cache) |
| **Option B** | **Cohere Embed v3 (English)** | 1024 | $0.10/1M tokens | Better semantic quality, good for dense legal text |
| **Option C** | **Cohere Embed v3 (Multilingual)** | 1024 | $0.10/1M tokens | Multi-language regulations (EU law, Indian law, etc.) |
| **Option D** | **Amazon Titan V2 + Cohere Rerank** | 1024 + rerank | $0.02 embed + $1/1K rerank | Best accuracy: cheap embed, quality reranking |

> **Recommendation:** Option A (Titan V2, 1024-dim) for English legal docs. Switch to Option D if accuracy is the top priority.

---

## Pipeline 2: Query / Chat

### Flow

```
[User] → [Chat UI]
              │
              ▼
   [Query Handler: Lambda / FastAPI]
              │
              ▼
   ┌──────────────────────────────────┐
   │  EMBED USER QUERY               │
   │  Same model as ingestion        │
   │  (Titan V2 or Cohere Embed v3)  │
   └──────────────┬───────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────┐
   │  OPENSEARCH SEARCH              │
   │  Hybrid: BM25 + kNN             │
   │  k = 15 (retrieve more first)   │
   │  Apply metadata filters (RBAC)  │
   └──────────────┬───────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────────────────────────┐
   │  CUSTOM RE-RANKING STRATEGY                         │
   │  ──────────────────────────────────────────────────  │
   │  Two signals combined with configurable weights:    │
   │                                                      │
   │  Signal 1: Semantic Similarity (vector cosine)      │
   │    • Already from OpenSearch kNN score              │
   │    • Weight: 0.6 (default)                          │
   │                                                      │
   │  Signal 2: Keyword / BM25 Similarity                │
   │    • Lexical overlap (legal terms, exact phrases)   │
   │    • Weight: 0.4 (default)                          │
   │                                                      │
   │  OPTION: Add Cohere Rerank 3.5 as 3rd signal        │
   │    • Cross-encoder re-score (most accurate)         │
   │    • $1.00 per 1K queries                           │
   │    • Overrides weights above when enabled           │
   │                                                      │
   │  Final: Top 5 chunks sent to LLM                    │
   └──────────────┬───────────────────────────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────┐
   │  LLM — AWS Bedrock              │
   │  Model options:                 │
   │  • Claude 3.5 Haiku (fast/cheap)│
   │  • Claude 3.5 Sonnet v2 (smart) │
   │  Streaming via SSE              │
   │  Guardrails: grounding check    │
   └──────────────┬───────────────────┘
                  │
                  ▼
   [Final Answer + Citations → User]
```

---

## Automated Setup (AWS CLI + IAM — No Manual Steps)

Everything below will be scripted. You provide:
1. AWS Access Key ID + Secret Key
2. AWS Account ID
3. Preferred region

The setup script will automatically configure:

```
scripts/
├── setup/
│   ├── 00_configure_aws.sh        ← aws configure + verify identity
│   ├── 01_create_s3.sh            ← bucket + versioning + KMS + EventBridge
│   ├── 02_create_dynamodb.sh      ← ingestion-log + sessions + dedup tables
│   ├── 03_create_opensearch.sh    ← collection + encryption policy + network policy + access policy
│   ├── 04_create_iam_roles.sh     ← lambda role + ecs task role + policies
│   ├── 05_enable_bedrock.sh       ← check/list available models (manual model access required in console)
│   ├── 06_create_guardrails.sh    ← Bedrock Guardrails for PII + grounding
│   ├── 07_create_elasticache.sh   ← Valkey (Redis) semantic cache
│   ├── 08_create_opensearch_index.py  ← Python: create knn + BM25 index
│   └── setup_all.sh               ← run all in order
```

> **Note:** AWS Bedrock model access still requires one-time console click (AWS limitation — cannot be automated via CLI). All other services are 100% automated.

---

## Project Structure

```
LegalRAG/
│
├── CLAUDE.md                          ← This file (spec + rules)
│
├── research/
│   └── AWS-RAG-Research.md            ← Full AWS RAG research (March 2026)
│
├── prompts/                           ← All prompt templates (keep here)
│   ├── rag_system_prompt.txt          ← Main RAG system prompt
│   ├── query_rewrite_prompt.txt       ← Query reformulation prompt
│   ├── citation_format_prompt.txt     ← How to format citations
│   ├── no_context_prompt.txt          ← When context is insufficient
│   └── legal_guardrail_prompt.txt     ← Legal safety prompt additions
│
├── scripts/
│   └── setup/                         ← Automated AWS setup scripts
│       ├── 00_configure_aws.sh
│       ├── 01_create_s3.sh
│       ├── 02_create_dynamodb.sh
│       ├── 03_create_opensearch.sh
│       ├── 04_create_iam_roles.sh
│       ├── 05_enable_bedrock.sh
│       ├── 06_create_guardrails.sh
│       ├── 07_create_elasticache.sh
│       ├── 08_create_opensearch_index.py
│       └── setup_all.sh
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py                    ← FastAPI entry point
│   │   ├── config.py                  ← Pydantic Settings (all from env)
│   │   ├── routes/
│   │   │   ├── ingest.py              ← POST /ingest
│   │   │   ├── query.py               ← POST /query (SSE stream)
│   │   │   └── health.py              ← GET /health
│   │   ├── services/
│   │   │   ├── embedder.py            ← Bedrock embedding (Titan V2 / Cohere)
│   │   │   ├── retriever.py           ← OpenSearch hybrid search
│   │   │   ├── reranker.py            ← Custom rerank (semantic + BM25 + optional Cohere)
│   │   │   ├── generator.py           ← Claude streaming generation
│   │   │   ├── chunker.py             ← Hierarchical chunking
│   │   │   ├── extractor.py           ← Textract + Comprehend
│   │   │   ├── dedup.py               ← SHA-256 hash check + DynamoDB
│   │   │   └── cache.py               ← ElastiCache semantic cache
│   │   ├── middleware/
│   │   │   └── dedup_middleware.py    ← File dedup before processing
│   │   └── models/
│   │       ├── ingest.py              ← IngestRequest / IngestResponse
│   │       └── query.py               ← QueryRequest / SSE events
│
├── lambda/
│   ├── ingest/handler.py              ← S3 trigger → ingest pipeline
│   └── query/handler.py               ← FastAPI on Lambda (Mangum)
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx               ← Chat interface
│   │   │   └── upload/page.tsx        ← Document upload UI
│   │   └── components/
│   │       ├── ChatWindow.tsx
│   │       ├── DocumentUpload.tsx
│   │       └── SourceCitations.tsx
│   └── Dockerfile
│
├── infra/
│   └── cdk/                           ← AWS CDK IaC
│
├── evaluation/
│   ├── ragas_eval.py                  ← RAGAS faithfulness + relevancy tests
│   └── test_queries.json              ← Gold standard Q&A pairs
│
├── docker-compose.yml                 ← Local dev
└── .env.example                       ← All required env vars listed
```

---

## Deduplication — Detailed Design

### File-Level Dedup (Ingestion Entry Point)

```
When a file arrives in S3:
1. Compute SHA-256 hash of file content
2. Query DynamoDB table `legalrag-dedup`:
   PK = file_hash
3. If record exists:
   → Return: {"status": "skipped", "reason": "already_processed", "doc_id": existing_doc_id}
4. If no record:
   → Write placeholder: {file_hash, doc_id, status: "processing", timestamp}
   → Continue to processing pipeline
5. On success:
   → Update: {status: "indexed", chunk_count, indexed_at}
6. On failure:
   → Update: {status: "failed", error_message}
   → Remove placeholder so re-upload is allowed
```

### Chunk-Level Dedup (Before OpenSearch Upsert)

```
Before bulk upsert:
1. Each chunk has chunk_id = SHA-256(doc_id + chunk_text + page_number)
2. Check OpenSearch: does chunk_id exist?
   YES, same hash → skip
   YES, different hash → update (document was re-processed with new content)
   NO → insert
```

### DynamoDB Table: `legalrag-dedup`
```
PK: file_hash (S)          ← SHA-256 of file bytes
SK: "FILE" (S)
Attributes:
  doc_id (S)               ← S3 key
  original_filename (S)
  status: "processing" | "indexed" | "failed"
  chunk_count (N)
  indexed_at (S)           ← ISO timestamp
  error_message (S)
TTL: expires_at (N)        ← optional, 1 year
```

---

## Prompt Templates (in `prompts/` folder)

### rag_system_prompt.txt
```
You are a legal document assistant. Your job is to answer questions based ONLY on the provided context from legal documents.

Rules:
1. ONLY use information from the provided <context> blocks.
2. ALWAYS cite the source document and page number for every claim.
3. If the context does not contain enough information, say: "I don't have enough information in the available documents to answer this question."
4. Do NOT provide legal advice. Present information only.
5. Be precise and concise.
6. Format citations as: [Source: {filename}, Page {page}]
```

### query_rewrite_prompt.txt
```
Given the following conversation history and a new question, rewrite the question to be self-contained and clear.

Conversation History:
{history}

New Question: {question}

Rewritten Question:
```

### no_context_prompt.txt
```
The retrieved documents do not contain sufficient information to answer this question.

Please try:
1. Rephrasing your question with different keywords
2. Checking if the relevant document has been uploaded
3. Asking a more specific question

Your question was: {question}
```

---

## AWS Services Stack

| Service | Purpose | Cost/Month |
|---------|---------|-----------|
| Amazon S3 | Document storage (versioned, KMS) | ~$2-5 |
| Amazon Textract | PDF/image OCR + tables | $0.0015-0.065/page |
| Amazon Comprehend | Entity extraction → metadata | $0.0001/100 chars |
| AWS Lambda | Ingest trigger + query handler | ~$5-15 |
| AWS Step Functions | Multi-step pipeline orchestration | ~$3-10 |
| Amazon Bedrock | Embeddings + Reranking + Generation | See embedding options |
| Amazon OpenSearch Serverless | Hybrid vector + BM25 search | $350+/mo (4 OCU min) |
| Amazon ElastiCache Valkey | Semantic cache (query dedup) | ~$50-200 |
| Amazon DynamoDB | File dedup + session history | ~$2-5 |
| Amazon API Gateway | HTTP endpoints | ~$5 |
| AWS CloudWatch + X-Ray | Monitoring + tracing | ~$5-15 |
| AWS IAM | All service permissions (auto-configured) | Free |

---

## Monthly Cost Estimates

| Scale | Docs | Queries/Day | Monthly |
|-------|------|-------------|---------|
| MVP (Aurora pgvector) | <10K | <100 | ~$180-220 |
| Small (OpenSearch) | 10K | 100 | ~$360-435 |
| Medium | 100K | 1K | ~$700-900 |
| Large | 1M | 10K | ~$4,800-5,800 |

---

## Re-ranking — Detailed Design

### Default: Custom Hybrid Re-ranker

```python
# Custom weighted re-ranking (no extra cost)
def rerank(query: str, chunks: list[dict], k: int = 5) -> list[dict]:
    """
    Combines two signals:
    - semantic_score: cosine similarity from OpenSearch kNN (range 0-1)
    - bm25_score: BM25 lexical score from OpenSearch text match (normalized 0-1)
    """
    SEMANTIC_WEIGHT = 0.6
    KEYWORD_WEIGHT  = 0.4

    for chunk in chunks:
        chunk["combined_score"] = (
            SEMANTIC_WEIGHT * chunk["knn_score"] +
            KEYWORD_WEIGHT  * chunk["bm25_score"]
        )

    return sorted(chunks, key=lambda x: x["combined_score"], reverse=True)[:k]
```

### Optional: Cohere Rerank 3.5 (Better Accuracy)

When `ENABLE_COHERE_RERANK=true`:
- Uses Bedrock Cohere Rerank 3.5 cross-encoder
- Completely replaces the custom weighted re-ranker
- $1.00 per 1K queries
- Recommended for production legal use cases

---

## Environment Variables (.env.example)

```bash
# ── AWS ──────────────────────────────────────────────
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=123456789012
# No keys needed — use IAM roles on Lambda/ECS

# ── Bedrock ──────────────────────────────────────────
BEDROCK_EMBED_MODEL=amazon.titan-embed-text-v2:0
# Options:
#   amazon.titan-embed-text-v2:0          (Titan V2, English)
#   cohere.embed-english-v3               (Cohere English)
#   cohere.embed-multilingual-v3          (Cohere Multilingual)
BEDROCK_LLM_FAST=anthropic.claude-3-5-haiku-20241022-v1:0
BEDROCK_LLM_SMART=anthropic.claude-3-5-sonnet-20241022-v2:0
BEDROCK_RERANK_MODEL=arn:aws:bedrock:us-east-1::foundation-model/cohere.rerank-v3-5:0
BEDROCK_GUARDRAIL_ID=<auto-created-by-setup-script>
BEDROCK_GUARDRAIL_VERSION=1

# ── Embedding Config ──────────────────────────────────
EMBED_DIMENSIONS=1024          # 256 | 512 | 1024 (Titan V2 only)
EMBED_NORMALIZE=true

# ── OpenSearch ────────────────────────────────────────
OPENSEARCH_ENDPOINT=<auto-filled-by-setup-script>
OPENSEARCH_INDEX=legal-docs
OPENSEARCH_REGION=us-east-1

# ── Re-ranking ────────────────────────────────────────
ENABLE_COHERE_RERANK=false     # true = Cohere Rerank 3.5, false = custom hybrid
SEMANTIC_WEIGHT=0.6            # weight for kNN score
KEYWORD_WEIGHT=0.4             # weight for BM25 score
TOP_K_RETRIEVE=15              # initial retrieval count
TOP_N_FINAL=5                  # after re-ranking

# ── ElastiCache ───────────────────────────────────────
ELASTICACHE_URL=redis://<auto-filled>:6379
CACHE_ENABLED=true
CACHE_SIMILARITY_THRESHOLD=0.95
CACHE_TTL_SECONDS=3600

# ── DynamoDB ──────────────────────────────────────────
DEDUP_TABLE=legalrag-dedup
SESSIONS_TABLE=legalrag-sessions

# ── S3 ────────────────────────────────────────────────
DOCUMENTS_BUCKET=legalrag-docs-<account-id>

# ── App ───────────────────────────────────────────────
LOG_LEVEL=INFO
ENABLE_GUARDRAILS=true
```

---

## RAGAS Evaluation Standards

```
Faithfulness:       > 0.90   (no hallucinated legal citations)
Answer Relevancy:   > 0.85   (on-topic responses)
Context Precision:  > 0.80   (retrieved the right chunks)
Context Recall:     > 0.75   (didn't miss key chunks)
```

Run: `python evaluation/ragas_eval.py`

---

## Engineering Rules

1. **No code in routes** — all logic in services
2. **Dedup always** — file-level SHA-256 check before any processing
3. **Hybrid search always** — never kNN-only for legal
4. **Metadata on every chunk** — source, page, entity, dept, citation_id
5. **Stream always** — never block on LLM responses
6. **Cite always** — every answer includes source filename + page
7. **Guardrails always on** in production — grounding check blocks hallucinations
8. **IAM roles only** — no access keys hardcoded or in containers
9. **Automated setup** — zero manual console clicks (except Bedrock model access)
10. **Prompts in `/prompts`** — never inline in code

---

## Build Order (After Approval)

```
Phase 1: Infrastructure Setup (automated scripts)
  └── Run setup_all.sh with AWS credentials

Phase 2: Ingestion Pipeline
  └── Lambda ingest handler + dedup middleware + Textract + embed + OpenSearch upsert

Phase 3: Query Pipeline
  └── FastAPI query endpoint + hybrid search + custom reranker + Claude streaming

Phase 4: Frontend
  └── Next.js upload UI + chat interface + SSE streaming + citation display

Phase 5: Production Hardening
  └── Guardrails + ElastiCache cache + RAGAS eval + CloudWatch alarms

Phase 6: Deployment
  └── Docker → ECR → ECS Fargate (or Lambda) via aws-production-deploy skill
```

---

## Parent Context

**Part of:** `Euron/AI Architech Mastery/`
**Skill:** `.context/claude-skills/.claude/skills/legal-rag-aws/SKILL.md`
**Research:** `LegalRAG/research/AWS-RAG-Research.md`
**Related:** `Multimodal-RAG-System/` (multimodal RAG reference)
