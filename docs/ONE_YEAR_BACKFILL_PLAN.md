# 过去一年播客 / YouTube 历史回填方案

> 用途：交给 Workbuddy 分阶段执行。本文只定义方案，不修改现有日报代码。
>
> 默认范围：按当前 `config/sources_by_category.md` 中的 41 个来源（小宇宙 13 个、YouTube 28 个），回填北京时间 `2025-06-28 06:00:00`（含）到 `2026-06-28 06:00:00`（不含）的全部符合条件内容。

## 1. 先定四条原则

1. **先盘点，后下载，最后总结和发布。** 没有完整目录清单前，不开始大规模字幕提取。
2. **历史回填与现有日报隔离。** 不直接循环现有日报脚本，也不改动当前每日自动任务；历史任务放在独立 `backfill/` 目录。
3. **以节目 ID 为唯一键，以日期为视图。** 字幕只保存一份；日报目录只引用节目，不复制全文。
4. **每一步可断点续跑。** 成功文件永不重复下载，失败任务有状态、错误类型和下次重试时间。

## 2. 为什么不能直接把现有日报跑 365 次

现有 `scripts/collect_daily_items.py` 适合“今天看最近更新”，不适合历史扫描：

- YouTube 默认每个来源只扫描最新 25 条。旧日期通常已经不在这 25 条里。
- 小宇宙当前从栏目网页的 `episodes` 字段读取；网页首屏数据不保证覆盖一整年。
- 因此，把 `--date` 从旧到新循环会产生“任务成功但历史条目漏掉”的假完整结果。

正确方法是：**每个来源只做一次向后分页的完整盘点，得到一年节目清单；再按发布日期分配到 365 个日报窗口。**

YouTube 盘点应使用 uploads playlist / 指定 playlist 的 `playlistItems.list`，每页 50 条，持续读取 `nextPageToken`，直到最旧条目的发布时间早于范围起点。该接口和 `videos.list` 当前均为每次 1 quota unit；不要用昂贵且不适合完整枚举的搜索接口。官方参考：

- <https://developers.google.com/youtube/v3/docs/playlistItems/list>
- <https://developers.google.com/youtube/v3/docs/videos/list>
- <https://developers.google.com/youtube/v3/determine_quota_cost>

## 3. 日期口径

沿用当前日报规则：日报日期 `D` 覆盖北京时间：

```text
[D-1 日 06:00:00, D 日 06:00:00)
```

本次一年范围对应的日报文件是：

```text
2025-06-29 至 2026-06-28（共 365 个日窗口）
```

节目归属日期的计算规则：

```text
report_date = date(published_at 转北京时间 - 6 小时) + 1 天
```

任何代码、数据库和飞书文档都必须使用同一规则，禁止按 UTC 日期或自然日零点分桶。

## 4. 推荐目录

```text
podcast-distill/
├─ config/                              # 现有线上日报配置，不在回填阶段改动
├─ scripts/                             # 现有线上日报脚本，不在第一阶段改动
├─ backfill/                            # 历史回填的全部数据和状态
│  ├─ README.md                         # 实际运行命令、机器环境、恢复方法
│  ├─ config/
│  │  ├─ backfill.yaml                  # 时间范围、并发、限速、输出策略
│  │  └─ sources.yaml                   # 41 个来源的稳定 ID 和发现方式
│  ├─ state/
│  │  ├─ backfill.sqlite                # 唯一任务状态库
│  │  ├─ run_status.json                # 给人看的当前进度快照
│  │  └─ feishu_map.json                # 日期与飞书 node/doc token 映射
│  ├─ catalog/
│  │  ├─ items.jsonl                    # 一年节目总清单，一行一条
│  │  ├─ source_audit.json              # 每个来源的覆盖范围和数量
│  │  └─ duplicates.json                # 跨来源/跨平台疑似重复项
│  ├─ items/
│  │  ├─ youtube/<video_id>/
│  │  │  ├─ metadata.json
│  │  │  ├─ transcript.vtt
│  │  │  ├─ transcript.txt
│  │  │  ├─ extraction.json
│  │  │  └─ summary.json
│  │  └─ xiaoyuzhou/<episode_id>/
│  │     ├─ metadata.json
│  │     ├─ transcript.srt
│  │     ├─ transcript.txt
│  │     ├─ extraction.json
│  │     └─ summary.json
│  ├─ daily/YYYY/YYYY-MM/YYYY-MM-DD/
│  │  ├─ items.json                     # 当日节目 ID 与相对路径引用
│  │  ├─ digest.json                    # 结构化日报
│  │  ├─ digest.md                      # 飞书发布前的人类可读稿
│  │  └─ manifest.json                  # 完整性、失败数、内容 hash
│  ├─ temp/                             # 临时音频；成功转写后删除
│  ├─ failures/
│  │  ├─ retryable.jsonl                # 可重试失败
│  │  └─ terminal.jsonl                 # 删除/私密/无权限等终止失败
│  └─ logs/YYYY-MM-DD/                  # 每次批处理日志
└─ scripts/backfill/                    # 后续新增的历史专用脚本
   ├─ inventory.py                      # 只枚举节目，不抓字幕
   ├─ extract_batch.py                  # 按任务队列抓字幕/ASR
   ├─ validate_transcripts.py           # 完整性校验
   ├─ build_daily_views.py              # 按 06:00 边界分桶
   ├─ summarize_batch.py                # 单集摘要缓存
   ├─ render_daily.py                   # 由单集摘要生成日报
   └─ publish_backfill.py               # 飞书层级、upsert、回读验证
```

### 文件夹设计说明

- `items/` 是内容真源：一个节目一个目录，目录名只用稳定 ID，不用标题，避免 Windows 非法字符和超长路径。
- `daily/` 是日期视图：只引用 `items/`，不复制字幕。
- `state/` 决定能否恢复：程序不能靠“文件似乎存在”猜任务状态。
- `temp/` 只放音频中间文件，转写并验证成功后立即删除，不长期保存视频或音频。
- `reports/` 和 `subtitles/` 继续服务现有日报；历史数据不要混进去。

## 5. 两个配置文件怎么写

### `backfill/config/backfill.yaml`

```yaml
schema_version: 1
timezone: Asia/Shanghai
coverage_start: "2025-06-28T06:00:00+08:00"
coverage_end: "2026-06-28T06:00:00+08:00"
window_end_hour: 6

inventory:
  page_size: 50
  stop_when_older_than_start: true

extraction:
  youtube_concurrency: 1
  xiaoyuzhou_concurrency: 2
  asr_concurrency: 1
  batch_size: 10
  max_attempts: 3
  youtube_delay_seconds: [5, 15]
  keep_temporary_audio: false

quality:
  minimum_transcript_coverage: 0.95
  minimum_text_chars: 200
  require_transcript_for_duration_seconds: 300

publish:
  enabled: false
  notify_each_day: false
  notify_each_month: true
  skip_empty_days: true
  verify_after_write: true
```

### `backfill/config/sources.yaml`

由当前分类配置生成，但必须补齐稳定的平台标识：

```yaml
- source_id: yt_the_interview_nyt
  platform: youtube
  category: 新闻 / 时评 / 全球议题
  name: The Interview - New York Times
  source_url: https://www.youtube.com/playlist?list=...
  discovery:
    kind: youtube_playlist
    playlist_id: "..."
  min_duration_seconds: 0
  enabled: true

- source_id: xyz_42zhangjing
  platform: xiaoyuzhou
  category: 科技 / AI / VC
  name: 42章经
  source_url: https://www.xiaoyuzhoufm.com/podcast/...
  discovery:
    kind: rss
    rss_url: "待核验"
    fallback: xiaoyuzhou_paginated_api
  min_duration_seconds: 0
  enabled: true
```

小宇宙来源优先为每个栏目核验 RSS 地址；RSS 不完整时才使用可分页的栏目接口。**不能只抓栏目网页首屏。**

默认沿用当前配置中的 `min_duration` 过滤规则。如果“全部”意味着连短视频也要收录，需要在正式盘点前显式把这些过滤值设为 0。

## 6. 单集元数据标准

`metadata.json` 至少包含：

```json
{
  "schema_version": 1,
  "item_id": "youtube:GNPDXbpaXlE",
  "platform": "youtube",
  "platform_id": "GNPDXbpaXlE",
  "source_id": "yt_the_interview_nyt",
  "category": "新闻 / 时评 / 全球议题",
  "title": "原始标题",
  "url": "原始链接",
  "published_at": "2026-06-27T20:45:01+08:00",
  "report_date": "2026-06-28",
  "duration_seconds": 3127,
  "language": "en",
  "discovered_at": "ISO-8601",
  "metadata_refreshed_at": "ISO-8601"
}
```

`extraction.json` 至少包含：

```json
{
  "status": "success",
  "method": "native_caption",
  "language": "en-orig",
  "attempts": 1,
  "duration_seconds": 3127,
  "last_timestamp_seconds": 3126.6,
  "coverage_ratio": 0.999,
  "text_chars": 48691,
  "sha256": "...",
  "completed_at": "ISO-8601",
  "error_type": null,
  "error_message": null
}
```

允许的状态只用固定枚举：

```text
pending / running / success / retryable / blocked / terminal
```

禁止把“命令退出码为 0”直接当作完整字幕成功；必须通过覆盖率和文本长度校验。

## 7. 爬取策略

### YouTube：API 只负责完整节目清单

1. 频道 URL 先解析为 uploads playlist；配置本身是 playlist 时直接使用。
2. `playlistItems.list(maxResults=50)` 向后分页。
3. 当一整页最旧发布时间早于范围起点后才停止。
4. 收集 video ID 后，每 50 个调用一次 `videos.list` 补全时长、状态等元数据。
5. 以 `youtube:<video_id>` 去重；同一视频出现在多个 playlist 时只保存一份，记录所有来源关系。

不要用官方 captions download 作为第三方公开视频字幕方案：官方接口要求调用者有编辑该视频的权限。参考：<https://developers.google.com/youtube/v3/docs/captions/download>

字幕提取顺序：

```text
已有成功文件
→ 原始人工字幕
→ 自动字幕
→ 下载临时音频并本地 ASR
→ 失败队列
```

历史字幕提取应从你的本地住宅网络运行。如果 Workbuddy 实际在云端执行，换平台并不会消除 YouTube 对云机房 IP 的限制。

遇到 `429`、bot challenge 或登录验证时：立即暂停整个 YouTube 队列并冷却，不要并发重试或连续撞站。恢复后从数据库中的未完成任务继续。

### 小宇宙：RSS / 分页清单与转录分开

1. 为 13 个栏目逐个核验 RSS URL，完整读取范围内 enclosure、GUID、发布时间和时长。
2. RSS 被截断或没有一年历史时，改走可分页的栏目接口。
3. 以 `xiaoyuzhou:<episode_id>` 或稳定 GUID 去重。
4. 优先获取官方逐字稿；没有逐字稿时使用 RSS enclosure 的音频做本地 ASR。
5. 只在 `temp/` 暂存音频，字幕验证后删除。

## 8. 完整性与去重

每个来源盘点完成后生成审计项：

```json
{
  "source_id": "...",
  "status": "complete",
  "oldest_seen": "...",
  "newest_seen": "...",
  "items_in_range": 123,
  "pages_fetched": 4,
  "stop_reason": "older_than_start",
  "failures": []
}
```

总盘点只有同时满足以下条件才叫 `complete`：

- 41 个来源全部有审计结果；
- 每个来源都明确记录停止原因；
- 节目 ID 无重复；
- 最早/最晚日期经过抽查；
- 每月、每平台、每来源的数量统计已生成。

跨平台同一期节目不要物理删除。保留两个原始记录，并写入 `canonical_group_id`；日报渲染时可合并展示，防止同一访谈同时来自 YouTube 和播客 RSS 时重复总结。

## 9. 摘要如何省钱

把模型调用拆成两层：

1. **单集摘要只生成一次**，写入 `items/.../summary.json`，带 `transcript_sha256`。字幕 hash 不变就绝不重新总结。
2. **日报只读取单集摘要**，不再把所有完整字幕重新喂给模型。

`summary.json` 建议保留：一句结论、3—7 条要点、关键事实、人物与机构、适用边界、证据时间戳、推荐等级。日报层只做排序、去重和跨节目主题归纳。

全文字幕必须完整保存在本地，但默认不把全部逐字稿上传飞书。飞书放“基于完整字幕生成的结构化摘要 + 原始链接”，既省空间，也降低大量转载第三方全文的权限和版权风险。

## 10. 飞书知识库结构

不要把 365 篇日报全部堆在知识库根目录。建议：

```text
🎧 播客蒸馏室
└─ 📚 过去一年历史回填
   ├─ 回填说明与进度
   ├─ 2025
   │  ├─ 2025-06
   │  │  ├─ 2025-06-29 播客与视频日报
   │  │  └─ 2025-06-30 播客与视频日报
   │  ├─ 2025-07
   │  └─ ...
   └─ 2026
      ├─ 2026-01
      └─ 2026-06
```

年节点和月节点本身就是索引文档：

- 年页：月份、节目总数、YouTube/小宇宙数量、完成状态。
- 月页：每天的链接、条数、失败数、缺失字幕数；没有更新的日期在表里标 0，不创建空日报。
- 日页：沿用现有日报版式，增加“覆盖窗口”和“完整性状态”。

飞书发布必须是 **upsert**：

- `feishu_map.json` 保存 `report_date -> node_token/doc_token/content_hash`。
- 同一日期已存在且 hash 相同：跳过。
- 日期已存在但 hash 改变：更新原文档，不新建重复节点。
- 每批最多发布 10 篇，逐篇回读验证后再标记成功。
- 历史回填不逐日群通知；每完成一个月只发一次汇总通知。

现有 `publish_feishu.py` 目前适合把日报放在根目录。正式回填前，需要另写 `publish_backfill.py`，或给现有脚本增加 `parent_node_token`、`upsert`、`no_notify` 和回读验证能力；第一阶段不要贸然改线上发布逻辑。

## 11. 合规和安全边界

- 只归档你有权处理的内容；飞书知识库应保持私有，不向外公开第三方完整字幕。
- YouTube Data API 的非授权 API 数据通常需要在 30 天内删除或刷新；元数据表要保留 `metadata_refreshed_at` 并设计刷新任务。官方政策：<https://developers.google.com/youtube/terms/developer-policies>
- 不长期保存 YouTube 视频/音频；ASR 临时文件完成后删除。
- API key、Cookie、飞书 secret 只能来自环境变量或本机密钥文件，不写入 YAML、日志、Markdown 或 Git。
- 此前已经在聊天中出现过的飞书密钥建议轮换。

## 12. 分阶段执行与验收

### 阶段 A：只搭架子

- 创建 `backfill/` 目录、配置样例、SQLite schema 和命令入口。
- 不访问 YouTube/小宇宙，不下载任何内容，不发布飞书。

验收：空库可初始化；重复初始化不报错；线上日报不受影响。

### 阶段 B：两源试跑

- 选 1 个高频 YouTube 源和 1 个小宇宙源。
- 盘点至少 90 天，证明真的支持向后分页，不是只读最新 25 条。
- 各抽取 3 条字幕，并故意中断一次后恢复。

验收：无重复；中断可续；成功任务不重做；失败有固定错误类型。

### 阶段 C：41 源完整盘点

- 只生成节目总清单和来源审计，不抓字幕。
- 先把准确总量、总时长、按月数量和预计 ASR 数量报给你。

验收：41/41 来源有审计记录，才能进入下一阶段。

### 阶段 D：字幕批处理

- 每批 10 条，YouTube 单并发。
- 优先字幕，缺字幕才 ASR。
- 每批结束更新数据库、JSON 进度快照和失败队列。

验收：所有超过 5 分钟的条目要么通过完整性校验，要么有明确终止原因；不能静默缺失。

### 阶段 E：单集摘要与日报

- 先缓存单集结构化摘要，再生成日期视图。
- 先渲染一个月供人工抽查，确认风格后再批量生成剩余月份。

验收：数字和引述可追溯到字幕时间戳；日报条数与当天 `items.json` 一致。

### 阶段 F：飞书灰度发布

- 先创建历史回填根节点、年节点和一个月节点。
- 先发布 3 篇日报，验证层级、格式、upsert 和回读。
- 确认后按月发布，月完成才通知。

验收：重复运行不产生重复页面；本地 hash 与飞书映射一致；日报层级正确。

## 13. 给 Workbuddy 的执行提示词

不要一次把全年任务全交给它。每轮只给一个阶段，并要求它停在验收点。

### 第一轮：搭架子

```text
你正在 D:\桌面\A自媒体账号\podcast-distill 工作。
先完整阅读 docs/ONE_YEAR_BACKFILL_PLAN.md。
本轮只执行“阶段 A：只搭架子”。不要联网抓取，不要下载字幕，不要调用模型，不要发布飞书，也不要修改现有 daily workflow 和现有 scripts。
新代码只能放 scripts/backfill，新数据只能放 backfill。
所有写文件操作必须可重复执行。完成后运行最小测试，并列出新增文件、测试结果和仍未完成事项，然后停止，等待确认。
```

### 第二轮：两源试跑

```text
阅读 docs/ONE_YEAR_BACKFILL_PLAN.md 和当前 backfill/README.md。
本轮只执行阶段 B。选择 1 个高频 YouTube 源和 1 个小宇宙源，盘点最近 90 天并证明分页跨过最新 25 条；每个平台只抽取 3 条字幕。
禁止开始 41 源全量任务，禁止总结，禁止写飞书。遇到 YouTube bot challenge 或 429，立即暂停 YouTube 队列并记录 checkpoint，不要连续重试。
完成后输出：两个来源的节目数、最早/最晚日期、分页数、字幕成功/失败数、恢复测试结果，然后停止。
```

### 第三轮：完整盘点

```text
本轮只执行阶段 C：盘点 config/sources_by_category.md 中当前 41 个来源在 2025-06-28 06:00+08:00 至 2026-06-28 06:00+08:00 的节目清单。
YouTube 必须分页到早于起点；小宇宙必须使用已核验 RSS 或分页接口，禁止只读网页首屏。
只生成 catalog、source_audit 和统计，不抓字幕、不总结、不发布飞书。
只有 41/41 来源都有明确 stop_reason 才能报告 complete，否则报告 partial 和具体缺口。完成后停止等待确认。
```

### 后续轮次

字幕、摘要和飞书分别执行阶段 D、E、F；每轮都明确“禁止自动进入下一阶段”。笨一点的 agent 并不可怕，最怕的是一口气给它全年权限还不设刹车。

## 14. 最终完成标准

- 当前 41 个来源的一年历史清单可审计。
- 每条节目有稳定 ID、发布日期、日报日期和来源关系。
- 每条长内容有完整字幕或明确失败原因。
- 任务可中断、可恢复、可重跑且不重复。
- 单集摘要只付费生成一次；日报不重复读取全文。
- 飞书按年/月/日组织，同日 upsert，不产生重复页面。
- 本地全文、飞书摘要、发布映射和状态库彼此可核对。

