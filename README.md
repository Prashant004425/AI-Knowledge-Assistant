[README.md.md](https://github.com/user-attachments/files/29088071/README.md.md)
# 🤖 AI Knowledge Assistant

> A local, open-source RAG-powered assistant that reads your internal docs and actually answers questions about them — with citations.

---

## What is this?

Ever joined a new team and spent your first week asking "where do I find X?" over and over?

This project is the answer to that. The **AI Knowledge Assistant** is a fully local, privacy-friendly AI system that ingests your internal documents (Markdown, PDFs, Word files, CSVs), builds a searchable knowledge base from them, and lets you ask questions in plain English — returning grounded answers with references to the exact source it pulled from.

No cloud. No subscriptions. No data leaving your machine.

Built as part of an onboarding engineering project, it's also a hands-on learning ground for understanding how real-world AI pipelines work — from raw documents all the way to an LLM-generated answer in a chat UI.

---

## How it works (the short version)

```
Your Docs → Ingestion → Chunking → Embeddings → Vector DB
                                                      ↓
                                You ask a question → Retriever
                                                      ↓
                                              LLM generates answer
                                                      ↓
                                         Answer + Citations → You
```

This is called **Retrieval-Augmented Generation (RAG)** — the LLM doesn't guess from memory, it reads your documents and answers from them. That's what makes citations possible and hallucinations far less likely.

---

## Features

- 📄 **Multi-format ingestion** — Markdown, PDF, DOCX, CSV
- 🧠 **Semantic search** — finds relevant content even if you don't use exact keywords
- 💬 **Chat interface** — ask questions, get answers, see where they came from
- 🔗 **Source citations** — every answer links back to the chunk it was derived from
- 📤 **Export** — save your Q&A session to Word or Excel
- 📊 **Evaluation logging** — latency, recall, citation coverage tracked automatically
- 🔄 **Re-index on demand** — add new docs and refresh the knowledge base with one command
- 🔒 **Local & private** — everything runs on your machine

---

## Tech Stack

| Layer | Tool | Cloud Equivalent |
|---|---|---|
| LLM | Ollama (Llama 3.1 / Qwen 2.5 / Mistral) | Azure OpenAI / AWS Bedrock |
| Embeddings | sentence-transformers (`bge-small-en-v1.5`) | Azure Embeddings / AWS Titan |
| Vector DB | Chroma or FAISS | Azure Cognitive Search / AWS Kendra |
| API | FastAPI | Azure Functions / AWS Lambda |
| UI | Next.js | Azure Web App / CloudFront |
| Parsing | PyMuPDF, docx2txt, pandas, unstructured | Azure Document Intelligence |
| Storage | SQLite / PostgreSQL | Blob Storage / S3 |
| Exports | python-docx, openpyxl | OpenXML |
| Monitoring | JSON logs + Matplotlib | App Insights / CloudWatch |

---

## Project Structure

```
ai-knowledge-assistant/
│
├── core/                   # Core RAG logic
│   ├── ingest.py           # Document parsing + chunking
│   ├── embed.py            # Embedding generation
│   ├── retriever.py        # Vector search + reranking
│   └── rag.py              # Prompt construction + LLM call
│
├── api/                    # FastAPI backend
│   └── main.py             # /ask endpoint
│
├── ui/                     # Next.js frontend
│   └── app/                # Chat interface + citation viewer
│
├── data/                   # Documents + generated chunks
│   ├── raw/                # Your input documents go here
│   ├── chunks.json         # Processed chunks output
│   └── synth/              # Synthetic data for testing
│
├── tools/
│   ├── synth_data.py       # Generates mock company documents
│   └── evaluate.py         # Runs evaluation question set
│
├── logs/                   # Query logs + trace files
├── .env.example            # Environment variable template
├── requirements.txt        # Python dependencies
└── Makefile                # Shortcuts for common commands
```

---

## Getting Started

### Prerequisites

Make sure you have these installed before you begin:

- Python 3.10+
- Node.js 18+
- [Ollama](https://ollama.ai) — for running the LLM locally
- Git

### 1. Clone the repo

```bash
git clone https://github.com/your-username/ai-knowledge-assistant.git
cd ai-knowledge-assistant
```

### 2. Set up Python environment

```bash
python -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Open `.env` and set your preferences:

```env
LLM_MODEL=llama3.1
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
VECTOR_STORE=chroma          # or faiss
CHUNK_SIZE=750
CHUNK_OVERLAP=100
TOP_K=5
API_TOKEN=your-secret-token-here
```

### 4. Pull the LLM

```bash
ollama pull llama3.1
```

> You can also use `qwen2.5`, `mistral`, or `mixtral` — just update `LLM_MODEL` in `.env`.

### 5. Add your documents

Drop your files into `data/raw/`. Supported formats:

```
data/raw/
├── onboarding-guide.md
├── team-faq.pdf
├── engineering-sop.docx
└── product-metrics.csv
```

Or generate synthetic test documents:

```bash
python tools/synth_data.py
```

### 6. Build the knowledge base

```bash
make reindex
```

This ingests, chunks, embeds, and indexes everything in `data/raw/`. You'll see a progress bar and a summary of how many chunks were created.

### 7. Start the API

```bash
make run
```

The API will be available at `http://localhost:8000`. You can test it directly:

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-secret-token-here" \
  -d '{"question": "What is the leave policy for new employees?"}'
```

### 8. Launch the UI

```bash
cd ui
npm install
npm run dev
```

Open `http://localhost:3000` and start asking questions.

---

## Usage

### Asking a question (API)

```http
POST /ask
Content-Type: application/json
Authorization: Bearer <token>

{
  "question": "How do I set up a new project in our system?"
}
```

**Response:**

```json
{
  "answer": "To set up a new project, you need to first create a repository under the Engineering workspace, add a .env file with the required credentials, and run the initialisation script as described in the internal SOP.",
  "citations": [
    {
      "source": "engineering-sop.docx",
      "chunk_id": "engineering-sop-chunk-4",
      "text": "New projects must be initialised using the setup script located at scripts/init_project.sh..."
    }
  ],
  "latency_ms": 2341
}
```

### Running evaluation

```bash
make eval
```

This runs the built-in evaluation question set and prints a summary:

```
Recall@5:          87%
Citation Coverage: 94%
Answer Grounding:  81%
Avg Latency:       2.4s
```

---

## Make Commands

| Command | What it does |
|---|---|
| `make reindex` | Ingests documents and rebuilds the vector index |
| `make run` | Starts the FastAPI backend |
| `make eval` | Runs the evaluation question set |
| `make clean` | Clears chunks and index (keeps raw docs) |
| `make lint` | Runs linting across the codebase |

---

## Adding New Documents

Just drop new files into `data/raw/` and run:

```bash
make reindex
```

Or trigger it from the UI using the **Re-index** button in the top-right corner of the chat interface.

---

## Architecture (Detailed)

```
┌─────────────────────────────────────────────────────────┐
│                        INGESTION                        │
│  raw docs → parsers → clean text → chunks → chunks.json │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────┐
│                       EMBEDDINGS                        │
│  chunks → sentence-transformers → vectors → Chroma/FAISS │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────┐
│                        RETRIEVAL                        │
│  user query → embed → similarity search → top-k chunks  │
│                         (optional: cross-encoder rerank) │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────┐
│                      LLM + PROMPT                       │
│  system prompt + retrieved context + user question      │
│                         → Ollama → answer               │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────┐
│                     API + UI LAYER                      │
│          FastAPI /ask → Next.js chat interface          │
│             answer + citations + export options         │
└─────────────────────────────────────────────────────────┘
```

---

## Security

- Secrets live in `.env` — never committed (it's in `.gitignore`)
- API endpoints require a bearer token
- PII redaction (emails, phone numbers, IDs) is applied at ingestion time before anything gets indexed
- The system is fully local — no data is ever sent to an external server

---

## Evaluation Metrics Explained

| Metric | What it measures |
|---|---|
| **Recall@5** | Of the truly relevant chunks for a question, how many appear in the top 5 results? |
| **Citation Coverage** | What percentage of answers include at least one valid source citation? |
| **Answer Grounding** | How much of the answer text can be traced back to the retrieved context? |
| **Latency** | How long does a full query take, end to end? |

---

## Optional Extensions

Things that are ready to be built on top of this foundation:

- [ ] **Hybrid retrieval** — combine keyword (BM25) + vector search for better recall
- [ ] **Usage dashboard** — queries over time, popular topics, latency trends
- [ ] **Tool-calling** — let the LLM trigger re-index, export, or evaluate as tools
- [ ] **Docker deployment** — containerise the whole stack for easy local or cloud deployment
- [ ] **Multi-user support** — per-user query history and personalised knowledge bases

---

## FAQ

**Does this send my documents to OpenAI or any external service?**
No. Everything runs locally. The LLM runs via Ollama on your machine. No data leaves your environment.

**What happens if the LLM doesn't know the answer?**
The system is designed to only answer from retrieved context. If no relevant chunks are found, the assistant will say so rather than hallucinating an answer.

**Can I use a different LLM?**
Yes — any model available in Ollama works. Just update `LLM_MODEL` in your `.env`. For better accuracy, `mixtral` or larger Llama models are recommended if your hardware supports it.

**How do I improve answer quality?**
Tune `CHUNK_SIZE`, `CHUNK_OVERLAP`, and `TOP_K` in `.env`. Smaller chunks improve precision; more overlap helps preserve context at boundaries. Increasing `TOP_K` gives the LLM more to work with but slightly increases latency.

**Can I run this on Windows?**
Yes. Use `venv\Scripts\activate` for the Python environment and make sure Ollama's Windows installer is used. The `make` commands require WSL or Git Bash on Windows.

---

## Contributing

Found a bug? Have an idea for an improvement? Pull requests are welcome.

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/your-idea`)
3. Make your changes
4. Run `make eval` to make sure nothing broke
5. Open a PR with a clear description of what you changed and why

---

## Acknowledgements

This project was built as part of an engineering onboarding program. It draws on the excellent open-source work from:

- [Ollama](https://ollama.ai) — for making local LLMs actually usable
- [sentence-transformers](https://www.sbert.net) — for fast, high-quality embeddings
- [Chroma](https://www.trychroma.com) — for the simplest vector DB experience
- [FastAPI](https://fastapi.tiangolo.com) — because life's too short for slow APIs

---

## License

MIT — use it, learn from it, build on it.

---

*Built with curiosity, a lot of terminal windows, and the firm belief that internal knowledge shouldn't be this hard to find.*
