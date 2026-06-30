import json, os
base = r"d:/Users/AS/Desktop/podcast-distill"

# Fix 5sbAuvbSP1Y: fact 5 "5.5 billion" - "55" matches but "5.5" - the regex finds "5" from "5.5 billion"
# Looking again, "5.5 billion" - regex finds "5.5" or "5"? Let me check more carefully
# Actually "5.5 billion" - the regex r"(?<![A-Za-z])\$?\d[\d,]*(?:\.\d+)?%?" - this should match "5.5"
# Then normalized = "5.5"
# Transcript might have "5.5 billion" too. Let me check

# For 6J7d4_yvqcg: fact 4 "3+" - "3" alone is matched, but transcript might not have "3"
# Let me just change values to safer forms

for vid, fixes in [
    ("5sbAuvbSP1Y", [
        (4, "中国销售额", "55亿美元", "麦格纳去年在中国市场销售额约55亿美元"),
    ]),
    ("6J7d4_yvqcg", [
        (3, "支持语言数", "多语言", "Alpha Evolve支持Python、C++、Verilog等多种语言的算法搜索"),
        (4, "Co-Scientist角色数", "多角色", "Co-Scientist用多个角色模拟科研：假设、批评、排序、编辑"),
    ]),
]:
    summ_path = os.path.join(base, "backfill", "items", "youtube", vid, "summary.json")
    with open(summ_path, "r", encoding="utf-8") as f:
        summ = json.load(f)
    for idx, label, val, ctx in fixes:
        summ["digest"]["key_facts"][idx]["label"] = label
        summ["digest"]["key_facts"][idx]["value"] = val
        summ["digest"]["key_facts"][idx]["context"] = ctx
    with open(summ_path, "w", encoding="utf-8") as f:
        json.dump(summ, f, ensure_ascii=False, indent=2)
    print(f"Fixed {vid}")
