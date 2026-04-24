from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BACKEND_ROOT = ROOT / "Backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

load_dotenv(BACKEND_ROOT / ".env")

from app.core.config import get_settings
from app.services.embeddings import get_embedding_service
from app.services.vector_store import DocumentChunk, QdrantVectorStore


def load_roles(pdf_path: Path, default_roles: list[str]) -> list[str]:
    manifest_path = pdf_path.with_suffix(".json")
    if manifest_path.exists():
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        roles = payload.get("allowed_roles", [])
        if not isinstance(roles, list) or not all(isinstance(role, str) for role in roles):
            raise ValueError(f"Invalid allowed_roles in {manifest_path}")
        return [role.strip() for role in roles if role.strip()]

    return [role.strip() for role in default_roles if role.strip()]


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 120) -> list[str]:
    words = text.split()
    if not words:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(len(words), start + chunk_size)
        chunk = " ".join(words[start:end]).strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(words):
            break
        start = max(end - overlap, start + 1)
    return chunks


def extract_pdf_pages(pdf_path: Path) -> list[tuple[int, str]]:
    reader = PdfReader(str(pdf_path))
    pages: list[tuple[int, str]] = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        cleaned = " ".join(text.split())
        if cleaned:
            pages.append((index, cleaned))
    return pages


def build_chunks(pdf_path: Path, allowed_roles: list[str], chunk_size: int, overlap: int) -> tuple[list[DocumentChunk], list[str]]:
    if not allowed_roles:
        raise ValueError(f"No allowed_roles configured for {pdf_path.name}; deny by default.")

    document_chunks: list[DocumentChunk] = []
    chunk_texts: list[str] = []
    document_id = pdf_path.stem

    for page_number, page_text in extract_pdf_pages(pdf_path):
        for chunk_index, chunk in enumerate(chunk_text(page_text, chunk_size=chunk_size, overlap=overlap), start=1):
            chunk_id = QdrantVectorStore.build_chunk_id(str(pdf_path), page_number, chunk_index, chunk)
            document_chunks.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    source_file=str(pdf_path.name),
                    page=page_number,
                    text=chunk,
                    allowed_roles=allowed_roles,
                )
            )
            chunk_texts.append(chunk)

    return document_chunks, chunk_texts


def ingest_directory(input_dir: Path, default_roles: list[str], chunk_size: int, overlap: int) -> int:
    settings = get_settings()
    embeddings = get_embedding_service(settings.embedding_model)
    store = QdrantVectorStore(settings.qdrant_url, settings.qdrant_api_key, settings.qdrant_collection)
    store.ensure_collection()

    pdf_files = sorted(input_dir.rglob("*.pdf"))
    ingested = 0

    for pdf_path in pdf_files:
        allowed_roles = load_roles(pdf_path, default_roles)
        chunks, chunk_texts = build_chunks(pdf_path, allowed_roles, chunk_size=chunk_size, overlap=overlap)
        if not chunks:
            continue

        vectors = embeddings.encode_batch(chunk_texts)
        store.upsert_chunks(chunks, vectors)
        ingested += len(chunks)

    return ingested


def parse_roles(value: str) -> list[str]:
    return [role.strip() for role in value.split(",") if role.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest authorized PDF documents into Qdrant.")
    parser.add_argument("--input-dir", required=True, help="Directory containing PDF files.")
    parser.add_argument(
        "--default-roles",
        default="",
        help="Comma-separated fallback roles when a PDF has no sidecar manifest.",
    )
    parser.add_argument("--chunk-size", type=int, default=800, help="Approximate word count per chunk.")
    parser.add_argument("--overlap", type=int, default=120, help="Word overlap between chunks.")
    args = parser.parse_args()

    input_dir = Path(args.input_dir).expanduser().resolve()
    if not input_dir.exists() or not input_dir.is_dir():
        raise SystemExit(f"Input directory does not exist: {input_dir}")

    default_roles = parse_roles(args.default_roles)

    ingested = ingest_directory(input_dir, default_roles, chunk_size=args.chunk_size, overlap=args.overlap)
    print(f"Ingested {ingested} chunks from {input_dir}")


if __name__ == "__main__":
    main()
