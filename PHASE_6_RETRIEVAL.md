# Phase 6: Semantic Search & Retrieval System

## Overview

The retrieval system performs **semantic search** over the knowledge base by:
1. Converting user queries to embeddings
2. Searching the vector database (Chroma)
3. Returning top-ranked results by similarity

---

## Module: `core/retrieval/retrieve.py`

### Core Functions

#### `encode_query(query, model) → list[float]`
Converts a user query string into a semantic embedding vector.

```python
query_embedding = encode_query("What is FloCard?", model)
# Returns: [0.12, -0.55, 0.91, ...] (384 dimensions)
```

#### `retrieve(query, model, collection, n_results=5) → dict`
Main semantic search function.

**Input:**
- `query`: Natural language question
- `model`: SentenceTransformer instance
- `collection`: Chroma collection
- `n_results`: Number of top results to return

**Output:**
```json
{
  "query": "What is FloCard?",
  "num_results": 5,
  "results": [
    {
      "id": "flocard_api_guide_chunk_001",
      "text": "FloCard is a payment processing API...",
      "source": "flocard_api_guide.md",
      "similarity": 0.8456
    },
    ...
  ]
}
```

#### `search(query, ...) → dict`
Complete pipeline: loads model, connects to vectorstore, retrieves results.

```python
from core.retrieval.retrieve import search

results = search("How do I authenticate?", n_results=3)
print(f"Found {results['num_results']} relevant chunks")
for result in results['results']:
    print(f"  - {result['source']}: {result['similarity']}")
```

#### `format_results(retrieval_output) → str`
Formats results for display.

```python
display = format_results(results)
print(display)
# 📚 Query: How do I authenticate?
# ✓ Found 3 relevant chunks
#
# [1] flocard_api_guide.md (similarity: 0.85)
#     ID: flocard_api_guide_chunk_002
#     Text: Authentication is required for all API calls...
```

---

## Architecture

```
User Query
    ↓
    └─→ encode_query()
        ↓
        └─→ [0.12, -0.55, 0.91, ...]  (Embedding Vector)
            ↓
            └─→ Chroma Collection.query()
                ↓
                └─→ Cosine Similarity Search
                    ↓
                    └─→ Top N Results
                        ↓
                        └─→ Format & Return
```

---

## Vector Database Storage

**Location:** `data/vectorstore/`

**Backend:** Chroma + SQLite

**Metadata per chunk:**
- `id`: Unique chunk identifier
- `text`: Chunk content (document)
- `source`: Source file name
- `embedding`: 384-dimensional vector (BAAI/bge-small-en-v1.5)

**Search Configuration:**
- Metric: `cosine` similarity
- Normalized to 0-1 range (higher = more similar)

---

## Usage Examples

### Example 1: Simple Search

```python
from core.retrieval.retrieve import search

results = search("What is FloCard?", n_results=5)
print(f"Query: {results['query']}")
print(f"Results: {results['num_results']}")
for r in results['results']:
    print(f"  {r['id']}: {r['similarity']}")
```

### Example 2: Custom Model/Vectorstore

```python
from core.retrieval.retrieve import search
from pathlib import Path

results = search(
    query="How do I authenticate?",
    vectorstore_dir=Path("data/vectorstore"),
    collection_name="knowledge_base",
    n_results=3,
    model_name="BAAI/bge-small-en-v1.5"
)
```

### Example 3: Low-Level API

```python
from core.retrieval.retrieve import (
    load_model,
    initialize_vectorstore,
    get_collection,
    encode_query,
    retrieve
)

model = load_model()
client = initialize_vectorstore()
collection = get_collection(client)

query_embedding = encode_query("Your question?", model)
results = retrieve("Your question?", model, collection, n_results=5)
```

---

## Integration Points

### With Ingestion Pipeline
```
Raw Files → Ingest → Chunks.json → Embed → Vectorstore → Retrieve
```

### With LLM (Planned)
```
User Query → Retrieve Chunks → Combine with LLM Prompt → Generate Answer
```

### With API (Planned)
```
HTTP POST /search?query=... → retrieve() → JSON Response
```

---

## Performance Considerations

- **Query Encoding**: ~100ms (first load) + ~20ms (cached model)
- **Similarity Search**: <5ms for 5 chunks
- **Model Size**: ~450MB (cached after first use)
- **Storage**: <1MB for vectorstore (5 chunks)

---

## Error Handling

The module handles:
- Missing vectorstore directory
- Vectorstore not initialized
- Collection doesn't exist
- Empty search results
- Model loading failures

All errors are logged with detailed messages.

---

## Testing

Run example retrieval queries:
```bash
python core/retrieval/retrieve.py
```

This executes the `if __name__ == "__main__"` block with example queries:
- "What is FloCard?"
- "How do I authenticate with the API?"
- "What are the company policies?"

---

## Next: RAG Pipeline

The retrieval system feeds into Retrieval-Augmented Generation:

```
User Query
    ↓
    ├─→ Semantic Search (this module)
    ├─→ Retrieve Top Chunks
    ├─→ Combine with LLM Prompt
    └─→ Generate Contextual Answer
```

This enables the AI to provide accurate, source-backed answers.
