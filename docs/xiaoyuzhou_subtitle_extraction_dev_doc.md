# 小宇宙播客字幕提取服务开发文档

## 1. 项目目标

开发一个专门处理小宇宙播客的媒体解析与字幕转写服务，供 GitHub Actions 定时调用。

服务端负责：

- 扫描小宇宙播客信源。
- 判断指定日报窗口内是否有新 episode。
- 解析 episode 的真实音频地址 `audio_url`。
- 下载音频并在服务端完成 ASR 转写。
- 生成完整真实逐字稿、SRT、VTT、元数据和日报采集产物。
- 对相同 episode 做缓存，避免重复下载和重复 ASR。

GitHub Actions 只负责：

- 定时触发。
- 调用本服务 API。
- 轮询任务状态。
- 下载 `daily_items.json`、`manifest.json`、`subtitles_bundle.zip`。
- 校验 `text_chars`、`sha256`、`coverage_ratio`。
- 校验通过后再生成日报和发布飞书。

GitHub Actions 不负责：

- 不解析小宇宙页面。
- 不下载小宇宙音频。
- 不运行 ASR。
- 不根据标题、简介、章节用大模型补写字幕。

## 2. 核心原则

1. 字幕必须来自真实音频 ASR。
2. 不允许用大模型根据标题、简介、摘要、时间线补写逐字稿。
3. 5 分钟以上内容必须有完整逐字稿。
4. 逐字稿必须可校验：
   - `text_chars > 0`
   - `sha256` 可本地复算一致
   - `coverage_ratio >= 0.95`
5. ASR 失败、字幕缺失或校验失败时，下游不得发布日报。
6. 服务必须支持长任务异步处理，不能让 HTTP 请求一直阻塞。

## 3. 推荐技术栈

后端 API：

- Python 3.11+
- FastAPI
- Pydantic
- requests 或 httpx

任务队列：

- 简单版本：SQLite + 后台 worker 轮询
- 稳定版本：PostgreSQL / Supabase / Redis Queue / Celery

音频处理：

- FFmpeg

ASR：

- 首选：faster-whisper
- CPU 或轻量部署可选：whisper.cpp
- 也可保留 OpenAI Whisper 开源仓库作为参考，但不要把 OpenAI API Key 作为必需项

存储：

- 本地磁盘、S3、Supabase Storage、Cloudflare R2 均可
- 必须能通过 API 下载最终文件

## 4. 参考 GitHub 项目

ASR / 语音识别：

- faster-whisper: https://github.com/SYSTRAN/faster-whisper
- whisper.cpp: https://github.com/ggml-org/whisper.cpp
- OpenAI Whisper 开源模型: https://github.com/openai/whisper

音频处理：

- FFmpeg: https://github.com/ffmpeg/ffmpeg
- pydub: https://github.com/jiaaro/pydub

Web API：

- FastAPI: https://github.com/fastapi/fastapi
- Pydantic: https://github.com/pydantic/pydantic

HTTP / RSS：

- requests: https://github.com/psf/requests
- httpx: https://github.com/encode/httpx
- feedparser: https://github.com/kurtmckee/feedparser

任务队列 / Edge：

- Celery: https://github.com/celery/celery
- Supabase Edge Runtime: https://github.com/supabase/edge-runtime

## 5. 信源配置要求

必须内置一个默认 profile：

```text
xiaoyuzhou-default
```

该 profile 包含 13 个小宇宙播客信源。

建议配置文件格式：

```json
{
  "profiles": {
    "xiaoyuzhou-default": [
      {
        "source_name": "晚点聊 LateTalk",
        "platform": "xiaoyuzhou",
        "source_url": "https://www.xiaoyuzhoufm.com/podcast/61933ace1b4320461e91fd55"
      }
    ]
  }
}
```

服务必须支持：

- 小宇宙 podcast 主页 URL。
- 小宇宙 episode 单集 URL。
- 从 podcast 主页或 RSS 中展开 episode 列表。
- 用 `published_at` 判断 episode 是否在日报窗口内。

## 6. 日报窗口规则

只传 `date` 时，服务端自动计算北京时间窗口：

```text
window_start = D-1 06:00:00+08:00
window_end   = D   06:00:00+08:00
```

示例：

```text
date = 2026-07-01
window_start = 2026-06-30T06:00:00+08:00
window_end   = 2026-07-01T06:00:00+08:00
```

边界规则：

- `published_at >= window_start`
- `published_at < window_end`

## 7. API 设计

### 7.1 Base URL

示例：

```text
https://backend.appmiaoda.com/projects/supabase330558257305272320/functions/v1
```

实际部署时可以换成开发者自己的公网域名。

### 7.2 鉴权

除健康检查外，所有接口都需要：

```http
Authorization: Bearer <API_TOKEN>
Content-Type: application/json
```

不要把 token 写死在代码里，必须通过环境变量配置。

### 7.3 健康检查

```http
GET /health
```

响应：

```json
{
  "status": "ok",
  "service": "xiaoyuzhou-transcript-service",
  "version": "v1"
}
```

### 7.4 创建日报采集任务

```http
POST /daily-collect
```

最小请求体：

```json
{
  "date": "2026-07-01"
}
```

完整请求体：

```json
{
  "date": "2026-07-01",
  "sources_profile": "xiaoyuzhou-default",
  "window_start": "2026-06-30T06:00:00+08:00",
  "window_end": "2026-07-01T06:00:00+08:00",
  "require_transcripts": true,
  "allow_asr": true
}
```

说明：

- `date` 必填。
- `sources_profile` 可选，默认必须是 `xiaoyuzhou-default`。
- `window_start` / `window_end` 可选，不传则由 `date` 自动推算。
- `require_transcripts` 默认 `true`。
- `allow_asr` 默认 `true`。

响应：

```json
{
  "job_id": "daily_035d3818a629",
  "status": "queued",
  "created_at": "2026-07-01T09:37:14.000Z"
}
```

### 7.5 查询日报任务状态

```http
GET /daily-collect/{job_id}
```

响应示例：

```json
{
  "job_id": "daily_035d3818a629",
  "status": "running",
  "date": "2026-07-01",
  "window_start": "2026-06-30T06:00:00+08:00",
  "window_end": "2026-07-01T06:00:00+08:00",
  "sources_profile": "xiaoyuzhou-default",
  "source_count": 13,
  "item_count": 5,
  "success_count": 3,
  "no_update_count": 7,
  "failure_count": 0,
  "progress": {
    "message": "processing 3/5",
    "total": 5,
    "finished": 3
  },
  "files": null,
  "error_type": null,
  "error_message": null
}
```

状态值：

```text
queued
running
success
failed
```

失败时必须提供：

```json
{
  "error_type": "asr_failed",
  "error_message": "human readable reason"
}
```

### 7.6 下载日报产物

任务 `status=success` 后必须支持：

```http
GET /daily-collect/{job_id}/files/daily_items.json
GET /daily-collect/{job_id}/files/manifest.json
GET /daily-collect/{job_id}/files/subtitles_bundle.zip
```

## 8. 单条 episode 提取 API

### 8.1 创建单条任务

```http
POST /media-extract
```

请求体：

```json
{
  "url": "https://www.xiaoyuzhoufm.com/episode/6a0a624de9161a38ce31ba3f",
  "language": "zh"
}
```

响应：

```json
{
  "job_id": "job_abc123def456",
  "status": "queued"
}
```

### 8.2 查询单条任务

```http
GET /media-extract/{job_id}
```

成功响应：

```json
{
  "job_id": "job_abc123def456",
  "status": "success",
  "platform": "xiaoyuzhou",
  "title": "165: GEAR 高深远：世界模型、自进化循环、DreamDojo",
  "source_name": "晚点聊 LateTalk",
  "published_at": "2026-05-18T00:45:00+08:00",
  "duration_seconds": 6543,
  "audio_url": "https://media.xyzcdn.net/xxx.mp3",
  "text_chars": 123456,
  "sha256": "txt_utf8_sha256",
  "last_timestamp_seconds": 6530,
  "coverage_ratio": 0.998,
  "source_method": "asr",
  "files": {
    "transcript_txt": "/media-extract/job_abc123def456/files/transcript.txt",
    "transcript_srt": "/media-extract/job_abc123def456/files/transcript.srt",
    "transcript_vtt": "/media-extract/job_abc123def456/files/transcript.vtt",
    "metadata_json": "/media-extract/job_abc123def456/files/metadata.json",
    "extraction_json": "/media-extract/job_abc123def456/files/extraction.json",
    "bundle_zip": "/media-extract/job_abc123def456/files/bundle.zip"
  }
}
```

### 8.3 下载单条产物

```http
GET /media-extract/{job_id}/files/transcript.txt
GET /media-extract/{job_id}/files/transcript.srt
GET /media-extract/{job_id}/files/transcript.vtt
GET /media-extract/{job_id}/files/metadata.json
GET /media-extract/{job_id}/files/extraction.json
GET /media-extract/{job_id}/files/bundle.zip
```

## 9. daily_items.json 格式

`daily_items.json` 必须是数组。

有更新且转写成功：

```json
{
  "platform": "xiaoyuzhou",
  "source_name": "晚点聊 LateTalk",
  "source_url": "https://www.xiaoyuzhoufm.com/podcast/61933ace1b4320461e91fd55",
  "title": "165: GEAR 高深远：世界模型、自进化循环、DreamDojo",
  "url": "https://www.xiaoyuzhoufm.com/episode/6a0a624de9161a38ce31ba3f",
  "published_at": "2026-05-18T00:45:00+08:00",
  "duration_seconds": 6543,
  "audio_url": "https://media.xyzcdn.net/xxx.mp3",
  "description": "episode description",
  "transcript_status": "success"
}
```

无更新：

```json
{
  "platform": "xiaoyuzhou",
  "source_name": "硅谷101",
  "source_url": "https://www.xiaoyuzhoufm.com/podcast/xxxx",
  "title": "",
  "url": "",
  "published_at": "",
  "duration_seconds": 0,
  "transcript_status": "no_update",
  "note": "该频道在本时间窗口内没有新发布的节目"
}
```

转写失败：

```json
{
  "platform": "xiaoyuzhou",
  "source_name": "某播客",
  "source_url": "https://www.xiaoyuzhoufm.com/podcast/xxxx",
  "title": "episode title",
  "url": "https://www.xiaoyuzhoufm.com/episode/xxxx",
  "published_at": "2026-07-01T01:00:00+08:00",
  "duration_seconds": 3600,
  "transcript_status": "failed",
  "error_type": "asr_failed",
  "error_message": "ASR failed after retries"
}
```

## 10. manifest.json 格式

```json
{
  "status": "success",
  "date": "2026-07-01",
  "window_start": "2026-06-30T06:00:00+08:00",
  "window_end": "2026-07-01T06:00:00+08:00",
  "sources_profile": "xiaoyuzhou-default",
  "source_count": 13,
  "item_count": 5,
  "success_count": 5,
  "no_update_count": 8,
  "failure_count": 0,
  "sources_summary": [
    {
      "source_name": "晚点聊 LateTalk",
      "source_url": "https://www.xiaoyuzhoufm.com/podcast/61933ace1b4320461e91fd55",
      "episode_count": 1,
      "status": "updated"
    },
    {
      "source_name": "硅谷101",
      "source_url": "https://www.xiaoyuzhoufm.com/podcast/xxxx",
      "episode_count": 0,
      "status": "no_update"
    }
  ],
  "errors": []
}
```

要求：

- 如果 `failure_count > 0`，`status` 不应该是 `success`，除非明确支持 `partial_failed` 并且下游知道如何处理。
- 推荐日报任务只在所有需要转写的 episode 成功时返回 `success`。

## 11. subtitles_bundle.zip 格式

压缩包根目录必须包含：

```text
subtitles/
  xiaoyuzhou_{episode_id}.txt
  xiaoyuzhou_{episode_id}.srt
  xiaoyuzhou_{episode_id}.vtt
  xiaoyuzhou_{episode_id}.json
```

每个 `xiaoyuzhou_{episode_id}.json` 必须包含：

```json
{
  "platform": "xiaoyuzhou",
  "episode_id": "6a0a624de9161a38ce31ba3f",
  "url": "https://www.xiaoyuzhoufm.com/episode/6a0a624de9161a38ce31ba3f",
  "title": "165: GEAR 高深远：世界模型、自进化循环、DreamDojo",
  "source_name": "晚点聊 LateTalk",
  "audio_url": "https://media.xyzcdn.net/xxx.mp3",
  "text": "xiaoyuzhou_6a0a624de9161a38ce31ba3f.txt",
  "subtitle_srt": "xiaoyuzhou_6a0a624de9161a38ce31ba3f.srt",
  "subtitle_vtt": "xiaoyuzhou_6a0a624de9161a38ce31ba3f.vtt",
  "text_chars": 123456,
  "sha256": "txt_utf8_sha256",
  "duration_seconds": 6543,
  "last_timestamp_seconds": 6530,
  "coverage_ratio": 0.998,
  "source": "asr",
  "language": "zh"
}
```

`sha256` 计算规则：

```python
sha256 = hashlib.sha256(txt_content.encode("utf-8")).hexdigest()
```

`coverage_ratio` 推荐计算规则：

```python
coverage_ratio = min(last_timestamp_seconds / duration_seconds, 1.0)
```

## 12. ASR 质量要求

必须做到：

- 支持 1 到 3 小时长音频。
- 支持中文普通话为主，允许夹杂英文术语。
- 输出纯文字 `.txt`。
- 输出带时间轴 `.srt`。
- 输出带时间轴 `.vtt`。
- 保留段落顺序。
- 不要把静音段幻想成内容。
- 不要重复生成“谢谢收听”“欢迎订阅”等不存在的句子。
- 对失败分片进行重试。

推荐 ASR 参数方向：

- 模型：`large-v3` 优先；资源不足可用 `medium`。
- 语言：`zh`。
- temperature：`0`。
- 开启 VAD 或静音过滤。
- 长音频切片处理，切片之间保留少量 overlap。
- 生成每段起止时间，用于 SRT/VTT。

ASR 失败处理：

- 遇到下载失败、网络失败、ASR 失败要重试。
- 遇到限流要排队等待，不要直接永久失败。
- 单条 episode 最多重试 3 次。
- 失败后必须记录 `error_type` 和 `error_message`。

## 13. 缓存与幂等

必须支持幂等：

- 同一个 episode URL 重复提交，不重复 ASR。
- 如果已有成功产物，直接返回已有 job 或创建一个指向缓存结果的新 job。
- 缓存 key 建议使用规范化 episode URL：

```text
xiaoyuzhou:{episode_id}
```

建议保存：

- episode metadata
- audio_url
- audio file sha256，可选
- transcript txt/srt/vtt
- extraction json
- created_at
- updated_at
- ASR backend/version/model

## 14. 错误类型建议

```text
invalid_request
unauthorized
invalid_sources_profile
source_resolve_failed
episode_resolve_failed
audio_url_missing
audio_download_failed
asr_rate_limited
asr_failed
coverage_too_low
storage_upload_failed
internal_error
```

失败响应示例：

```json
{
  "job_id": "job_abc123",
  "status": "failed",
  "error_type": "asr_rate_limited",
  "error_message": "ASR backend returned rate limit; job will be retried",
  "retryable": true
}
```

## 15. 环境变量

```text
API_TOKEN=your-token
JOBS_DIR=/data/jobs
DATABASE_URL=postgresql://...
STORAGE_BUCKET=media-outputs
ASR_BACKEND=faster-whisper
WHISPER_MODEL=large-v3
ASR_DEVICE=cuda
ASR_COMPUTE_TYPE=float16
MAX_CONCURRENT_ASR=1
HTTP_TIMEOUT_SECONDS=60
DOWNLOAD_TIMEOUT_SECONDS=600
```

如果没有 GPU：

```text
ASR_DEVICE=cpu
ASR_COMPUTE_TYPE=int8
WHISPER_MODEL=medium
```

## 16. 最小验收测试

### 16.1 健康检查

```bash
curl -i "$BASE/health"
```

必须返回 200。

### 16.2 单条 episode 测试

```bash
curl -X POST "$BASE/media-extract" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.xiaoyuzhoufm.com/episode/6a0a624de9161a38ce31ba3f","language":"zh"}'
```

然后轮询：

```bash
curl "$BASE/media-extract/{job_id}" \
  -H "Authorization: Bearer $TOKEN"
```

成功标准：

- `status = success`
- 有 `audio_url`
- 有 `text_chars`
- 有 `sha256`
- 有 `duration_seconds`
- 有 `last_timestamp_seconds`
- `coverage_ratio >= 0.95`
- 可下载：
  - `transcript.txt`
  - `transcript.srt`
  - `transcript.vtt`
  - `metadata.json`
  - `extraction.json`

### 16.3 日报采集测试

```bash
curl -X POST "$BASE/daily-collect" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"date":"2026-07-01"}'
```

成功标准：

- `source_count = 13`
- 能区分有更新和无更新频道
- 有更新 episode 被转写
- 无更新频道写入 `transcript_status=no_update`
- 任务完成后能下载：
  - `daily_items.json`
  - `manifest.json`
  - `subtitles_bundle.zip`

### 16.4 产物校验

解压：

```bash
unzip subtitles_bundle.zip -d .
```

对每个 `subtitles/*.json` 校验：

- `text` 指向的 txt 文件存在。
- `sha256` 与 txt 内容本地复算一致。
- `text_chars` 等于 txt 解码后的字符数。
- `duration_seconds > 0`。
- `last_timestamp_seconds > 0`。
- 5 分钟以上内容 `coverage_ratio >= 0.95`。
- `.srt` 或 `.vtt` 至少存在一个，推荐两个都存在。

Python 校验示例：

```python
import hashlib
import json
from pathlib import Path

for meta_path in Path("subtitles").glob("*.json"):
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    txt_path = Path("subtitles") / meta["text"]
    text = txt_path.read_text(encoding="utf-8")
    assert len(text) == meta["text_chars"]
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == meta["sha256"]
    if meta["duration_seconds"] >= 300:
        assert meta["coverage_ratio"] >= 0.95
```

## 17. GitHub Actions 对接要求

GitHub Actions 只按下面流程工作：

1. 计算或传入 `date`。
2. `POST /daily-collect`，只传 `{"date":"YYYY-MM-DD"}`。
3. 每 10 秒轮询 `GET /daily-collect/{job_id}`。
4. 等 `status=success`。
5. 下载三个产物。
6. 校验产物。
7. 校验通过才生成日报。
8. 校验失败不发布飞书，并上传 artifacts 方便排查。

GitHub Actions 不应该：

- 安装 Whisper。
- 安装 yt-dlp。
- 下载音频。
- 解析小宇宙页面。
- 直接调用 ASR。

## 18. 最终交付物

开发者需要交付：

- 后端服务源码。
- `README.md`。
- `.env.example`。
- `requirements.txt` 或 `pyproject.toml`。
- Dockerfile，推荐。
- API 文档。
- 本地启动命令。
- 部署说明。
- 测试脚本。
- 示例产物：
  - `daily_items.json`
  - `manifest.json`
  - `subtitles_bundle.zip`

最终验收标准：

- 单条小宇宙 episode 可完整转写。
- 日报采集可扫描 13 个小宇宙频道。
- 能正确识别日报窗口内更新。
- 能正确返回无更新频道。
- 所有 5 分钟以上 episode 有完整字幕。
- 产物可下载。
- `sha256` 本地复算一致。
- `coverage_ratio >= 0.95`。
- 重复提交同一 episode 不重复 ASR。
- ASR 限流或失败时有排队、重试和明确错误信息。
