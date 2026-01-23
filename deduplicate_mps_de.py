import json
from pathlib import Path

INPUT = Path("data/mps_de.json")
OUTPUT = Path("data/mps_de_clean.json")

PARTY_MAP = {
    "Sozialdemokratische Partei Deutschlands": "spd",
    "Christlich Demokratische Union": "cdu",
    "Christlich-Soziale Union in Bayern": "csu",
    "Bündnis 90/Die Grünen": "gruene",
    "Die Grünen": "gruene",
    "Freie Demokratische Partei": "fdp",
    "Alternative für Deutschland": "afd",
    "Die Linke": "linke",
    "Partei des Demokratischen Sozialismus": "linke",
    "Arbeit & soziale Gerechtigkeit – Die Wahlalternative": "linke",
    "Bündnis Sahra Wagenknecht – Vernunft und Gerechtigkeit": "bsw",
}

with INPUT.open() as f:
    rows = json.load(f)

mps = {}

for r in rows:
    qid = r["qid"]

    if qid not in mps:
        # --- base object ---
        mps[qid] = {
            "id": f"mp_de_{qid}",
            "qid": qid,
            "name": r.get("name"),
            "country": "Germany",
            "countryCode": "DE",
            "level": "national",
            "institution": "Bundestag",
            "role": "MP",
            "party": None,
            "email": None,
            "usesX": False,
            "xHandle": None,
        }

    # --- party ---
    party_label = r.get("party")
    if party_label and not mps[qid]["party"]:
        mps[qid]["party"] = PARTY_MAP.get(party_label, party_label)

    # --- email ---
    email = r.get("email")
    if email and not mps[qid]["email"]:
        if email.startswith("mailto:"):
            email = email.replace("mailto:", "")
        mps[qid]["email"] = email

    # --- X ---
    uses_x = r.get("usesX") in ("1", 1, True)
    if uses_x:
        mps[qid]["usesX"] = True
        if not mps[qid]["xHandle"] and r.get("xHandle"):
            mps[qid]["xHandle"] = r["xHandle"]

clean = list(mps.values())

print(f"Raw rows: {len(rows)}")
print(f"Unique MPs: {len(clean)}")
print(f"MPs with X: {sum(1 for m in clean if m['usesX'])}")

with OUTPUT.open("w", encoding="utf-8") as f:
    json.dump(clean, f, ensure_ascii=False, indent=2)

print(f"Saved → {OUTPUT}")
