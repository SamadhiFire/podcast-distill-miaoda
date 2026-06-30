# Phase E: YouTube 单集摘要 — 多窗口提示词

> 使用说明：每个窗口的代码块是**自包含的完整提示词**，可直接复制粘贴给独立的 AI agent。
> 不要写"同上"——每个窗口必须能独立运行。

---

## 窗口 1：2025-07（7月）— 142条待处理

```
## 前置说明（每个窗口通用）

所有 YouTube 字幕已提取完毕，`export_summary_jobs` 已导出所有月份的 `request.json` + `prompt.md`。
- 任务目录：`d:\Users\AS\Desktop\podcast-distill\backfill\summary_jobs\youtube\<video_id>\request.json`
- 字幕位置：`d:\Users\AS\Desktop\podcast-distill\backfill\items\youtube\<video_id>\transcript.txt`
- 输出位置：`d:\Users\AS\Desktop\podcast-distill\backfill\items\youtube\<video_id>\summary.json`

每个窗口负责一个固定月份，只处理该月内还没有 `summary.json` 的条目。
每批 3 条，写完运行 `validate`，验证通过后继续下一批，直到该月清空。

## 本窗口任务

Phase E: 处理 YouTube 2025-07 月份的单集摘要。
该月有 155 条，其中 13 条已完成（已有 summary.json），剩余 142 条待处理。

## 工作流

对每个未处理的 video_id，严格按以下步骤执行：

1. **筛选本月份条目**：列出 `summary_jobs\youtube\` 下所有子目录，读取每个 `request.json`，检查 `report_date` 是否为 `2025-07-xx`
2. **跳过已完成**：检查 `backfill\items\youtube\<video_id>\summary.json` 是否已存在，存在则跳过
3. **读取输入**：
   - 读 `request.json` → 获取 item_id、source_name、title、report_date、transcript_sha256、url 等元数据
   - 读 `transcript.txt` → 获取完整字幕文本
4. **生成 summary.json**：写入 `backfill\items\youtube\<video_id>\summary.json`，结构如下：
   ```json
   {
     "schema_version": 1,
     "item_id": "youtube:<video_id>",
     "metadata": { /* 从 request.json 完整复制所有 metadata 字段 */ },
     "generation": {
       "script": "trae_agent",
       "model": "trae_agent",
       "quality": "trae_agent_validated"
     },
     "digest": {
       "short_title": "简短中文标题（10字以内）",
       "one_liner": "一句话概括（30字以内）",
       "why_it_matters": "为什么重要（50字以内）",
       "summary": "2-6段中文摘要，按议题组织",
       "core_points": ["3-7条核心观点，每条一句话"],
       "key_facts": ["关键事实/数据/数字"],
       "takeaways": ["读者可带走的要点"],
       "guests": ["嘉宾姓名及身份"],
       "topics": ["涉及的主题标签"],
       "tensions": ["争议点或对立观点"],
       "quote": "最值得引用的一句话（原文+中文翻译）",
       "importance_score": 1-10,
       "content_density": "low|medium|high",
       "quality": "trae_agent_validated"
     }
   }
   ```
5. **内容要求**：中文摘要，按议题组织段落，数字/公司名/人名必须来自字幕原文（不编造）
6. **验证**：每写完 3 条，运行：
   ```
   python d:\Users\AS\Desktop\podcast-distill\scripts\backfill\validate_summary_outputs.py --platform youtube --item-id youtube:<video_id>
   ```
   如果 validate 失败，修复 summary.json 后重新验证，直到通过
7. **循环**：继续处理下一批 3 条，直到该月所有条目处理完毕。每 3 条汇报一次进度。

## 本月背景提示

7月有 2025 年 Q2 收官的 Bloomberg 节目、中美贸易谈判、科技财报季等，需要捕捉关键时间节点。
```

---

## 窗口 2：2025-08（8月）— 152条

```
## 前置说明（每个窗口通用）

所有 YouTube 字幕已提取完毕，`export_summary_jobs` 已导出所有月份的 `request.json` + `prompt.md`。
- 任务目录：`d:\Users\AS\Desktop\podcast-distill\backfill\summary_jobs\youtube\<video_id>\request.json`
- 字幕位置：`d:\Users\AS\Desktop\podcast-distill\backfill\items\youtube\<video_id>\transcript.txt`
- 输出位置：`d:\Users\AS\Desktop\podcast-distill\backfill\items\youtube\<video_id>\summary.json`

每个窗口负责一个固定月份，只处理该月内还没有 `summary.json` 的条目。
每批 3 条，写完运行 `validate`，验证通过后继续下一批，直到该月清空。

## 本窗口任务

Phase E: 处理 YouTube 2025-08 月份的单集摘要。
该月共 152 条，全部未处理。

## 工作流

对每个未处理的 video_id，严格按以下步骤执行：

1. **筛选本月份条目**：列出 `summary_jobs\youtube\` 下所有子目录，读取每个 `request.json`，检查 `report_date` 是否为 `2025-08-xx`
2. **跳过已完成**：检查 `backfill\items\youtube\<video_id>\summary.json` 是否已存在，存在则跳过
3. **读取输入**：
   - 读 `request.json` → 获取 item_id、source_name、title、report_date、transcript_sha256、url 等元数据
   - 读 `transcript.txt` → 获取完整字幕文本
4. **生成 summary.json**：写入 `backfill\items\youtube\<video_id>\summary.json`，结构如下：
   ```json
   {
     "schema_version": 1,
     "item_id": "youtube:<video_id>",
     "metadata": { /* 从 request.json 完整复制所有 metadata 字段 */ },
     "generation": {
       "script": "trae_agent",
       "model": "trae_agent",
       "quality": "trae_agent_validated"
     },
     "digest": {
       "short_title": "简短中文标题（10字以内）",
       "one_liner": "一句话概括（30字以内）",
       "why_it_matters": "为什么重要（50字以内）",
       "summary": "2-6段中文摘要，按议题组织",
       "core_points": ["3-7条核心观点，每条一句话"],
       "key_facts": ["关键事实/数据/数字"],
       "takeaways": ["读者可带走的要点"],
       "guests": ["嘉宾姓名及身份"],
       "topics": ["涉及的主题标签"],
       "tensions": ["争议点或对立观点"],
       "quote": "最值得引用的一句话（原文+中文翻译）",
       "importance_score": 1-10,
       "content_density": "low|medium|high",
       "quality": "trae_agent_validated"
     }
   }
   ```
5. **内容要求**：中文摘要，按议题组织段落，数字/公司名/人名必须来自字幕原文（不编造）
6. **验证**：每写完 3 条，运行：
   ```
   python d:\Users\AS\Desktop\podcast-distill\scripts\backfill\validate_summary_outputs.py --platform youtube --item-id youtube:<video_id>
   ```
   如果 validate 失败，修复 summary.json 后重新验证，直到通过
7. **循环**：继续处理下一批 3 条，直到该月所有条目处理完毕。每 3 条汇报一次进度。

## 本月背景提示

8月通常是财报季高峰、Jackson Hole 央行年会、暑期市场波动期。
```

---

## 窗口 3：2025-09（9月）— 134条

```
## 前置说明（每个窗口通用）

所有 YouTube 字幕已提取完毕，`export_summary_jobs` 已导出所有月份的 `request.json` + `prompt.md`。
- 任务目录：`d:\Users\AS\Desktop\podcast-distill\backfill\summary_jobs\youtube\<video_id>\request.json`
- 字幕位置：`d:\Users\AS\Desktop\podcast-distill\backfill\items\youtube\<video_id>\transcript.txt`
- 输出位置：`d:\Users\AS\Desktop\podcast-distill\backfill\items\youtube\<video_id>\summary.json`

每个窗口负责一个固定月份，只处理该月内还没有 `summary.json` 的条目。
每批 3 条，写完运行 `validate`，验证通过后继续下一批，直到该月清空。

## 本窗口任务

Phase E: 处理 YouTube 2025-09 月份的单集摘要。
该月共 134 条，全部未处理。

## 工作流

对每个未处理的 video_id，严格按以下步骤执行：

1. **筛选本月份条目**：列出 `summary_jobs\youtube\` 下所有子目录，读取每个 `request.json`，检查 `report_date` 是否为 `2025-09-xx`
2. **跳过已完成**：检查 `backfill\items\youtube\<video_id>\summary.json` 是否已存在，存在则跳过
3. **读取输入**：
   - 读 `request.json` → 获取 item_id、source_name、title、report_date、transcript_sha256、url 等元数据
   - 读 `transcript.txt` → 获取完整字幕文本
4. **生成 summary.json**：写入 `backfill\items\youtube\<video_id>\summary.json`，结构如下：
   ```json
   {
     "schema_version": 1,
     "item_id": "youtube:<video_id>",
     "metadata": { /* 从 request.json 完整复制所有 metadata 字段 */ },
     "generation": {
       "script": "trae_agent",
       "model": "trae_agent",
       "quality": "trae_agent_validated"
     },
     "digest": {
       "short_title": "简短中文标题（10字以内）",
       "one_liner": "一句话概括（30字以内）",
       "why_it_matters": "为什么重要（50字以内）",
       "summary": "2-6段中文摘要，按议题组织",
       "core_points": ["3-7条核心观点，每条一句话"],
       "key_facts": ["关键事实/数据/数字"],
       "takeaways": ["读者可带走的要点"],
       "guests": ["嘉宾姓名及身份"],
       "topics": ["涉及的主题标签"],
       "tensions": ["争议点或对立观点"],
       "quote": "最值得引用的一句话（原文+中文翻译）",
       "importance_score": 1-10,
       "content_density": "low|medium|high",
       "quality": "trae_agent_validated"
     }
   }
   ```
5. **内容要求**：中文摘要，按议题组织段落，数字/公司名/人名必须来自字幕原文（不编造）
6. **验证**：每写完 3 条，运行：
   ```
   python d:\Users\AS\Desktop\podcast-distill\scripts\backfill\validate_summary_outputs.py --platform youtube --item-id youtube:<video_id>
   ```
   如果 validate 失败，修复 summary.json 后重新验证，直到通过
7. **循环**：继续处理下一批 3 条，直到该月所有条目处理完毕。每 3 条汇报一次进度。

## 本月背景提示

9月是 Q3 收官月、美联储议息会议、科技秋季发布会（Apple iPhone 等）。
```

---

## 窗口 4：2025-10（10月）— 168条

```
## 前置说明（每个窗口通用）

所有 YouTube 字幕已提取完毕，`export_summary_jobs` 已导出所有月份的 `request.json` + `prompt.md`。
- 任务目录：`d:\Users\AS\Desktop\podcast-distill\backfill\summary_jobs\youtube\<video_id>\request.json`
- 字幕位置：`d:\Users\AS\Desktop\podcast-distill\backfill\items\youtube\<video_id>\transcript.txt`
- 输出位置：`d:\Users\AS\Desktop\podcast-distill\backfill\items\youtube\<video_id>\summary.json`

每个窗口负责一个固定月份，只处理该月内还没有 `summary.json` 的条目。
每批 3 条，写完运行 `validate`，验证通过后继续下一批，直到该月清空。

## 本窗口任务

Phase E: 处理 YouTube 2025-10 月份的单集摘要。
该月共 168 条，全部未处理。

## 工作流

对每个未处理的 video_id，严格按以下步骤执行：

1. **筛选本月份条目**：列出 `summary_jobs\youtube\` 下所有子目录，读取每个 `request.json`，检查 `report_date` 是否为 `2025-10-xx`
2. **跳过已完成**：检查 `backfill\items\youtube\<video_id>\summary.json` 是否已存在，存在则跳过
3. **读取输入**：
   - 读 `request.json` → 获取 item_id、source_name、title、report_date、transcript_sha256、url 等元数据
   - 读 `transcript.txt` → 获取完整字幕文本
4. **生成 summary.json**：写入 `backfill\items\youtube\<video_id>\summary.json`，结构如下：
   ```json
   {
     "schema_version": 1,
     "item_id": "youtube:<video_id>",
     "metadata": { /* 从 request.json 完整复制所有 metadata 字段 */ },
     "generation": {
       "script": "trae_agent",
       "model": "trae_agent",
       "quality": "trae_agent_validated"
     },
     "digest": {
       "short_title": "简短中文标题（10字以内）",
       "one_liner": "一句话概括（30字以内）",
       "why_it_matters": "为什么重要（50字以内）",
       "summary": "2-6段中文摘要，按议题组织",
       "core_points": ["3-7条核心观点，每条一句话"],
       "key_facts": ["关键事实/数据/数字"],
       "takeaways": ["读者可带走的要点"],
       "guests": ["嘉宾姓名及身份"],
       "topics": ["涉及的主题标签"],
       "tensions": ["争议点或对立观点"],
       "quote": "最值得引用的一句话（原文+中文翻译）",
       "importance_score": 1-10,
       "content_density": "low|medium|high",
       "quality": "trae_agent_validated"
     }
   }
   ```
5. **内容要求**：中文摘要，按议题组织段落，数字/公司名/人名必须来自字幕原文（不编造）
6. **验证**：每写完 3 条，运行：
   ```
   python d:\Users\AS\Desktop\podcast-distill\scripts\backfill\validate_summary_outputs.py --platform youtube --item-id youtube:<video_id>
   ```
   如果 validate 失败，修复 summary.json 后重新验证，直到通过
7. **循环**：继续处理下一批 3 条，直到该月所有条目处理完毕。每 3 条汇报一次进度。

## 本月背景提示

10月是 Q3 财报季开始、IMF/世行年会、诺贝尔奖季。
```

---

## 窗口 5：2025-11（11月）— 165条

```
## 前置说明（每个窗口通用）

所有 YouTube 字幕已提取完毕，`export_summary_jobs` 已导出所有月份的 `request.json` + `prompt.md`。
- 任务目录：`d:\Users\AS\Desktop\podcast-distill\backfill\summary_jobs\youtube\<video_id>\request.json`
- 字幕位置：`d:\Users\AS\Desktop\podcast-distill\backfill\items\youtube\<video_id>\transcript.txt`
- 输出位置：`d:\Users\AS\Desktop\podcast-distill\backfill\items\youtube\<video_id>\summary.json`

每个窗口负责一个固定月份，只处理该月内还没有 `summary.json` 的条目。
每批 3 条，写完运行 `validate`，验证通过后继续下一批，直到该月清空。

## 本窗口任务

Phase E: 处理 YouTube 2025-11 月份的单集摘要。
该月共 165 条，全部未处理。

## 工作流

对每个未处理的 video_id，严格按以下步骤执行：

1. **筛选本月份条目**：列出 `summary_jobs\youtube\` 下所有子目录，读取每个 `request.json`，检查 `report_date` 是否为 `2025-11-xx`
2. **跳过已完成**：检查 `backfill\items\youtube\<video_id>\summary.json` 是否已存在，存在则跳过
3. **读取输入**：
   - 读 `request.json` → 获取 item_id、source_name、title、report_date、transcript_sha256、url 等元数据
   - 读 `transcript.txt` → 获取完整字幕文本
4. **生成 summary.json**：写入 `backfill\items\youtube\<video_id>\summary.json`，结构如下：
   ```json
   {
     "schema_version": 1,
     "item_id": "youtube:<video_id>",
     "metadata": { /* 从 request.json 完整复制所有 metadata 字段 */ },
     "generation": {
       "script": "trae_agent",
       "model": "trae_agent",
       "quality": "trae_agent_validated"
     },
     "digest": {
       "short_title": "简短中文标题（10字以内）",
       "one_liner": "一句话概括（30字以内）",
       "why_it_matters": "为什么重要（50字以内）",
       "summary": "2-6段中文摘要，按议题组织",
       "core_points": ["3-7条核心观点，每条一句话"],
       "key_facts": ["关键事实/数据/数字"],
       "takeaways": ["读者可带走的要点"],
       "guests": ["嘉宾姓名及身份"],
       "topics": ["涉及的主题标签"],
       "tensions": ["争议点或对立观点"],
       "quote": "最值得引用的一句话（原文+中文翻译）",
       "importance_score": 1-10,
       "content_density": "low|medium|high",
       "quality": "trae_agent_validated"
     }
   }
   ```
5. **内容要求**：中文摘要，按议题组织段落，数字/公司名/人名必须来自字幕原文（不编造）
6. **验证**：每写完 3 条，运行：
   ```
   python d:\Users\AS\Desktop\podcast-distill\scripts\backfill\validate_summary_outputs.py --platform youtube --item-id youtube:<video_id>
   ```
   如果 validate 失败，修复 summary.json 后重新验证，直到通过
7. **循环**：继续处理下一批 3 条，直到该月所有条目处理完毕。每 3 条汇报一次进度。

## 本月背景提示

11月是美国中期选举后续、G20 峰会、感恩节消费季。
```

---

## 窗口 6：2025-12（12月）— 143条

```
## 前置说明（每个窗口通用）

所有 YouTube 字幕已提取完毕，`export_summary_jobs` 已导出所有月份的 `request.json` + `prompt.md`。
- 任务目录：`d:\Users\AS\Desktop\podcast-distill\backfill\summary_jobs\youtube\<video_id>\request.json`
- 字幕位置：`d:\Users\AS\Desktop\podcast-distill\backfill\items\youtube\<video_id>\transcript.txt`
- 输出位置：`d:\Users\AS\Desktop\podcast-distill\backfill\items\youtube\<video_id>\summary.json`

每个窗口负责一个固定月份，只处理该月内还没有 `summary.json` 的条目。
每批 3 条，写完运行 `validate`，验证通过后继续下一批，直到该月清空。

## 本窗口任务

Phase E: 处理 YouTube 2025-12 月份的单集摘要。
该月共 143 条，全部未处理。

## 工作流

对每个未处理的 video_id，严格按以下步骤执行：

1. **筛选本月份条目**：列出 `summary_jobs\youtube\` 下所有子目录，读取每个 `request.json`，检查 `report_date` 是否为 `2025-12-xx`
2. **跳过已完成**：检查 `backfill\items\youtube\<video_id>\summary.json` 是否已存在，存在则跳过
3. **读取输入**：
   - 读 `request.json` → 获取 item_id、source_name、title、report_date、transcript_sha256、url 等元数据
   - 读 `transcript.txt` → 获取完整字幕文本
4. **生成 summary.json**：写入 `backfill\items\youtube\<video_id>\summary.json`，结构如下：
   ```json
   {
     "schema_version": 1,
     "item_id": "youtube:<video_id>",
     "metadata": { /* 从 request.json 完整复制所有 metadata 字段 */ },
     "generation": {
       "script": "trae_agent",
       "model": "trae_agent",
       "quality": "trae_agent_validated"
     },
     "digest": {
       "short_title": "简短中文标题（10字以内）",
       "one_liner": "一句话概括（30字以内）",
       "why_it_matters": "为什么重要（50字以内）",
       "summary": "2-6段中文摘要，按议题组织",
       "core_points": ["3-7条核心观点，每条一句话"],
       "key_facts": ["关键事实/数据/数字"],
       "takeaways": ["读者可带走的要点"],
       "guests": ["嘉宾姓名及身份"],
       "topics": ["涉及的主题标签"],
       "tensions": ["争议点或对立观点"],
       "quote": "最值得引用的一句话（原文+中文翻译）",
       "importance_score": 1-10,
       "content_density": "low|medium|high",
       "quality": "trae_agent_validated"
     }
   }
   ```
5. **内容要求**：中文摘要，按议题组织段落，数字/公司名/人名必须来自字幕原文（不编造）
6. **验证**：每写完 3 条，运行：
   ```
   python d:\Users\AS\Desktop\podcast-distill\scripts\backfill\validate_summary_outputs.py --platform youtube --item-id youtube:<video_id>
   ```
   如果 validate 失败，修复 summary.json 后重新验证，直到通过
7. **循环**：继续处理下一批 3 条，直到该月所有条目处理完毕。每 3 条汇报一次进度。

## 本月背景提示

12月是年度回顾季、市场年终总结、美联储 12 月议息。
```

---

## 窗口 7：2026-01（1月）— 148条

```
## 前置说明（每个窗口通用）

所有 YouTube 字幕已提取完毕，`export_summary_jobs` 已导出所有月份的 `request.json` + `prompt.md`。
- 任务目录：`d:\Users\AS\Desktop\podcast-distill\backfill\summary_jobs\youtube\<video_id>\request.json`
- 字幕位置：`d:\Users\AS\Desktop\podcast-distill\backfill\items\youtube\<video_id>\transcript.txt`
- 输出位置：`d:\Users\AS\Desktop\podcast-distill\backfill\items\youtube\<video_id>\summary.json`

每个窗口负责一个固定月份，只处理该月内还没有 `summary.json` 的条目。
每批 3 条，写完运行 `validate`，验证通过后继续下一批，直到该月清空。

## 本窗口任务

Phase E: 处理 YouTube 2026-01 月份的单集摘要。
该月共 148 条，全部未处理。

## 工作流

对每个未处理的 video_id，严格按以下步骤执行：

1. **筛选本月份条目**：列出 `summary_jobs\youtube\` 下所有子目录，读取每个 `request.json`，检查 `report_date` 是否为 `2026-01-xx`
2. **跳过已完成**：检查 `backfill\items\youtube\<video_id>\summary.json` 是否已存在，存在则跳过
3. **读取输入**：
   - 读 `request.json` → 获取 item_id、source_name、title、report_date、transcript_sha256、url 等元数据
   - 读 `transcript.txt` → 获取完整字幕文本
4. **生成 summary.json**：写入 `backfill\items\youtube\<video_id>\summary.json`，结构如下：
   ```json
   {
     "schema_version": 1,
     "item_id": "youtube:<video_id>",
     "metadata": { /* 从 request.json 完整复制所有 metadata 字段 */ },
     "generation": {
       "script": "trae_agent",
       "model": "trae_agent",
       "quality": "trae_agent_validated"
     },
     "digest": {
       "short_title": "简短中文标题（10字以内）",
       "one_liner": "一句话概括（30字以内）",
       "why_it_matters": "为什么重要（50字以内）",
       "summary": "2-6段中文摘要，按议题组织",
       "core_points": ["3-7条核心观点，每条一句话"],
       "key_facts": ["关键事实/数据/数字"],
       "takeaways": ["读者可带走的要点"],
       "guests": ["嘉宾姓名及身份"],
       "topics": ["涉及的主题标签"],
       "tensions": ["争议点或对立观点"],
       "quote": "最值得引用的一句话（原文+中文翻译）",
       "importance_score": 1-10,
       "content_density": "low|medium|high",
       "quality": "trae_agent_validated"
     }
   }
   ```
5. **内容要求**：中文摘要，按议题组织段落，数字/公司名/人名必须来自字幕原文（不编造）
6. **验证**：每写完 3 条，运行：
   ```
   python d:\Users\AS\Desktop\podcast-distill\scripts\backfill\validate_summary_outputs.py --platform youtube --item-id youtube:<video_id>
   ```
   如果 validate 失败，修复 summary.json 后重新验证，直到通过
7. **循环**：继续处理下一批 3 条，直到该月所有条目处理完毕。每 3 条汇报一次进度。

## 本月背景提示

1月是新年展望、CES 科技展、达沃斯论坛、Q4 财报季开始。
```

---

## 窗口 8：2026-02（2月）— 140条

```
## 前置说明（每个窗口通用）

所有 YouTube 字幕已提取完毕，`export_summary_jobs` 已导出所有月份的 `request.json` + `prompt.md`。
- 任务目录：`d:\Users\AS\Desktop\podcast-distill\backfill\summary_jobs\youtube\<video_id>\request.json`
- 字幕位置：`d:\Users\AS\Desktop\podcast-distill\backfill\items\youtube\<video_id>\transcript.txt`
- 输出位置：`d:\Users\AS\Desktop\podcast-distill\backfill\items\youtube\<video_id>\summary.json`

每个窗口负责一个固定月份，只处理该月内还没有 `summary.json` 的条目。
每批 3 条，写完运行 `validate`，验证通过后继续下一批，直到该月清空。

## 本窗口任务

Phase E: 处理 YouTube 2026-02 月份的单集摘要。
该月共 140 条，全部未处理。

## 工作流

对每个未处理的 video_id，严格按以下步骤执行：

1. **筛选本月份条目**：列出 `summary_jobs\youtube\` 下所有子目录，读取每个 `request.json`，检查 `report_date` 是否为 `2026-02-xx`
2. **跳过已完成**：检查 `backfill\items\youtube\<video_id>\summary.json` 是否已存在，存在则跳过
3. **读取输入**：
   - 读 `request.json` → 获取 item_id、source_name、title、report_date、transcript_sha256、url 等元数据
   - 读 `transcript.txt` → 获取完整字幕文本
4. **生成 summary.json**：写入 `backfill\items\youtube\<video_id>\summary.json`，结构如下：
   ```json
   {
     "schema_version": 1,
     "item_id": "youtube:<video_id>",
     "metadata": { /* 从 request.json 完整复制所有 metadata 字段 */ },
     "generation": {
       "script": "trae_agent",
       "model": "trae_agent",
       "quality": "trae_agent_validated"
     },
     "digest": {
       "short_title": "简短中文标题（10字以内）",
       "one_liner": "一句话概括（30字以内）",
       "why_it_matters": "为什么重要（50字以内）",
       "summary": "2-6段中文摘要，按议题组织",
       "core_points": ["3-7条核心观点，每条一句话"],
       "key_facts": ["关键事实/数据/数字"],
       "takeaways": ["读者可带走的要点"],
       "guests": ["嘉宾姓名及身份"],
       "topics": ["涉及的主题标签"],
       "tensions": ["争议点或对立观点"],
       "quote": "最值得引用的一句话（原文+中文翻译）",
       "importance_score": 1-10,
       "content_density": "low|medium|high",
       "quality": "trae_agent_validated"
     }
   }
   ```
5. **内容要求**：中文摘要，按议题组织段落，数字/公司名/人名必须来自字幕原文（不编造）
6. **验证**：每写完 3 条，运行：
   ```
   python d:\Users\AS\Desktop\podcast-distill\scripts\backfill\validate_summary_outputs.py --platform youtube --item-id youtube:<video_id>
   ```
   如果 validate 失败，修复 summary.json 后重新验证，直到通过
7. **循环**：继续处理下一批 3 条，直到该月所有条目处理完毕。每 3 条汇报一次进度。

## 本月背景提示

2月是超级碗、中国春节消费数据、Q4 财报季高峰。
```

---

## 窗口 9：2026-03（3月）— 159条

```
## 前置说明（每个窗口通用）

所有 YouTube 字幕已提取完毕，`export_summary_jobs` 已导出所有月份的 `request.json` + `prompt.md`。
- 任务目录：`d:\Users\AS\Desktop\podcast-distill\backfill\summary_jobs\youtube\<video_id>\request.json`
- 字幕位置：`d:\Users\AS\Desktop\podcast-distill\backfill\items\youtube\<video_id>\transcript.txt`
- 输出位置：`d:\Users\AS\Desktop\podcast-distill\backfill\items\youtube\<video_id>\summary.json`

每个窗口负责一个固定月份，只处理该月内还没有 `summary.json` 的条目。
每批 3 条，写完运行 `validate`，验证通过后继续下一批，直到该月清空。

## 本窗口任务

Phase E: 处理 YouTube 2026-03 月份的单集摘要。
该月共 159 条，全部未处理。

## 工作流

对每个未处理的 video_id，严格按以下步骤执行：

1. **筛选本月份条目**：列出 `summary_jobs\youtube\` 下所有子目录，读取每个 `request.json`，检查 `report_date` 是否为 `2026-03-xx`
2. **跳过已完成**：检查 `backfill\items\youtube\<video_id>\summary.json` 是否已存在，存在则跳过
3. **读取输入**：
   - 读 `request.json` → 获取 item_id、source_name、title、report_date、transcript_sha256、url 等元数据
   - 读 `transcript.txt` → 获取完整字幕文本
4. **生成 summary.json**：写入 `backfill\items\youtube\<video_id>\summary.json`，结构如下：
   ```json
   {
     "schema_version": 1,
     "item_id": "youtube:<video_id>",
     "metadata": { /* 从 request.json 完整复制所有 metadata 字段 */ },
     "generation": {
       "script": "trae_agent",
       "model": "trae_agent",
       "quality": "trae_agent_validated"
     },
     "digest": {
       "short_title": "简短中文标题（10字以内）",
       "one_liner": "一句话概括（30字以内）",
       "why_it_matters": "为什么重要（50字以内）",
       "summary": "2-6段中文摘要，按议题组织",
       "core_points": ["3-7条核心观点，每条一句话"],
       "key_facts": ["关键事实/数据/数字"],
       "takeaways": ["读者可带走的要点"],
       "guests": ["嘉宾姓名及身份"],
       "topics": ["涉及的主题标签"],
       "tensions": ["争议点或对立观点"],
       "quote": "最值得引用的一句话（原文+中文翻译）",
       "importance_score": 1-10,
       "content_density": "low|medium|high",
       "quality": "trae_agent_validated"
     }
   }
   ```
5. **内容要求**：中文摘要，按议题组织段落，数字/公司名/人名必须来自字幕原文（不编造）
6. **验证**：每写完 3 条，运行：
   ```
   python d:\Users\AS\Desktop\podcast-distill\scripts\backfill\validate_summary_outputs.py --platform youtube --item-id youtube:<video_id>
   ```
   如果 validate 失败，修复 summary.json 后重新验证，直到通过
7. **循环**：继续处理下一批 3 条，直到该月所有条目处理完毕。每 3 条汇报一次进度。

## 本月背景提示

3月是两会、NVIDIA GTC、银行股压力测试、Q1 收官。
```

---

## 窗口 10：2026-04（4月）— 152条

```
## 前置说明（每个窗口通用）

所有 YouTube 字幕已提取完毕，`export_summary_jobs` 已导出所有月份的 `request.json` + `prompt.md`。
- 任务目录：`d:\Users\AS\Desktop\podcast-distill\backfill\summary_jobs\youtube\<video_id>\request.json`
- 字幕位置：`d:\Users\AS\Desktop\podcast-distill\backfill\items\youtube\<video_id>\transcript.txt`
- 输出位置：`d:\Users\AS\Desktop\podcast-distill\backfill\items\youtube\<video_id>\summary.json`

每个窗口负责一个固定月份，只处理该月内还没有 `summary.json` 的条目。
每批 3 条，写完运行 `validate`，验证通过后继续下一批，直到该月清空。

## 本窗口任务

Phase E: 处理 YouTube 2026-04 月份的单集摘要。
该月共 152 条，全部未处理。

## 工作流

对每个未处理的 video_id，严格按以下步骤执行：

1. **筛选本月份条目**：列出 `summary_jobs\youtube\` 下所有子目录，读取每个 `request.json`，检查 `report_date` 是否为 `2026-04-xx`
2. **跳过已完成**：检查 `backfill\items\youtube\<video_id>\summary.json` 是否已存在，存在则跳过
3. **读取输入**：
   - 读 `request.json` → 获取 item_id、source_name、title、report_date、transcript_sha256、url 等元数据
   - 读 `transcript.txt` → 获取完整字幕文本
4. **生成 summary.json**：写入 `backfill\items\youtube\<video_id>\summary.json`，结构如下：
   ```json
   {
     "schema_version": 1,
     "item_id": "youtube:<video_id>",
     "metadata": { /* 从 request.json 完整复制所有 metadata 字段 */ },
     "generation": {
       "script": "trae_agent",
       "model": "trae_agent",
       "quality": "trae_agent_validated"
     },
     "digest": {
       "short_title": "简短中文标题（10字以内）",
       "one_liner": "一句话概括（30字以内）",
       "why_it_matters": "为什么重要（50字以内）",
       "summary": "2-6段中文摘要，按议题组织",
       "core_points": ["3-7条核心观点，每条一句话"],
       "key_facts": ["关键事实/数据/数字"],
       "takeaways": ["读者可带走的要点"],
       "guests": ["嘉宾姓名及身份"],
       "topics": ["涉及的主题标签"],
       "tensions": ["争议点或对立观点"],
       "quote": "最值得引用的一句话（原文+中文翻译）",
       "importance_score": 1-10,
       "content_density": "low|medium|high",
       "quality": "trae_agent_validated"
     }
   }
   ```
5. **内容要求**：中文摘要，按议题组织段落，数字/公司名/人名必须来自字幕原文（不编造）
6. **验证**：每写完 3 条，运行：
   ```
   python d:\Users\AS\Desktop\podcast-distill\scripts\backfill\validate_summary_outputs.py --platform youtube --item-id youtube:<video_id>
   ```
   如果 validate 失败，修复 summary.json 后重新验证，直到通过
7. **循环**：继续处理下一批 3 条，直到该月所有条目处理完毕。每 3 条汇报一次进度。

## 本月背景提示

4月是关税大限后续、Q1 财报季、IMF 春季会议。
```

---

## 窗口 11：2026-05（5月）— 174条

```
## 前置说明（每个窗口通用）

所有 YouTube 字幕已提取完毕，`export_summary_jobs` 已导出所有月份的 `request.json` + `prompt.md`。
- 任务目录：`d:\Users\AS\Desktop\podcast-distill\backfill\summary_jobs\youtube\<video_id>\request.json`
- 字幕位置：`d:\Users\AS\Desktop\podcast-distill\backfill\items\youtube\<video_id>\transcript.txt`
- 输出位置：`d:\Users\AS\Desktop\podcast-distill\backfill\items\youtube\<video_id>\summary.json`

每个窗口负责一个固定月份，只处理该月内还没有 `summary.json` 的条目。
每批 3 条，写完运行 `validate`，验证通过后继续下一批，直到该月清空。

## 本窗口任务

Phase E: 处理 YouTube 2026-05 月份的单集摘要。
该月共 174 条，全部未处理。

## 工作流

对每个未处理的 video_id，严格按以下步骤执行：

1. **筛选本月份条目**：列出 `summary_jobs\youtube\` 下所有子目录，读取每个 `request.json`，检查 `report_date` 是否为 `2026-05-xx`
2. **跳过已完成**：检查 `backfill\items\youtube\<video_id>\summary.json` 是否已存在，存在则跳过
3. **读取输入**：
   - 读 `request.json` → 获取 item_id、source_name、title、report_date、transcript_sha256、url 等元数据
   - 读 `transcript.txt` → 获取完整字幕文本
4. **生成 summary.json**：写入 `backfill\items\youtube\<video_id>\summary.json`，结构如下：
   ```json
   {
     "schema_version": 1,
     "item_id": "youtube:<video_id>",
     "metadata": { /* 从 request.json 完整复制所有 metadata 字段 */ },
     "generation": {
       "script": "trae_agent",
       "model": "trae_agent",
       "quality": "trae_agent_validated"
     },
     "digest": {
       "short_title": "简短中文标题（10字以内）",
       "one_liner": "一句话概括（30字以内）",
       "why_it_matters": "为什么重要（50字以内）",
       "summary": "2-6段中文摘要，按议题组织",
       "core_points": ["3-7条核心观点，每条一句话"],
       "key_facts": ["关键事实/数据/数字"],
       "takeaways": ["读者可带走的要点"],
       "guests": ["嘉宾姓名及身份"],
       "topics": ["涉及的主题标签"],
       "tensions": ["争议点或对立观点"],
       "quote": "最值得引用的一句话（原文+中文翻译）",
       "importance_score": 1-10,
       "content_density": "low|medium|high",
       "quality": "trae_agent_validated"
     }
   }
   ```
5. **内容要求**：中文摘要，按议题组织段落，数字/公司名/人名必须来自字幕原文（不编造）
6. **验证**：每写完 3 条，运行：
   ```
   python d:\Users\AS\Desktop\podcast-distill\scripts\backfill\validate_summary_outputs.py --platform youtube --item-id youtube:<video_id>
   ```
   如果 validate 失败，修复 summary.json 后重新验证，直到通过
7. **循环**：继续处理下一批 3 条，直到该月所有条目处理完毕。每 3 条汇报一次进度。

## 本月背景提示

5月是伯克希尔股东大会、Google I/O、微软 Build、贸易谈判关键期。
```

---

## 窗口 12：2026-06（6月）— 142条

```
## 前置说明（每个窗口通用）

所有 YouTube 字幕已提取完毕，`export_summary_jobs` 已导出所有月份的 `request.json` + `prompt.md`。
- 任务目录：`d:\Users\AS\Desktop\podcast-distill\backfill\summary_jobs\youtube\<video_id>\request.json`
- 字幕位置：`d:\Users\AS\Desktop\podcast-distill\backfill\items\youtube\<video_id>\transcript.txt`
- 输出位置：`d:\Users\AS\Desktop\podcast-distill\backfill\items\youtube\<video_id>\summary.json`

每个窗口负责一个固定月份，只处理该月内还没有 `summary.json` 的条目。
每批 3 条，写完运行 `validate`，验证通过后继续下一批，直到该月清空。

## 本窗口任务

Phase E: 处理 YouTube 2026-06 月份的单集摘要。
该月共 142 条，全部未处理。

## 工作流

对每个未处理的 video_id，严格按以下步骤执行：

1. **筛选本月份条目**：列出 `summary_jobs\youtube\` 下所有子目录，读取每个 `request.json`，检查 `report_date` 是否为 `2026-06-xx`
2. **跳过已完成**：检查 `backfill\items\youtube\<video_id>\summary.json` 是否已存在，存在则跳过
3. **读取输入**：
   - 读 `request.json` → 获取 item_id、source_name、title、report_date、transcript_sha256、url 等元数据
   - 读 `transcript.txt` → 获取完整字幕文本
4. **生成 summary.json**：写入 `backfill\items\youtube\<video_id>\summary.json`，结构如下：
   ```json
   {
     "schema_version": 1,
     "item_id": "youtube:<video_id>",
     "metadata": { /* 从 request.json 完整复制所有 metadata 字段 */ },
     "generation": {
       "script": "trae_agent",
       "model": "trae_agent",
       "quality": "trae_agent_validated"
     },
     "digest": {
       "short_title": "简短中文标题（10字以内）",
       "one_liner": "一句话概括（30字以内）",
       "why_it_matters": "为什么重要（50字以内）",
       "summary": "2-6段中文摘要，按议题组织",
       "core_points": ["3-7条核心观点，每条一句话"],
       "key_facts": ["关键事实/数据/数字"],
       "takeaways": ["读者可带走的要点"],
       "guests": ["嘉宾姓名及身份"],
       "topics": ["涉及的主题标签"],
       "tensions": ["争议点或对立观点"],
       "quote": "最值得引用的一句话（原文+中文翻译）",
       "importance_score": 1-10,
       "content_density": "low|medium|high",
       "quality": "trae_agent_validated"
     }
   }
   ```
5. **内容要求**：中文摘要，按议题组织段落，数字/公司名/人名必须来自字幕原文（不编造）
6. **验证**：每写完 3 条，运行：
   ```
   python d:\Users\AS\Desktop\podcast-distill\scripts\backfill\validate_summary_outputs.py --platform youtube --item-id youtube:<video_id>
   ```
   如果 validate 失败，修复 summary.json 后重新验证，直到通过
7. **循环**：继续处理下一批 3 条，直到该月所有条目处理完毕。每 3 条汇报一次进度。

## 本月背景提示

6月是 Q2 收官、苹果 WWDC、美联储半年度国会听证、上半年回顾。
```

---

## 所有窗口完成后的收尾操作

逐个窗口跑完后，在主窗口运行以下命令做月度归一化和日报构建：

```bash
# 逐月验证并归一化（--write-normalized 会写入标准化文件）
python scripts\backfill\validate_summary_outputs.py --platform youtube --month 2025-07 --write-normalized
python scripts\backfill\validate_summary_outputs.py --platform youtube --month 2025-08 --write-normalized
python scripts\backfill\validate_summary_outputs.py --platform youtube --month 2025-09 --write-normalized
python scripts\backfill\validate_summary_outputs.py --platform youtube --month 2025-10 --write-normalized
python scripts\backfill\validate_summary_outputs.py --platform youtube --month 2025-11 --write-normalized
python scripts\backfill\validate_summary_outputs.py --platform youtube --month 2025-12 --write-normalized
python scripts\backfill\validate_summary_outputs.py --platform youtube --month 2026-01 --write-normalized
python scripts\backfill\validate_summary_outputs.py --platform youtube --month 2026-02 --write-normalized
python scripts\backfill\validate_summary_outputs.py --platform youtube --month 2026-03 --write-normalized
python scripts\backfill\validate_summary_outputs.py --platform youtube --month 2026-04 --write-normalized
python scripts\backfill\validate_summary_outputs.py --platform youtube --month 2026-05 --write-normalized
python scripts\backfill\validate_summary_outputs.py --platform youtube --month 2026-06 --write-normalized

# 构建日报视图
python scripts\backfill\build_daily_views.py --month 2025-07
# ... 逐月执行 ...

# 渲染日报（可选 --limit-days 先预览前 3 天）
python scripts\backfill\render_daily.py --month 2025-07 --limit-days 3
# ... 逐月执行 ...
```
