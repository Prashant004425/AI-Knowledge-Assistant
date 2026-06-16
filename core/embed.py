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


def load_model(model_name: str = "BAAI/bge-small-en-v1.5") -> SentenceTransformer:
    logger.info("Loading embedding model: %s", model_name)
    return SentenceTransformer(model_name)


def load_chunks(chunks_file: Path = CHUNKS_FILE) -> list[dict]:
    if not chunks_file.exists():
        raise FileNotFoundError(f"Chunks file not found: {chunks_file}")

    with chunks_file.open("r", encoding="utf-8") as handle:
        chunks = json.load(handle)

    logger.info("Loaded %d chunks", len(chunks))
    return chunks


def generate_embeddings(
    texts: list[str],
    model: SentenceTransformer,
) -> list[list[float]]:
    logger.info("Generating embeddings for %d texts", len(texts))
    return model.encode(
        texts,
        convert_to_numpy=True,
        show_progress_bar=False,
    ).tolist()


def initialize_vectorstore(
    vectorstore_dir: Path = VECTORSTORE_DIR,
) -> chromadb.PersistentClient:
    vectorstore_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(vectorstore_dir))


def create_or_get_collection(
    client: chromadb.PersistentClient,
    name: str = "knowledge_base",
) -> chromadb.Collection:
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


def embed_and_store(
    chunks: list[dict],
    model: SentenceTransformer,
    client: chromadb.PersistentClient,
    collection_name: str = "knowledge_base",
) -> int:

    collection = create_or_get_collection(client, collection_name)

    texts = [chunk["text"] for chunk in chunks]
    ids = [chunk["id"] for chunk in chunks]
    metadatas = [{"source": chunk["source"]} for chunk in chunks]

    embeddings = generate_embeddings(texts, model)

    collection.add(
        documents=texts,
        embeddings=embeddings,
        ids=ids,
        metadatas=metadatas,
    )

    logger.info(
        "Stored %d chunks in collection '%s'",
        len(chunks),
        collection_name,
    )

    return len(chunks)


def main(
    model_name: str = "BAAI/bge-small-en-v1.5",
    new_sources=None,
) -> None:
    """
    new_sources is accepted for compatibility with Streamlit upload workflow.
    Currently it is not used.
    """

    model = load_model(model_name)
    chunks = load_chunks()
    client = initialize_vectorstore()

    count = embed_and_store(
        chunks=chunks,
        model=model,
        client=client,
    )

    logger.info("Embedding complete: %d chunks", count)


if __name__ == "__main__":
    main()