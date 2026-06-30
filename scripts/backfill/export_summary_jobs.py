#!/usr/bin/env python3
"""Export phase-E item-summary jobs for an AI agent such as Trae.

Use this when there is no local LLM/API configuration. The script does not call
any model. It writes small job packets under backfill/summary_jobs/ that tell
Trae which transcript to read and exactly which summary.json file to create.

Typical flow:

    python scripts/backfill/export_summary_jobs.py --platform youtube --month 2025-07 --limit 10
    # Ask Trae to process the generated prompt.md files with its own model.
    python scripts/backfill/validate_summary_outputs.py --platform youtube --month 2025-07
    python scripts/backfill/build_daily_views.py --month 2025-07
    python scripts/backfill/render_daily.py --month 2025-07 --limit-days 3
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.backfill.db import get_conn


ITEMS_DIR = ROOT / "backfill" / "items"
JOBS_DIR = ROOT / "backfill" / "summary_jobs"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def query_items(
    conn: sqlite3.Connection,
    platform: str,
    month: str | None,
    date: str | None,
    limit: int | None,
) -> list[sqlite3.Row]:
    clauses = ["i.platform = ?", "e.status = 'success'"]
    params: list[Any] = [platform]
    if month:
        clauses.append("substr(i.report_date, 1, 7) = ?")
        params.append(month)
    if date:
        clauses.append("i.report_date = ?")
        params.append(date)

    sql = f"""
        SELECT
            i.item_id, i.platform, i.platform_id, i.source_id, i.category,
            i.title, i.url, i.published_at, i.report_date, i.duration_seconds,
            i.language, s.name AS source_name,
            e.method AS extraction_method, e.language AS extraction_language,
            e.sha256 AS transcript_sha256, e.text_chars, e.coverage_ratio,
            e.completed_at AS extraction_completed_at
        FROM items i
        JOIN extractions e ON e.item_id = i.item_id
        LEFT JOIN sources s ON s.source_id = i.source_id
        WHERE {" AND ".join(clauses)}
        ORDER BY i.report_date, i.published_at, i.item_id
    """
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
    return list(conn.execute(sql, params))


def is_fallback_summary(payload: dict[str, Any]) -> bool:
    digest = payload.get("digest") if isinstance(payload.get("digest"), dict) else {}
    quality = str(digest.get("quality") or payload.get("generator") or "").lower()
    generation = payload.get("generation") if isinstance(payload.get("generation"), dict) else {}
    script = str(generation.get("script") or "").lower()
    return "fallback" in quality or "deterministic" in quality or "deterministic" in script


def summary_is_current(
    summary_path: Path, transcript_sha256: str | None, accept_fallback_cache: bool
) -> bool:
    existing = read_json(summary_path)
    if not (
        existing
        and isinstance(existing.get("digest"), dict)
        and existing.get("transcript_sha256")
        and (not transcript_sha256 or existing.get("transcript_sha256") == transcript_sha256)
    ):
        return False
    return accept_fallback_cache or not is_fallback_summary(existing)


def build_item(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "item_id": row["item_id"],
        "platform": row["platform"],
        "platform_id": row["platform_id"],
        "source_id": row["source_id"],
        "source_name": row["source_name"] or row["source_id"],
        "category": row["category"] or "待分类",
        "title": row["title"] or "",
        "url": row["url"] or "",
        "published_at": row["published_at"] or "",
        "report_date": row["report_date"] or "",
        "duration_seconds": int(row["duration_seconds"] or 0),
        "language": row["language"] or row["extraction_language"] or "",
    }


def build_request(row: sqlite3.Row) -> dict[str, Any]:
    item = build_item(row)
    item_root = ITEMS_DIR / row["platform"] / row["platform_id"]
    transcript_path = item_root / "transcript.txt"
    summary_path = item_root / "summary.json"
    job_dir = JOBS_DIR / row["platform"] / row["platform_id"]
    return {
        "schema_version": 1,
        "job_type": "phase_e_item_summary",
        "status": "pending_for_agent",
        "mode": "trae_agent_no_local_llm",
        "created_at": utc_now(),
        "item": item,
        "transcript": {
            "path": rel(transcript_path),
            "vtt_path": rel(item_root / "transcript.vtt"),
            "sha256": row["transcript_sha256"],
            "text_chars": row["text_chars"],
            "coverage_ratio": row["coverage_ratio"],
            "extraction_method": row["extraction_method"],
            "extraction_completed_at": row["extraction_completed_at"],
        },
        "output": {
            "summary_path": rel(summary_path),
            "job_dir": rel(job_dir),
        },
        "digest_contract": {
            "short_title": "18字以内中文短标题",
            "one_liner": "30字以内，完整中文句子，讲清主题+意义",
            "why_it_matters": "60字以内，说明为什么值得读",
            "summary": "2到6段，每段150字以内，按议题组织，不按时间流水账",
            "core_points": "3到7条，每条90字以内",
            "key_facts": "最多8条；每条含 label/value/context/source_refs",
            "takeaways": "1到2条，读者可采用的判断或行动，不写问句",
            "guests": "0到5条，人物、机构、角色",
            "topics": "最多3个主题词",
            "tensions": "最多3条分歧、限制或未决点",
            "quote": "没有确定逐字原文时写 null，或 kind 写 paraphrase",
            "importance_score": "1到5的整数",
            "content_density": "brief | standard | high",
        },
    }


def build_prompt(request: dict[str, Any]) -> str:
    item = request["item"]
    transcript = request["transcript"]
    output = request["output"]
    return f"""# Trae 阶段 E 单集摘要任务

你正在 `D:\\Users\\AS\\Desktop\\podcast-distill` 工作。不要调用本地大模型服务，不要配置 `LLM_BASE_URL`。请使用你作为 Trae agent 自身的大模型能力完成总结。

## 任务边界

- 只处理这一条 YouTube 节目。
- 读取完整字幕：`{transcript['path']}`
- 如需核对逐字引用或时间上下文，可读取 VTT：`{transcript['vtt_path']}`
- 写入结果文件：`{output['summary_path']}`
- 不修改 SQLite。
- 不发布飞书。
- 不处理小宇宙。
- 不改动阶段 D 进程或状态。

## 节目元数据

```json
{json.dumps(item, ensure_ascii=False, indent=2)}
```

## 必须写出的 summary.json 结构

把下面 JSON 写入 `{output['summary_path']}`。字段名必须保持一致。`digest` 必须完全基于字幕内容，不要编造字幕中没有的信息。

```json
{{
  "schema_version": 1,
  "item_id": "{item['item_id']}",
  "platform": "{item['platform']}",
  "platform_id": "{item['platform_id']}",
  "source_id": "{item['source_id']}",
  "source_name": "{item['source_name']}",
  "category": "{item['category']}",
  "title": "{item['title']}",
  "url": "{item['url']}",
  "published_at": "{item['published_at']}",
  "report_date": "{item['report_date']}",
  "duration_seconds": {item['duration_seconds']},
  "transcript_sha256": "{transcript['sha256']}",
  "transcript_text_chars": {transcript.get('text_chars') or 0},
  "extraction": {{
    "method": "{transcript.get('extraction_method') or ''}",
    "language": "{item['language']}",
    "coverage_ratio": {transcript.get('coverage_ratio') if transcript.get('coverage_ratio') is not None else 'null'},
    "text_chars": {transcript.get('text_chars') or 0},
    "completed_at": "{transcript.get('extraction_completed_at') or ''}"
  }},
  "generation": {{
    "script": "trae_agent",
    "generated_at": "请填写当前 ISO-8601 时间",
    "llm_configured": false,
    "model": "trae_agent",
    "base_url": "",
    "max_attempts": 1
  }},
  "digest": {{
    "short_title": "18字以内中文短标题",
    "one_liner": "30字以内完整句",
    "why_it_matters": "60字以内",
    "summary": ["2到6段，每段150字以内"],
    "core_points": ["3到7条，每条90字以内"],
    "key_facts": [
      {{"label": "14字内", "value": "36字内", "context": "90字内", "source_refs": []}}
    ],
    "takeaways": ["1到2条，不写问句"],
    "guests": ["人物或机构，最多5条"],
    "topics": ["最多3个主题词"],
    "tensions": ["最多3条限制、分歧或未决点"],
    "quote": null,
    "importance_score": 1,
    "content_density": "brief",
    "quality": "trae_agent_validated"
  }}
}}
```

## 飞书格式边界

你不负责飞书格式，也不要尝试复刻飞书页面。下列内容全部由程序 `scripts/report_contract.py` 和发布脚本自动生成：

- 文档标题、一级 / 二级 / 三级标题层级。
- `今日信息地图` 的 mermaid / whiteboard。
- `3 分钟速览`、单篇信息块、30 秒结论等 callout。
- callout 颜色、emoji、边框色。
- grid 双栏 / 三栏布局。
- 关键事实表格。
- 引用块、链接、加粗、字体颜色、星级显示。
- “全部更新”下固定五大分类，以及无更新分类的“今日无新增”。

你只写 `summary.json` 里的纯内容字段。严禁在字段里写 Markdown 标题、表格、XML、HTML、mermaid、callout、grid、颜色、字号、加粗标记或代码块。

## 字段写作规范

- `short_title`：18 字以内中文短标题，只写主题判断，不写节目名、栏目名、嘉宾名堆叠；不能照抄英文标题。
- `one_liner`：30 字以内，一句话说清“这期主要讲什么 + 最核心判断”；不写背景铺垫，不写“本期讨论了……”。
- `why_it_matters`：60 字以内，只写它和普通读者、产品、投资、组织、政策或知识判断的关系；不复述 `one_liner`。
- `summary`：2 到 6 段，每段只讲一个议题；按议题组织，不按时间线流水账；可以综合多个片段，但必须来自字幕。
- `core_points`：3 到 7 条，每条必须是判断、因果、机制、趋势或可迁移框架；不要写“嘉宾提到 X”“节目讨论了 Y”这种空话。
- `key_facts`：只放可核对的事实、数字、年份、金额、比例、机构动作或明确案例；没有可靠事实就写空数组，不为填表编内容。
- `takeaways`：1 到 2 条，写读者可执行的判断方法或行动；不能写问句，不能写给作者自己的研究 Todo。
- `guests`：只写字幕或标题中明确出现的人物、机构、角色；不知道职位就不要补职位。
- `topics`：最多 3 个主题词，用名词短语，不写长句。
- `tensions`：最多 3 条，写对立观点、适用边界、风险、限制或未决问题；不要写泛泛的“仍需观察”。
- `quote`：只有值得记忆且能核对时才写；不能逐字匹配就写 `paraphrase`，不确定就写 `null`。
- `importance_score`：1 到 5。5 = 高密度 / 强时效 / 一手信息 / 可迁移价值高；3 = 普通可读；1 = 低信息密度或只适合归档。
- `content_density`：`brief` 用于短或低密度内容；`standard` 用于常规访谈 / 新闻；`high` 用于长节目、多议题、数据密集或一手信息多的内容。

## 防幻觉规则

- 字幕中没有明确出现的人名、公司、年份、金额、比例、职位、政策、产品状态，一律不要写。
- 不要根据标题、常识、新闻背景或你自己的知识补充事实。
- 不要为了让摘要“更完整”补节目没有讲的上下文。
- 对英文字幕可以翻译和概括，但必须保留原意；不确定的术语宁可保留英文。
- 如果字幕质量差，只写能确定的部分，并在 `tensions` 写明信息限制；不要编造缺失内容。
- 同一个事实不要在 `summary`、`core_points`、`key_facts` 中机械重复。

## 内容要求

- 摘要要用中文，即使节目是英文。
- `short_title`、`one_liner`、`why_it_matters`、`summary`、`core_points`、`takeaways` 必须是中文读者可直接读懂的表达；英文专有名词可以保留，但不能整句照抄英文字幕。
- `summary` 按议题组织，不按字幕时间线流水账。
- `one_liner` 要让读者 30 秒内知道这期讲什么、为什么重要。
- 严禁把 `WEBVTT`、`Kind: captions`、`Language: en`、`[music]`、主持开场寒暄或字幕噪声当成摘要内容。
- 按时长保留信息密度：30 分钟以下至少 2 段摘要 / 3 条要点；30 分钟以上至少 3 段摘要 / 4 条要点；60 分钟以上或高密度内容至少 4 段摘要 / 5 条要点。
- 有数字、年份、金额、公司、人名时必须来自字幕；不确定就省略。`key_facts` 中的数字必须能在字幕中找到。
- 只有能在原字幕中逐字匹配时，`quote.kind` 才能写 `verbatim`；否则写 `paraphrase` 或 `quote: null`。
- 不要输出 Markdown 正文，不要写解释，只写目标 JSON 文件。
- 写完后运行校验；如果校验失败，读取错误原因并修正 `summary.json`，直到该条输出 `valid`：

```powershell
python scripts\\backfill\\validate_summary_outputs.py --platform youtube --item-id {item['item_id']}
```
"""


def export_one(
    row: sqlite3.Row, force: bool, dry_run: bool, accept_fallback_cache: bool
) -> str:
    item_root = ITEMS_DIR / row["platform"] / row["platform_id"]
    transcript_path = item_root / "transcript.txt"
    summary_path = item_root / "summary.json"
    job_dir = JOBS_DIR / row["platform"] / row["platform_id"]

    if not transcript_path.exists():
        return "missing_transcript"
    if not force and summary_is_current(summary_path, row["transcript_sha256"], accept_fallback_cache):
        return "skipped_cached"

    request = build_request(row)
    prompt = build_prompt(request)
    if dry_run:
        print(f"[DRY] would export {row['item_id']} -> {job_dir}")
        return "dry_run"

    write_json(job_dir / "request.json", request)
    (job_dir / "prompt.md").write_text(prompt, encoding="utf-8")
    print(f"[OK] exported {row['item_id']} -> {job_dir}")
    return "exported"


def main() -> int:
    parser = argparse.ArgumentParser(description="Export summary jobs for Trae agent mode.")
    parser.add_argument("--platform", default="youtube")
    parser.add_argument("--month", help="Only export report_date month YYYY-MM")
    parser.add_argument("--date", help="Only export one report_date YYYY-MM-DD")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--force", action="store_true", help="Export jobs even when summary cache is current")
    parser.add_argument(
        "--accept-fallback-cache",
        action="store_true",
        help="Treat deterministic fallback summaries as current. Default is to re-export them for Trae.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conn = get_conn()
    rows = query_items(conn, args.platform, args.month, args.date, args.limit)
    print(f"Export summary jobs: platform={args.platform}, candidates={len(rows)}")
    counts: dict[str, int] = {}
    for row in rows:
        status = export_one(row, args.force, args.dry_run, args.accept_fallback_cache)
        counts[status] = counts.get(status, 0) + 1
    print("Export result:")
    for key in sorted(counts):
        print(f"  {key}: {counts[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
