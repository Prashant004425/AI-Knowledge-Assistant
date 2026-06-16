# Phase 8: FastAPI Backend

## Overview

Phase 8 exposes all AI Knowledge Assistant functionality through RESTful HTTP APIs powered by FastAPI.

**Features:**
- Interactive API documentation (Swagger UI)
- Type-safe request/response validation
- CORS support for frontend integration
- Metrics and health monitoring
- Error handling with detailed messages

---

## Architecture

```
Frontend / Client
        ↓
   HTTP Requests
        ↓
   FastAPI (api/main.py)
        ↓
   ├─→ /search (Semantic Search)
   ├─→ /ask (RAG Pipeline)
   ├─→ /reindex (Vector DB Rebuild)
   ├─→ /health (Status Check)
   └─→ /metrics (Analytics)
        ↓
   Core Modules (Phase 5-7)
        ↓
   HTTP Responses (JSON)
```

---

## Installation & Setup

### Prerequisites

- Python 3.8+
- Virtual environment activated
- All dependencies installed: `pip install -r requirements.txt`
- Ollama running for `/ask` endpoint: `ollama serve`

### Start the API Server

```bash
# From project root directory
python api/main.py

# Or using uvicorn directly
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

**Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Press CTRL+C to quit
```

### Access API Documentation

- **Interactive Docs:** http://localhost:8000/docs (Swagger UI)
- **Alternative Docs:** http://localhost:8000/redoc (ReDoc)
- **OpenAPI Schema:** http://localhost:8000/openapi.json

---

## API Endpoints

### 1. Health Check

**Endpoint:** `GET /health`

**Purpose:** Check API and dependency status

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "api_start_time": "2026-05-29T12:00:00"
}
```

**Example:**
```bash
curl http://localhost:8000/health
```

---

### 2. Metrics

**Endpoint:** `GET /metrics`

**Purpose:** Get API usage statistics

**Response:**
```json
{
  "total_questions": 15,
  "total_searches": 42,
  "total_reindexes": 2,
  "api_start_time": "2026-05-29T12:00:00"
}
```

**Example:**
```bash
curl http://localhost:8000/metrics
```

---

### 3. Semantic Search

**Endpoint:** `POST /search`

**Purpose:** Retrieve relevant chunks from knowledge base

**Request Body:**
```json
{
  "query": "What is FloCard?",
  "n_results": 5
}
```

**Parameters:**
- `query` (string, required): Search query
- `n_results` (integer, optional): Number of results (default: 5, max: 20)

**Response:**
```json
{
  "query": "What is FloCard?",
  "num_results": 3,
  "results": [
    {
      "id": "flocard_api_guide_chunk_001",
      "text": "FloCard is a payment processing platform...",
      "source": "flocard_api_guide.md",
      "similarity": 0.8456
    },
    {
      "id": "flocard_api_guide_chunk_002",
      "text": "FloCard supports multiple payment methods...",
      "source": "flocard_api_guide.md",
      "similarity": 0.7823
    },
    {
      "id": "payments_guide_chunk_005",
      "text": "To use FloCard, authenticate first...",
      "source": "payments_guide.md",
      "similarity": 0.7234
    }
  ]
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do I authenticate?",
    "n_results": 3
  }'
```

**Python:**
```python
import requests

response = requests.post(
    "http://localhost:8000/search",
    json={
        "query": "What is FloCard?",
        "n_results": 5
    }
)

results = response.json()
print(f"Found {results['num_results']} chunks")
for result in results['results']:
    print(f"  - {result['source']}: {result['similarity']}")
```

---

### 4. Ask Question (RAG Pipeline)

**Endpoint:** `POST /ask`

**Purpose:** Ask a question and get an AI-generated answer with citations

**Request Body:**
```json
{
  "question": "What is FloCard?",
  "n_retrieve": 5,
  "model": "llama3.1",
  "temperature": 0.3
}
```

**Parameters:**
- `question` (string, required): Question to answer
- `n_retrieve` (integer, optional): Number of chunks to retrieve (default: 5)
- `model` (string, optional): LLM model name (default: "llama3.1")
- `temperature` (float, optional): Generation temperature 0-1 (default: 0.3)

**Response:**
```json
{
  "query": "What is FloCard?",
  "answer": "FloCard is an internal payment processing platform used by the organization for employee reimbursements and transactions. It integrates with the accounting system and supports multiple payment methods including credit cards, bank transfers, and digital wallets. All transactions are encrypted and logged for audit purposes.",
  "sources": [
    {
      "source": "flocard_api_guide.md",
      "relevance": 0.8456
    },
    {
      "source": "payments_guide.md",
      "relevance": 0.7823
    }
  ],
  "chunks_used": 5,
  "model": "llama3.1"
}
```

**Error Responses:**

**Ollama Not Running:**
```json
{
  "detail": "LLM service (Ollama) is not running. Start it with: ollama serve",
  "status_code": 503
}
```

**Generation Timeout:**
```json
{
  "detail": "Answer generation failed: Request timed out",
  "status_code": 500
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How do I authenticate?",
    "n_retrieve": 3,
    "temperature": 0.5
  }'
```

**Python:**
```python
import requests

response = requests.post(
    "http://localhost:8000/ask",
    json={
        "question": "What are the company policies?",
        "n_retrieve": 5,
        "model": "llama3.1",
        "temperature": 0.3
    }
)

result = response.json()
print(f"Q: {result['query']}")
print(f"A: {result['answer']}")
print(f"Sources: {[s['source'] for s in result['sources']]}")
```

**JavaScript/Fetch:**
```javascript
async function askQuestion(question) {
  const response = await fetch('http://localhost:8000/ask', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      question: question,
      n_retrieve: 5
    })
  });
  
  const data = await response.json();
  console.log('Answer:', data.answer);
  console.log('Sources:', data.sources);
  return data;
}

askQuestion("What is FloCard?");
```

---

### 5. Reindex Knowledge Base

**Endpoint:** `POST /reindex`

**Purpose:** Rebuild vector database from raw documents

**Request Body:** (None - POST without body)

**Response:**
```json
{
  "status": "success",
  "chunks_ingested": 5,
  "chunks_embedded": 5,
  "timestamp": "2026-05-29T12:15:30"
}
```

**Use Cases:**
- After adding new documents to `data/raw/`
- Updating existing documents
- Recovering from vectorstore corruption

**Example:**
```bash
curl -X POST http://localhost:8000/reindex
```

**Python:**
```python
import requests

response = requests.post("http://localhost:8000/reindex")
result = response.json()
print(f"Reindexed {result['chunks_embedded']} chunks")
```

**Expected Execution Time:** 30-60 seconds (includes re-ingestion + re-embedding)

---

## Request/Response Models

### SearchRequest
```python
{
  "query": str,          # Required: search query
  "n_results": int = 5   # Optional: number of results
}
```

### SearchResult
```python
{
  "id": str,            # Chunk identifier
  "text": str,          # Chunk content
  "source": str,        # Source document
  "similarity": float   # Similarity score (0-1)
}
```

### AskRequest
```python
{
  "question": str,           # Required: question
  "n_retrieve": int = 5,     # Optional: chunks to retrieve
  "model": str = "llama3.1", # Optional: LLM model
  "temperature": float = 0.3 # Optional: generation temperature
}
```

### Citation
```python
{
  "source": str,         # Document source
  "relevance": float     # Relevance score (0-1)
}
```

### AskResponse
```python
{
  "query": str,              # Original question
  "answer": str,             # Generated answer
  "sources": list[Citation], # Cited sources
  "chunks_used": int,        # Number of chunks used
  "model": str               # Model used
}
```

---

## CORS Configuration

The API accepts requests from any origin (useful for frontend development):

```python
CORSMiddleware(
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Production:** Restrict to specific domains:
```python
allow_origins=[
    "http://localhost:3000",
    "https://app.example.com",
]
```

---

## Error Handling

### Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad request (validation error) |
| 500 | Server error |
| 503 | Service unavailable (Ollama not running) |

### Common Errors

**Empty Query:**
```json
{
  "detail": [
    {
      "loc": ["body", "query"],
      "msg": "ensure this value has at least 1 characters",
      "type": "value_error.any_str.min_length"
    }
  ]
}
```

**Ollama Timeout:**
```json
{
  "detail": "Answer generation failed: Ollama request timed out after 300 seconds"
}
```

**No Results:**
```json
{
  "query": "xyz",
  "answer": "I couldn't find any relevant information in the knowledge base to answer your question.",
  "sources": [],
  "chunks_used": 0,
  "model": "llama3.1"
}
```

---

## Integration Examples

### React Frontend

```jsx
import React, { useState } from 'react';

function AskQuestion() {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const response = await fetch('http://localhost:8000/ask', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          question: question,
          n_retrieve: 5
        })
      });
      
      const data = await response.json();
      setAnswer(data.answer);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="text"
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="Ask a question..."
      />
      <button type="submit" disabled={loading}>
        {loading ? 'Thinking...' : 'Ask'}
      </button>
      {answer && <div className="answer">{answer}</div>}
    </form>
  );
}

export default AskQuestion;
```

### Vue 3

```vue
<template>
  <div>
    <input 
      v-model="question" 
      placeholder="Ask a question..."
      @keyup.enter="askQuestion"
    />
    <button @click="askQuestion" :disabled="loading">
      {{ loading ? 'Thinking...' : 'Ask' }}
    </button>
    <div v-if="answer" class="answer">
      {{ answer }}
    </div>
    <div v-if="sources.length" class="sources">
      <h4>Sources:</h4>
      <ul>
        <li v-for="source in sources" :key="source.source">
          {{ source.source }} ({{ (source.relevance * 100).toFixed(1) }}%)
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const question = ref('');
const answer = ref('');
const sources = ref([]);
const loading = ref(false);

async function askQuestion() {
  loading.value = true;
  try {
    const response = await fetch('http://localhost:8000/ask', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ question: question.value })
    });
    const data = await response.json();
    answer.value = data.answer;
    sources.value = data.sources;
  } finally {
    loading.value = false;
  }
}
</script>
```

---

## Performance Considerations

### Response Times

- **Search:** <50ms (cached model)
- **Ask:** 10-60 seconds (LLM generation)
- **Reindex:** 30-60 seconds (re-ingestion + re-embedding)
- **Health:** <5ms

### Optimization Tips

1. **Reduce n_retrieve for faster answers:**
   ```json
   {"question": "...", "n_retrieve": 2}
   ```

2. **Lower temperature for deterministic output:**
   ```json
   {"question": "...", "temperature": 0.1}
   ```

3. **Use search endpoint for retrieval-only:**
   ```json
   POST /search {"query": "..."}
   ```

4. **Caching:** Implement frontend caching for duplicate questions

---

## Running with Production Settings

### With Gunicorn

```bash
pip install gunicorn
gunicorn api.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --port 8000
```

### Docker Support (Optional)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t ai-assistant .
docker run -p 8000:8000 ai-assistant
```

---

## Monitoring & Logging

All requests and responses are logged to console and `logs/` directory.

**Log Levels:**
- INFO: Request/response details
- WARNING: Recoverable issues
- ERROR: Failures

**Example Log:**
```
INFO:api.main:Question received: What is FloCard?
INFO:core.retrieval.retrieve:Retrieved 5 relevant chunks
INFO:core.rag.generate:Calling Ollama API with model: llama3.1
INFO:api.main:Answer generated for question: What is FloCard?
```

---

## Troubleshooting

### Issue: "Connection refused" for /ask

**Solution:** Start Ollama:
```bash
ollama serve
```

### Issue: Slow /search responses

**Solution:** Vector database may need rebuild:
```bash
curl -X POST http://localhost:8000/reindex
```

### Issue: CORS errors in frontend

**Solution:** Already enabled in production code. For additional domains:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourapp.com"],
    ...
)
```

---

## Next: Phase 9 - Web UI

The Phase 9 frontend will consume these APIs to create an interactive chat interface with:
- Real-time question/answer display
- Source citations with document highlighting
- Conversation history
- API status indicator

---

## Summary

Phase 8 completes the backend infrastructure:

✅ REST API with FastAPI  
✅ Type-safe request/response validation  
✅ 5 core endpoints (search, ask, reindex, health, metrics)  
✅ CORS support for frontend  
✅ Error handling & logging  
✅ Interactive API docs (Swagger UI)  

**Next Steps:**
1. Start API: `python api/main.py`
2. Visit docs: http://localhost:8000/docs
3. Test endpoints
4. Build frontend (Phase 9)
