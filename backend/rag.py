"""
rag.py
------
Core RAG (Retrieval-Augmented Generation) logic.

Retrieves relevant Gita verses from ChromaDB, then calls the Groq API
(Llama 3.1) to generate a grounded, citation-rich answer.

Set the GROQ_API_KEY environment variable before running.
Get a free key at: https://console.groq.com
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import AsyncGenerator, Optional

import chromadb
from groq import AsyncGroq
from sentence_transformers import SentenceTransformer

# ── Config (override via environment variables) ────────────────────────────────
CHROMA_PATH  = Path(os.getenv("CHROMA_PATH", str(Path(__file__).parent.parent / "data" / "chroma_db")))
COLLECTION   = os.getenv("CHROMA_COLLECTION", "bhagavad_gita")
EMBED_MODEL  = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")
GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")   # free & fast
TOP_K        = int(os.getenv("TOP_K", "5"))
# ──────────────────────────────────────────────────────────────────────────────

# Singletons — loaded once at startup
_embedder:   Optional[SentenceTransformer] = None
_collection: Optional[chromadb.Collection] = None
_groq_client: Optional[AsyncGroq] = None


def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(EMBED_MODEL)
    return _embedder


def get_collection() -> chromadb.Collection:
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        _collection = client.get_collection(COLLECTION)
    return _collection


def get_groq() -> AsyncGroq:
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY environment variable is not set. "
                "Get a free key at https://console.groq.com"
            )
        _groq_client = AsyncGroq(api_key=api_key)
    return _groq_client


def retrieve(query: str, top_k: int = TOP_K) -> list:
    """Embed the query and return the top-k most relevant verse records."""
    query_emb  = get_embedder().encode([query])[0].tolist()
    results    = get_collection().query(
        query_embeddings=[query_emb],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    hits = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        hits.append({
            "document":        doc,
            "reference":       meta.get("reference", ""),
            "url":             meta.get("url", ""),
            "translation":     meta.get("translation", ""),
            "purport_snippet": meta.get("purport_snippet", ""),
            "score":           round(1 - dist, 4),
        })
    return hits


SYSTEM_PROMPT = """\
You are a knowledgeable and devotional assistant for Srila Prabhupada's \
Bhagavad-gita As It Is. Your role is to answer questions using ONLY the \
provided verse excerpts and purports — do not invent or speculate beyond them.

Guidelines:
- Always cite the verse reference (e.g. BG 2.47) when quoting or paraphrasing.
- Use a warm, respectful tone appropriate for spiritual inquiry.
- If the provided verses do not contain enough information to answer, say so \
  honestly and suggest the devotee consult the full text at vedabase.io.
- Keep answers clear and accessible — avoid unnecessary jargon.
- End with an encouraging spiritual note when appropriate.
"""


def build_context(hits: list) -> str:
    sections = []
    for h in hits:
        section = f"[{h['reference']}]\n"
        if h["translation"]:
            section += f"Translation: {h['translation']}\n"
        if h["purport_snippet"]:
            section += f"Purport (excerpt): {h['purport_snippet']}"
        sections.append(section.strip())
    return "\n\n---\n\n".join(sections)


async def stream_answer(
    question: str,
    history: Optional[list] = None,
) -> AsyncGenerator[str, None]:
    """
    Full RAG pipeline: retrieve → build prompt → stream Groq response.
    Yields text chunks, then a __SOURCES__ sentinel with citation data.
    """
    hits    = retrieve(question)
    context = build_context(hits)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history[-6:])
    messages.append({
        "role": "user",
        "content": (
            f"Relevant scripture excerpts:\n\n{context}\n\n"
            f"---\n\nQuestion: {question}"
        ),
    })

    # Stream from Groq
    client = get_groq()
    stream = await client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        stream=True,
        max_tokens=1024,
        temperature=0.3,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta

    # Send source citations as a sentinel after the text
    sources = [
        {"reference": h["reference"], "url": h["url"], "score": h["score"]}
        for h in hits
    ]
    yield "\n\n__SOURCES__" + json.dumps(sources)
