#!/usr/bin/env python3
import csv
import json

INPUT_CSV = "data/meps_all.csv"
OUTPUT_JSON = "data/meps_all.json"

# Minimal country → ISO code mapping for EU countries
EU_COUNTRY_CODES = {
    "Austria": "AT",
    "Belgium": "BE",
    "Bulgaria": "BG",
    "Croatia": "HR",
    "Cyprus": "CY",
    "Czech Republic": "CZ",
    "Czechia": "CZ",
    "Denmark": "DK",
    "Estonia": "EE",
    "Finland": "FI",
    "France": "FR",
    "Germany": "DE",
    "Greece": "GR",
    "Hungary": "HU",
    "Ireland": "IE",
    "Italy": "IT",
    "Latvia": "LV",
    "Lithuania": "LT",
    "Luxembourg": "LU",
    "Malta": "MT",
    "Netherlands": "NL",
    "Poland": "PL",
    "Portugal": "PT",
    "Romania": "RO",
    "Slovakia": "SK",
    "Slovenia": "SI",
    "Spain": "ES",
    "Sweden": "SE"
}

EU_GROUP_MAP = {
    "Group of the European People's Party (Christian Democrats)": "EPP",
    "Group of the Progressive Alliance of Socialists and Democrats in the European Parliament": "S&D",
    "Renew Europe Group": "Renew",
    "Group of the Greens/European Free Alliance": "Greens/EFA",
    "European Conservatives and Reformists Group": "ECR",
    "Identity and Democracy Group": "ID",
    "The Left group in the European Parliament - GUE/NGL": "The Left",
    "Non-attached Members": "NI",
}

def map_eu_group_to_short(name: str | None) -> str | None:
    if not name:
        return None
    name = name.strip()
    return EU_GROUP_MAP.get(name, name)  # fallback to full text if unknown


def country_to_code(country: str):
    if not country:
        return None
    c = country.strip()
    code = EU_COUNTRY_CODES.get(c)
    if code is None:
        print(f"[WARN] No country code mapping for: {c!r}")
    return code


def normalize_name(name: str) -> str:
    """Remove 'Home' prefix and trim."""
    if not name:
        return ""
    name = name.strip()
    if name.startswith("Home"):
        name = name[len("Home"):].strip()
    return name


def normalize_x_handle(raw: str):
    if not raw:
        return None
    raw = raw.strip()
    if not raw:
        return None
    if raw.startswith("@"):
        return raw
    return "@" + raw


def main():
    data = []

    with open(INPUT_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            mep_id = row.get("mep_id", "").strip()
            name = normalize_name(row.get("name", ""))
            country = (row.get("country") or "").strip() or None
            country_code = country_to_code(country) if country else None

            x_url = (row.get("x_url") or "").strip()
            x_handle_raw = (row.get("x_handle") or "").strip()
            uses_x = bool(x_url)

            x_handle = normalize_x_handle(x_handle_raw) if uses_x else None

            email = (row.get("email") or "").strip() or None
            political_group = (row.get("political_group") or "").strip() or None
            eu_group_short = map_eu_group_to_short(political_group)

            # Build the JSON object for this MEP
            mep_obj = {
                "id": f"mep_{mep_id}" if mep_id else None,
                "name": name or None,
                "country": country,
                "countryCode": country_code,
                "level": "eu",
                "institution": "European Parliament",
                "role": "MEP",
                # you can switch to national_party if you prefer that
                "party": political_group,
                "euGroupFull": political_group,
                "email": email,
                "usesX": uses_x,
                "xHandle": x_handle,
            }

            data.append(mep_obj)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as out:
        json.dump(data, out, ensure_ascii=False, indent=2)

    print(f"[INFO] Wrote {len(data)} records to {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
