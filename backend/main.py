"""
main.py
-------
FastAPI app for the ISKCON Gita chatbot.

Endpoints:
  POST /api/chat        — streaming SSE chat response
  GET  /api/health      — health check
  GET  /api/stats       — collection stats
"""

from __future__ import annotations

import json
import logging
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from rag import get_collection, retrieve, stream_answer

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="ISKCON Gita Chatbot API",
    description="RAG-powered Q&A over Bhagavad-gita As It Is by Srila Prabhupada",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Restrict in production to your frontend domain
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ───────────────────────────────────────────────────────────────────
class Message(BaseModel):
    role: str          # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    question: str
    history: list[Message] = []


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "iskcon-gita-chatbot"}


@app.get("/api/stats")
async def stats():
    try:
        col = get_collection()
        return {
            "collection": col.name,
            "total_verses_indexed": col.count(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """
    Returns a Server-Sent Events (SSE) stream.

    Each event is either:
      data: <text chunk>
      data: __SOURCES__[{"reference":…,"url":…,"score":…}, …]
    """
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    history = [m.model_dump() for m in req.history]
    log.info("Chat | Q: %s", req.question[:80])

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            async for chunk in stream_answer(req.question, history):
                # SSE format: each line starts with "data: "
                yield f"data: {json.dumps(chunk)}\n\n"
        except Exception as e:
            log.exception("Stream error")
            error_payload = json.dumps({"error": str(e)})
            yield f"data: __ERROR__{error_payload}\n\n"
        finally:
            yield "data: __DONE__\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":  "no-cache",
            "X-Accel-Buffering": "no",   # disable nginx buffering
        },
    )


# ── Dev server ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
