import logging
from pathlib import Path
from typing import Optional

import requests

from core.retrieval.retrieve import search

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

OLLAMA_API_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "llama3.1:latest"   # fixed: was "llama3.1"
DEFAULT_N_RETRIEVE = 3
MAX_PROMPT_CHARS = 8000


def build_prompt(question: str, chunks: list[dict], previous_answers: Optional[list[str]] = None) -> str:
    context = "\n\n".join(
        [f"[{chunk['source']}]\n{chunk['text']}" for chunk in chunks]
    )
    prompt = f"""You are an intelligent AI Knowledge Assistant.

Your goal is to answer the user's question naturally and accurately.

Instructions:
1. Answer ONLY using information relevant to the question.
2. Ignore any retrieved context that discusses unrelated topics.
3. Do not combine information from different products or documents
   unless they clearly refer to the same subject.
4. If context is insufficient, say:
   "I couldn't find enough information in the knowledge base."
5. Keep answers concise and factual.

Retrieved Context:
{context}

"""
    if previous_answers:
        prompt += "Previous answers (do not repeat these verbatim):\n"
        for idx, prev in enumerate(previous_answers[-5:], start=1):
            prompt += f"[{idx}] {prev}\n"
        prompt += "\n"

    prompt += f"QUESTION:\n{question}\n\nANSWER:\n"
    return prompt


def trim_chunks_to_max_prompt_size(
    question: str, chunks: list[dict], max_chars: int = MAX_PROMPT_CHARS
) -> tuple[list[dict], bool]:
    if not chunks or len(build_prompt(question, chunks)) <= max_chars:
        return chunks, False
    for k in range(len(chunks) - 1, 0, -1):
        if len(build_prompt(question, chunks[:k])) <= max_chars:
            return chunks[:k], True
    return chunks[:1], True


def call_ollama(
    prompt: str,
    model: str = DEFAULT_MODEL,
    ollama_url: str = OLLAMA_API_URL,
    temperature: float = 0.3,
) -> Optional[str]:
    try:
        logger.info("Calling Ollama model: %s temperature: %.2f", model, temperature)
        response = requests.post(
            ollama_url,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "temperature": temperature,
            },
            timeout=300,
        )
        response.raise_for_status()
        answer = response.json().get("response", "").strip()
        logger.info("Answer generated (%d chars)", len(answer))
        return answer
    except requests.exceptions.ConnectionError:
        logger.error("Cannot connect to Ollama at %s — is it running?", ollama_url)
        return None
    except requests.exceptions.Timeout:
        logger.error("Ollama request timed out")
        return None
    except Exception as exc:
        logger.error("Ollama error: %s", repr(exc))
        return None


def extract_sources(chunks: list[dict]) -> list[dict]:
    sources_map: dict[str, float] = {}
    for chunk in chunks:
        src = chunk["source"]
        sim = chunk.get("similarity", 0)
        if src not in sources_map or sim > sources_map[src]:
            sources_map[src] = sim
    return [
        {"source": src, "relevance": sim}
        for src, sim in sorted(sources_map.items(), key=lambda x: x[1], reverse=True)
    ]


def boost_filename_matches(question: str, chunks: list[dict]) -> list[dict]:
    """Boost chunks whose filename appears in the question."""
    question_lower = question.lower()
    for chunk in chunks:
        source_name = chunk.get("source", "").lower()
        name_parts = source_name.replace("_", " ").replace(".", " ").replace("-", " ").split()
        if any(part in question_lower for part in name_parts if len(part) > 1):
            original = chunk["similarity"]
            chunk["similarity"] = min(1.0, chunk["similarity"] + 0.15)
            logger.info("Filename boost: %s %.4f → %.4f", source_name, original, chunk["similarity"])
    return chunks


def generate_answer(
    question: str,
    model: str = DEFAULT_MODEL,
    n_retrieve: int = DEFAULT_N_RETRIEVE,
    ollama_url: str = OLLAMA_API_URL,
    temperature: float = 0.3,
    previous_answers: Optional[list[str]] = None,
    retrieved_chunks: Optional[list[dict]] = None,
) -> Optional[dict]:
    try:
        logger.info("RAG pipeline: %s", question)

        # Step 1: Retrieve
        if retrieved_chunks is not None:
            chunks = retrieved_chunks
        else:
            chunks = search(question, n_results=n_retrieve * 2).get("results", [])

        if not chunks:
            return {
                "query": question,
                "answer": "I couldn't find any relevant information in the knowledge base.",
                "sources": [], "chunks_used": 0, "model": model,
                "fallback_used": False, "truncation_used": False,
            }

        # Step 2: Apply filename boost BEFORE sorting and threshold check
        chunks = boost_filename_matches(question, chunks)

        # Step 3: Sort and filter to top N within 0.05 of best score
        chunks = sorted(chunks, key=lambda x: x.get("similarity", 0), reverse=True)
        best_score = chunks[0]["similarity"]
        chunks = [c for c in chunks if c["similarity"] >= best_score - 0.05][:n_retrieve]

        # Debug
        print("\n" + "=" * 80)
        print("RETRIEVED CHUNKS")
        print("=" * 80)
        for i, chunk in enumerate(chunks, 1):
            print(f"\nChunk {i} | {chunk['source']} | sim={chunk['similarity']}")
            print(chunk["text"][:300])

        # Step 4: Bail if best match is too weak
        if chunks[0].get("similarity", 0) < 0.45:
            logger.warning("Top similarity %.4f below threshold", chunks[0].get("similarity", 0))
            return {
                "query": question,
                "answer": "I couldn't find any relevant information in the knowledge base.",
                "sources": [], "chunks_used": 0, "model": model,
                "fallback_used": False, "truncation_used": False,
            }

        # Step 5: Trim prompt if needed
        chunks, truncation_used = trim_chunks_to_max_prompt_size(question, chunks)

        # Step 6: Build prompt and call LLM
        prompt = build_prompt(question, chunks, previous_answers=previous_answers)
        answer = call_ollama(prompt, model, ollama_url, temperature)

        # Step 7: Fallback with fewer chunks if generation failed
        fallback_used = False
        if not answer:
            for k in range(len(chunks) - 1, 0, -1):
                short_prompt = build_prompt(question, chunks[:k])
                answer = call_ollama(short_prompt, model, ollama_url, temperature)
                if answer:
                    chunks = chunks[:k]
                    fallback_used = True
                    break

        if not answer:
            logger.error("Generation failed after all retries")
            return None

        return {
            "query": question,
            "answer": answer,
            "sources": extract_sources(chunks),
            "chunks_used": len(chunks),
            "retrieved_chunks": chunks,
            "model": model,
            "fallback_used": fallback_used,
            "truncation_used": truncation_used,
        }

    except Exception as exc:
        logger.error("RAG pipeline error: %s", exc)
        return None


if __name__ == "__main__":
    result = generate_answer("What is the main topic?")
    if result:
        print(f"\nAnswer: {result['answer']}")
        print(f"Sources: {result['sources']}")