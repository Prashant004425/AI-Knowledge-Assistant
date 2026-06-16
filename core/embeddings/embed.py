import json
import logging
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path.cwd()
CHUNKS_FILE = BASE_DIR / "data" / "processed" / "chunks.json"
VECTORSTORE_DIR = BASE_DIR / "data" / "vectorstore"

BATCH_SIZE = 128

# Load model only once
_MODEL: SentenceTransformer | None = None


def load_model(model_name: str = "BAAI/bge-small-en-v1.5") -> SentenceTransformer:
    global _MODEL

    if _MODEL is None:
        logger.info("Loading embedding model: %s", model_name)
        _MODEL = SentenceTransformer(model_name)

    return _MODEL


def load_chunks(chunks_file: Path = CHUNKS_FILE) -> list[dict]:
    if not chunks_file.exists():
        raise FileNotFoundError(f"Chunks file not found: {chunks_file}")

    with chunks_file.open("r", encoding="utf-8") as f:
        chunks = json.load(f)

    logger.info("Loaded %d chunks", len(chunks))
    return chunks


def initialize_vectorstore(
    vectorstore_dir: Path = VECTORSTORE_DIR,
) -> chromadb.PersistentClient:
    vectorstore_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(vectorstore_dir))


def create_or_get_collection(
    client: chromadb.PersistentClient,
    name: str = "knowledge_base",
):
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


def get_existing_ids(collection) -> set[str]:
    try:
        result = collection.get(include=[])
        return set(result["ids"])
    except Exception:
        return set()


def embed_and_store(
    chunks: list[dict],
    model: SentenceTransformer,
    client: chromadb.PersistentClient,
    collection_name: str = "knowledge_base",
    batch_size: int = BATCH_SIZE,
    incremental: bool = True,
) -> int:

    collection = create_or_get_collection(client, collection_name)

    if incremental:
        existing_ids = get_existing_ids(collection)
        chunks = [c for c in chunks if c["id"] not in existing_ids]

        logger.info(
            "Skipping %d already indexed chunks",
            len(load_chunks()) - len(chunks),
        )

    if not chunks:
        logger.info("Nothing new to embed.")
        return 0

    texts = [c["text"] for c in chunks]
    ids = [c["id"] for c in chunks]
    metadatas = [{"source": c["source"]} for c in chunks]

    logger.info("Embedding %d chunks...", len(texts))

    embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]

        batch_embeddings = model.encode(
            batch,
            convert_to_numpy=True,
            show_progress_bar=False,
        ).tolist()

        embeddings.extend(batch_embeddings)

    for i in range(0, len(texts), batch_size):
        collection.add(
            documents=texts[i:i + batch_size],
            embeddings=embeddings[i:i + batch_size],
            ids=ids[i:i + batch_size],
            metadatas=metadatas[i:i + batch_size],
        )

    logger.info("Stored %d chunks", len(texts))
    return len(texts)


def main(
    model_name: str = "BAAI/bge-small-en-v1.5",
    chunks_file: Path = CHUNKS_FILE,
    vectorstore_dir: Path = VECTORSTORE_DIR,
    collection_name: str = "knowledge_base",
    incremental: bool = True,
    new_sources=None,
) -> None:
    """
    new_sources is accepted so Streamlit can call:
    embed_pipeline(new_sources=...)
    """

    logger.info("embed.py main() called")

    model = load_model(model_name)
    chunks = load_chunks(chunks_file)
    client = initialize_vectorstore(vectorstore_dir)

    count = embed_and_store(
        chunks=chunks,
        model=model,
        client=client,
        collection_name=collection_name,
        incremental=incremental,
    )

    logger.info("Embedding complete: %d chunks", count)
    print(f"✓ Done — {count} chunks indexed")


if __name__ == "__main__":
    main()