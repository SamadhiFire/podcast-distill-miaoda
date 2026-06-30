# Trae 阶段 E 单集摘要任务

你正在 `D:\Users\AS\Desktop\podcast-distill` 工作。不要调用本地大模型服务，不要配置 `LLM_BASE_URL`。请使用你作为 Trae agent 自身的大模型能力完成总结。

## 任务边界

- 只处理这一条 YouTube 节目。
- 读取完整字幕：`backfill/items/youtube/-h0z8eXY1qY/transcript.txt`
- 如需核对逐字引用或时间上下文，可读取 VTT：`backfill/items/youtube/-h0z8eXY1qY/transcript.vtt`
- 写入结果文件：`backfill/items/youtube/-h0z8eXY1qY/summary.json`
- 不修改 SQLite。
- 不发布飞书。
- 不处理小宇宙。
- 不改动阶段 D 进程或状态。

## 节目元数据

```json
{
  "item_id": "youtube:-h0z8eXY1qY",
  "platform": "youtube",
  "platform_id": "-h0z8eXY1qY",
  "source_id": "yt_bloomberg_surveillance",
  "source_name": "Bloomberg Surveillance Full Shows",
  "category": "商业 / 财经 / 投资",
  "title": "Bloomberg Surveillance Jackson Hole Special 8/22/2025",
  "url": "https://www.youtube.com/watch?v=-h0z8eXY1qY",
  "published_at": "2025-08-22T18:51:01+00:00",
  "report_date": "2025-08-23",
  "duration_seconds": 9882,
  "language": "en"
}
```

## 必须写出的 summary.json 结构

把下面 JSON 写入 `backfill/items/youtube/-h0z8eXY1qY/summary.json`。字段名必须保持一致。`digest` 必须完全基于字幕内容，不要编造字幕中没有的信息。

```json
{
  "schema_version": 1,
  "item_id": "youtube:-h0z8eXY1qY",
  "platform": "youtube",
  "platform_id": "-h0z8eXY1qY",
  "source_id": "yt_bloomberg_surveillance",
  "source_name": "Bloomberg Surveillance Full Shows",
  "category": "商业 / 财经 / 投资",
  "title": "Bloomberg Surveillance Jackson Hole Special 8/22/2025",
  "url": "https://www.youtube.com/watch?v=-h0z8eXY1qY",
  "published_at": "2025-08-22T18:51:01+00:00",
  "report_date": "2025-08-23",
  "duration_seconds": 9882,
  "transcript_sha256": "07c82cc1dff9da3c64673f84f43b303dea1da626bd86f370cbae1d5d84afc269",
  "transcript_text_chars": 163770,
  "extraction": {
    "method": "yt-dlp",
    "language": "en",
    "coverage_ratio": 0.999605343047966,
    "text_chars": 163770,
    "completed_at": "2026-06-29 09:25:54"
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
python scripts\backfill\validate_summary_outputs.py --platform youtube --item-id youtube:-h0z8eXY1qY
```
