import requests
import json

SPARQL = """
SELECT
  ?person
  (STRAFTER(STR(?person), "entity/") AS ?qid)
  (SAMPLE(?personLabel) AS ?name)
  (SAMPLE(?partyLabel) AS ?partyName)
  (SAMPLE(?email) AS ?email)
  (SAMPLE(?x) AS ?x)
WHERE {
  ?person p:P39 ?st .
  ?st ps:P39 wd:Q1939555 .

  OPTIONAL { ?st pq:P582 ?endDate . }
  FILTER( !BOUND(?endDate) || ?endDate > NOW() )

  OPTIONAL { ?person wdt:P102 ?party . }
  OPTIONAL { ?party rdfs:label ?partyLabel . FILTER(LANG(?partyLabel) = "de") }

  OPTIONAL { ?person wdt:P968 ?email . }
  OPTIONAL { ?person wdt:P2002 ?x . }

  SERVICE wikibase:label { bd:serviceParam wikibase:language "de,en". }
  ?person rdfs:label ?personLabel .
  FILTER(LANG(?personLabel) = "de" || LANG(?personLabel) = "en")
}
GROUP BY ?person ?qid
ORDER BY ?name
"""

def main():
    url = "https://query.wikidata.org/sparql"

    resp = requests.post(
        url,
        data={"query": SPARQL},
        headers={
            "Accept": "application/sparql-results+json",
            "User-Agent": "leavex.eu (contact@leavex.eu)",
        },
        timeout=(10, 180),
    )
    resp.raise_for_status()

    if resp.status_code != 200:
        print("Status:", resp.status_code)
        print(resp.text[:1000])  # shows WDQS error message
        resp.raise_for_status()

    data = resp.json()


    bindings = data["results"]["bindings"]
    print("Raw rows:", len(bindings))

    mps = {}

    for b in bindings:
        qid = b["qid"]["value"]           # stable unique key
        name = b.get("name", {}).get("value") or b.get("personLabel", {}).get("value")

        if qid not in mps:
            mps[qid] = {
                "id": f"mp_de_{qid}",
                "name": name,
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

        # fill fields if present (later rows won't overwrite earlier good data)
        if not mps[qid]["party"] and "partyName" in b:
            mps[qid]["party"] = b["partyName"]["value"]

        if not mps[qid]["email"] and "email" in b:
            mps[qid]["email"] = b["email"]["value"]

        if not mps[qid]["usesX"] and "x" in b:
            x = b["x"]["value"]
            mps[qid]["usesX"] = True
            mps[qid]["xHandle"] = f"@{x}"

    final_list = list(mps.values())
    print("Unique MPs:", len(final_list))

if __name__ == "__main__":
    main()