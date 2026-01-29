import re
from pathlib import Path

input_file = Path("data/mps_se_orig.json")
output_file = Path("data/mps_se.json")

text = input_file.read_text(encoding="utf-8")

# Replace: xHandle": @Something  →  xHandle": "@Something"
pattern = re.compile(
    r'("xHandle"\s*:\s*)(@[\w_]+)'
)

fixed_text = pattern.sub(r'\1"\2"', text)

output_file.write_text(fixed_text, encoding="utf-8")

print(f"Done! Fixed file written to {output_file}")
