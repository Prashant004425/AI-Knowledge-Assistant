import logging
import requests

from core.retrieval.retrieve import search

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/generate"


def build_prompt(question: str, chunks: list[dict]) -> str:
    context = "\n\n".join(
        [f"[{chunk['source']}]\n{chunk['text']}" for chunk in chunks]
    )
    return f"""You are an AI Knowledge Assistant.

Answer only the user's question using the context below.

Rules:
- Focus strictly on the question asked.
- Ignore unrelated context.
- Do not summarize all documents.
- Do not merge unrelated topics.
- Use only relevant information.
- Keep answers concise and natural.
- If the information is missing, say so clearly.

CONTEXT:
{context}

QUESTION:
{question}

ANSWER:
"""


def call_ollama(prompt: str, model: str = "llama3.1", temperature: float = 0.3) -> str | None:
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": model,
                "prompt": prompt,
                "temperature": temperature,
                "stream": False,
            },
            timeout=300,
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        logger.error("Cannot connect to Ollama. Is it running? Try: ollama serve")
        return None
    except requests.exceptions.Timeout:
        logger.error("Ollama request timed out")
        return None
    except Exception as exc:
        logger.error("Ollama error: %s", exc)
        return None


def generate_answer(
    question: str,
    n_retrieve: int = 3,
    temperature: float = 0.3,
    model: str = "llama3.1",
) -> dict | None:
    # Step 1: Retrieve chunks
    results = search(question, n_results=n_retrieve * 2)
    chunks = results.get("results", [])

    if not chunks:
        return {
            "query": question,
            "answer": "I couldn't find any relevant information in the knowledge base.",
            "sources": [],
            "chunks_used": 0,
        }

    # Sort by similarity, keep top N within 0.05 of best score
    chunks = sorted(chunks, key=lambda x: x.get("similarity", 0), reverse=True)
    best_score = chunks[0]["similarity"]
    chunks = [c for c in chunks if c["similarity"] >= best_score - 0.05][:n_retrieve]

    # Debug output
    print("\n" + "=" * 80)
    print("RETRIEVED CHUNKS")
    print("=" * 80)
    for i, chunk in enumerate(chunks, 1):
        print(f"\nChunk {i} | Source: {chunk.get('source')} | Similarity: {chunk.get('similarity')}")
        print(chunk.get("text", "")[:300])

    # Bail if best match is too weak
    if chunks[0].get("similarity", 0) < 0.60:
        logger.warning("Top similarity below threshold — no confident answer available")
        return {
            "query": question,
            "answer": "I couldn't find any relevant information in the knowledge base.",
            "sources": [],
            "chunks_used": 0,
        }

    # Step 2: Build prompt and call LLM
    prompt = build_prompt(question, chunks)
    answer = call_ollama(prompt, model=model, temperature=temperature)

    if not answer:
        return None

    # Step 3: Extract unique sources
    sources_map = {}
    for chunk in chunks:
        src = chunk["source"]
        sim = chunk.get("similarity", 0)
        if src not in sources_map or sim > sources_map[src]:
            sources_map[src] = sim

    sources = [
        {"source": src, "relevance": sim}
        for src, sim in sorted(sources_map.items(), key=lambda x: x[1], reverse=True)
    ]

    return {
        "query": question,
        "answer": answer,
        "sources": sources,
        "chunks_used": len(chunks),
        "retrieved_chunks": chunks,
        "model": model,
    }