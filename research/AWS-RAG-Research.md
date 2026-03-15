# Production RAG on AWS — Complete Research Reference
**Date:** March 2026 | **Project:** LegalRAG | **Researcher:** Claude Sonnet 4.6

---

## 1. Vector Database Options on AWS

### Amazon OpenSearch Serverless — Vector Engine

**The default for Bedrock Knowledge Bases and the most capable AWS-native option.**

**Pricing:**
- $0.24 per OCU-hour for indexing AND search
- Hard minimum: 4 OCUs for first vector collection = ~$350/month floor
- Vector collections cannot share OCUs with other collection types
- GPU acceleration available: 10x faster indexing at 1/4 CPU cost (separate charge)

**Performance (2025):**
- 1 OCU = 4M vectors @ 128 dims OR 500K vectors @ 768 dims at 99% recall
- OpenSearch 2.17: 4x latency improvement, 25% better throughput via parallelization
- Auto-scales with traffic — no manual scaling needed

**Hybrid Search:** BM25 (lexical) + kNN (vector) native support — best of both worlds.

**Best for:** 100M+ vectors, unpredictable traffic, hybrid search, Bedrock KB integration.

---

### Amazon Aurora PostgreSQL with pgvector

**Pricing:**
- Aurora Serverless v2: $0.12/ACU-hour (scales to 0.5 ACU idle)
- ~$100-175/month for typical RAG workload
- pgvector is FREE — included with Aurora PostgreSQL
- Graviton3: 40% better price-performance vs x86
- 67x faster embedding loads (2024 Aurora storage optimization)

**Performance:**
- HNSW index: 15.5x faster than IVFFlat
- Critical: entire HNSW index must fit in RAM — instance sizing is critical
- Supports L2, cosine, inner product distance

**Best for:** <100M vectors, existing PostgreSQL shops, ACID + vectors, strong joins.

**Integration:** Fully supported as Bedrock Knowledge Bases vector store.

---

### Amazon MemoryDB for Redis (Vector Search)

**Pricing:**
- Vector search: FREE — no additional charge
- Pay for instance type + data volume written per GB
- ~$180/month floor for production instance

**Performance:**
- Fastest single-digit millisecond query AND update latency
- Entire index lives in memory — blazing fast
- As of mid-2024: highest recall among all AWS vector options at highest throughput

**Best for:** Real-time RAG, semantic caching layer, sub-ms requirements.

**Limitation:** Memory-bound → expensive at billion-vector scale.

---

### Amazon Neptune Analytics (GraphRAG)

**GA:** March 2025, natively integrated into Bedrock Knowledge Bases.

**How it works:**
- Automatically generates vector embeddings + graph representation of entities/relationships
- Combines vector similarity search with graph traversal in a single query
- Open-source GraphRAG Toolkit (Python) available
- BYOKG (Bring Your Own Knowledge Graph) support: August 2025

**Pricing:** $0.07/graph-hour + $0.00035/GB-hour memory

**Accuracy gain:** 30-40% improvement on multi-document reasoning vs standard RAG.

**Best for:** Legal document networks (cases referencing cases), compliance chains, multi-hop entity reasoning.

---

### Amazon S3 Vectors (GA December 2025)

**The newest AWS vector option — purpose-built at object storage prices.**

- 2 billion vectors per index (40x increase from preview)
- 10,000 vector indexes per vector bucket
- Up to 90% cheaper than OpenSearch Serverless for pure storage
- Pay for: PUT (logical GB), storage (per GB), query processing (per query)

**Architecture pattern:**
```
Hot queries → OpenSearch Serverless (fast)
Cold/archive → S3 Vectors (cheap)
```

**Best for:** Billion-scale archival, compliance records, historical document stores.

---

### Amazon Kendra (Managed Enterprise Search)

**Pricing:**
- Developer: $810/month
- Enterprise: $1,008/month + $0.005/document + $0.0004/query

**Best for:** Enterprise SharePoint/Confluence RAG where non-technical teams own content.

---

### Vector DB Decision Matrix

| Scenario | Best Choice | Monthly Floor |
|---|---|---|
| Startup, <10M vectors | Aurora pgvector | ~$100 |
| Real-time, sub-ms latency | MemoryDB | ~$180 |
| Hybrid BM25 + vector | OpenSearch Serverless | ~$350 |
| Multi-hop graph (legal cases) | Neptune Analytics | ~$200 |
| Billion-scale, cost-first | S3 Vectors | Pay-per-use |
| Enterprise SharePoint | Kendra | ~$810 |
| Bedrock Knowledge Bases default | OpenSearch Serverless | ~$350 |

**LegalRAG Choice:** OpenSearch Serverless (hybrid search critical for legal keyword + semantic matching)

---

## 2. Embedding Models on Amazon Bedrock

### Amazon Titan Text Embeddings V2

| Property | Value |
|---|---|
| Model ID | `amazon.titan-embed-text-v2:0` |
| Dimensions | 256, 512, or 1024 (configurable) |
| Context window | 8,192 tokens / 50,000 characters |
| Price (on-demand) | $0.02 per 1M input tokens |
| Price (batch) | $0.01 per 1M input tokens (50% off) |
| MRL support | Yes — truncate to 256 dims at 97% of 1024-dim accuracy |

**MRL (Matryoshka Representation Learning):** Use 256 dims to save 75% storage with only 3% accuracy loss. Game-changer for cost optimization.

**Best for:** English-primary, cost-sensitive production. Default AWS choice.

---

### Cohere Embed v3

| Property | Value |
|---|---|
| Dimensions | 1024 (fixed) |
| Price | $0.10 per 1M tokens |
| Languages | 100+ languages |
| Multimodal (Jan 2025) | Text AND images in same embedding space |

**Best for:** Global legal apps, multilingual document RAG (EU regulations in multiple languages).

---

### Reranking Models (Cross-Encoders)

| Model | Price | Notes |
|---|---|---|
| Cohere Rerank 3.5 | $1.00 / 1K queries | Up to 100 chunks per query |
| Amazon Rerank v1.0 | $1.00 / 1K queries | Available in us-east-1, us-west-2, eu-west-1 |

**Pattern:** Retrieve 15-20 with hybrid search → rerank to top 5. Consistently outperforms retrieving top 5 directly. Critical for legal precision.

---

## 3. LLM/Foundation Models via Bedrock — Pricing

All prices per 1M tokens, on-demand, March 2026:

| Model | Input $/1M | Output $/1M | Best RAG Use |
|---|---|---|---|
| **Claude 3.5 Sonnet v2** | $3.00 | $15.00 | Complex legal reasoning, long-context synthesis |
| **Claude 3.5 Haiku** | $0.80 | $4.00 | High-volume Q&A, chatbots, simple lookup |
| Claude 3 Haiku | $0.25 | $1.25 | Budget, simple extraction |
| Claude 3 Opus | $15.00 | $75.00 | Critical decisions, highest accuracy |
| Llama 3 70B | $0.99 | $0.99 | Open model, symmetric pricing |
| Llama 3 8B | ~$0.30 | ~$0.60 | Cheapest capable model |
| Amazon Nova Pro | $0.80 | $3.20 | AWS native, competitive |
| Amazon Nova Micro | $0.035 | $0.14 | Absolute cheapest on AWS |

**Batch inference:** 50% discount on any model. Ideal for ingestion-time summarization.

**LegalRAG recommendation:** Claude 3.5 Haiku for standard Q&A, Claude 3.5 Sonnet v2 for complex legal reasoning.

---

## 4. Document Processing

### Amazon Textract

| API Type | First 1M Pages | After 1M |
|---|---|---|
| DetectDocumentText (OCR) | $0.0015 | $0.0006 |
| AnalyzeDocument — Tables | $0.015 | $0.010 |
| AnalyzeDocument — Forms | $0.050 | $0.040 |
| Queries (custom extraction) | $0.065 | $0.050 |

**Key patterns:**
- Use async `StartDocumentAnalysis` + SNS notification for large PDFs
- Sync API for single pages in real-time upload flows
- Tables API critical for legal contracts with structured clauses

### Amazon Comprehend

- Entity detection: $0.0001 per 100-character unit
- Key phrase extraction: $0.0001 per unit
- **RAG use:** Tag chunks with entities → filter retrieved chunks by entity type at query time
- Legal entities: PERSON, ORGANIZATION, DATE, LOCATION, QUANTITY, TITLE

---

## 5. Architecture Patterns (Relevant to LegalRAG)

### Pattern 1: LegalRAG Core (Matches Diagram)

```
INGESTION:
[Data KB] + [UI Upload]
    → [S3 Bucket] (versioned, KMS encrypted)
    → [EventBridge] → [Lambda: Validate + Route]
    → [Textract] (PDF/image OCR, table extraction)
    → [Lambda: Chunker] (hierarchical: parent 1500t, child 512t)
    → [Comprehend] (entity extraction → metadata)
    → [Bedrock: Titan V2] (1024-dim embeddings)
    → [OpenSearch Serverless] (kNN + BM25 hybrid index)

QUERY:
[User Query]
    → [Lambda: Embed] (Titan V2)
    → [OpenSearch: Hybrid Search] (BM25 + kNN, k=15)
    → [Bedrock: Cohere Rerank 3.5] (top 5)
    → [Bedrock: Claude 3.5 Haiku/Sonnet] (streaming)
    → [SSE Response + citations]
```

### Pattern 2: Production with Step Functions

```
[S3 Upload]
  → [EventBridge Rule]
  → [Step Functions State Machine]
       ├── Lambda: Validate + classify doc type (contract/policy/regulation)
       ├── Choice: PDF / DOCX / HTML / Image
       │     PDF: Textract Async + Tables → SNS → Lambda parse
       │     DOCX: python-docx
       │     HTML: BeautifulSoup
       ├── Lambda: Hierarchical chunking (parent 1500 + child 512 tokens)
       ├── Lambda: Comprehend entity extraction → metadata tags
       ├── Map State: Parallel batch embedding (Titan V2, batch API)
       ├── Lambda: OpenSearch bulk upsert
       ├── DynamoDB: Write ingestion record + version
       └── SNS: Notify admin on completion
```

### Pattern 3: Agentic Legal RAG (Bedrock Agents)

```
[User]
  → [Bedrock Agent] (Claude 3.5 Sonnet as orchestrator)
       ├── Knowledge Base Query → OpenSearch (case law, contracts)
       ├── Action Group: GetCaseStatus → Lambda → Case Management System
       ├── Action Group: LookupRegulation → Lambda → Regulatory DB
       └── Action Group: GenerateSummary → Lambda → Document summarizer
```

### Pattern 4: GraphRAG for Legal Networks

```
[Legal Documents]
  → [Neptune Analytics KB]
     (auto-generates: entities, relationships, citations, cross-references)
  → Query: "Find all cases that cite Smith v. Jones and relate to contract breach"
     → Graph traversal + vector similarity (30-40% better multi-hop accuracy)
```

### Pattern 5: Hybrid Search Query (OpenSearch)

```python
{
  "query": {
    "hybrid": {
      "queries": [
        {"match": {"text": {"query": user_query, "boost": 0.3}}},  # BM25
        {"knn": {"embedding": {"vector": query_vector, "k": 15, "boost": 0.7}}}  # vector
      ]
    }
  }
}
```

---

## 6. Bedrock Knowledge Bases — Deep Dive

### End-to-End Flow
1. Connect data sources: S3, Confluence, SharePoint, Salesforce, Web Crawler
2. Configure chunking strategy
3. Select embedding model (Titan V2 or Cohere Embed v3)
4. Select vector store (OpenSearch Serverless default)
5. Sync → triggers ingestion pipeline
6. Query via `RetrieveAndGenerate` (one-call RAG) or `Retrieve` (retrieval only)

### Chunking Strategies

| Strategy | Best For | Config |
|---|---|---|
| Fixed | General docs | 300-1024 tokens, configurable overlap |
| Semantic | Dense technical docs | Groups by embedding similarity threshold |
| **Hierarchical** | **Legal docs, manuals** | Parent: 1500t, Child: 300t |
| Custom Lambda | Proprietary formats | Your Lambda handles chunking |

**For LegalRAG:** Hierarchical is best — embed child chunks for precision, return parent for full clause context.

### Metadata Filtering for RBAC

```python
# User can only see their department's documents
filter={
    "andAll": [
        {"equals": {"key": "department", "value": user_dept}},
        {"in": {"key": "clearance_level", "value": user_clearance_levels}}
    ]
}
```

Works with `.metadata.json` sidecar files in S3. Multi-tenant from single knowledge base.

### Limitations vs Custom RAG

| Feature | Bedrock KB | Custom RAG |
|---|---|---|
| Setup time | Hours | Days |
| Streaming responses | No | Yes |
| Hybrid search | Yes (OpenSearch) | Full control |
| Custom chunking | Lambda only | Any code |
| Reranking | Not built-in | Full control |
| Cost at scale | Higher overhead | Lower with tuning |
| **LegalRAG verdict** | Good for MVP | Production = custom |

---

## 7. Bedrock Agents — Deep Dive

### Core Components

| Component | Purpose |
|---|---|
| Foundation Model | Reasoning engine (Claude 3.5 Sonnet v2 recommended) |
| Knowledge Bases | The agent decides when to query |
| Action Groups | Lambda functions with OpenAPI schema for deterministic ops |
| Guardrails | Content filtering on inputs and outputs |
| Memory | Built-in session history management |

### Multi-Agent Collaboration (GA March 2025)

**Supervisor mode:** Supervisor breaks tasks → delegates to specialists → synthesizes.

**Supervisor + routing mode:** Simple requests → direct sub-agent (fast). Complex → full orchestration.

### Bedrock AgentCore (GA October 2025)

Production runtime for agents:

| Feature | Details |
|---|---|
| **Runtime** | Serverless, per-session microVM, 8-hour execution windows |
| **Session isolation** | Dedicated CPU/memory/filesystem per user session |
| **Memory** | Episodic + semantic. Self-managed extraction pipelines |
| **Gateway** | Auto-converts APIs + Lambda → MCP tools |
| **Browser** | Secure browser runtime for web workflows |
| **Code Interpreter** | Sandboxed Python execution |
| **Policy** | Intercept + govern tool calls before execution |
| **Protocol** | A2A (Agent-to-Agent) support, bidirectional streaming |

**LegalRAG use case:** AgentCore for a legal research agent that can browse court databases, execute code for date calculations, and maintain 8-hour research sessions.

---

## 8. Cost Estimates (Monthly)

### Tier 1: Small — 10K docs, 100 queries/day

| Component | Config | Cost |
|---|---|---|
| OpenSearch Serverless | 4 OCU min | ~$350 |
| Textract ingestion | 50K pages (one-time) | ~$75 |
| Titan Embed queries | 100/day × 30 | ~$0.01 |
| Claude 3.5 Haiku | 100 queries/day | ~$5 |
| S3 + DynamoDB + Lambda | — | ~$3 |
| **Total** | | **~$360-435** |

> **Optimization:** Replace OpenSearch with Aurora pgvector (~$100/mo) → total drops to ~$185/month

### Tier 2: Medium — 100K docs, 1K queries/day

| Component | Config | Cost |
|---|---|---|
| OpenSearch Serverless | 6-8 OCU | ~$525-700 |
| Claude 3.5 Haiku | 1K queries/day | ~$48 |
| Cohere Rerank | 1K queries/day | ~$30 |
| ElastiCache Valkey | Semantic cache | ~$50 |
| Lambda + Fargate | — | ~$30 |
| S3 + DynamoDB + CloudWatch | — | ~$15 |
| **Total** | | **~$700-900** |

### Tier 3: Large — 1M docs, 10K queries/day

| Component | Config | Cost |
|---|---|---|
| OpenSearch Serverless | 20+ OCU | ~$3,500 |
| S3 Vectors | Cold archive (90% savings) | ~$50 |
| Claude 3.5 Haiku | + cache hits | ~$480 |
| Cohere Rerank | 10K queries/day | ~$300 |
| ElastiCache cluster | Semantic cache | ~$200 |
| ECS Fargate workers | Ingestion | ~$150 |
| S3 + Textract | Ongoing | ~$75 |
| Observability | CloudWatch + X-Ray | ~$50 |
| **Total** | | **~$4,800-5,800** |

### Cost Optimization Playbook

1. **S3 Vectors for cold + OpenSearch for hot** — 90% storage savings
2. **Batch embed at ingestion** — 50% cheaper vs on-demand
3. **ElastiCache semantic cache** — 30-60% inference savings on repeated queries
4. **Claude 3.5 Haiku not Sonnet** for simple Q&A — 80% cost reduction
5. **256-dim Titan V2 (MRL)** — 75% vector storage savings, only 3% accuracy loss
6. **Provisioned Throughput** for >10M tokens/month — reduces effective per-token cost

---

## 9. Security & Compliance

### IAM Minimal Policy for Bedrock

```json
{
  "Action": [
    "bedrock:InvokeModel",
    "bedrock:InvokeModelWithResponseStream",
    "bedrock:Retrieve",
    "bedrock:RetrieveAndGenerate"
  ],
  "Resource": [
    "arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-v2:0",
    "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-*",
    "arn:aws:bedrock:us-east-1:ACCOUNT:knowledge-base/*"
  ]
}
```

Plus `aoss:APIAccessAll` for OpenSearch Serverless.

### VPC Endpoints (PrivateLink)

Create Interface endpoints for `bedrock-runtime` and `bedrock-agent-runtime`. All traffic stays within VPC — never traverses public internet.

### Bedrock Guardrails — 6 Filter Types

| Filter | What it blocks | LegalRAG use |
|---|---|---|
| Content filters | Hate, violence, prompt attacks | Block adversarial inputs |
| Denied topics | Custom topic blocks | "Don't discuss pending litigation" |
| Word filters | Profanity, custom words | Company-specific terms |
| PII detection | SSN, DOB, email, phone, address (25+ types) | REDACT or BLOCK client PII |
| Contextual grounding | Hallucinations, ungrounded responses | Critical for legal — block non-cited answers |
| Code security (2025) | Malicious code injection | For code-gen use cases |

### Compliance

| Standard | Status | Requirement |
|---|---|---|
| SOC 2 | Certified | KMS encryption at rest + transit |
| HIPAA | Eligible | BAA + model invocation logging |
| GDPR | Supported | PII guardrails + VPC PrivateLink + data residency |

---

## 10. Observability & Evaluation

### CloudWatch Custom Metrics (RAG/Production namespace)

- `RetrievedChunks` — number of chunks per query
- `ResponseTokens` — output token count
- `LatencyMs` — end-to-end query latency
- `CacheHit` — semantic cache hit rate (1/0)
- `FaithfulnessScore` — RAGAS metric per query (async)

### Bedrock Model Invocation Logging

Enable via `put_model_invocation_logging_configuration`. Sends all inputs/outputs to CloudWatch + S3. Required for HIPAA. Full audit trail.

### RAGAS Evaluation (Bedrock-native, no OpenAI)

```python
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_recall, context_precision
from langchain_aws import ChatBedrock
from ragas.llms import LangchainLLMWrapper

ragas_llm = LangchainLLMWrapper(
    ChatBedrock(model_id="anthropic.claude-3-5-haiku-20241022-v1:0")
)
results = evaluate(dataset=dataset, metrics=[faithfulness, answer_relevancy, context_recall, context_precision], llm=ragas_llm)
```

**Target thresholds for legal RAG:**

| Metric | Target | Why |
|---|---|---|
| Faithfulness | > 0.90 | No hallucinated legal citations |
| Answer Relevancy | > 0.85 | On-topic responses |
| Context Precision | > 0.80 | Retrieved right chunks |
| Context Recall | > 0.75 | Didn't miss key chunks |

### Additional Tools

- **LangSmith:** Deep LangChain tracing — drill into embedding, retrieval, ranking, generation
- **Langfuse:** Open-source LLM observability (self-hosted option)
- **AWS X-Ray:** Distributed tracing across Lambda + ECS
- **Arize Phoenix:** ML observability with RAG-specific metrics

---

## 11. Semantic Caching with ElastiCache

ElastiCache for Valkey (Redis-compatible) has vector search built in (GA 2024).

**Pattern:**
```
User Query → embed (256-dim) → ElastiCache vector search
  → similarity > 0.95? → return cached response (microseconds)
  → else: run full RAG pipeline → cache result (TTL: 1hr)
```

**Impact:** Latency: seconds → microseconds for cache hits. 30-60% Bedrock API cost reduction.

---

## 12. What AI Agents Can Do on Top of LegalRAG

| Capability | How |
|---|---|
| Multi-hop reasoning | Agent queries KB multiple times across related docs |
| Self-correcting RAG | Detects low confidence → reformulates query → re-retrieves |
| Adaptive retrieval | Expands search radius if initial chunks are low relevance |
| Cross-system orchestration | KB + case management system + regulatory DB |
| Knowledge graph traversal | Neptune GraphRAG for case citation networks |
| Web augmentation | Action Group fetches latest regulatory updates |
| Document comparison | Agent retrieves two contract versions → diff analysis |
| Timeline extraction | Agent traces dates/events across multiple documents |

---

## 13. AWS Services Quick Reference Map

```
DATA SOURCES:
  S3 (primary), Confluence (KB connectors), SharePoint (KB connectors), Web Crawler

PROCESSING:
  Textract ($0.0015-$0.065/page) — OCR, tables, forms
  Comprehend (entities, key phrases) — metadata enrichment
  Step Functions — orchestration for complex multi-step ingestion

EMBEDDING:
  Titan V2 ($0.02/1M, 256-1024 dims, MRL) ← PRIMARY CHOICE
  Cohere Embed v3 ($0.10/1M, multilingual, multimodal) ← multilingual docs

VECTOR STORAGE:
  OpenSearch Serverless ($350+/mo, hybrid BM25+vector) ← PRIMARY
  Aurora pgvector ($100+/mo) ← cost-sensitive small deployments
  Neptune Analytics ($200+/mo, GraphRAG) ← multi-hop legal reasoning
  S3 Vectors (pay-per-use, 90% cheaper) ← cold archive

CACHING:
  ElastiCache Valkey (semantic cache, vector search, microsecond hits)
  DynamoDB (session history, ingestion metadata, TTL auto-expiry)

RERANKING:
  Cohere Rerank 3.5 ($1/1K queries) ← CRITICAL for legal precision
  Amazon Rerank v1.0 ($1/1K queries) ← alternative

GENERATION:
  Claude 3.5 Haiku ($0.80/$4 per 1M) ← standard Q&A
  Claude 3.5 Sonnet v2 ($3/$15 per 1M) ← complex legal reasoning
  Nova Micro ($0.035/$0.14 per 1M) ← cheapest fallback

ORCHESTRATION:
  Lambda (simple handlers, <15min)
  Step Functions (document processing pipelines)
  ECS Fargate (long-running ingestion workers)
  Bedrock Agents (agentic legal research)
  Bedrock AgentCore (production agent runtime, microVM isolation)

SECURITY:
  IAM least privilege
  VPC Endpoints (PrivateLink for Bedrock)
  KMS CMK encryption
  Bedrock Guardrails (grounding check critical for legal)
  Metadata filtering (RBAC per department/clearance)

OBSERVABILITY:
  CloudWatch (custom RAG metrics + logs + alarms)
  X-Ray (distributed traces)
  Bedrock invocation logging (audit trail)
  RAGAS (faithfulness, relevancy, precision, recall)
  LangSmith (deep LangChain tracing)
```

---

## Sources

- [Amazon Bedrock Knowledge Bases](https://aws.amazon.com/bedrock/knowledge-bases/)
- [OpenSearch Service Pricing](https://aws.amazon.com/opensearch-service/pricing/)
- [Amazon Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/)
- [Titan Text Embeddings V2](https://aws.amazon.com/blogs/aws/amazon-titan-text-v2-now-available-in-amazon-bedrock-optimized-for-improving-rag/)
- [Amazon S3 Vectors GA](https://aws.amazon.com/blogs/aws/amazon-s3-vectors-now-generally-available-with-increased-scale-and-performance/)
- [Aurora pgvector 67x Faster](https://aws.amazon.com/blogs/database/load-vector-embeddings-up-to-67x-faster-with-pgvector-and-amazon-aurora/)
- [MemoryDB Vector Search GA](https://aws.amazon.com/blogs/aws/vector-search-for-amazon-memorydb-is-now-generally-available/)
- [Neptune GraphRAG GA](https://aws.amazon.com/blogs/machine-learning/announcing-general-availability-of-amazon-bedrock-knowledge-bases-graphrag-with-amazon-neptune-analytics/)
- [Bedrock Agents](https://aws.amazon.com/blogs/aws/introducing-multi-agent-collaboration-capability-for-amazon-bedrock/)
- [Bedrock AgentCore](https://aws.amazon.com/bedrock/agentcore/)
- [ElastiCache Semantic Cache](https://aws.amazon.com/blogs/database/lower-cost-and-latency-for-ai-using-amazon-elasticache-as-a-semantic-cache-with-amazon-bedrock/)
- [Bedrock Guardrails](https://aws.amazon.com/bedrock/guardrails/)
- [RBAC with Metadata Filtering](https://aws.amazon.com/blogs/machine-learning/access-control-for-vector-stores-using-metadata-filtering-with-knowledge-bases-for-amazon-bedrock/)
- [Cohere Embed 3 Multimodal](https://aws.amazon.com/about-aws/whats-new/2025/01/amazon-bedrock-multimodal-cohere-embed-3-multilingual-english/)
- [RAGAS Evaluation with Bedrock](https://aws.amazon.com/blogs/machine-learning/evaluate-rag-responses-with-amazon-bedrock-llamaindex-and-ragas/)
- [Bedrock Advanced Chunking](https://aws.amazon.com/blogs/machine-learning/amazon-bedrock-knowledge-bases-now-supports-advanced-parsing-chunking-and-query-reformulation-giving-greater-control-of-accuracy-in-rag-based-applications/)
- [Vector DB Comparison on AWS](https://docs.aws.amazon.com/prescriptive-guidance/latest/choosing-an-aws-vector-database-for-rag-use-cases/vector-db-comparison.html)
