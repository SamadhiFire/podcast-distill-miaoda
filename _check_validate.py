import json, os
base = r"d:/Users/AS/Desktop/podcast-distill"

# Read the validate script to understand requirements
with open(os.path.join(base, "scripts", "backfill", "validate_summary_outputs.py"), "r", encoding="utf-8") as f:
    code = f.read()
print(code[:8000])
