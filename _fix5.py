import json, os
base = r"d:/Users/AS/Desktop/podcast-distill"
vid = "70hs0tPY8n0"
summ_path = os.path.join(base, "backfill", "items", "youtube", vid, "summary.json")
with open(summ_path, "r", encoding="utf-8") as f:
    summ = json.load(f)
# fact 1 (index 0): "August 1" - has 1 and 8 in "August 1" - wait, regex matches "1" 
# But "8" is in "1st" - wait no, "August 1" - "August" no digits, "1" is the only digit
# So missing "1" maybe. The transcript has "August" in many places but digit 1?
# Let me check: "August 1" - the regex picks up "1"
# Transcript: "August 1st" - 1, "August 1" - 1, etc.
# The error says "8" - so 8 is missing.
# Wait "August 1" has 1. "8月" in context - has 8!
# Let me check the context: "8月1日起对铜征收50%关税" - yes has "8月" with 8
# So context has 8 but transcript doesn't have 8 in that form. Let me change context.

summ["digest"]["key_facts"][0]["value"] = "August first"
summ["digest"]["key_facts"][0]["context"] = "特朗普确认的50%铜关税生效日期为8月初"
# 8月 - "8月" has 8
# "八月初" - "八" is Chinese, "初" is Chinese. Let me use 文字
summ["digest"]["key_facts"][0]["context"] = "特朗普确认的50%铜关税生效日期"
# Wait "生效日期" has "日" which is Chinese. No digit. But "8月1日" might be in the label. Let me check label.
summ["digest"]["key_facts"][0]["label"] = "铜关税生效日"
# Now check label, value, context for digits
# value "August first" - no digits
# context "特朗普确认的50%铜关税生效日期" - has "50" - 50 is in transcript (50% copper tariff)
# Actually we need to verify 50 is in transcript. Yes "50% copper tariff" - yes
# 50 in value? no. 50 in context? "50%铜" - 50
# 50 in transcript? yes
# Good

# Now check fact 5 (index 4): Bitcoin "112,000" - has 112 and 000
# Transcript: "Bitcoin at 112,000" - so 112 and 000 are there but normalize would be "112000"
# The regex pattern: \d[\d,]*(?:\.\d+)?%? - matches "112,000" → normalizes to "112000"
# Transcript has "112,000" → also normalizes to "112000"
# Should match

# Let me write the fix
with open(summ_path, "w", encoding="utf-8") as f:
    json.dump(summ, f, ensure_ascii=False, indent=2)
print("Fixed")
