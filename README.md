# Leave X Tools

Tools to collect, clean, and enrich data for the [Leave X campaign](https://leavex.eu), which tracks the usage of X/Twitter by politicians at the EU and national levels.

## Related repositories

- **leavex.eu website**: https://github.com/everton137/leavex.eu


## Scripts Overview

Short explanation of each script and its role in the data pipeline.

### **`get_eu_mp.py`**
Scrapes the European Parliament website to collect data on current MEPs:

- name and country
- email (decoded from obfuscated HTML)
- EU political group + national party
- X/Twitter account and handle  
- outputs: `meps_all.csv`

### **`csv_to_json_meps.py`**
Converts `meps_all.csv` into the JSON structure used by the website:

- cleans and normalizes fields
- adds ISO country codes
- infers X usage (`usesX`, `xHandle`)
- outputs: `meps_all.json`


### **`apply_meps_overrides.py`**
Applies manual corrections and metadata on top of scraped data:

- reads `meps_all.json`
- merges overrides from `meps_overrides.json`
- updates or adds fields such as:
  - corrected X handle
  - X status (`active`, `inactive`, etc.)
  - archive links, notes, timestamps
- outputs: `meps_all_with_overrides.json`

Used to ensure accuracy when the scraper or Wikidata misses details.

## Supporting Files

### **`meps_overrides.json`**
Contains manual overrides keyed by MEP ID.

Used for:

- fixing missing or incorrect X handles
- marking X accounts as inactive
- storing last activity / exit dates
- adding contextual notes and archive URLs

Overrides are merged automatically by `apply_meps_overrides.py`.

## Data Pipeline Summary

- get_eu_mp.py → meps_all.csv
- csv_to_json_meps.py → meps_all.json
- apply_meps_overrides.py + meps_overrides.json → meps_all_with_overrides.json

This pipeline produces a clean, consistent dataset of EU and national politicians with X/Twitter metadata suitable for the Leave X website and analysis tools.


