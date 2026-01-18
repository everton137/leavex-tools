#!/usr/bin/env python3
"""
apply_meps_overrides.py

Merge manual overrides from meps_overrides.json into meps_all.json.

- Base file: meps_all.json   (list of MEP objects)
- Overrides: meps_overrides.json (object keyed by MEP id)
- Output:    meps_all_with_overrides.json

Behavior:
- For each override entry:
  - If the id exists in the base list, update that object with all override keys.
  - If the id does NOT exist in the base list, create a new stub object and append it.
"""

import json
from pathlib import Path
from urllib.parse import urlparse

BASE_FILE = Path("data/meps_all.json")
OVERRIDES_FILE = Path("data/meps_overrides.json")
OUTPUT_FILE = Path("data/meps_all_with_overrides.json")


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main():
    if not BASE_FILE.exists():
        raise SystemExit(f"Base file not found: {BASE_FILE}")
    if not OVERRIDES_FILE.exists():
        raise SystemExit(f"Overrides file not found: {OVERRIDES_FILE}")

    base_data = load_json(BASE_FILE)
    overrides = load_json(OVERRIDES_FILE)

    if not isinstance(base_data, list):
        raise SystemExit("meps_all.json must be a JSON array (list of objects).")
    if not isinstance(overrides, dict):
        raise SystemExit("meps_overrides.json must be a JSON object keyed by MEP id.")

    # Index base data by id for fast lookup
    index = {}
    for obj in base_data:
        obj_id = obj.get("id")
        if obj_id:
            if obj_id in index:
                print(f"[WARN] Duplicate id in base data: {obj_id}")
            index[obj_id] = obj

    def _extract_handle(v):
        if v is None:
            return None
        if not isinstance(v, str):
            return None
        v = v.strip()
        if not v:
            return None

        # URL case
        if "://" in v:
            try:
                p = urlparse(v)
            except Exception:
                return None
            host = (p.netloc or "").lower()
            if host.endswith("x.com") or host.endswith("twitter.com"):
                path = (p.path or "").strip("/")
                if not path:
                    return None
                return path.split("/")[0] or None
            return None

        # @handle or handle
        return v.lstrip("@").strip() or None


    def normalize_x_fields(obj: dict):
        if not isinstance(obj, dict):
            return

        uses = obj.get("usesX", None)
        xh = obj.get("xHandle", None)

        handle = _extract_handle(xh)

        # If usesX explicitly false: force xHandle = null
        if uses is False:
            obj["xHandle"] = None
            return

        # If we have a handle, normalize it and (optionally) set usesX
        if handle:
            obj["xHandle"] = f"@{handle}"
            if uses is None:
                obj["usesX"] = True
            return

        # No handle present (null/empty/unparseable)
        if uses is None:
            obj["usesX"] = False
        # If usesX true but xHandle missing, keep as-is (or choose to force false)
        if obj.get("usesX") is False:
            obj["xHandle"] = None

    # After applying overrides:
    for obj in base_data:
        normalize_x_fields(obj)

    # Apply overrides
    for mep_id, override_data in overrides.items():
        if not isinstance(override_data, dict):
            print(f"[WARN] Override for {mep_id} is not an object, skipping.")
            continue

        if mep_id in index:
            base_obj = index[mep_id]
            print(f"[INFO] Applying override to existing MEP: {mep_id}")
            # Shallow merge: override / add keys onto the base object
            for key, value in override_data.items():
                base_obj[key] = value
        else:
            print(f"[WARN] Override id {mep_id} not found in base data; creating stub entry.")
            # Create a new minimal object and append it
            new_obj = {"id": mep_id}
            new_obj.update(override_data)
            base_data.append(new_obj)
            index[mep_id] = new_obj

    # Write merged output
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(base_data, f, ensure_ascii=False, indent=2)

    print(f"[INFO] Wrote merged data with overrides to {OUTPUT_FILE}")
    print(f"[INFO] Total records: {len(base_data)}")


if __name__ == "__main__":
    main()
