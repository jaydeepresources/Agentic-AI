from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table


APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent
DOCS_DIR = APP_DIR / "docs"
INDEX_PATH = APP_DIR / "embeddings.json"
MODEL_ID = "nvidia/nemotron-3.5-embed-8b"
API_BASE_URL = "https://integrate.api.nvidia.com/v1"
CHUNK_SIZE = 1800
CHUNK_OVERLAP = 250
EMBEDDING_BATCH_SIZE = 32
INDEX_VERSION = 1

console = Console()


@dataclass(slots=True)
class PolicyChunk:
    source: str
    page: int
    chunk: int
    text: str
    embedding: list[float] | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Search the HR policy PDFs with pure cosine similarity."
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=None,
        help="Maximum number of matching chunks to display (overrides 2_RAG/.env).",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Minimum cosine similarity in [-1, 1] (overrides 2_RAG/.env).",
    )
    parser.add_argument(
        "--rebuild-index",
        action="store_true",
        help="Re-extract and embed the PDF documents even if an index exists.",
    )
    return parser.parse_args()


def load_settings(args: argparse.Namespace) -> tuple[int, float, str | None]:
    load_dotenv(PROJECT_DIR / ".env")
    load_dotenv(APP_DIR / ".env", override=True)

    top_k = args.top_k if args.top_k is not None else int(os.getenv("TOP_K", "5"))
    threshold = (
        args.threshold
        if args.threshold is not None
        else float(os.getenv("SIMILARITY_THRESHOLD", "0.20"))
    )
    api_key = os.getenv("NVIDIA_AI_KEY") or os.getenv("NVIDIA_API_KEY")

    if top_k < 1:
        raise ValueError("TOP_K must be at least 1.")
    if not -1.0 <= threshold <= 1.0:
        raise ValueError("SIMILARITY_THRESHOLD must be between -1 and 1.")
    return top_k, threshold, api_key


def chunk_text(text: str, max_chars: int = CHUNK_SIZE) -> list[str]:
    if max_chars <= CHUNK_OVERLAP:
        raise ValueError("Chunk size must be larger than the overlap.")

    text = re.sub(r"\s+", " ", text).strip()
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start, end)
            if boundary > start:
                end = boundary

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(end - CHUNK_OVERLAP, start + 1)
    return chunks


def document_fingerprint(pdf_paths: Sequence[Path]) -> str:
    digest = hashlib.sha256()
    for path in pdf_paths:
        digest.update(path.relative_to(DOCS_DIR).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def extract_chunks(pdf_paths: Sequence[Path]) -> list[PolicyChunk]:
    chunks: list[PolicyChunk] = []
    for pdf_path in pdf_paths:
        reader = PdfReader(pdf_path)
        for page_number, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            if not page_text.strip():
                console.print(
                    f"[yellow]Warning:[/] no extractable text on "
                    f"{pdf_path.name}, page {page_number}."
                )
                continue
            for chunk_number, text in enumerate(chunk_text(page_text), start=1):
                chunks.append(
                    PolicyChunk(
                        source=pdf_path.relative_to(DOCS_DIR).as_posix(),
                        page=page_number,
                        chunk=chunk_number,
                        text=text,
                    )
                )
    if not chunks:
        raise ValueError(
            f"No searchable text was found in the PDFs under {DOCS_DIR}. "
            "If the files are scanned images, run OCR before using this bot."
        )
    return chunks


def embed_texts(
    client: OpenAI, texts: Sequence[str], input_type: str
) -> list[list[float]]:
    vectors: list[list[float]] = []
    for start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[start : start + EMBEDDING_BATCH_SIZE]
        response = client.embeddings.create(
            input=list(batch),
            model=MODEL_ID,
            encoding_format="float",
            extra_body={
                "modality": ["text"],
                "input_type": input_type,
                "truncate": "END",
            },
        )
        ordered_data = sorted(response.data, key=lambda item: item.index)
        if len(ordered_data) != len(batch):
            raise ValueError("NVIDIA returned an incomplete embedding batch.")
        vectors.extend([item.embedding for item in ordered_data])
    return vectors


def save_index(fingerprint: str, records: list[PolicyChunk]) -> None:
    payload = {
        "version": INDEX_VERSION,
        "model": MODEL_ID,
        "source_fingerprint": fingerprint,
        "records": [asdict(record) for record in records],
    }
    temporary_path = INDEX_PATH.with_suffix(".json.tmp")
    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )
    temporary_path.replace(INDEX_PATH)


def load_index(fingerprint: str) -> list[PolicyChunk] | None:
    if not INDEX_PATH.is_file():
        return None

    try:
        payload = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Could not parse {INDEX_PATH}: {error}") from error

    if not isinstance(payload, dict):
        raise ValueError(f"The embedding index at {INDEX_PATH} is malformed.")
    if (
        payload.get("version") != INDEX_VERSION
        or payload.get("model") != MODEL_ID
        or payload.get("source_fingerprint") != fingerprint
    ):
        return None

    raw_records = payload.get("records")
    if not isinstance(raw_records, list) or not raw_records:
        raise ValueError(f"The embedding index at {INDEX_PATH} contains no records.")
    records: list[PolicyChunk] = []
    for raw_record in raw_records:
        if not isinstance(raw_record, dict):
            raise ValueError(f"The embedding index at {INDEX_PATH} is malformed.")
        source = raw_record.get("source")
        page = raw_record.get("page")
        chunk = raw_record.get("chunk")
        text = raw_record.get("text")
        embedding = raw_record.get("embedding")
        if (
            not isinstance(source, str)
            or not isinstance(page, int)
            or not isinstance(chunk, int)
            or not isinstance(text, str)
            or not isinstance(embedding, list)
            or not embedding
            or any(not isinstance(value, (int, float)) for value in embedding)
        ):
            raise ValueError(f"The embedding index at {INDEX_PATH} has an invalid vector.")
        records.append(
            PolicyChunk(
                source=source,
                page=page,
                chunk=chunk,
                text=text,
                embedding=[float(value) for value in embedding],
            )
        )
    return records


def cosine_similarities(
    query_vector: Sequence[float], candidate_vectors: Sequence[Sequence[float]]
) -> np.ndarray:
    query = np.asarray(query_vector, dtype=np.float64)
    candidates = np.asarray(candidate_vectors, dtype=np.float64)
    if query.ndim != 1 or candidates.ndim != 2:
        raise ValueError("Cosine similarity requires one query vector and a vector matrix.")
    if candidates.shape[1] != query.shape[0]:
        raise ValueError("Query and document embeddings have different dimensions.")
    if not np.isfinite(query).all() or not np.isfinite(candidates).all():
        raise ValueError("Embeddings must contain only finite numbers.")

    numerators = candidates @ query
    denominators = np.linalg.norm(candidates, axis=1) * np.linalg.norm(query)
    return np.divide(
        numerators,
        denominators,
        out=np.zeros_like(numerators, dtype=np.float64),
        where=denominators != 0,
    )


def rank_results(
    query_vector: Sequence[float],
    records: Sequence[PolicyChunk],
    top_k: int,
    threshold: float,
) -> list[tuple[PolicyChunk, float]]:
    vectors: list[list[float]] = []
    for record in records:
        if record.embedding is None:
            raise ValueError("A document chunk is missing its embedding.")
        vectors.append(record.embedding)
    scores = cosine_similarities(query_vector, vectors)
    ordered_indices = np.argsort(-scores, kind="stable")
    results: list[tuple[PolicyChunk, float]] = []
    for index in ordered_indices:
        score = float(scores[index])
        if score >= threshold:
            results.append((records[int(index)], score))
            if len(results) == top_k:
                break
    return results


def display_results(
    query: str, results: Sequence[tuple[PolicyChunk, float]], threshold: float
) -> None:
    if not results:
        console.print(
            Panel(
                f"No chunks met the cosine similarity threshold of [bold]{threshold:.3f}[/].",
                title="No matching policy sections",
                border_style="yellow",
            )
        )
        return

    table = Table(
        title=f"Top matches for: {query}",
        title_style="bold cyan",
        header_style="bold magenta",
        show_lines=True,
    )
    table.add_column("#", justify="right", width=3)
    table.add_column("Cosine score", justify="right", width=13)
    table.add_column("Source", min_width=16)
    table.add_column("Page", justify="right", width=6)
    table.add_column("Policy text", ratio=1)

    for rank, (record, score) in enumerate(results, start=1):
        table.add_row(
            str(rank),
            f"{score:.4f}",
            record.source,
            str(record.page),
            record.text,
        )
    console.print(table)
    console.print(
        "[dim]Scores are pure cosine similarity (higher is closer); "
        f"minimum accepted score: {threshold:.3f}.[/]\n"
    )


def get_or_build_index(
    client: OpenAI, pdf_paths: Sequence[Path], force_rebuild: bool
) -> list[PolicyChunk]:
    fingerprint = document_fingerprint(pdf_paths)
    records = None if force_rebuild else load_index(fingerprint)
    if records is not None:
        console.print(
            f"[green]Loaded[/] {len(records)} embedded chunks from "
            f"[cyan]{INDEX_PATH.name}[/]."
        )
        return records

    console.print(
        f"[cyan]Creating embeddings[/] for {len(pdf_paths)} PDF(s) with {MODEL_ID}..."
    )
    records = extract_chunks(pdf_paths)
    embeddings = embed_texts(
        client, [record.text for record in records], "passage"
    )
    if len(embeddings) != len(records):
        raise ValueError("The number of returned embeddings did not match the chunks.")
    for record, embedding in zip(records, embeddings, strict=True):
        record.embedding = embedding
    save_index(fingerprint, records)
    console.print(
        f"[green]Saved[/] {len(records)} embedded chunks to "
        f"[cyan]{INDEX_PATH.name}[/]."
    )
    return records


def run() -> int:
    args = parse_args()
    try:
        top_k, threshold, api_key = load_settings(args)
    except (ValueError, OSError) as error:
        console.print(f"[bold red]Invalid configuration:[/] {error}")
        return 2
    if not api_key:
        console.print(
            "[bold red]NVIDIA API key not found.[/] Set NVIDIA_AI_KEY or "
            "NVIDIA_API_KEY in the project-root .env file."
        )
        return 1

    pdf_paths = sorted(DOCS_DIR.rglob("*.pdf"))
    if not pdf_paths:
        console.print(f"[bold red]No PDF files found in {DOCS_DIR}.[/]")
        return 1

    client = OpenAI(api_key=api_key, base_url=API_BASE_URL)
    console.print(
        Panel(
            "[bold]HR Policy Search[/]\n"
            "Ask a question to find the most relevant policy passages.",
            subtitle=f"[dim]{MODEL_ID} | NumPy cosine similarity[/]",
            border_style="cyan",
            padding=(1, 2),
        )
    )
    console.print(
        f"[dim]Documents: {len(pdf_paths)} PDF(s) | top-k: {top_k} | "
        f"threshold: {threshold:.3f} | type /exit to quit.[/]\n"
    )

    try:
        records = get_or_build_index(client, pdf_paths, args.rebuild_index)
    except (OpenAIError, OSError, PdfReadError, ValueError) as error:
        console.print(f"[bold red]Could not prepare the search index:[/] {error}")
        return 1

    while True:
        try:
            query = Prompt.ask("[bold green]Your question[/]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Search session ended.[/]")
            return 0
        if query.lower() in {"/exit", "/quit"}:
            console.print("[dim]Search session ended.[/]")
            return 0
        if not query:
            continue

        try:
            query_vector = embed_texts(client, [query], "query")[0]
            results = rank_results(query_vector, records, top_k, threshold)
        except (OpenAIError, ValueError) as error:
            console.print(f"[bold red]Could not search this question:[/] {error}")
            continue
        display_results(query, results, threshold)


if __name__ == "__main__":
    sys.exit(run())
