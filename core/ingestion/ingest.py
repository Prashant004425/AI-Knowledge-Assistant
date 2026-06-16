import json
import logging
import re
from pathlib import Path

import docx2txt
import fitz
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path.cwd()

RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
CHUNKS_FILE = PROCESSED_DIR / "chunks.json"


def load_markdown(file_path: Path) -> str:
    with file_path.open("r", encoding="utf-8") as handle:
        text = handle.read()
    text = re.sub(r"```json\s.*?\s```", "", text, flags=re.S)
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
    df = pd.read_csv(
        file_path,
        comment="#",
        dtype=str,
        keep_default_na=False,
        na_filter=False,
    )
    rows = [", ".join(map(str, row)) for row in df.itertuples(index=False, name=None)]
    header = ", ".join(df.columns.astype(str))
    return "\n".join([header] + rows).strip()


def load_plain_text(file_path: Path) -> str:
    with file_path.open("r", encoding="utf-8") as handle:
        return handle.read().strip()


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
        return load_plain_text(file_path)
    raise ValueError(f"Unsupported file type: {suffix}")


def clean_text(text: str) -> str:
    text = text.replace("\r", " ").replace("\n", " ")
    text = re.sub(r"[\x00-\x1F\x7F]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def chunk_text(text: str, chunk_size: int = 100, overlap: int = 20) -> list[str]:
    """
    Sentence-aware chunking.

    Splits the text into sentences, then accumulates whole sentences into chunks
    up to approximately `chunk_size` words. When a chunk is completed it retains
    the last `overlap` words as a prefix for the next chunk to preserve context.
    """
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks: list[str] = []
    current_words: list[str] = []

    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        sent_words = sent.split()
        if len(current_words) + len(sent_words) <= chunk_size or not current_words:
            current_words.extend(sent_words)
            continue

        # Finalize the current chunk
        chunks.append(" ".join(current_words))

        # Seed the next chunk with overlap words for context
        if overlap > 0:
            current_words = current_words[-overlap:]
        else:
            current_words = []

        current_words.extend(sent_words)

    # Flush remaining words as the final chunk
    if current_words:
        chunks.append(" ".join(current_words))

    return chunks  # Fix 1: was missing, causing function to return None


def ensure_processed_dir() -> None:  # Fix 2: moved out of chunk_text() to module level
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def ingest_directory(
    raw_dir: Path = RAW_DIR,
    output_file: Path = CHUNKS_FILE,
    chunk_size: int = 100,
    overlap: int = 20,
) -> list[dict]:
    if not raw_dir.exists():
        raise FileNotFoundError(f"Raw data directory not found: {raw_dir}")

    ensure_processed_dir()
    chunks = []

    for file_path in sorted(raw_dir.glob("*")):
        if not file_path.is_file():
            continue
        try:
            text = load_text(file_path)
        except Exception as exc:
            logger.warning("Skipping %s: %s", file_path.name, exc)
            continue

        cleaned = clean_text(text)
        for idx, chunk in enumerate(chunk_text(cleaned, chunk_size, overlap), start=1):
            logger.info(  # Fix 3: logger.info and chunks.append back inside the for loop
                "Created chunk %s (%d words)",
                f"{file_path.stem}_chunk_{idx:03d}",
                len(chunk.split()),
            )
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
    generated = ingest_directory()
    print(f"Saved {len(generated)} chunks to {CHUNKS_FILE}")