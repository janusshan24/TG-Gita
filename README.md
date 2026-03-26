# 🕉️ ISKCON Gita Chatbot

A RAG-powered chatbot that lets you have a conversation with the **Bhagavad-gita As It Is** by Srila Prabhupada — powered by a fully local, free, open-source stack.

---

## Architecture

```
User question
     │
     ▼
Sentence-Transformers (embed query)
     │
     ▼
ChromaDB (find top-5 most relevant verses/purports)
     │
     ▼
Ollama / Llama 3.1 (generate grounded answer with citations)
     │
     ▼
FastAPI (streaming SSE response)
     │
     ▼
React frontend (renders streamed text + source cards)
```

**Stack:**
- **Backend**: Python · FastAPI · ChromaDB · sentence-transformers · httpx
- **LLM**: Ollama (Llama 3.1 — runs locally, no API costs)
- **Frontend**: React 18 · Vite · plain CSS

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | ≥ 3.11 | [python.org](https://python.org) |
| Node.js | ≥ 20 | [nodejs.org](https://nodejs.org) |
| Ollama | latest | [ollama.com](https://ollama.com) |

---

## Step 1 — Install Ollama & pull the model

```bash
# macOS / Linux
curl -fsSL https://ollama.com/install.sh | sh

# Pull Llama 3.1 (8B model, ~4.7 GB)
ollama pull llama3.1

# Start the Ollama server (runs on http://localhost:11434)
ollama serve
```

> **Tip:** For faster responses on a GPU machine, Ollama will automatically use your GPU. On CPU-only, expect ~2–10 seconds per response.

---

## Step 2 — Backend setup

```bash
cd backend

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## Step 3 — Scrape the Bhagavad-gita

This downloads all 700 verses + purports from vedabase.io (~30–40 min with polite rate limiting).

```bash
# From the project root
python scripts/scrape_gita.py
```

Output: `data/bhagavad_gita.json` (~700 verse records)

> **Already have the data?** You can skip this step and provide your own `bhagavad_gita.json` following the same schema.

---

## Step 4 — Index into ChromaDB

```bash
python scripts/index_gita.py
```

This embeds every verse+purport with `all-MiniLM-L6-v2` and stores vectors in `data/chroma_db/`.
Re-running is safe — upsert is idempotent.

---

## Step 5 — Start the backend

```bash
cd backend
python main.py
# → http://localhost:8000
# → Swagger docs: http://localhost:8000/docs
```

Optional environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_MODEL` | `llama3.1` | Any model pulled via `ollama pull` |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server URL |
| `TOP_K` | `5` | Number of verses retrieved per query |
| `CHROMA_PATH` | `data/chroma_db` | Path to ChromaDB storage |

---

## Step 6 — Start the frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

Open your browser → ask away! 🙏

---

## Deployment to a Public URL

For a publicly accessible chatbot you'll need a server that can run Ollama (≥8 GB RAM recommended).

### Option A — DigitalOcean Droplet (recommended)

1. Create a **Basic Droplet** (4 vCPU / 8 GB RAM / Ubuntu 22.04) — ~$48/mo
2. SSH in, install Ollama + Python + Node.js
3. Clone your repo, follow Steps 1–5
4. Use **Caddy** or **nginx** as a reverse proxy with HTTPS:
   ```
   https://gita.yourdomain.com → FastAPI :8000
   https://gita.yourdomain.com (static) → React build
   ```
5. Build the React app: `cd frontend && npm run build`
6. Serve `frontend/dist/` as static files via your reverse proxy

### Option B — Fly.io (cheaper, serverless)

Fly.io supports persistent volumes for ChromaDB, but Ollama requires a GPU or larger VM.
See [fly.io/docs](https://fly.io/docs) for machine configuration.

### Option C — Swap Ollama for a cloud LLM (zero-GPU option)

If you don't want to manage a GPU server, swap `rag.py`'s Ollama call for the Anthropic or OpenAI SDK — the RAG retrieval logic stays identical.

---

## Project Structure

```
iskcon-chatbot/
├── backend/
│   ├── main.py           # FastAPI app & routes
│   ├── rag.py            # RAG pipeline (retrieval + Ollama streaming)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── index.css
│   │   └── components/
│   │       ├── ChatMessage.jsx
│   │       └── SourceCard.jsx
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── scripts/
│   ├── scrape_gita.py    # Vedabase.io scraper
│   └── index_gita.py     # Embedding + ChromaDB indexer
└── data/                 # (created after running scripts)
    ├── bhagavad_gita.json
    └── chroma_db/
```

---

## Expanding to More Books

To add Srimad-Bhagavatam, Chaitanya Charitamrita, etc.:

1. Add a new scraper in `scripts/` targeting their vedabase.io URLs
2. Run the new scraper → saves to `data/<book>.json`
3. Add a new ChromaDB collection (or extend the existing one with a `book` metadata field)
4. Update `rag.py` to query across multiple collections or filter by book

---

## License

Content from vedabase.io is © The Bhaktivedanta Book Trust International. This project is for personal/educational use. Please respect the BBT's terms of use when deploying publicly.

---

Hare Krishna! 🙏
