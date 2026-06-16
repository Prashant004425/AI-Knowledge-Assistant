# AI Knowledge Assistant

An intelligent document ingestion, semantic search, and retrieval system built with Python.

## 🚀 Phase 12: Security & Deployment

This phase adds API token protection, sensitive data redaction, and deployment tooling.

### What’s included
- `.env` configuration for API secrets
- API token check for protected endpoints
- redaction of emails, phone numbers, and IDs in responses
- `Makefile` with `make run`, `make reindex`, and `make eval`
- updated README with setup, architecture, commands, and security guidance

## Setup

1. Activate your Python environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

2. Install dependencies:
   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Configure secrets in `.env`:
   ```text
   APP_ENV=development
   SECRET_KEY=changeme
   API_KEY=mysecret
   ```

4. Ingest documents:
   ```powershell
   python core/ingestion/ingest.py
   ```

5. Create embeddings:
   ```powershell
   python core/embeddings/embed.py
   ```

6. Start the API:
   ```powershell
   make run
   ```

7. Start the Streamlit UI:
   ```powershell
   make ui
   ```

8. Start the Next.js frontend UI:
   ```powershell
   cd ui
   npm install
   npm run dev
   ```

## Architecture

```
Raw files (data/raw/) → core/ingestion/ingest.py → data/processed/chunks.json
      → core/embeddings/embed.py → data/vectorstore/
      → core/retrieval/retrieve.py → semantic search
      → core/rag/generate.py → answer generation
      → api/main.py → protected API endpoints
```

## Project Structure

```
ai-knowledge-assistant/
├── api/                      # FastAPI backend
├── core/                     # ingestion, embeddings, retrieval, security, evaluation
├── data/                     # raw documents, processed chunks, vectorstore, reports
├── logs/                     # query and app logs
├── tools/                    # synthetic data tooling
├── tests/                    # test suite
├── Makefile                 # development commands
├── requirements.txt         # Python dependencies
├── README.md                # project documentation
└── .env                     # local secret configuration
```

## API Security

Protected endpoints require either:
- `X-API-Key: <API_KEY>`
- `Authorization: Bearer <API_KEY>`

Protected endpoints:
- `POST /search`
- `POST /ask`
- `POST /upload`
- `POST /reindex`

Public endpoints:
- `GET /health`
- `GET /`
- `GET /docs`

## Sample API Usage

### Search
```powershell
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: mysecret" \
  -d '{"query":"What is FloCard?","n_results":5}'
```

### Ask
```powershell
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer mysecret" \
  -d '{"question":"How do I authenticate?","n_retrieve":5}'
```

### Reindex
```powershell
curl -X POST http://localhost:8000/reindex \
  -H "X-API-Key: mysecret"
```

## Evaluation & Logging

- Query logs are saved to `logs/query_logs.jsonl`
- Evaluation reports and plots are generated in `data/reports/`
- Run:
  ```powershell
  make eval
  ```

## Make Commands

- `make run` — start the FastAPI server
- `make ui` — launch the Streamlit knowledge assistant UI
- `make reindex` — ingest and embed documents
- `make eval` — run evaluation scripts and generate analytics plots

## Notes

- Ensure `ollama` is running before using `/ask`
- Keep `.env` out of git and use a strong API key in production
- Redaction is applied automatically to returned texts
