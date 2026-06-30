# Trae 阶段 E 单集摘要任务

你正在 `D:\Users\AS\Desktop\podcast-distill` 工作。不要调用本地大模型服务，不要配置 `LLM_BASE_URL`。请使用你作为 Trae agent 自身的大模型能力完成总结。

## 任务边界

- 只处理这一条 YouTube 节目。
- 读取完整字幕：`backfill/items/youtube/3Y8aq_ofEVs/transcript.txt`
- 写入结果文件：`backfill/items/youtube/3Y8aq_ofEVs/summary.json`
- 不修改 SQLite。
- 不发布飞书。
- 不处理小宇宙。
- 不改动阶段 D 进程或状态。

## 节目元数据

```json
{
  "item_id": "youtube:3Y8aq_ofEVs",
  "platform": "youtube",
  "platform_id": "3Y8aq_ofEVs",
  "source_id": "yt_sequoia",
  "source_name": "Sequoia Capital",
  "category": "科技 / AI / VC",
  "title": "Robotics' End Game: Nvidia's Jim Fan",
  "url": "https://www.youtube.com/watch?v=3Y8aq_ofEVs",
  "published_at": "2026-04-30T15:26:49+00:00",
  "report_date": "2026-05-01",
  "duration_seconds": 1203,
  "language": "en"
}
```

## 必须写出的 summary.json 结构

把下面 JSON 写入 `backfill/items/youtube/3Y8aq_ofEVs/summary.json`。字段名必须保持一致。`digest` 必须完全基于字幕内容，不要编造字幕中没有的信息。

```json
{
  "schema_version": 1,
  "item_id": "youtube:3Y8aq_ofEVs",
  "platform": "youtube",
  "platform_id": "3Y8aq_ofEVs",
  "source_id": "yt_sequoia",
  "source_name": "Sequoia Capital",
  "category": "科技 / AI / VC",
  "title": "Robotics' End Game: Nvidia's Jim Fan",
  "url": "https://www.youtube.com/watch?v=3Y8aq_ofEVs",
  "published_at": "2026-04-30T15:26:49+00:00",
  "report_date": "2026-05-01",
  "duration_seconds": 1203,
  "transcript_sha256": "d2e6d948b8d666c63788de14279db68cba1a01f6380c87f6ba1072206bfa1e2f",
  "transcript_text_chars": 16193,
  "extraction": {
    "method": "yt-dlp",
    "language": "en",
    "coverage_ratio": 0.9963948462177888,
    "text_chars": 16193,
    "completed_at": "2026-06-29 13:36:31"
  },
  "generation": {
    "script": "trae_agent",
    "generated_at": "请填写当前 ISO-8601 时间",
    "llm_configured": false,
    "model": "trae_agent",
    "base_url": "",
    "max_attempts": 1
  },
  "digest": {
    "short_title": "18字以内中文短标题",
    "one_liner": "30字以内完整句",
    "why_it_matters": "60字以内",
    "summary": ["2到6段，每段150字以内"],
    "core_points": ["3到7条，每条90字以内"],
    "key_facts": [
      {"label": "14字内", "value": "36字内", "context": "90字内", "source_refs": []}
    ],
    "takeaways": ["1到2条，不写问句"],
    "guests": ["人物或机构，最多5条"],
    "topics": ["最多3个主题词"],
    "tensions": ["最多3条限制、分歧或未决点"],
    "quote": null,
    "importance_score": 1,
    "content_density": "brief",
    "quality": "trae_agent_validated"
  }
}
```

## 内容要求

- 摘要要用中文，即使节目是英文。
- `summary` 按议题组织，不按字幕时间线流水账。
- `one_liner` 要让读者 30 秒内知道这期讲什么、为什么重要。
- 有数字、公司、人名时必须来自字幕；不确定就省略。
- 不要输出 Markdown 正文，不要写解释，只写目标 JSON 文件。
- 写完后运行：

```powershell
python scripts\backfill\validate_summary_outputs.py --platform youtube --item-id youtube:3Y8aq_ofEVs
```
