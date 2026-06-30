import json, re

with open(r'd:\Users\AS\Desktop\podcast-distill\backfill\items\youtube\0tCxeVLWpvc\summary.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

dig = d['digest']
print("=== VALIDATION ===")
print(f"short_title: {len(dig['short_title'])} <= 10: {len(dig['short_title'])<=10}")
print(f"one_liner: {len(dig['one_liner'])} <= 30: {len(dig['one_liner'])<=30}")
print(f"why_it_matters: {len(dig['why_it_matters'])} <= 50: {len(dig['why_it_matters'])<=50}")

print(f"\nSummary ({len(dig['summary'])} paragraphs, need >=4):")
for i, s in enumerate(dig['summary']):
    status = "OK" if len(s) <= 150 else "OVER"
    print(f"  [{i}] {len(s)} chars {status}")

print(f"\nCore points ({len(dig['core_points'])} items, need >=5):")
for i, c in enumerate(dig['core_points']):
    status = "OK" if len(c) <= 90 else "OVER"
    print(f"  [{i}] {len(c)} chars {status}")

print(f"\nKey facts: {len(dig['key_facts'])}")
print(f"Takeaways: {len(dig['takeaways'])} (1-2: {1<=len(dig['takeaways'])<=2})")
print(f"Topics: {len(dig['topics'])} <= 3: {len(dig['topics'])<=3}")
for t in dig['topics']:
    status = "OK" if len(t) <= 12 else "OVER"
    print(f"  '{t}' {len(t)} chars {status}")

print(f"\nQuality: {dig['quality']} (correct: {dig['quality']=='traeagentvalidated'})")
print(f"Content density: {dig['content_density']}")
print(f"Importance score: {dig['importance_score']}")
print(f"Quote keys: {sorted(dig['quote'].keys())}")
print(f"Generation keys: {sorted(d['generation'].keys())}")

# Check markdown
text = json.dumps(dig, ensure_ascii=False)
has_md = False
for pattern in [r'\*\*', r'##', r'```', r'<[a-z][^>]*>']:
    found = re.findall(pattern, text)
    if found:
        print(f"WARNING: markdown found: {found}")
        has_md = True
if not has_md:
    print("\nNo markdown - OK")

# Check no questions in takeaways
for t in dig['takeaways']:
    if t.endswith('？') or t.endswith('?'):
        print(f"WARNING: takeaway ends with question mark: {t}")

print("\n=== DONE ===")
