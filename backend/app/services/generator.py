"""Bedrock LLM streaming generation with citations."""
import json
import os
from pathlib import Path
from typing import Generator
from app.utils.aws_clients import get_bedrock
from app.utils.logger import get_logger
from app.config import get_settings

logger = get_logger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent.parent.parent.parent / "prompts"


def load_prompt(filename: str) -> str:
    path = PROMPTS_DIR / filename
    if path.exists():
        return path.read_text()
    return ""


def build_context(chunks: list[dict]) -> str:
    parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {})
        source = meta.get("source", "Unknown")
        page = meta.get("page_number", "?")
        citation_id = meta.get("citation_id", f"ref-{i}")
        parts.append(f"[{i}] Source: {source}, Page {page} (ref: {citation_id})\n{chunk['text']}")
    return "\n\n---\n\n".join(parts)


def build_prompt(query: str, context: str, history: list[dict]) -> str:
    system_prompt = load_prompt("rag_system_prompt.txt")
    history_text = ""
    if history:
        history_text = "\n".join(
            f"{'User' if h['role'] == 'user' else 'Assistant'}: {h['content']}"
            for h in history[-6:]  # last 3 turns
        )

    return f"""{system_prompt}

<conversation_history>
{history_text}
</conversation_history>

<context>
{context}
</context>

<question>
{query}
</question>

Answer:"""


def _is_nova_model(model_id: str) -> bool:
    return "nova" in model_id.lower()


def _stream_via_euri(prompt: str, chunks: list[dict]) -> Generator[dict, None, None]:
    """Stream via Euri API (OpenAI-compatible SSE)."""
    from openai import OpenAI
    s = get_settings()
    client = OpenAI(api_key=s.euri_api_key, base_url=s.euri_base_url)
    stream = client.chat.completions.create(
        model=s.euri_llm_model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=s.max_tokens,
        temperature=s.temperature,
        stream=True,
    )
    for chunk in stream:
        if not chunk.choices:
            continue
        text = chunk.choices[0].delta.content or ""
        if text:
            yield {"type": "text", "content": text}

    sources = []
    for chunk in chunks:
        meta = chunk.get("metadata", {})
        sources.append({"source": meta.get("source", "Unknown"), "page": meta.get("page_number", "?"), "citation_id": meta.get("citation_id", "")})
    yield {"type": "sources", "sources": sources}


def stream_response(
    query: str,
    chunks: list[dict],
    history: list[dict] = None,
    use_smart_model: bool = False,
) -> Generator[dict, None, None]:
    """
    Stream LLM response token by token.
    Yields dicts: {"type": "text", "content": "..."} or {"type": "sources", "sources": [...]}
    """
    s = get_settings()
    history = history or []

    if not chunks:
        no_ctx = load_prompt("no_context_prompt.txt").format(question=query)
        yield {"type": "text", "content": no_ctx}
        return

    context = build_context(chunks)
    prompt = build_prompt(query, context, history)

    # Route to Euri if Bedrock unavailable
    if s.use_euri:
        yield from _stream_via_euri(prompt, chunks)
        return

    bedrock = get_bedrock()

    # Select model
    if use_smart_model:
        model_id = s.bedrock_llm_smart_model_id
    else:
        model_id = s.bedrock_llm_model_id

    logger.info(f"Generating with model: {model_id}")

    # Build request body based on model type
    if "claude" in model_id.lower():
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": s.max_tokens,
            "temperature": s.temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
    elif _is_nova_model(model_id):
        body = {
            "inferenceConfig": {"maxNewTokens": s.max_tokens, "temperature": s.temperature},
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
        }
    else:
        # Titan text models
        body = {
            "inputText": prompt,
            "textGenerationConfig": {
                "maxTokenCount": s.max_tokens,
                "temperature": s.temperature,
                "stopSequences": [],
            },
        }

    try:
        response = bedrock.invoke_model_with_response_stream(
            modelId=model_id,
            body=json.dumps(body),
        )

        for event in response["body"]:
            chunk_data = json.loads(event["chunk"]["bytes"])

            # Claude streaming
            if "delta" in chunk_data and chunk_data.get("type") == "content_block_delta":
                text = chunk_data["delta"].get("text", "")
                if text:
                    yield {"type": "text", "content": text}

            # Nova streaming
            elif "contentBlockDelta" in chunk_data:
                text = chunk_data["contentBlockDelta"].get("delta", {}).get("text", "")
                if text:
                    yield {"type": "text", "content": text}

            # Titan streaming
            elif "outputText" in chunk_data:
                yield {"type": "text", "content": chunk_data["outputText"]}

    except Exception as e:
        logger.error(f"Generation failed: {e}")
        yield {"type": "error", "content": f"Generation error: {str(e)}"}
        return

    # Send citations as final event
    sources = []
    for chunk in chunks:
        meta = chunk.get("metadata", {})
        sources.append({
            "source": meta.get("source", "Unknown"),
            "page": meta.get("page_number", "?"),
            "citation_id": meta.get("citation_id", ""),
        })

    yield {"type": "sources", "sources": sources}
