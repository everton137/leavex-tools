#!/usr/bin/env python3
"""
Bundestag MPs → X handle scraper

Strategy:
- Use official XML endpoint to get the full MDB list:
  https://www.bundestag.de/xml/v2/mdb/index.xml
- For each MDB, fetch the public biography HTML page and extract:
  "Profile im Internet" -> X link (twitter.com / x.com)
- Output JSON records similar to your target structure.

Deps:
  pip install requests beautifulsoup4 lxml
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Iterable, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from lxml import etree


INDEX_XML_URL = "https://www.bundestag.de/xml/v2/mdb/index.xml"
BIO_HTML_BASE = "https://www.bundestag.de/abgeordnete/biografien"


SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": "Mozilla/5.0 (compatible; BundestagXScraper/1.0; +https://example.org)",
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    }
)

HANDLE_RE = re.compile(r"^@[A-Za-z0-9_]{1,15}$")


@dataclass(frozen=True)
class MpRecord:
    id: str
    name: str
    country: str = "Germany"
    countryCode: str = "DE"
    level: str = "national"
    institution: str = "Bundestag"
    role: str = "MP"
    party: Optional[str] = None
    email: Optional[str] = None
    usesX: bool = False
    xHandle: Optional[str] = None


def fetch_text(url: str, timeout: int = 30) -> str:
    r = SESSION.get(url, timeout=timeout)
    r.raise_for_status()
    return r.text


def extract_candidate_mdb_ids(index_xml: str) -> list[int]:
    """
    Robustly extract numeric MDB IDs from the index.xml.

    Because we don't rely on exact tag names, we:
    - parse XML
    - collect all integers found in text nodes that look like IDs
    - de-duplicate
    - apply a sanity filter (typical Bundestag IDs are >= 1000, but we keep it loose)
    """
    parser = etree.XMLParser(recover=True, huge_tree=True)
    root = etree.fromstring(index_xml.encode("utf-8"), parser=parser)

    ids: set[int] = set()

    # Gather numbers from all text nodes
    for el in root.iter():
        if el.text:
            txt = el.text.strip()
            if txt.isdigit():
                n = int(txt)
                # loose sanity filter
                if n >= 1:
                    ids.add(n)

        # Also check attributes for digit strings
        for v in el.attrib.values():
            v = v.strip()
            if v.isdigit():
                ids.add(int(v))

    # Heuristic: IDs list can include unrelated numeric fields.
    # Keep the "most plausible" ones by focusing on values that appear many times near MDB nodes.
    # If the index is clean, this still returns the correct set.
    # As a fallback, keep the largest ~3000 numbers (covers all modern IDs).
    ids_list = sorted(ids)
    if len(ids_list) > 3000:
        ids_list = ids_list[-3000:]

    return ids_list


def guess_bio_url_from_html_id(html_id: int) -> str:
    """
    If you already have the public biography numeric ID (like ...-1043330),
    the URL is:
      https://www.bundestag.de/abgeordnete/biografien/<LETTER>/<slug>-<id>
    But from MDB_ID (XML) you usually *don't* have that <slug>-<id> directly.

    So we do a different approach:
    - Use the XML biography endpoint instead to obtain the 'internet' biography page URL
      if present; otherwise you can build a mapping once you inspect the XML.

    This function is kept only for your reference.
    """
    raise NotImplementedError


def extract_x_handle_from_bio_html(bio_html: str) -> Optional[str]:
    soup = BeautifulSoup(bio_html, "html.parser")

    # Find the heading "Profile im Internet"
    h = soup.find(
        lambda tag: tag.name in {"h2", "h3"}
        and tag.get_text(strip=True) == "Profile im Internet"
    )
    if not h:
        return None

    # Next list after the heading contains the links
    ul = h.find_next("ul")
    if not ul:
        return None

    links = ul.find_all("a", href=True)
    for a in links:
        href = a["href"].strip()
        label = a.get_text(" ", strip=True)

        if label == "X" or "twitter.com" in href or "x.com" in href:
            # Extract handle from URL path
            try:
                p = urlparse(href)
                # Common cases: https://twitter.com/<handle> or https://x.com/<handle>
                parts = [x for x in p.path.split("/") if x]
                if not parts:
                    return None
                candidate = parts[0]
                # Sometimes it's like /intent/user?screen_name=...
                if candidate.lower() == "intent" and "screen_name=" in (p.query or ""):
                    m = re.search(r"screen_name=([A-Za-z0-9_]{1,15})", p.query)
                    if m:
                        return f"@{m.group(1)}"
                    return None

                # Strip leading @ if present
                candidate = candidate.lstrip("@")
                handle = f"@{candidate}"

                return (
                    handle if HANDLE_RE.match(handle) else handle
                )  # keep even if it violates old rules
            except Exception:
                return None

    return None


def extract_name_party_from_bio_html(
    bio_html: str,
) -> tuple[Optional[str], Optional[str]]:
    soup = BeautifulSoup(bio_html, "html.parser")

    # Name is typically the main H1
    h1 = soup.find("h1")
    name = h1.get_text(" ", strip=True) if h1 else None

    # There's often a line under the name like: "<profession> SPD" or similar
    # We’ll take the first strong hint: a short all-caps token at the end of the subtitle area.
    party = None
    # Try to find a text node near h1:
    if h1:
        # Look at next few text chunks
        nxt = h1.find_next(string=True)
        # We'll instead scan a small region of visible text near the top
        top_text = soup.get_text("\n", strip=True).splitlines()[:30]
        blob = " ".join(top_text)
        # Common party labels/Fraktionen: CDU/CSU, SPD, AfD, FDP, Die Linke, Bündnis 90/Die Grünen
        # Keep it simple:
        m = re.search(
            r"\b(CDU/CSU|SPD|AfD|FDP|Die Linke|Bündnis 90/Die Grünen|fraktionslos)\b",
            blob,
        )
        if m:
            party = (
                m.group(1)
                .lower()
                .replace(" ", "_")
                .replace("ü", "ue")
                .replace("ö", "oe")
                .replace("ä", "ae")
            )

    return name, party


def build_records_from_bio_pages(
    bio_urls: Iterable[str], sleep_s: float = 0.3
) -> list[MpRecord]:
    records: list[MpRecord] = []
    for i, url in enumerate(bio_urls, start=1):
        html = fetch_text(url)
        name, party = extract_name_party_from_bio_html(html)
        x = extract_x_handle_from_bio_html(html)

        mp_id = f"mp_de_{i:03d}"
        records.append(
            MpRecord(
                id=mp_id,
                name=name or url,
                party=party,
                usesX=bool(x),
                xHandle=x,
                email=None,  # Bundestag uses contact forms; direct email often isn't exposed here
            )
        )

        time.sleep(sleep_s)
    return records


def main() -> None:
    # 1) Fetch index.xml
    index_xml = fetch_text(INDEX_XML_URL)

    # 2) Extract MDB IDs
    mdb_ids = extract_candidate_mdb_ids(index_xml)
    print(f"Found {len(mdb_ids)} candidate numeric IDs in index.xml")

    # 3) IMPORTANT: map MDB_ID -> biography HTML URL
    # The clean way is usually: fetch the biography XML for each MDB_ID and read the biography page URL from it.
    # Because XML structure can differ, we do a light heuristic:
    #   - Fetch biography XML for each ID
    #   - Look for an embedded URL containing "/abgeordnete/biografien/"
    bio_urls: list[str] = []
    for mdb_id in mdb_ids:
        bio_xml_url = f"https://www.bundestag.de/xml/v2/mdb/biografien/{mdb_id}.xml"
        try:
            bio_xml = fetch_text(bio_xml_url, timeout=20)
        except Exception:
            continue

        m = re.search(
            r"https?://www\.bundestag\.de/abgeordnete/biografien/[A-Z]/[^\s<\"]+",
            bio_xml,
        )
        if m:
            bio_urls.append(m.group(0))

    # De-duplicate while preserving order
    seen = set()
    bio_urls = [u for u in bio_urls if not (u in seen or seen.add(u))]

    print(f"Resolved {len(bio_urls)} biography HTML URLs via biography XML")

    # 4) Visit each bio page and extract X handle
    records = build_records_from_bio_pages(bio_urls)

    # 5) Write JSON
    out_path = "bundestag_mps.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump([r.__dict__ for r in records], f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(records)} records to {out_path}")


if __name__ == "__main__":
    main()
