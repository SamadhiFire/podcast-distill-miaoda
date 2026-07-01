# Podcast Distill Miaoda

这是 `podcast-distill` 的秒哒接入版。仓库目标是做一个很薄、稳定、可校验的自动化层：GitHub Actions 只负责调度、调用秒哒 API、下载标准产物、校验完整逐字稿，然后基于这些真实字幕生成中文日报并发布到飞书。

## 职责边界

秒哒负责：

- 读取 `sources_profile` 或服务端信源配置。
- 展开 YouTube playlist / channel / uploads。
- 展开小宇宙 podcast，识别日报窗口内真实更新的 episode。
- 解析小宇宙 episode 的真实 `audio_url`。
- 提取 YouTube 官方字幕或自动字幕。
- 没有字幕时在秒哒服务器侧 ASR。
- 对小宇宙音频在秒哒服务器侧 ASR。
- 输出完整真实逐字稿、`daily_items.json`、`manifest.json`、`subtitles_bundle.zip`。
- 缓存结果，避免重复下载和重复转写。

GitHub Actions 负责：

- 定时或手动触发。
- 调用 `POST /daily-collect`。
- 轮询 `GET /daily-collect/{job_id}`。
- 下载 `daily_items.json`、`manifest.json`、`subtitles_bundle.zip`。
- 本地校验 `text_chars`、`sha256`、`coverage_ratio` 和必需字幕覆盖。
- 校验通过后运行 `scripts/generate_daily_report.py`。
- 发布到飞书并上传 artifacts。

GitHub Actions 不再负责：

- 不跑 ASR。
- 不安装 Whisper / whisper.cpp。
- 不调用 `yt-dlp`。
- 不下载 YouTube 或小宇宙音频。
- 不直接抓 YouTube 字幕。
- 不直接解析小宇宙音频链接。

## 正式 workflow

主工作流是 [.github/workflows/daily-digest.yml](.github/workflows/daily-digest.yml)。

触发方式：

- 定时：北京时间每天 06:15，对应 UTC `22:15`。
- 手动：`workflow_dispatch` 支持指定 `date=YYYY-MM-DD`。

日报窗口固定为：

```text
日报日期 D = 北京时间 D-1 06:00:00 到 D 06:00:00
```

例如 `2026-06-30`：

```text
2026-06-29T06:00:00+08:00
2026-06-30T06:00:00+08:00
```

## 必需 Secrets

在 GitHub Repository Settings -> Secrets and variables -> Actions 配置：

```text
MIAODA_API_BASE
MIAODA_API_TOKEN
LLM_BASE_URL
LLM_API_KEY
LLM_MODEL
FEISHU_APP_ID
FEISHU_APP_SECRET
FEISHU_WIKI_SPACE_ID
FEISHU_NOTIFY_WEBHOOK
```

可选：

```text
FEISHU_PARENT_NODE_TOKEN
FEISHU_SORT_DAILY_REPORTS
```

不要把秒哒 token 写入仓库文件。

当前秒哒公网 Edge Function Base URL：

```text
https://backend.appmiaoda.com/projects/supabase330558257305272320/functions/v1
```

## 秒哒产物契约

GitHub Actions 从秒哒下载 3 个文件：

```text
reports/daily_items_YYYY-MM-DD.json
reports/daily_items_YYYY-MM-DD.manifest.json
subtitles_bundle.zip
```

`subtitles_bundle.zip` 解压后必须得到：

```text
subtitles/
  <platform>_<id>.json
  <platform>_<id>.txt
  <platform>_<id>.srt 或 <platform>_<id>.vtt
```

每个 `subtitles/*.json` 至少包含：

```json
{
  "url": "原始媒体链接",
  "text": "xxx.txt",
  "text_chars": 12345,
  "sha256": "xxx.txt 的 UTF-8 sha256",
  "duration_seconds": 1234,
  "last_timestamp_seconds": 1230,
  "coverage_ratio": 0.99,
  "source": "official_caption / auto_caption / asr"
}
```

## 本地脚本

调用秒哒并下载产物：

```bash
python scripts/miaoda_collect_daily.py \
  --date 2026-06-30 \
  --timezone Asia/Shanghai \
  --sources-profile podcast-distill-default \
  --items-json reports/daily_items_2026-06-30.json \
  --manifest-json reports/daily_items_2026-06-30.manifest.json \
  --bundle-path subtitles_bundle.zip \
  --status-json reports/miaoda_collect_2026-06-30.status.json \
  --subtitles-dir subtitles
```

校验秒哒产物：

```bash
python scripts/validate_miaoda_bundle.py \
  --items-json reports/daily_items_2026-06-30.json \
  --manifest-json reports/daily_items_2026-06-30.manifest.json \
  --subtitles-dir subtitles \
  --bundle-zip subtitles_bundle.zip \
  --min-coverage 0.95 \
  --min-duration-seconds 300
```

生成日报：

```bash
python scripts/generate_daily_report.py \
  --date 2026-06-30 \
  --items-json reports/daily_items_2026-06-30.json \
  --subtitles-dir subtitles \
  --require-transcripts \
  --llm-policy required \
  --output reports/daily-2026-06-30.md
```

## 发布保护

以下任一情况会让 workflow 失败，并且不会发布飞书：

- 秒哒任务返回 `failed` 或 `partial_failed`。
- `manifest.json` 不是成功状态。
- `manifest.json` 有 `failure_count` 或 `errors`。
- `subtitles_bundle.zip` 不能解压成 `subtitles/`。
- 5 分钟以上条目缺少逐字稿。
- `sha256` 本地复算不一致。
- `text_chars <= 0` 或与本地文本长度不一致。
- `coverage_ratio < 0.95`。
- 逐字稿来源不是 `official_caption`、`auto_caption` 或 `asr`。

无论成功或失败，workflow 都会上传 artifacts 方便排查。

## 2026-06-30 第一阶段验收

手动触发 workflow，输入：

```text
date = 2026-06-30
```

必须覆盖窗口：

```text
2026-06-29T06:00:00+08:00 到 2026-06-30T06:00:00+08:00
```

并且 `daily_items.json` 和 `subtitles/` 中必须包含并转写成功：

```text
https://www.xiaoyuzhoufm.com/episode/6a41f1212e335a35a80b0159
https://www.xiaoyuzhoufm.com/episode/6a40b830ffcf45052c805d5f
https://www.xiaoyuzhoufm.com/episode/6a412def9d2f5743683f320e
```

这一天的 workflow 会额外校验这 3 个 URL 是否存在。
