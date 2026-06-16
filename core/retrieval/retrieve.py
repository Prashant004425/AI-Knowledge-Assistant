import logging
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)

logger = logging.getLogger(__name__)

BASE_DIR = Path.cwd()
VECTORSTORE_DIR = BASE_DIR / "data" / "vectorstore"

# ------------------------------------------------------------------
# Global cached objects
# ------------------------------------------------------------------

_MODEL = None
_CLIENT = None
_COLLECTION = None


def load_model(
    model_name: str = "BAAI/bge-small-en-v1.5"
) -> SentenceTransformer:
    """
    Load embedding model only once.
    """
    global _MODEL

    if _MODEL is None:
        logger.info(
            "Loading embedding model: %s",
            model_name
        )
        _MODEL = SentenceTransformer(model_name)

    return _MODEL


def initialize_vectorstore(
    vectorstore_dir: Path = VECTORSTORE_DIR,
) -> chromadb.PersistentClient:
    """
    Connect to ChromaDB once.
    """
    global _CLIENT

    if _CLIENT is None:

        if not vectorstore_dir.exists():
            raise FileNotFoundError(
                f"Vectorstore not found at {vectorstore_dir}"
            )

        _CLIENT = chromadb.PersistentClient(
            path=str(vectorstore_dir)
        )

        logger.info(
            "Connected to vectorstore at %s",
            vectorstore_dir
        )

    return _CLIENT


def get_collection(
    client: chromadb.PersistentClient,
    name: str = "knowledge_base",
):
    """
    Load collection once.
    """
    global _COLLECTION

    if _COLLECTION is None:

        _COLLECTION = client.get_collection(
            name=name
        )

        logger.info(
            "Retrieved collection: %s",
            name
        )

    return _COLLECTION


def encode_query(
    query: str,
    model: SentenceTransformer,
) -> list[float]:

    return model.encode(
        query,
        convert_to_numpy=True,
        normalize_embeddings=True
    ).tolist()


def retrieve(
    query: str,
    model: SentenceTransformer,
    collection,
    n_results: int = 5,
) -> dict:

    query_embedding = encode_query(
        query,
        model
    )

    logger.info(
        "Searching for %d results matching query: %s",
        n_results,
        query
    )

    search_results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=[
            "documents",
            "metadatas",
            "distances"
        ]
    )

    results = []

    documents = search_results.get(
        "documents",
        [[]]
    )[0]

    metadatas = search_results.get(
        "metadatas",
        [[]]
    )[0]

    distances = search_results.get(
        "distances",
        [[]]
    )[0]

    ids = search_results.get(
        "ids",
        [[]]
    )[0]

    for doc, meta, dist, chunk_id in zip(
        documents,
        metadatas,
        distances,
        ids
    ):

        similarity = 1 - (dist / 2)

        if similarity >= 0.45:

            results.append(
                {
                    "id": chunk_id,
                    "text": doc,
                    "source": meta.get(
                        "source",
                        "unknown"
                    ),
                    "similarity": round(
                        similarity,
                        4
                    ),
                }
            )

    logger.info(
        "Retrieved %d relevant chunks",
        len(results)
    )

    return {
        "query": query,
        "num_results": len(results),
        "results": sorted(
            results,
            key=lambda x: x["similarity"],
            reverse=True
        ),
    }


def format_results(
    retrieval_output: dict
) -> str:

    output = []

    output.append(
        f"\n📚 Query: {retrieval_output['query']}"
    )

    output.append(
        f"✓ Found {retrieval_output['num_results']} relevant chunks\n"
    )

    for i, result in enumerate(
        retrieval_output["results"],
        start=1,
    ):

        output.append(
            f"[{i}] {result['source']} "
            f"(similarity: {result['similarity']})"
        )

        output.append(
            f"    ID: {result['id']}"
        )

        output.append(
            f"    Text: {result['text'][:100]}..."
        )

        output.append("")

    return "\n".join(output)


def search(
    query: str,
    vectorstore_dir: Path = VECTORSTORE_DIR,
    collection_name: str = "knowledge_base",
    n_results: int = 5,
    model_name: str = "BAAI/bge-small-en-v1.5",
) -> dict:

    model = load_model(model_name)

    client = initialize_vectorstore(
        vectorstore_dir
    )

    collection = get_collection(
        client,
        collection_name
    )

    output = retrieve(
        query=query,
        model=model,
        collection=collection,
        n_results=n_results,
    )

    logger.info(
        "Retrieval complete for query: %s",
        query
    )

    return output


if __name__ == "__main__":

    test_queries = [
        "What is FloCard?",
        "How do I authenticate?",
        "What are company policies?"
    ]

    for query in test_queries:

        try:

            results = search(
                query,
                n_results=3
            )

            print(
                format_results(results)
            )

        except Exception as exc:

            print(
                f"✗ Error searching for '{query}': {exc}"
            )