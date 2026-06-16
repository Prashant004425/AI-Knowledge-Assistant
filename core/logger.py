import json
from datetime import datetime
from pathlib import Path

LOG_DIR = Path.cwd() / "logs"
LOG_FILE = LOG_DIR / "queries.json"


def ensure_log_dir() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def log_query(query: str, latency_ms: float, retrieved_chunks: list[dict]) -> Path:
    ensure_log_dir()
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "query": query,
        "latency_ms": round(latency_ms, 2),
        "retrieved_chunks": [
            {
                "id": chunk.get("id"),
                "source": chunk.get("source"),
                "similarity": chunk.get("similarity"),
            }
            for chunk in retrieved_chunks
        ],
    }
    logs = []
    if LOG_FILE.exists():
        try:
            logs = json.loads(LOG_FILE.read_text(encoding="utf-8"))
        except Exception:
            logs = []
    logs.append(entry)
    LOG_FILE.write_text(json.dumps(logs, indent=2), encoding="utf-8")
    return LOG_FILE
