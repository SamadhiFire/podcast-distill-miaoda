# GitHub Actions 端到端跑通方案

## 1. 最终原则

GitHub Actions 不跑 ASR。

最终职责划分：

```text
秒哒：
  采集源
  解析 YouTube / 小宇宙
  提取官方字幕 / 自动字幕
  没有字幕时在秒哒服务器侧 ASR
  生成 daily_items.json
  生成 manifest.json
  生成 subtitles_bundle.zip

GitHub Actions：
  定时触发
  调用秒哒 /v1/daily/collect
  轮询任务
  下载产物
  校验产物
  生成日报
  写飞书
  上传 artifacts
```

GitHub Actions 不做：

- 安装 whisper
- 跑 whisper / faster-whisper / whisper.cpp
- 调用 `extract_subtitles.py`
- 用 `yt-dlp` 下载字幕或音频
- 下载小宇宙音频
- 保存浏览器 cookie 作为正式依赖

## 2. 为什么旧 workflow 不能作为最终方案

当前仓库已有 `.github/workflows/daily-digest.yml`，但它是旧方案：

- 它会在 GitHub Actions 中安装 whisper.cpp。
- 它会下载 ASR 模型。
- 它会调用 `extract_subtitles.py`。
- 它仍可能由 GitHub Actions IP 触发 YouTube 风控。
- 它把长音频 ASR 放在 GitHub Actions 里，容易慢和超时。

秒哒接入后的最终 workflow 必须替换这部分，让秒哒直接输出全部文本。

## 3. 秒哒必须输出什么

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
  "platform": "xiaoyuzhou",
  "media_id": "6a40b830ffcf45052c805d5f",
  "title": "170: 【具身季报 26Q2】世界模型大风不停，和不想被贴标签的人",
  "url": "https://www.xiaoyuzhoufm.com/episode/6a40b830ffcf45052c805d5f",
  "language": "zh",
  "source": "miaoda:asr",
  "text": "xiaoyuzhou_6a40b830ffcf45052c805d5f.txt",
  "subtitle_srt": "xiaoyuzhou_6a40b830ffcf45052c805d5f.srt",
  "text_chars": 123456,
  "sha256": "...",
  "duration_seconds": 6830,
  "last_timestamp_seconds": 6828.1,
  "coverage_ratio": 0.9997
}
```

当前 `scripts/generate_daily_report.py` 只读取 `subtitles/*.json` 中的 `url` 和 `text` 字段来定位逐字稿，所以这个扁平格式是硬性要求。

## 4. GitHub Secrets

最终必需：

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

不作为正式依赖：

```text
YTDLP_COOKIES_B64
```

如果秒哒服务器自己需要 YouTube Data API key，应配置在秒哒服务端，不放在这个 GitHub Actions workflow 里。

## 5. 推荐 Workflow

下面是最终方向的 workflow 示例。它不跑 ASR，只调用秒哒。

```yaml
name: Daily Podcast Digest Via Miaoda

on:
  workflow_dispatch:
    inputs:
      date:
        description: "Report date, YYYY-MM-DD. Empty means today in Asia/Shanghai."
        required: false
        type: string
      dry_run_feishu:
        description: "Generate the report but do not publish to Feishu."
        required: false
        default: false
        type: boolean
  schedule:
    - cron: "15 22 * * *"

permissions:
  contents: read

concurrency:
  group: daily-podcast-digest-miaoda
  cancel-in-progress: false

jobs:
  daily-digest:
    runs-on: ubuntu-latest
    timeout-minutes: 360

    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          sudo apt-get update
          sudo apt-get install -y unzip

      - name: Resolve report date
        id: report_date
        shell: bash
        run: |
          if [ -n "${{ github.event.inputs.date }}" ]; then
            REPORT_DATE="${{ github.event.inputs.date }}"
          else
            REPORT_DATE="$(TZ=Asia/Shanghai date +'%Y-%m-%d')"
          fi
          echo "date=$REPORT_DATE" >> "$GITHUB_OUTPUT"
          echo "REPORT_DATE=$REPORT_DATE" >> "$GITHUB_ENV"
          echo "REPORT_PATH=reports/daily-${REPORT_DATE}.md" >> "$GITHUB_ENV"
          echo "ITEMS_PATH=reports/daily_items_${REPORT_DATE}.json" >> "$GITHUB_ENV"
          echo "MANIFEST_PATH=reports/daily_items_${REPORT_DATE}.manifest.json" >> "$GITHUB_ENV"

      - name: Check required secrets
        shell: bash
        run: |
          test -n "${{ secrets.MIAODA_API_BASE }}"
          test -n "${{ secrets.MIAODA_API_TOKEN }}"
          test -n "${{ secrets.LLM_BASE_URL }}"
          test -n "${{ secrets.LLM_MODEL }}"
          test -n "${{ secrets.FEISHU_APP_ID }}"
          test -n "${{ secrets.FEISHU_APP_SECRET }}"
          test -n "${{ secrets.FEISHU_WIKI_SPACE_ID }}"

      - name: Collect and transcribe via Miaoda
        env:
          MIAODA_API_BASE: ${{ secrets.MIAODA_API_BASE }}
          MIAODA_API_TOKEN: ${{ secrets.MIAODA_API_TOKEN }}
        shell: bash
        run: |
          python - <<'PY'
          import json
          import os
          import time
          import zipfile
          from datetime import datetime, timedelta, timezone
          from pathlib import Path
          from urllib.parse import urljoin

          import requests

          base = os.environ["MIAODA_API_BASE"].rstrip("/") + "/"
          token = os.environ["MIAODA_API_TOKEN"]
          report_date = os.environ["REPORT_DATE"]
          headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

          tz = timezone(timedelta(hours=8))
          end = datetime.fromisoformat(report_date).replace(tzinfo=tz, hour=6, minute=0, second=0, microsecond=0)
          start = end - timedelta(days=1)

          body = {
              "date": report_date,
              "timezone": "Asia/Shanghai",
              "window_start": start.isoformat(),
              "window_end": end.isoformat(),
              "sources_profile": "podcast-distill-default",
              "require_transcripts": True,
              "allow_asr": True,
          }
          resp = requests.post(urljoin(base, "v1/daily/collect"), headers=headers, json=body, timeout=30)
          resp.raise_for_status()
          job = resp.json()
          job_id = job["job_id"]

          deadline = time.time() + 5 * 60 * 60
          while True:
              resp = requests.get(urljoin(base, f"v1/daily/collect/{job_id}"), headers=headers, timeout=30)
              resp.raise_for_status()
              status = resp.json()
              state = status.get("status")
              print(json.dumps(status, ensure_ascii=False)[:2000], flush=True)
              if state == "success":
                  break
              if state in {"failed", "partial_failed"}:
                  raise SystemExit(f"Miaoda daily collect failed: {json.dumps(status, ensure_ascii=False)}")
              if time.time() > deadline:
                  raise SystemExit("Miaoda daily collect timed out")
              time.sleep(30)

          files = status["files"]
          Path("reports").mkdir(exist_ok=True)
          Path("subtitles").mkdir(exist_ok=True)

          downloads = {
              os.environ["ITEMS_PATH"]: files["daily_items_json"],
              os.environ["MANIFEST_PATH"]: files["manifest_json"],
              "subtitles_bundle.zip": files["subtitles_bundle_zip"],
          }
          for target, href in downloads.items():
              url = href if href.startswith("http") else urljoin(base, href.lstrip("/"))
              r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=300)
              r.raise_for_status()
              Path(target).write_bytes(r.content)

          with zipfile.ZipFile("subtitles_bundle.zip") as zf:
              zf.extractall(".")
          PY

      - name: Validate Miaoda transcript bundle
        shell: bash
        run: |
          python - <<'PY'
          import hashlib
          import json
          from pathlib import Path

          failures = []
          for meta_path in Path("subtitles").glob("*.json"):
              meta = json.loads(meta_path.read_text(encoding="utf-8"))
              text_name = meta.get("text")
              if not text_name:
                  failures.append(f"{meta_path}: missing text")
                  continue
              text_path = meta_path.with_name(text_name)
              if not text_path.exists():
                  failures.append(f"{meta_path}: missing {text_name}")
                  continue
              data = text_path.read_bytes()
              digest = hashlib.sha256(data).hexdigest()
              if meta.get("sha256") and digest != meta["sha256"]:
                  failures.append(f"{meta_path}: sha256 mismatch")
              if int(meta.get("text_chars") or 0) <= 0:
                  failures.append(f"{meta_path}: text_chars <= 0")
              if float(meta.get("coverage_ratio") or 0) < 0.95:
                  failures.append(f"{meta_path}: coverage_ratio < 0.95")
          if failures:
              raise SystemExit("\n".join(failures))
          PY

      - name: Generate daily report from full transcripts
        env:
          LLM_BASE_URL: ${{ secrets.LLM_BASE_URL }}
          LLM_API_KEY: ${{ secrets.LLM_API_KEY }}
          LLM_MODEL: ${{ secrets.LLM_MODEL }}
          LLM_TIMEOUT: "600"
          LLM_CHUNK_CHARS: "30000"
        run: |
          python scripts/generate_daily_report.py \
            --date "$REPORT_DATE" \
            --items-json "$ITEMS_PATH" \
            --subtitles-dir subtitles \
            --require-transcripts \
            --llm-policy required \
            --llm-max-attempts 3 \
            --output "$REPORT_PATH"

      - name: Install lark-cli
        run: npm install -g @larksuite/cli@1.0.59

      - name: Publish to Feishu Wiki and notify group
        env:
          FEISHU_APP_ID: ${{ secrets.FEISHU_APP_ID }}
          FEISHU_APP_SECRET: ${{ secrets.FEISHU_APP_SECRET }}
          FEISHU_WIKI_SPACE_ID: ${{ secrets.FEISHU_WIKI_SPACE_ID }}
          FEISHU_NOTIFY_WEBHOOK: ${{ secrets.FEISHU_NOTIFY_WEBHOOK }}
        shell: bash
        run: |
          DRY_RUN=""
          if [ "${{ github.event.inputs.dry_run_feishu }}" = "true" ]; then
            DRY_RUN="--dry-run"
          fi
          python scripts/publish_feishu.py \
            --file "$REPORT_PATH" \
            --title "${REPORT_DATE} 播客与视频更新日报" \
            $DRY_RUN

      - name: Upload report artifact
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: daily-digest-${{ steps.report_date.outputs.date }}
          path: |
            ${{ env.REPORT_PATH }}
            reports/daily-${{ steps.report_date.outputs.date }}.json
            ${{ env.ITEMS_PATH }}
            ${{ env.MANIFEST_PATH }}
            subtitles_bundle.zip
            subtitles/
```

## 6. 端到端验收清单

必须同时满足：

- 手动触发 `workflow_dispatch` 可以指定日期。
- 定时触发为北京时间 06:15，即 UTC 22:15。
- `2026-06-30` 测试只包含北京时间 `2026-06-29 06:00` 到 `2026-06-30 06:00` 的内容。
- GitHub Actions 没有安装 whisper。
- GitHub Actions 没有调用 `extract_subtitles.py`。
- GitHub Actions 没有用 `yt-dlp` 下载字幕或音频。
- 秒哒返回 `daily_items.json`、`manifest.json`、`subtitles_bundle.zip`。
- `subtitles/` 中所有 5 分钟以上条目都有 `.json + .txt + .srt/.vtt`。
- `sha256` 本地复算一致。
- `text_chars > 0`。
- `coverage_ratio >= 0.95`。
- `generate_daily_report.py --require-transcripts` 成功。
- 飞书发布步骤成功，且标题为中文正常文本。
- 任一校验失败时不发布飞书。
- 成功或失败都上传 artifacts。

## 7. 阻断条件

出现任一情况，不能宣称 GitHub Actions 已跑通：

- 秒哒只做网页，没有 API。
- 秒哒只返回摘要，没有逐字稿。
- 秒哒没有 `/v1/daily/collect`。
- 秒哒没有输出 `subtitles_bundle.zip`。
- `subtitles_bundle.zip` 不能直接解压成 `subtitles/`。
- GitHub Actions 仍然跑 ASR。
- GitHub Actions 仍然调用 `extract_subtitles.py`。
- GitHub Actions 仍然依赖 `yt-dlp` 抓字幕或音频。
- 没有 `sha256`。
- 没有 `coverage_ratio`。
- 字幕缺失后仍然发布飞书。

## 8. 2026-06-30 必测

请求：

```json
{
  "date": "2026-06-30",
  "timezone": "Asia/Shanghai",
  "window_start": "2026-06-29T06:00:00+08:00",
  "window_end": "2026-06-30T06:00:00+08:00",
  "sources_profile": "podcast-distill-default",
  "require_transcripts": true,
  "allow_asr": true
}
```

必须成功转写这 3 条小宇宙：

```text
https://www.xiaoyuzhoufm.com/episode/6a41f1212e335a35a80b0159
https://www.xiaoyuzhoufm.com/episode/6a40b830ffcf45052c805d5f
https://www.xiaoyuzhoufm.com/episode/6a412def9d2f5743683f320e
```

这一天的 GitHub Actions artifacts 必须包含：

```text
reports/daily_items_2026-06-30.json
reports/daily_items_2026-06-30.manifest.json
subtitles_bundle.zip
subtitles/
reports/daily-2026-06-30.json
reports/daily-2026-06-30.md
```
