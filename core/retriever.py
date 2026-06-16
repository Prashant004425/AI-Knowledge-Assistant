import logging
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path.cwd()
VECTORSTORE_DIR = BASE_DIR / "data" / "vectorstore"

MODEL = None


def load_model(model_name: str = "BAAI/bge-small-en-v1.5") -> SentenceTransformer:
    logger.info("Loading retrieval model: %s", model_name)
    return SentenceTransformer(model_name)


def get_model() -> SentenceTransformer:
    """Return the module-level model, initializing it on first call."""
    global MODEL
    if MODEL is None:
        MODEL = load_model()
    return MODEL


def initialize_vectorstore(vectorstore_dir: Path = VECTORSTORE_DIR) -> chromadb.PersistentClient:
    if not vectorstore_dir.exists():
        raise FileNotFoundError(f"Vectorstore not found: {vectorstore_dir}")
    return chromadb.PersistentClient(path=str(vectorstore_dir))


def get_collection(client: chromadb.PersistentClient, name: str = "knowledge_base") -> chromadb.Collection:
    return client.get_collection(name=name)


def encode_query(query: str, model: SentenceTransformer) -> list[float]:
    return model.encode(query, convert_to_numpy=True).tolist()


def retrieve(query: str, n_results: int = 5) -> dict:
    client = initialize_vectorstore()
    collection = get_collection(client)

    query_embedding = encode_query(query, get_model())

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances", "ids"],
    )

    hits = []

    for doc, meta, dist, chunk_id in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
        results["ids"][0],
    ):
        similarity = 1 - (dist / 2)

        hits.append({
            "id": chunk_id,
            "text": doc,
            "source": meta.get("source", "unknown"),
            "similarity": round(similarity, 4),
        })

    return {
        "query": query,
        "results": hits,
        "num_results": len(hits),
    }


def search(query: str, n_results: int = 5) -> dict:
    """Public alias used by the RAG pipeline."""
    return retrieve(query, n_results=n_results)


if __name__ == "__main__":
    print(retrieve("What is FloCard?", n_results=3))