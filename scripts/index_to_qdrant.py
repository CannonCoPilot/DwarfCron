#!/usr/bin/env python3
"""Index DwarfCron source repos and wiki data into Qdrant collections.

Creates three collections:
  - dfhack: DFHack source code, df-structures XML, scripts, docs
  - dwarf-therapist: Dwarf Therapist C++/Qt source
  - df-wiki: Scraped wiki articles as markdown

Uses Ollama (qwen3-embedding:4b) for embeddings, matching Jarvis infrastructure.

Usage:
    python index_to_qdrant.py [--source dfhack|dwarf-therapist|df-wiki|all]
                               [--qdrant-url URL] [--ollama-url URL]
                               [--recreate]
"""

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

# Configuration
QDRANT_URL = "http://localhost:6333"
OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "qwen3-embedding:4b"
EMBED_DIM = 2560

REPOS_DIR = Path("/Users/nathanielcannon/Claude/Projects/DwarfCron/repos")
WIKI_DIR = Path("/Users/nathanielcannon/Claude/Projects/DwarfCron/data/wiki")

# File patterns per source
SOURCE_CONFIG = {
    "dfhack": {
        "base_dir": REPOS_DIR / "dfhack",
        "collection": "dfhack",
        "patterns": {
            "**/*.cpp": "cpp",
            "**/*.h": "header",
            "**/*.lua": "lua",
            "**/*.rst": "docs",
            "**/*.md": "docs",
            "library/xml/*.xml": "df-structures",
        },
        # Skip build artifacts, tests, and vendored dependencies
        "exclude_dirs": {
            "build", "depends/googletest", "depends/clsocket",
            "depends/jsoncpp-sub", "depends/libexpat", "depends/libzip",
            "depends/xlsxio", ".git",
        },
    },
    "dwarf-therapist": {
        "base_dir": REPOS_DIR / "Dwarf-Therapist",
        "collection": "dwarf-therapist",
        "patterns": {
            "**/*.cpp": "cpp",
            "**/*.h": "header",
            "**/*.rst": "docs",
            "**/*.md": "docs",
        },
        "exclude_dirs": {".git", "debian"},
    },
    "df-wiki": {
        "base_dir": WIKI_DIR,
        "collection": "df-wiki",
        "patterns": {
            "**/*.md": "wiki",
        },
        "exclude_dirs": set(),
    },
}

# Embedding client (synchronous for simplicity in batch script)
http_client = httpx.Client(timeout=120.0)


def get_embedding(text: str) -> list[float]:
    """Get embedding vector from Ollama."""
    resp = http_client.post(
        f"{OLLAMA_URL}/api/embed",
        json={"model": EMBED_MODEL, "input": text},
    )
    resp.raise_for_status()
    data = resp.json()
    embeddings = data.get("embeddings", [])
    if not embeddings:
        raise ValueError(f"No embeddings returned: {data}")
    return embeddings[0]


def chunk_code(text: str, file_path: str, file_type: str,
               chunk_size: int = 1500, overlap: int = 200) -> list[dict]:
    """Chunk source code with awareness of logical boundaries.

    For code files, tries to break at function/class boundaries.
    For XML (df-structures), chunks by top-level element definitions.
    For docs/wiki, uses section-header-aware chunking.
    """
    chunks = []

    if file_type == "df-structures":
        # XML structure definitions: chunk by top-level type definitions
        # Each <ld:global-type> or similar is a natural unit
        chunks = _chunk_xml_structures(text, file_path)
    elif file_type in ("cpp", "header"):
        chunks = _chunk_code_by_function(text, file_path, "cpp")
    elif file_type == "lua":
        chunks = _chunk_code_by_function(text, file_path, "lua")
    elif file_type in ("docs", "wiki"):
        chunks = _chunk_by_section(text, file_path)
    else:
        chunks = _chunk_simple(text, file_path, chunk_size, overlap)

    return chunks


def _chunk_xml_structures(text: str, file_path: str) -> list[dict]:
    """Chunk df-structures XML by type definition blocks."""
    chunks = []

    # Split on top-level type definitions
    # Pattern: <ld:global-type ...> through closing tag, or <enum-type ...>, <struct-type ...>, etc.
    type_pattern = re.compile(
        r'(<(?:ld:global-type|enum-type|struct-type|bitfield-type|class-type|df-linked-list-type)[^>]*>.*?</(?:ld:global-type|enum-type|struct-type|bitfield-type|class-type|df-linked-list-type)>)',
        re.DOTALL
    )

    matches = list(type_pattern.finditer(text))

    if not matches:
        # Fallback: chunk entire file
        return _chunk_simple(text, file_path, 2000, 200)

    # Also capture the file header (namespace, imports)
    if matches[0].start() > 50:
        header = text[:matches[0].start()].strip()
        if header:
            # Extract type-name from header for context
            chunks.append({
                "text": header,
                "metadata": {
                    "section": "file_header",
                    "file_path": file_path,
                }
            })

    for match in matches:
        block = match.group(0)
        # Extract the type name for metadata
        name_match = re.search(r'(?:type-name|name)=["\']([^"\']+)["\']', block)
        type_name = name_match.group(1) if name_match else "unknown"

        # If block is too large, sub-chunk it
        if len(block) > 3000:
            sub_chunks = _chunk_simple(block, file_path, 2000, 200)
            for i, sc in enumerate(sub_chunks):
                sc["metadata"]["section"] = f"type:{type_name}:part{i}"
            chunks.extend(sub_chunks)
        else:
            chunks.append({
                "text": block,
                "metadata": {
                    "section": f"type:{type_name}",
                    "file_path": file_path,
                }
            })

    return chunks


def _chunk_code_by_function(text: str, file_path: str, lang: str) -> list[dict]:
    """Chunk code files trying to break at function boundaries."""
    chunks = []

    if lang == "cpp":
        # Split at function definitions: lines starting with return_type function_name(
        # or at class definitions, namespace blocks
        split_pattern = re.compile(
            r'\n(?=(?:static |virtual |inline |extern |void |int |bool |std::|const |unsigned |'
            r'class |struct |namespace |template |#include |/\*\*|/// ))',
            re.MULTILINE
        )
    elif lang == "lua":
        # Split at function definitions and local function declarations
        split_pattern = re.compile(
            r'\n(?=(?:function |local function |-- =|----))',
            re.MULTILINE
        )
    else:
        return _chunk_simple(text, file_path, 1500, 200)

    segments = split_pattern.split(text)

    current_chunk = ""
    for segment in segments:
        if len(current_chunk) + len(segment) > 2000 and current_chunk:
            chunks.append({
                "text": current_chunk.strip(),
                "metadata": {"file_path": file_path}
            })
            # Keep last 200 chars as overlap
            current_chunk = current_chunk[-200:] + segment
        else:
            current_chunk += segment

    if current_chunk.strip():
        chunks.append({
            "text": current_chunk.strip(),
            "metadata": {"file_path": file_path}
        })

    return chunks if chunks else _chunk_simple(text, file_path, 1500, 200)


def _chunk_by_section(text: str, file_path: str) -> list[dict]:
    """Chunk markdown/RST by section headings."""
    # Split on markdown or RST headings
    sections = re.split(r'\n(?=#{1,4}\s|\n[=-]{3,}\n)', text)

    chunks = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        if len(section) > 2500:
            chunks.extend(_chunk_simple(section, file_path, 1500, 200))
        elif len(section) > 50:  # skip very small sections
            chunks.append({
                "text": section,
                "metadata": {"file_path": file_path}
            })

    return chunks if chunks else _chunk_simple(text, file_path, 1500, 200)


def _chunk_simple(text: str, file_path: str, chunk_size: int = 1500,
                  overlap: int = 200) -> list[dict]:
    """Simple overlapping character-based chunking."""
    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)

        # Try to break at a newline
        if end < text_len:
            newline_pos = text.rfind('\n', start + chunk_size - 300, end)
            if newline_pos > start:
                end = newline_pos + 1

        chunk_text = text[start:end].strip()
        if chunk_text and len(chunk_text) > 30:
            chunks.append({
                "text": chunk_text,
                "metadata": {"file_path": file_path}
            })

        start = end - overlap
        if start >= text_len:
            break

    return chunks


def should_skip(file_path: Path, exclude_dirs: set) -> bool:
    """Check if a file should be skipped based on exclude dirs."""
    parts = file_path.parts
    for excl in exclude_dirs:
        if excl in parts:
            return True
    # Skip very large files (>500KB likely auto-generated)
    if file_path.stat().st_size > 500_000:
        return True
    # Skip binary/generated files
    if file_path.suffix in ('.o', '.obj', '.dll', '.so', '.exe', '.pyc', '.png', '.jpg', '.gif'):
        return True
    return False


def ensure_collection(qdrant: QdrantClient, name: str, recreate: bool = False):
    """Create a Qdrant collection if it doesn't exist."""
    existing = [c.name for c in qdrant.get_collections().collections]

    if name in existing:
        if recreate:
            print(f"  Recreating collection '{name}'...")
            qdrant.delete_collection(name)
        else:
            print(f"  Collection '{name}' already exists, will upsert.")
            return

    qdrant.create_collection(
        collection_name=name,
        vectors_config=VectorParams(
            size=EMBED_DIM,
            distance=Distance.COSINE,
        ),
    )
    print(f"  Created collection '{name}' (dim={EMBED_DIM}, cosine)")


def index_source(source_name: str, qdrant: QdrantClient, recreate: bool = False):
    """Index a single source into its Qdrant collection."""
    config = SOURCE_CONFIG[source_name]
    base_dir = config["base_dir"]
    collection = config["collection"]
    patterns = config["patterns"]
    exclude_dirs = config["exclude_dirs"]

    print(f"\n{'='*60}")
    print(f"Indexing: {source_name}")
    print(f"  Source: {base_dir}")
    print(f"  Collection: {collection}")
    print(f"{'='*60}")

    if not base_dir.exists():
        print(f"  ERROR: Source directory not found: {base_dir}")
        return

    ensure_collection(qdrant, collection, recreate)

    # Collect all files
    all_files = []
    for pattern, file_type in patterns.items():
        matched = sorted(base_dir.glob(pattern))
        for f in matched:
            if f.is_file() and not should_skip(f, exclude_dirs):
                all_files.append((f, file_type))

    # Deduplicate (a file might match multiple patterns)
    seen = set()
    unique_files = []
    for f, ft in all_files:
        if f not in seen:
            seen.add(f)
            unique_files.append((f, ft))

    print(f"  Found {len(unique_files)} files to index")

    stats = {"indexed": 0, "chunks": 0, "skipped": 0, "errors": 0}

    for i, (file_path, file_type) in enumerate(unique_files):
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
            if not text.strip():
                stats["skipped"] += 1
                continue

            file_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
            rel_path = str(file_path.relative_to(base_dir))

            # Check if already indexed
            try:
                existing = qdrant.scroll(
                    collection_name=collection,
                    scroll_filter=Filter(
                        must=[FieldCondition(key="file_hash", match=MatchValue(value=file_hash))]
                    ),
                    limit=1,
                )
                if existing[0]:
                    stats["skipped"] += 1
                    continue
            except Exception:
                pass

            # Delete old vectors for this file
            try:
                qdrant.delete(
                    collection_name=collection,
                    points_selector=Filter(
                        must=[FieldCondition(key="source", match=MatchValue(value=rel_path))]
                    ),
                )
            except Exception:
                pass

            # Chunk the file
            chunks = chunk_code(text, rel_path, file_type)

            # Embed and upsert
            points = []
            for ci, chunk_data in enumerate(chunks):
                try:
                    embedding = get_embedding(chunk_data["text"])
                except Exception as e:
                    print(f"    Embedding error on {rel_path} chunk {ci}: {e}")
                    continue

                point_id = abs(hash(f"{collection}:{rel_path}:{ci}:{file_hash}")) % (2**63)
                payload = {
                    "text": chunk_data["text"],
                    "source": rel_path,
                    "file_name": file_path.name,
                    "file_ext": file_path.suffix,
                    "file_type": file_type,
                    "chunk_index": ci,
                    "total_chunks": len(chunks),
                    "file_hash": file_hash,
                }
                payload.update(chunk_data.get("metadata", {}))

                points.append(PointStruct(id=point_id, vector=embedding, payload=payload))

            # Upsert in batches
            if points:
                for batch_start in range(0, len(points), 50):
                    batch = points[batch_start:batch_start + 50]
                    qdrant.upsert(collection_name=collection, points=batch)

                stats["indexed"] += 1
                stats["chunks"] += len(points)

            if (i + 1) % 25 == 0 or (i + 1) == len(unique_files):
                print(f"  [{i+1}/{len(unique_files)}] "
                      f"indexed={stats['indexed']}, chunks={stats['chunks']}, "
                      f"skipped={stats['skipped']}, errors={stats['errors']}")

        except Exception as e:
            stats["errors"] += 1
            if stats["errors"] <= 10:
                print(f"    Error on {file_path.name}: {e}")

    print(f"\n  DONE: {stats['indexed']} files, {stats['chunks']} chunks, "
          f"{stats['skipped']} skipped, {stats['errors']} errors")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Index DwarfCron sources into Qdrant")
    parser.add_argument("--source", default="all",
                        choices=["dfhack", "dwarf-therapist", "df-wiki", "all"])
    parser.add_argument("--qdrant-url", default=QDRANT_URL)
    parser.add_argument("--ollama-url", default=OLLAMA_URL)
    parser.add_argument("--recreate", action="store_true",
                        help="Recreate collections (deletes existing data)")
    args = parser.parse_args()

    qdrant_url = args.qdrant_url
    ollama_url = args.ollama_url

    qdrant = QdrantClient(url=qdrant_url)

    # Verify Qdrant connectivity
    try:
        qdrant.get_collections()
        print("[+] Qdrant connected")
    except Exception as e:
        print(f"[!] Cannot connect to Qdrant at {QDRANT_URL}: {e}")
        sys.exit(1)

    # Verify Ollama connectivity
    try:
        resp = http_client.get(f"{OLLAMA_URL}/api/tags")
        models = [m["name"] for m in resp.json().get("models", [])]
        if not any(EMBED_MODEL in m for m in models):
            print(f"[!] Embedding model '{EMBED_MODEL}' not found in Ollama. Available: {models}")
            sys.exit(1)
        print(f"[+] Ollama connected, model '{EMBED_MODEL}' available")
    except Exception as e:
        print(f"[!] Cannot connect to Ollama at {OLLAMA_URL}: {e}")
        sys.exit(1)

    sources = list(SOURCE_CONFIG.keys()) if args.source == "all" else [args.source]

    total_stats = {"indexed": 0, "chunks": 0, "skipped": 0, "errors": 0}

    for source in sources:
        result = index_source(source, qdrant, args.recreate)
        if result:
            for k in total_stats:
                total_stats[k] += result.get(k, 0)

    print(f"\n{'='*60}")
    print(f"TOTAL: {total_stats['indexed']} files, {total_stats['chunks']} chunks, "
          f"{total_stats['skipped']} skipped, {total_stats['errors']} errors")

    # Show final collection stats
    print(f"\nCollection stats:")
    for c in qdrant.get_collections().collections:
        info = qdrant.get_collection(c.name)
        print(f"  {c.name}: {info.points_count} vectors")


if __name__ == "__main__":
    main()
