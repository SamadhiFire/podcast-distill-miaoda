# 阶段 E-YouTube 草稿运行说明

用途：在小宇宙阶段 D 仍在处理时，先让 YouTube 已成功字幕进入阶段 E，生成单集摘要缓存和 YouTube-only 日期日报草稿。

本地没有大模型、也不准备配置大模型时，使用本文默认的 **Trae agent 模式**：脚本只导出任务和校验结果，真正的总结由 Trae 用它自身的大模型能力完成。

本轮边界：

- 只处理 `platform = youtube` 且 `extractions.status = success` 的条目。
- 不处理小宇宙。
- 不停止、不修改阶段 D 的小宇宙转录进程。
- 不发布飞书。
- 输出必须标记为 `youtube_only_draft`，不能当作完整日报。

## 1. Trae Agent 模式

### 1.1 导出小样本任务

先导出 10 条 YouTube 摘要任务：

```powershell
python scripts\backfill\export_summary_jobs.py --platform youtube --month 2025-07 --limit 10
```

任务会出现在：

```text
backfill/summary_jobs/youtube/<video_id>/
├── request.json
└── prompt.md
```

如果仓库里已经存在 `deterministic_extractive` / `fallback` 质量的 `summary.json`，导出脚本仍会重新导出任务；这些规则摘要不会被当作正式阶段 E 摘要。

### 1.2 交给 Trae 处理

把下面这段给 Trae：

```text
请阅读 docs/PHASE_E_YOUTUBE_ONLY_RUNBOOK.md。
本轮只处理 backfill/summary_jobs/youtube 下刚导出的 10 个任务。
逐个打开每个任务目录的 prompt.md，按照里面的要求读取对应 transcript.txt，并用你自身的大模型能力写入目标 summary.json。
不要配置或调用本地 LLM_BASE_URL，不要修改 SQLite，不要发布飞书，不要处理小宇宙，不要进入下一阶段。
每写完一条，运行：
python scripts\backfill\validate_summary_outputs.py --platform youtube --item-id <对应 item_id>
如果校验失败，必须读取错误原因并重写对应 `summary.json`，直到该条校验为 `valid`。全部完成后汇报成功、失败和需要人工处理的任务。
```

### 1.2.1 外部模型必须遵守的边界

外部模型只写 `summary.json` 内容，不负责飞书排版。以下格式全部由程序生成，不允许外部模型在字段里手写：

- `今日信息地图` 的 mermaid / whiteboard。
- callout、callout 颜色、emoji、边框色。
- grid 双栏 / 三栏布局。
- 一级 / 二级 / 三级标题层级。
- 关键事实表格。
- 引用块、链接、加粗、字体颜色、星级显示。
- “全部更新”下固定五大分类，以及无更新分类的“今日无新增”。

外部模型严禁输出 Markdown 标题、表格、XML、HTML、mermaid、callout、grid、颜色、字号、加粗标记或代码块。它只写纯 JSON 字段；飞书目录和视觉格式由 `scripts/report_contract.py` 统一渲染。

### 1.2.2 字段内容规范

- `short_title`：18 字以内中文短标题，只写主题判断，不照抄英文标题。
- `one_liner`：30 字以内，说清“主要讲什么 + 最核心判断”；不写“本期讨论了……”。
- `why_it_matters`：60 字以内，说明和读者判断、产品、投资、组织、政策或知识迁移的关系；不复述 `one_liner`。
- `summary`：2 到 6 段，每段只讲一个议题；按议题组织，不按时间线流水账。
- `core_points`：3 到 7 条，每条是判断、因果、机制、趋势或框架；不要写空泛话。
- `key_facts`：只放可核对事实、数字、年份、金额、比例、机构动作或明确案例；没有可靠事实就空数组。
- `takeaways`：1 到 2 条，写读者能执行的判断方法或行动；不能写问句或作者 Todo。
- `guests`：只写字幕或标题中明确出现的人物、机构、角色；不知道职位就不要补职位。
- `topics`：最多 3 个主题词，用名词短语。
- `tensions`：最多 3 条，写对立观点、适用边界、风险、限制或未决问题。
- `quote`：只有值得记忆且能核对时才写；不能逐字匹配就写 `paraphrase`，不确定就写 `null`。
- `importance_score`：1 到 5。5 代表高密度 / 强时效 / 一手信息 / 可迁移价值高；3 代表普通可读；1 代表低信息密度或只适合归档。
- `content_density`：`brief` 用于短或低密度内容；`standard` 用于常规内容；`high` 用于长节目、多议题、数据密集或一手信息多的内容。

### 1.2.3 防幻觉规则

- 字幕中没有明确出现的人名、公司、年份、金额、比例、职位、政策、产品状态，一律不要写。
- 不要根据标题、常识、新闻背景或模型自己的知识补充事实。
- 不要为了让摘要“更完整”补节目没有讲的上下文。
- 英文字幕可以翻译和概括，但必须保留原意；不确定的术语宁可保留英文。
- 字幕质量差时，只写能确定的部分，并在 `tensions` 写明信息限制；不要编造缺失内容。
- 同一个事实不要在 `summary`、`core_points`、`key_facts` 中机械重复。

### 1.3 校验小样本

Trae 写完后，统一校验：

```powershell
python scripts\backfill\validate_summary_outputs.py --platform youtube --month 2025-07 --limit 10 --write-normalized
```

校验报告会写入：

```text
backfill/summary_jobs/validation_report.json
```

### 1.4 生成小样本日期草稿

```powershell
python scripts\backfill\build_daily_views.py --month 2025-07
python scripts\backfill\render_daily.py --month 2025-07 --limit-days 3
```

抽查：

- `backfill/items/youtube/<video_id>/summary.json`
- `backfill/daily/2025/2025-07/YYYY-MM-DD/items.json`
- `backfill/daily/2025/2025-07/YYYY-MM-DD/manifest.json`
- `backfill/daily/2025/2025-07/YYYY-MM-DD/digest.md`

验收要点：

- `summary.json` 里有 `transcript_sha256`，且和 SQLite 中 extraction hash 一致。
- `summary.json` 不能是规则抽取 / fallback / deterministic 质量；`one_liner`、`summary`、`core_points`、`takeaways` 必须是中文读者版表达。
- 不允许把 `WEBVTT`、`Kind: captions`、`Language: en`、`[music]` 或主持开场寒暄当作摘要内容。
- `key_facts` 中的数字必须能在字幕中找到；逐字 quote 必须能在字幕中匹配，否则改为 `paraphrase` 或 `null`。
- `digest.md` 顶部必须写明 YouTube-only 草稿范围。
- `manifest.json` 必须记录 skipped/incomplete，尤其是短视频、缺 summary、blocked 条目。
- 不应出现飞书发布动作。

## 2. 全量 YouTube 草稿

小样本确认后，导出全部尚未缓存的 YouTube 任务：

```powershell
python scripts\backfill\export_summary_jobs.py --platform youtube
```

让 Trae 分批处理 `backfill/summary_jobs/youtube/*/prompt.md`。建议每批 20 到 50 条，处理完一批就校验：

```powershell
python scripts\backfill\validate_summary_outputs.py --platform youtube --write-normalized
```

全部校验通过后：

```powershell
python scripts\backfill\build_daily_views.py --platform youtube
python scripts\backfill\render_daily.py
```

不要使用 `--force`，除非你明确想重做已有摘要。正常导出会跳过 transcript hash 没变的 `summary.json`。

## 3. 可选：OpenAI-Compatible API 模式

如果将来 Trae 或其他工具暴露了兼容 `/chat/completions` 的 HTTP 服务，才使用：

```powershell
$env:LLM_BASE_URL="http://127.0.0.1:8000/v1"
$env:LLM_MODEL="your-model-name"
$env:LLM_API_KEY="optional-api-key"
$env:LLM_TIMEOUT="300"
$env:LLM_MAX_ATTEMPTS="2"
$env:LLM_CHUNK_CHARS="24000"

python scripts\backfill\summarize_batch.py --platform youtube --month 2025-07 --limit 10 --require-llm
```

当前你不配置本地大模型，所以默认不要走这一节。

## 4. 输出给用户

完成后汇报：

- 导出了多少个任务，Trae 实际写入多少个 `summary.json`。
- 校验有效、缺失、无效各多少。
- 生成了多少个日期目录。
- 渲染了多少个 `digest.md`。
- blocked/skipped 的数量和主要原因。
- 给出 1 到 3 个可抽查的 `digest.md` 路径。

阶段 E-YouTube 完成后仍然只是草稿。等小宇宙阶段 D/E 完成后，需要重新构建合并版日期视图和完整日报。
