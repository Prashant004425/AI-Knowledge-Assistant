import csv
import json
import re
from pathlib import Path

import docx2txt
import fitz
import pandas as pd

BASE_DIR = Path.cwd()
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
CHUNKS_FILE = PROCESSED_DIR / "chunks.json"


def load_markdown(file_path: Path) -> str:
    with file_path.open("r", encoding="utf-8") as handle:
        text = handle.read()
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    return text.strip()


def load_pdf(file_path: Path) -> str:
    text_parts = []
    with fitz.open(file_path) as doc:
        for page in doc:
            text_parts.append(page.get_text())
    return "\n".join(text_parts).strip()


def load_docx(file_path: Path) -> str:
    return docx2txt.process(str(file_path)).strip()


def load_csv(file_path: Path) -> str:
    df = pd.read_csv(file_path, dtype=str, keep_default_na=False, na_filter=False)
    rows = [", ".join(map(str, row)) for row in df.itertuples(index=False, name=None)]
    header = ", ".join(df.columns.astype(str))
    return "\n".join([header] + rows).strip()


def load_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix == ".md":
        return load_markdown(file_path)
    if suffix == ".pdf":
        return load_pdf(file_path)
    if suffix == ".docx":
        return load_docx(file_path)
    if suffix == ".csv":
        return load_csv(file_path)
    if suffix in {".txt", ".text"}:
        return file_path.read_text(encoding="utf-8").strip()
    raise ValueError(f"Unsupported file type: {suffix}")


def clean_text(text: str) -> str:
    text = text.replace("\r", " ").replace("\n", " ")
    text = re.sub(r"[\x00-\x1F\x7F]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def chunk_text(text: str, chunk_size: int = 700, overlap: int = 100) -> list[str]:
    words = text.split()
    if not words:
        return []
    step = max(1, chunk_size - overlap)
    chunks = []
    for start in range(0, len(words), step):
        chunk = " ".join(words[start : start + chunk_size])
        if chunk:
            chunks.append(chunk)
        if start + chunk_size >= len(words):
            break
    return chunks


def ensure_processed_dir() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def ingest_directory(
    raw_dir: Path = RAW_DIR,
    output_file: Path = CHUNKS_FILE,
    chunk_size: int = 700,
    overlap: int = 100,
) -> list[dict]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    ensure_processed_dir()

    chunks = []
    for file_path in sorted(raw_dir.glob("*")):
        if not file_path.is_file():
            continue
        try:
            text = load_text(file_path)
        except Exception:
            continue
        cleaned = clean_text(text)
        for idx, chunk in enumerate(chunk_text(cleaned, chunk_size, overlap), start=1):
            chunks.append(
                {
                    "id": f"{file_path.stem}_chunk_{idx:03d}",
                    "text": chunk,
                    "source": file_path.name,
                }
            )
    with output_file.open("w", encoding="utf-8") as handle:
        json.dump(chunks, handle, indent=2)
    return chunks


if __name__ == "__main__":
    chunks = ingest_directory()
    print(f"Saved {len(chunks)} chunks to {CHUNKS_FILE}")
