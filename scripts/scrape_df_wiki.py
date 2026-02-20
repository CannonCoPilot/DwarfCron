#!/usr/bin/env python3
"""Scrape Dwarf Fortress Wiki articles to markdown files for RAG indexing.

Uses the MediaWiki API to enumerate and download articles. Converts wikitext
to simplified markdown. Targets key categories: modding, raws, gameplay
mechanics, structures, creatures, materials.

Usage:
    python scrape_df_wiki.py [--output-dir DIR] [--max-pages N] [--category CAT]
"""

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.request
import urllib.parse
from pathlib import Path

API_URL = "https://dwarffortresswiki.org/api.php"
OUTPUT_DIR = Path("/Users/nathanielcannon/Claude/Projects/DwarfCron/data/wiki")
REQUEST_DELAY = 0.5  # seconds between API calls (be polite)


def api_query(params: dict) -> dict:
    """Make a MediaWiki API request and return JSON response."""
    params["format"] = "json"
    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "DwarfCron/1.0 (Dwarf Fortress research project; contact@example.com)"
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_all_pages(namespace: int = 0, limit: int = 5000) -> list[str]:
    """Enumerate all page titles in a namespace using allpages API."""
    titles = []
    params = {
        "action": "query",
        "list": "allpages",
        "apnamespace": namespace,
        "aplimit": "500",
    }
    while len(titles) < limit:
        data = api_query(params)
        pages = data.get("query", {}).get("allpages", [])
        titles.extend(p["title"] for p in pages)
        cont = data.get("continue", {})
        if "apcontinue" not in cont:
            break
        params["apcontinue"] = cont["apcontinue"]
        time.sleep(REQUEST_DELAY)
    return titles[:limit]


def get_category_members(category: str, limit: int = 500) -> list[str]:
    """Get all pages in a category."""
    titles = []
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": f"Category:{category}",
        "cmlimit": "500",
        "cmtype": "page",
    }
    while len(titles) < limit:
        data = api_query(params)
        members = data.get("query", {}).get("categorymembers", [])
        titles.extend(m["title"] for m in members)
        cont = data.get("continue", {})
        if "cmcontinue" not in cont:
            break
        params["cmcontinue"] = cont["cmcontinue"]
        time.sleep(REQUEST_DELAY)
    return titles[:limit]


def get_page_content(title: str) -> str | None:
    """Fetch raw wikitext for a page."""
    params = {
        "action": "query",
        "titles": title,
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
    }
    data = api_query(params)
    pages = data.get("query", {}).get("pages", {})
    for page_id, page_data in pages.items():
        if page_id == "-1":
            return None
        revisions = page_data.get("revisions", [])
        if revisions:
            slots = revisions[0].get("slots", {})
            main_slot = slots.get("main", {})
            return main_slot.get("*", "")
    return None


def wikitext_to_markdown(wikitext: str, title: str) -> str:
    """Convert MediaWiki wikitext to simplified markdown.

    This is a pragmatic conversion — not perfect, but good enough for
    RAG chunking where we care about content, not pixel-perfect rendering.
    """
    text = wikitext

    # Remove noinclude/includeonly tags
    text = re.sub(r"<noinclude>.*?</noinclude>", "", text, flags=re.DOTALL)
    text = re.sub(r"<includeonly>.*?</includeonly>", "", text, flags=re.DOTALL)

    # Convert headings: == H2 == → ## H2
    text = re.sub(r"^======\s*(.+?)\s*======", r"###### \1", text, flags=re.MULTILINE)
    text = re.sub(r"^=====\s*(.+?)\s*=====", r"##### \1", text, flags=re.MULTILINE)
    text = re.sub(r"^====\s*(.+?)\s*====", r"#### \1", text, flags=re.MULTILINE)
    text = re.sub(r"^===\s*(.+?)\s*===", r"### \1", text, flags=re.MULTILINE)
    text = re.sub(r"^==\s*(.+?)\s*==", r"## \1", text, flags=re.MULTILINE)
    text = re.sub(r"^=\s*(.+?)\s*=", r"# \1", text, flags=re.MULTILINE)

    # Convert bold/italic: '''bold''' → **bold**, ''italic'' → *italic*
    text = re.sub(r"'''(.+?)'''", r"**\1**", text)
    text = re.sub(r"''(.+?)''", r"*\1*", text)

    # Convert internal links: [[Page|display]] → display, [[Page]] → Page
    text = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", text)

    # Convert external links: [url text] → text
    text = re.sub(r"\[https?://\S+\s+([^\]]+)\]", r"\1", text)
    text = re.sub(r"\[https?://\S+\]", "", text)

    # Convert bullet lists: * item → - item
    text = re.sub(r"^\*\*\*\*\s*", "        - ", text, flags=re.MULTILINE)
    text = re.sub(r"^\*\*\*\s*", "      - ", text, flags=re.MULTILINE)
    text = re.sub(r"^\*\*\s*", "    - ", text, flags=re.MULTILINE)
    text = re.sub(r"^\*\s*", "- ", text, flags=re.MULTILINE)

    # Convert numbered lists: # item → 1. item
    text = re.sub(r"^#+\s*", "1. ", text, flags=re.MULTILINE)

    # Strip templates ({{...}}) — these are wiki-specific and not useful for RAG
    # Handle nested templates by iterating
    for _ in range(5):
        new_text = re.sub(r"\{\{[^{}]*\}\}", "", text)
        if new_text == text:
            break
        text = new_text

    # Strip HTML tags but keep content
    text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.DOTALL)
    text = re.sub(r"<ref[^/]*/?>", "", text)
    text = re.sub(r"<gallery[^>]*>.*?</gallery>", "", text, flags=re.DOTALL)
    text = re.sub(r"</?(?:div|span|center|small|big|sup|sub|br\s*/?)>", "", text)
    text = re.sub(r"<code>(.*?)</code>", r"`\1`", text, flags=re.DOTALL)
    text = re.sub(r"<pre>(.*?)</pre>", r"```\n\1\n```", text, flags=re.DOTALL)

    # Convert tables (simplified — just extract cell content)
    text = re.sub(r"^\{\|.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\|\}.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\|-.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\!\s*", "**", text, flags=re.MULTILINE)
    text = re.sub(r"^\|\s*", "| ", text, flags=re.MULTILINE)

    # Clean up categories and interwiki links
    text = re.sub(r"\[\[Category:[^\]]+\]\]", "", text)
    text = re.sub(r"\[\[[a-z]{2}:[^\]]+\]\]", "", text)

    # Clean up excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Add title as H1
    result = f"# {title}\n\n{text.strip()}\n"
    return result


def sanitize_filename(title: str) -> str:
    """Convert a wiki page title to a safe filename."""
    name = title.replace("/", "_").replace(":", "_").replace(" ", "_")
    name = re.sub(r"[^a-zA-Z0-9_.-]", "", name)
    return name[:200]  # cap length


# Priority categories and pages for DF modding and development
PRIORITY_CATEGORIES = [
    "Modding",
    "DF2014:Modding",
    "Raw files",
    "Creatures",
    "Materials",
    "Buildings",
    "Reactions",
    "Items",
    "Entities",
    "Graphics",
    "Tilesets",
    "World generation",
    "Adventure mode",
    "Fortress mode",
    "Legends",
]

# Individual high-value pages to always include
PRIORITY_PAGES = [
    "DF2014:Raw file",
    "DF2014:Token",
    "DF2014:Creature token",
    "DF2014:Entity token",
    "DF2014:Item token",
    "DF2014:Inorganic token",
    "DF2014:Material token",
    "DF2014:Material definition token",
    "DF2014:Building token",
    "DF2014:Reaction token",
    "DF2014:Plant token",
    "DF2014:Body token",
    "DF2014:Body detail plan token",
    "DF2014:Tissue token",
    "DF2014:Interaction token",
    "DF2014:Graphics token",
    "DF2014:World generation",
    "DF2014:Legends",
    "DF2014:Adventure mode",
    "DF2014:Fortress mode",
    "DF2014:Embark",
    "Modding",
    "Modding guide",
    "Raw file",
    "Token",
    "Creature",
    "Entity",
    "Civilization",
    "Dwarf",
    "Personality trait",
    "Attribute",
    "Skill",
    "Labor",
    "Material",
    "Metal",
    "Stone",
    "Gem",
    "Wood",
    "Item",
    "Artifact",
    "Building",
    "Workshop",
    "Reaction",
    "Plant",
    "Language",
    "Name",
    "Historical figure",
    "History",
    "Site",
    "Region",
    "World",
    "Legends mode",
    "XML dump",
    "DF2014:XML dump",
    "Utility:DFHack",
    "DFHack",
    "Character creation",
    "Combat",
    "Mood",
    "Strange mood",
    "Stress",
    "Thought",
    "Need",
    "Value",
    "Belief",
    "Personality trait",
    "Relationship",
    "Family",
    "Noble",
    "Military",
    "Squad",
    "Caravan",
    "Siege",
    "Megabeast",
    "Titan",
    "Forgotten beast",
    "Deity",
    "Religion",
]


def main():
    parser = argparse.ArgumentParser(description="Scrape DF Wiki to markdown")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--max-pages", type=int, default=2000,
                        help="Maximum total pages to scrape")
    parser.add_argument("--categories-only", action="store_true",
                        help="Only scrape priority categories + pages, skip allpages")
    parser.add_argument("--all-pages", action="store_true",
                        help="Scrape ALL wiki pages (very large)")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Track what we've already downloaded (by content hash)
    manifest_path = args.output_dir / "_manifest.json"
    manifest = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())

    # Collect target pages
    target_titles = set()

    # 1. Always include priority pages
    target_titles.update(PRIORITY_PAGES)
    print(f"[+] {len(PRIORITY_PAGES)} priority pages queued")

    # 2. Enumerate priority categories
    for cat in PRIORITY_CATEGORIES:
        try:
            members = get_category_members(cat)
            target_titles.update(members)
            print(f"[+] Category '{cat}': {len(members)} pages")
            time.sleep(REQUEST_DELAY)
        except Exception as e:
            print(f"[!] Category '{cat}' failed: {e}")

    # 3. Optionally enumerate all pages
    if args.all_pages and len(target_titles) < args.max_pages:
        print("[*] Enumerating all wiki pages...")
        remaining = args.max_pages - len(target_titles)
        all_titles = get_all_pages(limit=remaining)
        target_titles.update(all_titles)

    target_list = sorted(target_titles)[:args.max_pages]
    print(f"\n[*] Total pages to scrape: {len(target_list)}")

    # Download and convert pages
    downloaded = 0
    skipped = 0
    failed = 0

    for i, title in enumerate(target_list):
        filename = sanitize_filename(title) + ".md"
        filepath = args.output_dir / filename

        # Skip if already in manifest with same title
        if title in manifest and filepath.exists():
            skipped += 1
            continue

        try:
            content = get_page_content(title)
            if content is None:
                print(f"  [{i+1}/{len(target_list)}] SKIP (not found): {title}")
                failed += 1
                continue

            # Skip redirects
            if content.strip().upper().startswith("#REDIRECT"):
                skipped += 1
                continue

            # Skip very short pages (stubs)
            if len(content) < 100:
                skipped += 1
                continue

            markdown = wikitext_to_markdown(content, title)
            filepath.write_text(markdown, encoding="utf-8")

            content_hash = hashlib.md5(content.encode()).hexdigest()
            manifest[title] = {
                "file": filename,
                "hash": content_hash,
                "size": len(markdown),
            }

            downloaded += 1
            if downloaded % 25 == 0:
                print(f"  [{i+1}/{len(target_list)}] Downloaded {downloaded} pages...")
                # Save manifest periodically
                manifest_path.write_text(json.dumps(manifest, indent=2))

            time.sleep(REQUEST_DELAY)

        except Exception as e:
            print(f"  [{i+1}/{len(target_list)}] FAIL: {title} — {e}")
            failed += 1
            time.sleep(REQUEST_DELAY * 2)

    # Final manifest save
    manifest_path.write_text(json.dumps(manifest, indent=2))

    print(f"\n[*] Done: {downloaded} downloaded, {skipped} skipped, {failed} failed")
    print(f"[*] Output: {args.output_dir}")
    print(f"[*] Total files: {len(list(args.output_dir.glob('*.md')))}")


if __name__ == "__main__":
    main()
