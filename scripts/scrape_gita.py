"""
scrape_gita.py
--------------
Scrapes the Bhagavad-gita As It Is (all 18 chapters) from vedabase.io
and saves each verse (or verse group) as a structured JSON record.

Handles combined verses like BG 1.16-18, 11.26-27, 13.8-12, etc.
by first discovering the real verse URLs from each chapter's index page.

Output: data/bhagavad_gita.json

Usage:
    python scripts/scrape_gita.py
"""

from __future__ import annotations   # fixes `X | None` on Python < 3.10

import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL    = "https://vedabase.io/en/library/bg"
OUTPUT_PATH = Path(__file__).parent.parent / "data" / "bhagavad_gita.json"
CHAPTERS    = range(1, 19)          # chapters 1–18
CRAWL_DELAY = 0.8                   # seconds between requests (be polite)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; ISKCONBot/1.0; "
        "+https://github.com/your-repo/iskcon-chatbot)"
    )
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def get(url: str) -> BeautifulSoup | None:
    """GET a page and return a BeautifulSoup object, or None on error."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except requests.RequestException as e:
        print(f"  ✗ {url} → {e}")
        return None


def discover_verse_urls(chapter: int) -> list[str]:
    """
    Scrape the chapter index page and return all verse page URLs in order.
    This naturally captures combined verses like /bg/1/16-18/.
    """
    chapter_url = f"{BASE_URL}/{chapter}/"
    soup = get(chapter_url)
    if not soup:
        return []

    urls = []
    # Verse links look like /en/library/bg/1/1/ or /en/library/bg/1/16-18/
    pattern = re.compile(rf"^/en/library/bg/{chapter}/[\d\-]+/$")
    seen = set()

    for a in soup.find_all("a", href=pattern):
        href = a["href"]
        full = "https://vedabase.io" + href
        if full not in seen:
            seen.add(full)
            urls.append(full)

    return urls


def parse_verse_slug(url: str) -> str:
    """Extract the verse slug from a URL, e.g. '16-18' from .../bg/1/16-18/"""
    parts = url.rstrip("/").split("/")
    return parts[-1]   # e.g. "16-18" or "5"


def fetch_verse_page(url: str, chapter: int) -> dict | None:
    """Fetch a verse (or verse-group) page and extract all fields."""
    slug = parse_verse_slug(url)

    # Build a clean reference string: "BG 1.16-18" or "BG 2.47"
    reference = f"BG {chapter}.{slug.replace('-', '–')}"

    # Build a stable id: "bg_1_16-18" or "bg_2_47"
    record_id = f"bg_{chapter}_{slug}"

    soup = get(url)
    if not soup:
        return None

    def text(selector: str) -> str:
        el = soup.select_one(selector)
        if not el:
            return ""
        for tag in el.select("sup, nav, .footnote, script"):
            tag.decompose()
        return el.get_text(separator="\n", strip=True)

    sanskrit    = text(".r-verse-text, .verse-text, [class*='devanagari']")
    synonyms    = text(".r-synonyms, .synonyms, [class*='synonyms']")
    translation = text(".r-translation, .translation, [class*='translation']")
    purport     = text(".r-purport, .purport, [class*='purport']")

    # Fallback if translation selector missed
    if not translation:
        main = soup.select_one("article, main, #content")
        if main:
            translation = main.get_text(separator=" ", strip=True)[:800]

    return {
        "id":          record_id,
        "chapter":     chapter,
        "verse":       slug,           # e.g. "16-18" or "47"
        "reference":   reference,
        "url":         url,
        "sanskrit":    sanskrit,
        "synonyms":    synonyms,
        "translation": translation.strip(),
        "purport":     purport.strip(),
    }


def fetch_chapter_intro(chapter: int) -> dict | None:
    """Fetch the chapter introduction page."""
    url  = f"{BASE_URL}/{chapter}/"
    soup = get(url)
    if not soup:
        return None

    intro_el = soup.select_one("article, .chapter-intro, main")
    intro_text = intro_el.get_text(separator="\n", strip=True) if intro_el else ""

    h1    = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else f"Chapter {chapter}"

    return {
        "id":          f"bg_{chapter}_intro",
        "chapter":     chapter,
        "verse":       "intro",
        "reference":   f"BG Chapter {chapter} Introduction",
        "url":         url,
        "sanskrit":    "",
        "synonyms":    "",
        "translation": "",
        "purport":     intro_text[:3000],
        "title":       title,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    all_records = []

    print(f"📖 Scraping Bhagavad-gita As It Is from {BASE_URL}\n")

    for chapter in CHAPTERS:
        print(f"── Chapter {chapter} ──────────────────────────────────────")

        # 1. Chapter introduction
        intro = fetch_chapter_intro(chapter)
        if intro:
            all_records.append(intro)
            print(f"  ✓ Chapter {chapter} intro  ({intro['title'][:50]})")
        time.sleep(CRAWL_DELAY)

        # 2. Discover real verse URLs (handles combined verses automatically)
        verse_urls = discover_verse_urls(chapter)
        print(f"  → Found {len(verse_urls)} verse pages in chapter {chapter}")

        for url in verse_urls:
            record = fetch_verse_page(url, chapter)
            if record:
                all_records.append(record)
                print(f"  ✓ {record['reference']}")
            else:
                print(f"  ✗ Failed: {url}")
            time.sleep(CRAWL_DELAY)

    # Save
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Done! Saved {len(all_records)} records → {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
