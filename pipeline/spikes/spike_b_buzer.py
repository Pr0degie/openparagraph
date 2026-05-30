#!/usr/bin/env python3
"""
Spike B — FNA acquisition, SECONDARY path: scrape the buzer.de FNA tree.

⚠️  OPERATIONAL CAVEAT (the central finding of this path):
buzer.de mirrors the FNA in clean, easily-parsed HTML — each leaf page carries
a law table with the EXACT code per law:

    <td class="fnal">400-2</td> … <a class="ltg" href="/BGB.htm">Bürgerliches…</a>

…but it defends itself with an aggressive behavioural anti-bot. A fast crawl
(~7 req/s) trips a firewall-level block: first `ConnectionError` (connection
refused), then a persistent HTTP 403 with body "use gateway to start". The
block does NOT clear on its own within ~45 min and is *renewed* by continued
probing. robots.txt itself permits /fna/ (only /s2.htm, some .js, /outb/,
newsletter and ?m=/?line= patterns are disallowed) — the block is purely
rate/behaviour based.

Consequence: buzer is NOT a reliable dependency for an unattended weekly CI
build. It is usable only as best-effort *enrichment* with a slow, jittered,
disk-cached, single-threaded crawler that backs off hard on any block. The
PRIMARY FNA source is therefore the BMJ PDF (see spike_b_fna.py + ADR 002).

This script is kept as the buzer prototype. It will most likely hit the 403
gateway block when run from a cold IP; that is the documented behaviour, not a
bug. The disk cache makes any partial progress resumable.

Run:  uv run python spikes/spike_b_buzer.py      # expect a 403 gateway block
"""

from __future__ import annotations

import hashlib
import html as html_mod
import json
import logging
import os
import random
import re
import time
from pathlib import Path
from urllib.parse import quote, unquote

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("spike_b_buzer")

BUZER = "https://www.buzer.de"
OUT_DIR = Path(__file__).parent.parent.parent / "data" / "spike_b"
CACHE = OUT_DIR / "buzer_cache"
# buzer blocks aggressive crawling, so be slow and jittered. Even so, a cold IP
# will usually receive the "use gateway to start" 403.
POLITE_DELAY = float(os.environ.get("SPIKE_B_DELAY", "1.1"))
MAX_PAGES = 2000

HEADERS = {"User-Agent": "openparagraph-spike-b/0.1 (research; github.com/openparagraph)"}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

NON_LAW_SLUGS = {
    "index", "s", "z", "v", "h", "i", "li", "k", "fna", "werben", "quality",
    "screen", "print", "buzer", "gesetze-ticker", "gesetze_feed",
    "rechtskataster", "Gesetze_PDF_ausdrucken",
}

# Law row: <td class="fnal">CODE</td> <td> … <a href="URL" class="ltg">TITLE</a>
ROW_RE = re.compile(
    r'<td class="fnal">\s*([0-9][0-9\-]*)\s*</td>\s*'
    r'<td>.*?<a\s+href="([^"]+)"[^>]*class="ltg"[^>]*>(.*?)</a>',
    re.S,
)


def fetch(path: str) -> str:
    """GET buzer.de<path> with on-disk cache, jittered delay and hard backoff."""
    CACHE.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(path.encode("utf-8")).hexdigest()[:16]
    cached = CACHE / f"{key}.html"
    if cached.exists():
        return cached.read_text(encoding="utf-8")

    url = BUZER + quote(path, safe="/%?=&")
    last_exc: Exception | None = None
    for attempt in range(5):
        try:
            r = SESSION.get(url, timeout=25)
            if r.status_code == 403 and "gateway" in r.text:
                raise RuntimeError("403 'use gateway to start' — anti-bot block active")
            r.raise_for_status()
            time.sleep(POLITE_DELAY + random.uniform(0, 0.6))
            cached.write_text(r.text, encoding="utf-8")
            return r.text
        except Exception as exc:  # noqa: BLE001 — network is dirty / blocked
            last_exc = exc
            wait = min(60, 4 * (2 ** attempt)) + random.uniform(0, 3)
            log.warning("  fetch %s failed (%s); retry in %.1fs", path, exc, wait)
            time.sleep(wait)
    raise RuntimeError(f"giving up on {path}: {last_exc}")


def code_of_fna_path(path: str) -> str | None:
    m = re.search(r"/fna/([^-]+)-", unquote(path))
    return m.group(1).strip() if m else None


def child_fna_links(page_html: str) -> set[str]:
    out: set[str] = set()
    for href in re.findall(r'href="(/fna/[^"]+\.htm)"', page_html):
        href = html_mod.unescape(href)
        if "setmobile" in href or href.endswith("/index.htm"):
            continue
        out.add(href)
    return out


def slug_from_url(url: str) -> str | None:
    m = re.search(r"buzer\.de/([^/]+)\.htm$", url)
    if not m:
        return None
    slug = html_mod.unescape(m.group(1))
    return None if slug.lower() in NON_LAW_SLUGS or "/" in slug else slug


def parse_law_rows(page_html: str) -> list[dict]:
    rows = []
    for code, url, raw_title in ROW_RE.findall(page_html):
        title = html_mod.unescape(re.sub(r"<[^>]+>", "", raw_title)).strip()
        rows.append({
            "code": code.strip(),
            "main_group": code.strip()[0],
            "abbr": slug_from_url(html_mod.unescape(url)),
            "title": re.sub(r"\s*\([^()]+\)\s*$", "", title).strip(),
        })
    return rows


def crawl_fna_tree() -> list[dict]:
    """BFS the FNA tree; return all law rows. Raises on the gateway block."""
    root = fetch("/fna/index.htm")
    frontier = sorted(child_fna_links(root))
    seen = set(frontier)
    all_rows: list[dict] = []
    pages = 0
    while frontier and pages < MAX_PAGES:
        nxt: list[str] = []
        for path in frontier:
            code = code_of_fna_path(path)
            page = fetch(path)
            pages += 1
            all_rows.extend(parse_law_rows(page))
            for child in child_fna_links(page):
                cc = code_of_fna_path(child)
                if (child not in seen and cc and cc.isdigit() and code and code.isdigit()
                        and len(cc) > len(code) and cc.startswith(code)):
                    seen.add(child)
                    nxt.append(child)
        frontier = sorted(nxt)
    log.info("Crawl done: %d pages, %d law rows", pages, len(all_rows))
    return all_rows


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        rows = crawl_fna_tree()
    except Exception as exc:  # noqa: BLE001
        log.error("buzer crawl blocked (expected from a cold IP): %s", exc)
        log.error("This is the documented anti-bot behaviour. Use spike_b_fna.py (PDF).")
        return
    by_code = {r["code"]: r for r in rows}
    (OUT_DIR / "buzer_rows.json").write_text(
        json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("Wrote %d rows (%d unique codes)", len(rows), len(by_code))


if __name__ == "__main__":
    main()
