import json
from pathlib import Path

INPUT_PATH = Path("data/mps_se.json")
OUTPUT_PATH = Path("data/mps_se_with_party.json")

PARTY_MAP = {
    "S":  "Socialdemokraterna",
    "M":  "Moderaterna",
    "SD": "Sverigedemokraterna",
    "C":  "Centerpartiet",
    "V":  "Vänsterpartiet",
    "KD": "Kristdemokraterna",
    "L":  "Liberalerna",
    "MP": "Miljöpartiet de gröna",
    "-":  "Partilös (obunden)",
}

def main():
    data = json.loads(INPUT_PATH.read_text(encoding="utf-8"))

    unknown_codes = set()

    for person in data:
        code = person.get("party")
        if code in PARTY_MAP:
            person["party"] = PARTY_MAP[code]
        else:
            unknown_codes.add(code)

    OUTPUT_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    if unknown_codes:
        print("Unknown party codes found:", sorted(unknown_codes))
    print("Output written to:", OUTPUT_PATH)

if __name__ == "__main__":
    main()
