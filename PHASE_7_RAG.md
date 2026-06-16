# Phase 7: Retrieval-Augmented Generation (RAG) Pipeline

## Overview

RAG combines semantic search with LLM generation to create contextual, source-backed answers. The pipeline:

1. **Retrieves** relevant chunks from the vector database
2. **Builds** a prompt with context and the user's question
3. **Generates** an answer using a local LLM (via Ollama)
4. **Returns** the answer with citations and relevance scores

---

## Architecture

```
User Question
       ↓
   Retrieval (Phase 6)
       ↓
  Top-N Chunks + Metadata
       ↓
   Prompt Building
       ↓
   "You are an AI assistant..."
   "[Context chunks]"
   "[User question]"
       ↓
   LLM (Ollama + llama3.1)
       ↓
  Generated Answer
       ↓
  Format with Citations
       ↓
   Response Object
```

---

## Prerequisites: Install Ollama

### Step 1: Download Ollama

Download from: **https://ollama.ai**

Choose your operating system (Windows, macOS, Linux).

### Step 2: Run Ollama Service

After installation, start the Ollama service:

```bash
ollama serve
```

This starts the API server on `http://localhost:11434`

**Output:**
```
2026-05-29 12:00:00 INFO Listening on http://localhost:11434
```

### Step 3: Pull the Model

In another terminal:

```bash
ollama pull llama3.1
```

This downloads the Llama 3.1 model (~4.7 GB).

**Output:**
```
pulling manifest
pulling 9f438cb83e99
pulling d00ed0ee0a7c
pulling ...
success
```

### Step 4: Verify Installation

Test the Ollama API:

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.1",
  "prompt": "What is AI?",
  "stream": false
}'
```

You should get a JSON response with generated text.

---

## Module: `core/rag/generate.py`

### Core Functions

#### `build_prompt(question, chunks) → str`

Creates a prompt with retrieved context.

**Input:**
```python
question = "What is FloCard?"
chunks = [
    {"text": "FloCard is...", "source": "flocard_api_guide.md"},
    {"text": "FloCard allows...", "source": "payments_guide.md"},
]
```

**Output:**
```
You are a helpful AI assistant...

CONTEXT:

[flocard_api_guide.md]
FloCard is...

[payments_guide.md]
FloCard allows...

QUESTION:

What is FloCard?

ANSWER:
```

#### `call_ollama(prompt, model="llama3.1") → str`

Calls the Ollama API to generate an answer.

```python
answer = call_ollama(prompt, model="llama3.1")
# Returns: Generated text from LLM
```

**Parameters:**
- `prompt`: Full prompt with context
- `model`: Model name (default: llama3.1)
- `ollama_url`: API endpoint (default: http://localhost:11434/api/generate)
- `temperature`: Generation temperature 0-1 (default: 0.3, lower = deterministic)

**Error Handling:**
- Detects if Ollama is not running
- Handles timeouts gracefully
- Logs detailed error messages

#### `extract_sources(chunks) → list[dict]`

Extracts unique sources from retrieved chunks with relevance scores.

```python
sources = extract_sources(chunks)
# Returns: [
#   {"source": "flocard_api_guide.md", "relevance": 0.8456},
#   {"source": "payments_guide.md", "relevance": 0.7234},
# ]
```

#### `generate_answer(question, model="llama3.1", n_retrieve=5) → dict`

Complete RAG pipeline: retrieve → prompt → generate → format.

```python
result = generate_answer("What is FloCard?")
# Returns: {
#   "query": "What is FloCard?",
#   "answer": "FloCard is an internal payment platform...",
#   "sources": [{"source": "...", "relevance": 0.85}],
#   "chunks_used": 3,
#   "model": "llama3.1"
# }
```

#### `format_response(rag_output) → str`

Formats RAG output for display.

```python
display = format_response(result)
print(display)
# ❓ Question: What is FloCard?
# 💬 Answer: FloCard is...
# 📚 Sources (2 cited):
#   [1] flocard_api_guide.md (relevance: 84.56%)
#   [2] payments_guide.md (relevance: 72.34%)
# 🔧 Model: llama3.1
# 📊 Context chunks: 3
```

---

## RAG Pipeline Flow

### Step 1: Retrieve Context

```python
from core.retrieval.retrieve import search

results = search("What is FloCard?", n_results=5)
chunks = results["results"]
# chunks = [
#   {"id": "...", "text": "...", "source": "...", "similarity": 0.85},
#   ...
# ]
```

### Step 2: Build Prompt

```python
prompt = build_prompt(question, chunks)
# Prompt includes:
# - System instructions
# - Retrieved context
# - User question
# - Placeholder for answer
```

### Step 3: Call LLM

```python
answer = call_ollama(prompt, model="llama3.1")
# Sends to: http://localhost:11434/api/generate
# Receives: Generated answer text
```

### Step 4: Extract Citations

```python
sources = extract_sources(chunks)
# Deduplicated sources with highest relevance scores
```

### Step 5: Return Result

```python
result = {
    "query": question,
    "answer": answer,
    "sources": sources,
    "chunks_used": len(chunks),
    "model": "llama3.1"
}
```

---

## Usage Examples

### Example 1: Simple Query

```python
from core.rag.generate import generate_answer, format_response

result = generate_answer("What is FloCard?")

if result:
    print(format_response(result))
else:
    print("Failed to generate answer. Check Ollama connection.")
```

### Example 2: Custom Model & Parameters

```python
from core.rag.generate import generate_answer

result = generate_answer(
    question="How do I authenticate?",
    model="llama3.1",
    n_retrieve=3,
    temperature=0.5  # Higher temperature = more creative
)
```

### Example 3: Low-Level Control

```python
from core.rag.generate import (
    search,
    build_prompt,
    call_ollama,
    extract_sources
)

# Step 1: Retrieve
chunks = search("Your question?", n_results=5)["results"]

# Step 2: Build prompt
prompt = build_prompt("Your question?", chunks)

# Step 3: Generate
answer = call_ollama(prompt, model="llama3.1")

# Step 4: Citations
sources = extract_sources(chunks)

# Step 5: Format
print(f"Answer: {answer}")
print(f"Sources: {[s['source'] for s in sources]}")
```

### Example 4: Run Demo

```bash
python core/rag/generate.py
```

Runs example queries:
- "What is FloCard?"
- "How do I authenticate with the API?"
- "What are the company policies?"

---

## Configuration

### Ollama Endpoint

Default: `http://localhost:11434/api/generate`

To use a remote Ollama instance:

```python
result = generate_answer(
    question="Your question?",
    ollama_url="http://remote-server:11434/api/generate"
)
```

### Temperature

Controls generation "creativity" (0-1):
- **0.1-0.3**: Deterministic, factual (recommended for knowledge bases)
- **0.5-0.7**: Balanced
- **0.8-1.0**: Creative, may hallucinate

Default: 0.3 (factual)

### Context Size

Number of retrieved chunks:

```python
result = generate_answer(
    question="Your question?",
    n_retrieve=3  # Use fewer chunks for faster generation
)
```

---

## Error Handling

### Connection Error

**Error:** `Failed to connect to Ollama at http://localhost:11434`

**Solution:**
```bash
# Start Ollama service
ollama serve
```

### Model Not Found

**Error:** `model "llama3.1" not found`

**Solution:**
```bash
# Pull the model
ollama pull llama3.1
```

### No Relevant Chunks

**Error:** No chunks retrieved for question

**Result:** Returns message: "I couldn't find any relevant information..."

### Timeout

**Error:** Generation takes >5 minutes

**Solution:** Reduce n_retrieve or use a smaller model

---

## Performance

- **Retrieval**: <5ms (cached model)
- **Prompt Building**: <10ms
- **LLM Generation**: 10-60 seconds (depends on question complexity)
- **Source Extraction**: <5ms
- **Total**: ~10-60 seconds per query

---

## Prompt Engineering

The default prompt:

```
You are a helpful AI assistant for the AI Knowledge Base.

Your task is to answer questions ONLY based on the provided context.
If the answer is not in the context, say "I don't have information about that..."

Provide clear, concise, and accurate answers. When referring to information 
from the context, mention the source document.

CONTEXT:
[retrieved chunks]

QUESTION:
[user question]

ANSWER:
```

### Customization

To use a custom prompt template:

```python
def custom_build_prompt(question, chunks):
    context = "\n\n".join([c["text"] for c in chunks])
    return f"""
Your custom prompt here.

Context: {context}
Question: {question}
Answer:
"""

prompt = custom_build_prompt(question, chunks)
answer = call_ollama(prompt)
```

---

## Available Models

Ollama supports many models:

```bash
ollama pull llama3.1        # 4.7 GB, recommended
ollama pull llama2          # 3.8 GB, older
ollama pull mistral         # 4.0 GB, fast
ollama pull neural-chat     # 4.8 GB
```

Switch models:

```python
result = generate_answer(
    question="Your question?",
    model="mistral"  # Use a different model
)
```

---

## Evaluation & Improvement

### Quality Metrics

1. **Relevance**: Does the answer match the question?
2. **Accuracy**: Is information from context used correctly?
3. **Completeness**: Does it cover all aspects?
4. **Citations**: Are sources properly referenced?

### Optimization

- **Few-shot prompting**: Add examples to the prompt
- **Retrieval tuning**: Increase `n_retrieve` for complex questions
- **Temperature tuning**: Lower for factual, higher for creative
- **Model selection**: Use faster models for production

---

## Next Steps

### Phase 8: API Endpoints

Expose RAG pipeline via FastAPI:

```bash
# FastAPI server
python api/server.py

# Query endpoint
POST /api/ask
{
  "question": "What is FloCard?"
}

# Response
{
  "answer": "FloCard is...",
  "sources": [...],
  "model": "llama3.1"
}
```

### Phase 9: Web UI

Build frontend for interactive RAG:
- Chat interface
- Source citations with highlighting
- Conversation history
- Model selection

### Phase 10: Production Deployment

- Vector database scaling
- Multi-model support
- Caching layer
- Monitoring & logging
- API rate limiting

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Ollama connection refused | Run `ollama serve` in another terminal |
| Model not found | Run `ollama pull llama3.1` |
| Very slow generation | Reduce `n_retrieve` or use `temperature=0.1` |
| Hallucinated answers | Lower temperature or increase retrieval quality |
| Out of memory | Use a smaller model (mistral) |

---

## Summary

Phase 7 completes the core RAG pipeline:

✅ Retrieval (Phase 6)  
✅ Prompt Building  
✅ LLM Integration (Ollama)  
✅ Answer Generation  
✅ Citation Formatting  

**Result:** Contextual, source-backed answers powered by local LLM.
