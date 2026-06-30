import re, json
NUMBER_RE = re.compile(r"(?<![A-Za-z])\$?\d[\d,]*(?:\.\d+)?%?")
with open('backfill/items/youtube/elxkRPcsSQQ/summary.json','r',encoding='utf-8') as f:
    s = json.load(f)
kfs = s.get('digest',{}).get('key_facts',[])
for i, kf in enumerate(kfs):
    val = kf.get('value','')
    ctx = kf.get('context','')
    val_nums = NUMBER_RE.findall(val)
    ctx_nums = NUMBER_RE.findall(ctx)
    print(f"[{i}] val: {val_nums}, ctx: {ctx_nums}")
    # normalize as validator does
    norm_val = set()
    for r in val_nums:
        norm_val.add(r.replace(',','').lstrip('$'))
    norm_ctx = set()
    for r in ctx_nums:
        norm_ctx.add(r.replace(',','').lstrip('$'))
    print(f"    normalized val: {norm_val}, ctx: {norm_ctx}")
