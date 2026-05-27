#!/usr/bin/env python3
"""Crawl a public website and convert pages to vault-native markdown.

Politely crawls a single domain to a limited depth, fetches HTML, extracts
each page's title and body, converts to markdown, and rewrites internal
links as Obsidian [[wikilinks]]. Output is a directory of markdown files
ready to feed into `vault_graph.py`.

This is the ingestion step for a Strategic Knowledge Audit on a client's
existing public content footprint.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify  # type: ignore

USER_AGENT = "Blueprint-OS-Audit-Bot/0.1 (+https://blueprintit.ai)"

# Asset and noise extensions we will never crawl.
SKIP_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico",
    ".pdf", ".zip", ".mp4", ".mov", ".mp3",
    ".css", ".js", ".xml", ".json", ".txt",
}

# URL path prefixes to skip. Cart/account/checkout/search clutter the graph;
# product detail pages explode the corpus without adding conceptual structure.
SKIP_PATH_PREFIXES = (
    "/cart", "/checkout", "/account", "/login", "/logout", "/register",
    "/search", "/api/", "/admin", "/cdn/",
    "/products/",          # individual product pages: too many, too similar
    "/policies/",          # legal boilerplate
    "/collections/vendors",  # Shopify vendor-search UI, collapses to one node
)

# Path patterns to skip. Catches Shopify-style faceted-filter URLs and
# collection-scoped product URLs (e.g. /collections/X/color_white,
# /collections/X/products/Y). These are filter/detail views, not concept pages.
SKIP_PATH_PATTERNS = (
    re.compile(r"^/collections/[^/]+/.+"),
)

# Sentinels chosen to survive markdownify without escaping. No underscores,
# no markdown-special chars, but distinctive enough to never collide with content.
WIKILINK_OPEN = "zzWIKIOPENzz"
WIKILINK_CLOSE = "zzWIKICLOSEzz"
WIKILINK_SEP = "zzWIKISEPzz"


def normalize_url(url: str) -> str:
    url, _ = urldefrag(url)
    parsed = urlparse(url)
    # collapse trailing slash except for site root
    path = parsed.path
    if path.endswith("/") and len(path) > 1:
        path = path.rstrip("/")
    return parsed._replace(path=path, query="", fragment="").geturl()


def is_crawlable(url: str, base_netloc: str) -> bool:
    parsed = urlparse(url)
    if parsed.netloc != base_netloc:
        return False
    path = parsed.path.lower()
    if any(path.endswith(ext) for ext in SKIP_EXTENSIONS):
        return False
    if any(path.startswith(pref) for pref in SKIP_PATH_PREFIXES):
        return False
    if any(pat.search(path) for pat in SKIP_PATH_PATTERNS):
        return False
    return True


def slug_to_title(path: str) -> str:
    """Convert a URL path like '/collections/outdoor-patio' into 'Outdoor Patio'."""
    segment = path.strip("/").split("/")[-1]
    if not segment:
        return ""
    # Strip Shopify-style collection prefixes ("living-room-sofas" -> "Sofas") only
    # when the segment is long; otherwise titleize as-is.
    words = segment.replace("_", "-").split("-")
    return " ".join(w.capitalize() for w in words if w)


def safe_slug(s: str) -> str:
    s = s.strip()
    s = re.sub(r"[^A-Za-z0-9\-\s]", "", s)
    s = re.sub(r"\s+", "-", s)
    return (s[:80] or "untitled").lower()


def filename_for_title(s: str) -> str:
    """Build a filename that matches the wikilink target.

    Obsidian wikilinks resolve to files by basename. Preserve title casing
    and spaces, only strip filesystem-unsafe characters, so [[Contact Us]]
    resolves to 'Contact Us.md'.
    """
    s = s.strip().lstrip("#").strip()
    s = re.sub(r'[/\\:*?"<>|]+', "-", s)
    s = re.sub(r"\s+", " ", s)
    return (s[:120] or "Untitled")


def clean_title(raw: str, site_name_hint: str | None = None) -> str:
    """Strip common 'Section | Site Name' suffixes; return the specific part."""
    t = raw.strip()
    for sep in (" | ", " - ", " :: ", " — "):
        if sep in t:
            parts = [p.strip() for p in t.split(sep) if p.strip()]
            if len(parts) >= 2:
                if site_name_hint:
                    parts = [p for p in parts if site_name_hint.lower() not in p.lower()] or parts
                t = parts[0] if len(parts[0]) >= 4 else max(parts, key=len)
                break
    return t


def extract_title(soup: BeautifulSoup, url: str, site_name_hint: str | None) -> str:
    if soup.title and soup.title.string:
        title = clean_title(soup.title.string, site_name_hint)
        if title:
            return title
    if soup.h1 and soup.h1.get_text(strip=True):
        return soup.h1.get_text(strip=True)
    path = urlparse(url).path.strip("/")
    return path.replace("/", " - ").replace("-", " ").title() or "Home"


def fetch(session: requests.Session, url: str) -> tuple[str, str] | None:
    """Return (final_url, html) on success."""
    try:
        r = session.get(url, timeout=15, allow_redirects=True)
    except requests.RequestException as exc:
        print(f"  error: {exc}", file=sys.stderr)
        return None
    if r.status_code != 200:
        print(f"  status {r.status_code}: {url}", file=sys.stderr)
        return None
    ctype = r.headers.get("Content-Type", "").lower()
    if "html" not in ctype:
        return None
    return normalize_url(r.url), r.text


def crawl(start_url: str, max_depth: int, max_pages: int, delay: float) -> dict[str, dict]:
    base_netloc = urlparse(start_url).netloc
    queue: deque[tuple[str, int]] = deque([(normalize_url(start_url), 0)])
    seen: set[str] = set()
    results: dict[str, dict] = {}
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "text/html"})

    while queue and len(results) < max_pages:
        url, depth = queue.popleft()
        if url in seen:
            continue
        seen.add(url)
        if not is_crawlable(url, base_netloc):
            continue

        print(f"[d{depth} {len(results) + 1}/{max_pages}] {url}", file=sys.stderr)
        fetched = fetch(session, url)
        if not fetched:
            time.sleep(delay)
            continue
        final_url, html = fetched
        # if redirected, dedupe by final URL too
        if final_url in results:
            continue
        results[final_url] = {"html": html, "depth": depth, "requested_url": url}

        if depth < max_depth:
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.find_all("a", href=True):
                target = normalize_url(urljoin(final_url, a["href"]))
                if not is_crawlable(target, base_netloc):
                    continue
                if target not in seen:
                    queue.append((target, depth + 1))
        time.sleep(delay)
    return results


def build_title_map(pages: dict[str, dict], site_name_hint: str | None) -> dict[str, str]:
    titles: dict[str, str] = {}
    used: dict[str, int] = {}
    for url, data in pages.items():
        soup = BeautifulSoup(data["html"], "html.parser")
        t = extract_title(soup, url, site_name_hint)
        # dedupe identical titles by appending the URL slug
        key = t
        if key in used:
            used[key] += 1
            slug = urlparse(url).path.strip("/").split("/")[-1] or f"page-{used[key]}"
            t = f"{t} ({slug})"
        used[key] = used.get(key, 0) + 1
        titles[url] = t
    return titles


def html_to_markdown(html: str, page_url: str, url_to_title: dict[str, str]) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "iframe", "svg", "form"]):
        tag.decompose()

    # Pick the most content-bearing region.
    container = (
        soup.find("main")
        or soup.find("article")
        or soup.find(attrs={"id": re.compile(r"main|content", re.I)})
        or soup.body
        or soup
    )

    base_netloc = urlparse(page_url).netloc

    # Replace internal anchor tags with sentinel-wrapped wikilink markers.
    # Use the same is_crawlable filter so uncrawled-but-eligible URLs become
    # dangling references in the graph, while filter/cart/product URLs are dropped.
    for a in container.find_all("a", href=True):
        target = normalize_url(urljoin(page_url, a["href"]))
        if target == page_url:
            continue
        if not is_crawlable(target, base_netloc):
            continue
        if target in url_to_title:
            title = url_to_title[target]
        else:
            title = slug_to_title(urlparse(target).path)
            if not title:
                continue
        text = a.get_text(" ", strip=True) or title
        sentinel = f"{WIKILINK_OPEN}{title}{WIKILINK_SEP}{text}{WIKILINK_CLOSE}"
        a.replace_with(sentinel)

    md = markdownify(str(container), heading_style="ATX", bullets="-").strip()

    def restore(match: re.Match[str]) -> str:
        title = match.group(1).strip()
        text = match.group(2).strip()
        if not title:
            return ""
        if title == text or not text:
            return f"[[{title}]]"
        return f"[[{title}|{text}]]"

    pattern = re.compile(
        re.escape(WIKILINK_OPEN) + r"(.*?)" + re.escape(WIKILINK_SEP) + r"(.*?)" + re.escape(WIKILINK_CLOSE),
        re.DOTALL,
    )
    md = pattern.sub(restore, md)

    # Tidy whitespace.
    md = re.sub(r"\n{3,}", "\n\n", md)
    md = re.sub(r"[ \t]+\n", "\n", md)
    return md.strip()


def write_corpus(
    pages: dict[str, dict],
    titles: dict[str, str],
    out_dir: Path,
) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    used_filenames: set[str] = set()
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for url, data in pages.items():
        title = titles[url]
        body_md = html_to_markdown(data["html"], url, titles)
        stem = filename_for_title(title)
        filename = f"{stem}.md"
        i = 2
        while filename in used_filenames:
            filename = f"{stem} ({i}).md"
            i += 1
        used_filenames.add(filename)

        frontmatter = (
            "---\n"
            "type: ingested-page\n"
            f"title: {title}\n"
            f"source_url: {url}\n"
            f"fetched_at: {fetched_at}\n"
            "tags: [ingested, audit-corpus]\n"
            "---\n\n"
            f"# {title}\n\n"
        )
        (out_dir / filename).write_text(frontmatter + body_md + "\n", encoding="utf-8")
        count += 1
    return count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--start", required=True, help="Start URL (e.g. https://example.com/)")
    parser.add_argument("--output", required=True, help="Output directory for the markdown corpus")
    parser.add_argument("--max-depth", type=int, default=2)
    parser.add_argument("--max-pages", type=int, default=80)
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between requests")
    parser.add_argument("--site-name", help="Site name to strip from titles like 'Page | Site Name'")
    args = parser.parse_args(argv)

    pages = crawl(args.start, args.max_depth, args.max_pages, args.delay)
    if not pages:
        print("no pages crawled", file=sys.stderr)
        return 1

    titles = build_title_map(pages, args.site_name)
    out_dir = Path(args.output).expanduser().resolve()
    count = write_corpus(pages, titles, out_dir)
    print(f"corpus -> {out_dir} ({count} pages)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
