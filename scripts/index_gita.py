"""
index_gita.py
-------------
Reads data/bhagavad_gita.json, creates text chunks per verse,
embeds them with sentence-transformers, and upserts into ChromaDB.

Usage:
    python scripts/index_gita.py

Run this ONCE after scraping. Re-running is safe (upsert is idempotent).
"""

import json
from pathlib import Path

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# ── Config ────────────────────────────────────────────────────────────────────
DATA_PATH   = Path(__file__).parent.parent / "data" / "bhagavad_gita.json"
CHROMA_PATH = Path(__file__).parent.parent / "data" / "chroma_db"
COLLECTION  = "bhagavad_gita"
EMBED_MODEL = "all-MiniLM-L6-v2"   # 80 MB, runs on CPU, no GPU needed
BATCH_SIZE  = 64
# ──────────────────────────────────────────────────────────────────────────────


def build_chunk_text(record: dict) -> str:
    """
    Combine the parts of a verse into a single searchable string.
    The model will embed this; the full record is stored as metadata.
    """
    parts = []
    if record.get("reference"):
        parts.append(record["reference"])
    if record.get("title"):
        parts.append(record["title"])
    if record.get("translation"):
        parts.append("Translation: " + record["translation"])
    # Include first 800 chars of purport so semantic search hits purport topics
    if record.get("purport"):
        parts.append("Purport: " + record["purport"][:800])
    return "\n\n".join(parts)


def main():
    # Load data
    print(f"📂 Loading data from {DATA_PATH}")
    with open(DATA_PATH, encoding="utf-8") as f:
        records = json.load(f)
    print(f"   {len(records)} records loaded.\n")

    # Load embedding model
    print(f"🤖 Loading embedding model: {EMBED_MODEL}")
    model = SentenceTransformer(EMBED_MODEL)

    # Connect to (or create) ChromaDB
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_or_create_collection(
        name=COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )
    print(f"📦 ChromaDB collection: '{COLLECTION}' at {CHROMA_PATH}\n")

    # Process in batches
    ids, texts, metadatas, embeddings = [], [], [], []

    def flush():
        if not ids:
            return
        embs = model.encode(texts, batch_size=BATCH_SIZE, show_progress_bar=False)
        collection.upsert(
            ids=ids,
            embeddings=embs.tolist(),
            documents=texts,
            metadatas=metadatas,
        )
        ids.clear(); texts.clear(); metadatas.clear()

    print("⚙️  Embedding and indexing…")
    for record in tqdm(records, unit="verse"):
        chunk = build_chunk_text(record)
        if not chunk.strip():
            continue

        ids.append(record["id"])
        texts.append(chunk)
        metadatas.append({
            "chapter":     record["chapter"],
            "verse":       record["verse"],
            "reference":   record.get("reference", ""),
            "url":         record.get("url", ""),
            "translation": record.get("translation", "")[:500],
            "purport_snippet": record.get("purport", "")[:500],
        })

        if len(ids) >= BATCH_SIZE:
            flush()

    flush()  # final batch

    total = collection.count()
    print(f"\n✅ Indexing complete! {total} vectors stored in ChromaDB.")


if __name__ == "__main__":
    main()
