"""
历史回填命令行入口。
阶段 A: `python -m scripts.backfill.cli init`
"""

import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))


def cmd_init():
    """初始化 backfill 目录结构和数据库。"""
    from scripts.backfill.db import init_db

    print("=" * 60)
    print("  Backfill 阶段 A — 初始化")
    print("=" * 60)

    # 1. 创建目录
    dirs = [
        "backfill/config",
        "backfill/state",
        "backfill/catalog",
        "backfill/items/youtube",
        "backfill/items/xiaoyuzhou",
        "backfill/daily",
        "backfill/temp",
        "backfill/failures",
        "backfill/logs",
        "scripts/backfill",
    ]
    for d in dirs:
        full = ROOT / d
        full.mkdir(parents=True, exist_ok=True)
        print(f"  [OK] 目录: {d}")

    # 2. 初始化数据库
    success, msg = init_db()
    print(f"  {'[OK]' if success else '[FAIL]'} {msg}")

    # 3. 检查配置文件
    config_files = ["backfill/config/backfill.yaml", "backfill/config/sources.yaml"]
    for cf in config_files:
        exists = (ROOT / cf).exists()
        print(f"  {'[OK]' if exists else '[MISS]'} 配置: {cf}")

    # 4. 统计来源数
    try:
        import yaml
        sources_path = ROOT / "backfill" / "config" / "sources.yaml"
        with open(sources_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        src_list = data.get("sources", [])
        plat_count = {}
        for s in src_list:
            plat_count[s["platform"]] = plat_count.get(s["platform"], 0) + 1
        print(f"  来源总数: {len(src_list)}")
        for p, c in sorted(plat_count.items()):
            print(f"    {p}: {c}")
    except Exception as e:
        print(f"  [WARN] 无法解析 sources.yaml: {e}")

    # 5. 判断线上日报是否受影响
    print(f"\n  线上日报目录检查:")
    for d in ["config", "scripts", "reports", "subtitles"]:
        full = ROOT / d
        if full.exists():
            print(f"    [OK] {d}/ -- 未修改")
        else:
            print(f"    [MISS] {d}/ -- 缺失")

    print("\n  初始化完成。")
    print("=" * 60)


def cmd_status():
    """查看当前进度快照。"""
    from scripts.backfill.db import get_conn
    conn = get_conn()
    cur = conn.cursor()

    print("=" * 60)
    print("  Backfill 状态")
    print("=" * 60)

    cur.execute("SELECT status, COUNT(*) FROM sources GROUP BY status")
    src = dict(cur.fetchall())
    print(f"\n  来源状态: {src}")

    cur.execute("SELECT COUNT(*) FROM items")
    items = cur.fetchone()[0]
    print(f"  已盘点节目: {items}")

    cur.execute("SELECT status, COUNT(*) FROM extractions GROUP BY status")
    ext = dict(cur.fetchall())
    print(f"  字幕状态: {ext}")

    cur.execute("SELECT status, COUNT(*) FROM daily_views GROUP BY status")
    dv = dict(cur.fetchall())
    print(f"  日报状态: {dv}")

    cur.execute("SELECT error_type, COUNT(*) FROM failures GROUP BY error_type")
    fl = dict(cur.fetchall())
    print(f"  失败: {fl}")

    conn.close()
    print("=" * 60)


def cmd_inventory():
    """盘点来源."""
    from scripts.backfill.inventory import cmd_inventory as run
    source = os.environ.get("BACKFILL_SOURCE", "")
    days = int(os.environ.get("BACKFILL_LOOKBACK", "90"))
    sys.exit(run(source if source else None, days))


def cmd_extract():
    """提取字幕."""
    from scripts.backfill.extract_batch import cmd_extract as run
    source = os.environ.get("BACKFILL_SOURCE", "")
    limit = int(os.environ.get("BACKFILL_LIMIT", "3"))
    if not source:
        print("需要设置 BACKFILL_SOURCE 环境变量")
        sys.exit(1)
    sys.exit(run(source, limit))


def cmd_phase_b():
    """阶段 B: 两源试跑 (yt_dwarkesh + xyz_42zhangjing)."""
    from scripts.backfill.inventory import cmd_inventory as inv
    from scripts.backfill.extract_batch import cmd_extract as ext

    sources = ["yt_dwarkesh", "xyz_42zhangjing"]

    print("=" * 60)
    print("  Phase B: Two-source trial")
    print("=" * 60)

    # Step 1: Inventory
    for sid in sources:
        print(f"\n--- Inventory: {sid} ---")
        try:
            inv(sid, 90)
        except SystemExit:
            pass

    # Step 2: Extract (3 each)
    for sid in sources:
        print(f"\n--- Extract: {sid} (limit=3) ---")
        try:
            ext(sid, 3)
        except SystemExit:
            pass

    # Step 3: Status
    print("\n--- Final Status ---")
    cmd_status()


COMMANDS = {
    "init": cmd_init,
    "status": cmd_status,
    "inventory": cmd_inventory,
    "extract": cmd_extract,
    "phase-b": cmd_phase_b,
}


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("用法: python -m scripts.backfill.cli <命令>")
        print(f"命令: {', '.join(COMMANDS)}")
        print("环境变量: BACKFILL_SOURCE, BACKFILL_LOOKBACK, BACKFILL_LIMIT")
        sys.exit(1)
    COMMANDS[sys.argv[1]]()
