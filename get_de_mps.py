#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path

import yaml


HANDLE_RE = re.compile(r"https?://(?:www\.)?(?:twitter\.com|x\.com)/@?([^/?#]+)", re.I)

# If your project uses different party slugs, adjust here.
PARTY_MAP = {
    "SPD": "spd",
    "CDU": "cdu",
    "CSU": "csu",
    "FDP": "fdp",
    "AfD": "afd",
    "GRÜNE": "gruene",
    "GRUENE": "gruene",
    "DIE GRÜNEN": "gruene",
    "Die Grünen": "gruene",
    "BÜNDNIS 90/DIE GRÜNEN": "gruene",
    "DIE LINKE": "linke",
    "Die Linke": "linke",
    "BSW": "bsw",
    "fraktionslos": "fraktionslos",
}


def normalize_name(name: str) -> str:
    """
    Convert 'Last, First Middle' -> 'First Middle Last'.
    If there's no comma, return the name as-is (trimmed).
    """
    name = (name or "").strip()
    if "," in name:
        last, first = [p.strip() for p in name.split(",", 1)]
        if first and last:
            return f"{first} {last}".strip()
    return name


def party_slug(party: str) -> str | None:
    if not party:
        return None
    p = party.strip()
    return PARTY_MAP.get(p, p.lower().strip())


def extract_x_handle(url: str | None) -> str | None:
    if not url:
        return None
    m = HANDLE_RE.match(url.strip())
    if not m:
        return None
    handle = m.group(1)
    # ignore special paths that aren't usernames
    if handle.lower() in {"intent", "share", "home"}:
        return None
    return f"@{handle}"


def transform(input_path: Path) -> list[dict]:
    raw = yaml.safe_load(input_path.read_text(encoding="utf-8"))
    mps = raw.get("abgeordnete", [])

    out = []
    for i, mp in enumerate(mps, start=1):
        name = normalize_name(mp.get("name"))
        party = party_slug(mp.get("partei"))

        socials = mp.get("socialmedia") or {}
        x_url = socials.get("twitter")
        x_handle = extract_x_handle(x_url)

        obj = {
            "id": f"mp_de_{i:03d}",
            "name": name,
            "country": "Germany",
            "countryCode": "DE",
            "level": "national",
            "institution": "Bundestag",
            "role": "MP",
            "party": party,
            "email": None,  # not present in this YAML
            "usesX": bool(x_handle),
            "xHandle": x_handle,
        }
        out.append(obj)

    return out


def main():
    ap = argparse.ArgumentParser(description="Transform bundestag.yaml into Leave X MP JSON format.")
    ap.add_argument("input", nargs="?", default="bundestag.yaml", help="Path to bundestag.yaml")
    ap.add_argument("-o", "--output", default="data/mps_de_from_bundestag.yaml.json", help="Output JSON path")
    args = ap.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = transform(input_path)
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    total = len(data)
    with_x = sum(1 for r in data if r["usesX"])
    print(f"Saved {total} MPs → {output_path}")
    print(f"MPs with X: {with_x} ({with_x/total*100:.1f}%)")


if __name__ == "__main__":
    main()
