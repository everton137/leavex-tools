#!/usr/bin/env python3
"""
get-eu-mp.py

Scrape the European Parliament MEP list and extract, for each MEP:
- Email
- X/Twitter URL + handle
- Political group (party at EU level)
- Country (and raw "country + national party" line)

Output: meps.csv (semicolon-separated by default).

Requirements:
    pip install requests beautifulsoup4
"""

import csv
import re
import time
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.europarl.europa.eu"
FULL_LIST_URL = f"{BASE_URL}/meps/en/full-list/all"

# Be polite to the EP website – adjust if needed
REQUEST_DELAY_SECONDS = 0.2
TIMEOUT = 15


@dataclass
class MEP:
    mep_id: str
    name: str
    profile_url: str
    email: Optional[str]
    x_url: Optional[str]
    x_handle: Optional[str]
    political_group: Optional[str]
    country: Optional[str]
    national_party: Optional[str]
    country_and_national_party: Optional[str]


def fetch(url: str) -> Optional[str]:
    """Fetch a URL and return its text, with basic error handling."""
    headers = {
        "User-Agent": "LeaveXContactScraper/1.0 (+https://leavex.eu)"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        print(f"[ERROR] Failed to fetch {url}: {e}")
        return None


def get_all_mep_ids_and_urls() -> Dict[str, str]:
    """
    Scrape the full list page and return a dict:
        {mep_id: profile_url}
    """
    print(f"[INFO] Fetching full list: {FULL_LIST_URL}")
    html = fetch(FULL_LIST_URL)
    if html is None:
        raise SystemExit("Could not fetch full list page")

    soup = BeautifulSoup(html, "html.parser")

    meps: Dict[str, str] = {}

    # Strategy:
    # - find all <a> tags whose href contains '/meps/en/'
    # - extract the numeric ID after '/meps/en/'
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/meps/en/" not in href:
            continue

        # Example hrefs:
        #   /meps/en/256810
        #   /meps/en/256810/MIKA_AALTOLA/home
        m = re.search(r"/meps/en/(\d+)", href)
        if not m:
            continue

        mep_id = m.group(1)

        # Normalize to a canonical profile URL (without name/home; the site redirects)
        profile_url = urljoin(BASE_URL, f"/meps/en/{mep_id}")
        meps[mep_id] = profile_url

    print(f"[INFO] Found {len(meps)} unique MEP IDs")
    return meps


def extract_x_handle_from_url(x_url: str) -> Optional[str]:
    """
    Extract X/Twitter handle from URL like:
        https://x.com/MikaAaltola
    Returns e.g. 'MikaAaltola'
    """
    if not x_url:
        return None
    try:
        path = urlparse(x_url).path  # e.g. '/MikaAaltola'
        if not path:
            return None
        handle = path.strip("/").split("/")[0]
        return handle or None
    except Exception:
        return None


def parse_mep_profile(mep_id: str, url: str) -> Optional[MEP]:
    """Parse a single MEP profile page and extract relevant fields."""
    print(f"[INFO] Fetching MEP {mep_id}: {url}")
    html = fetch(url)
    if html is None:
        return None

    soup = BeautifulSoup(html, "html.parser")

    # Name: top of the page, usually as plain text or an <h1>.
    # We'll try several approaches to be robust.
    name = ""
    # Try an <h1> with the name
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        name = h1.get_text(strip=True)
    else:
        # Fallback: first strong text near top with typical structure
        # For your own debugging, you might want to print some text snippets here.
        # As a generic fallback, we search for the member name by looking at the
        # first big text chunk above the political group.
        text_candidates = soup.find_all(string=True)
        for t in text_candidates:
            s = t.strip()
            if len(s.split()) >= 2 and s.isupper() is False and "Group of the" in soup.get_text():
                name = s
                break

    if not name:
        # Last resort – use the ID itself as name placeholder
        name = f"MEP-{mep_id}"

    # Political group (party at EU level)
    # HTML example:
    #   <h3 class="erpl_title-h3 mt-1 sln-political-group-name">
    #       Group of the European People's Party (Christian Democrats)
    #   </h3>
    political_group_el = soup.select_one("h3.erpl_title-h3.mt-1.sln-political-group-name")
    political_group = political_group_el.get_text(strip=True) if political_group_el else None

    # Country + national party
    country_block_el = soup.select_one("div.erpl_title-h3.mt-1.mb-1")
    raw_country_block = country_block_el.get_text(" ", strip=True) if country_block_el else None

    country = None
    national_party = None

    if raw_country_block:
        # Normalize whitespace
        cleaned = " ".join(raw_country_block.split())
        # Expected format: "Finland - Kansallinen Kokoomus (Finland)"
        if " - " in cleaned:
            country, nat_party = cleaned.split(" - ", 1)
            country = country.strip()
            national_party = nat_party.strip()
        else:
            country = cleaned
            national_party = None


    # E-mail
    # <a class="link_email mr-2" href="mailto:mika.aaltola@europarl.europa.eu" ...>
    email_el = soup.find("a", class_="link_email")
    email = None
    if email_el and email_el.has_attr("href"):
        href = email_el["href"]
        if href.startswith("mailto:"):
            email = href[len("mailto:"):].strip()

    # X / Twitter
    # <a class="link_twitt mr-2" href="https://x.com/MikaAaltola" ...>
    x_el = soup.find("a", class_="link_twitt")
    x_url = None
    x_handle = None
    if x_el and x_el.has_attr("href"):
        x_url = x_el["href"]
        x_handle = extract_x_handle_from_url(x_url)

    return MEP(
        mep_id=mep_id,
        name=name,
        profile_url=url,
        email=email,
        x_url=x_url,
        x_handle=x_handle,
        political_group=political_group,
        country=country,
        national_party=national_party,
        country_and_national_party=raw_country_block,
    )


def scrape_all_meps(only_with_x: bool = False) -> List[MEP]:
    """Scrape all MEPs, optionally filtering to those who have an X/Twitter account."""
    meps_meta = get_all_mep_ids_and_urls()
    results: List[MEP] = []

    for i, (mep_id, url) in enumerate(meps_meta.items(), start=1):
        mep = parse_mep_profile(mep_id, url)
        if mep is None:
            continue

        if only_with_x and not mep.x_url:
            # Skip MEPs without X/Twitter
            print(f"[DEBUG] Skipping {mep.mep_id} (no X)")
        else:
            results.append(mep)

        # Be nice to the server
        if i % 10 == 0:
            print(f"[INFO] Processed {i} MEPs...")
        time.sleep(REQUEST_DELAY_SECONDS)

    print(f"[INFO] Scraping finished. Collected {len(results)} MEPs.")
    return results


def write_csv(meps: List[MEP], filename: str = "meps.csv") -> None:
    """Write list of MEPs to a CSV file (semicolon-separated)."""
    if not meps:
        print("[WARN] No MEP data to write.")
        return

    fieldnames = list(asdict(meps[0]).keys())

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        for mep in meps:
            writer.writerow(asdict(mep))

    print(f"[INFO] Wrote {len(meps)} rows to {filename}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Scrape EU MEPs' contact info (email, X/Twitter, party, country)."
    )
    parser.add_argument(
        "--only-with-x",
        action="store_true",
        help="Only include MEPs that have an X/Twitter account.",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="meps.csv",
        help="Output CSV filename (default: meps.csv).",
    )
    args = parser.parse_args()

    meps = scrape_all_meps(only_with_x=args.only_with_x)
    write_csv(meps, filename=args.output)


if __name__ == "__main__":
    main()
