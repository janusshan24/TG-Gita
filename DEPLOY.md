# 🚀 Deployment Guide — Free Hosting

**Stack:** Groq API (free LLM) · Render (free backend) · Vercel (free frontend)
**Cost:** $0/month

---

## Overview

```
Browser → Vercel (React frontend)
              ↓ /api/chat
         Render (FastAPI backend)
              ↓ vector search
         ChromaDB (bundled in repo)
              ↓ LLM call
         Groq API (Llama 3.1, free)
```

---

## Step 1 — Get a free Groq API key (2 min)

1. Go to **[console.groq.com](https://console.groq.com)** and sign up (free, no credit card)
2. Click **API Keys → Create API Key**
3. Copy the key — you'll need it in Step 3

---

## Step 2 — Prepare your repo

The ChromaDB index needs to travel with your code (it's only ~5–10 MB).

```bash
# From your project root — run these ONCE locally first if you haven't yet:
python scripts/scrape_gita.py     # downloads the Gita (~30 min)
python scripts/index_gita.py      # builds the vector index

# Make sure data/chroma_db/ exists and has files in it
ls data/chroma_db/
```

Then push everything to GitHub:

```bash
cd /Users/janusshan/Desktop/iskcon-chatbot

git init
git add .
git commit -m "Initial commit — ISKCON Gita chatbot"

# Create a repo on github.com, then:
git remote add origin https://github.com/YOUR_USERNAME/iskcon-chatbot.git
git push -u origin main
```

> ⚠️ Make sure `data/chroma_db/` is NOT in `.gitignore` — we need it deployed.

---

## Step 3 — Deploy backend to Render (5 min)

1. Go to **[render.com](https://render.com)** → sign up free → **New → Web Service**
2. Connect your GitHub repo
3. Render will auto-detect `render.yaml` — click **Apply**
4. Under **Environment Variables**, add:
   - Key: `GROQ_API_KEY`
   - Value: *(paste your key from Step 1)*
5. Click **Create Web Service**
6. Wait ~3 min for the first deploy to finish
7. Copy your backend URL — it looks like:
   `https://iskcon-gita-backend.onrender.com`

> **Free tier note:** The app sleeps after 15 min of inactivity. First request after sleep takes ~30 sec to wake up. This is normal on the free tier.

---

## Step 4 — Deploy frontend to Vercel (3 min)

1. Open `frontend/.env.production` and replace the URL with your Render URL:
   ```
   VITE_API_URL=https://iskcon-gita-backend.onrender.com
   ```
2. Commit and push that change:
   ```bash
   git add frontend/.env.production
   git commit -m "Set production API URL"
   git push
   ```
3. Go to **[vercel.com](https://vercel.com)** → sign up free → **Add New Project**
4. Import your GitHub repo
5. Set **Root Directory** to `frontend`
6. Vercel auto-detects Vite — click **Deploy**
7. Your chatbot is live at `https://your-project.vercel.app` 🎉

---

## Step 5 — Connect a custom domain (optional)

In Vercel → Project → Settings → Domains, add your domain (e.g. `gita.yourdomain.com`).
Vercel handles the SSL certificate automatically.

---

## Updating the chatbot

Any `git push` to `main` automatically re-deploys both Render and Vercel.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Backend returns 500 | Check Render logs → likely missing `GROQ_API_KEY` |
| Cold start takes 30s | Normal on free tier — add a loading message in the UI |
| ChromaDB not found | Make sure `data/chroma_db/` is committed to git |
| CORS errors | Your Render URL must match `VITE_API_URL` exactly (no trailing slash) |

---

## Upgrading later

- **Render Starter ($7/mo):** Eliminates cold starts — always on
- **Better LLM:** Change `GROQ_MODEL` env var to `llama-3.1-70b-versatile` for deeper answers (still free on Groq)
- **More books:** Add Srimad-Bhagavatam etc. — see the main README for instructions
