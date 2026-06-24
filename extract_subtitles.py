#!/usr/bin/env python3
"""
视频字幕提取工具
支持平台: YouTube, Bilibili, 小宇宙播客
用途: 提取字幕/转录文本，用于总结整理

使用方法:
    # 提取 YouTube 字幕
    python extract_subtitles.py https://www.youtube.com/watch?v=xxxxx

    # 提取 B站字幕
    python extract_subtitles.py https://www.bilibili.com/video/BVxxxxx

    # 提取小宇宙播客
    python extract_subtitles.py https://www.xiaoyuzhoufm.com/episode/xxxxx

    # 指定输出文件
    python extract_subtitles.py <URL> -o output.txt

    # 指定语言 (默认: 中文优先，回退英文)
    python extract_subtitles.py <URL> --lang zh-Hans zh-Hant en

代理设置 (中国大陆访问 YouTube 需要):
    # 方式1: 环境变量
    export HTTPS_PROXY=http://127.0.0.1:7890
    export HTTP_PROXY=http://127.0.0.1:7890

    # 方式2: 命令行参数
    python extract_subtitles.py <URL> --proxy http://127.0.0.1:7890
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse


def extract_youtube_transcript_api(url, languages, proxy=None):
    """方法1: 使用 youtube-transcript-api (推荐，最轻量)"""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        return None, "youtube-transcript-api 未安装，请运行: pip install youtube-transcript-api"

    # 提取 video ID
    video_id = None
    patterns = [
        r'(?:v=|/v/|/embed/|/shorts/|youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            break

    if not video_id:
        return None, f"无法从 URL 提取 YouTube video ID: {url}"

    try:
        # 配置代理
        api = YouTubeTranscriptApi()

        # 列出可用字幕
        transcript_list = api.list(video_id)
        available = []
        for t in transcript_list:
            available.append(f"  {t.language_code} ({'自动生成' if t.is_generated else '手动上传'})")

        # 获取字幕
        transcript = api.fetch(video_id, languages=languages)

        # 格式化输出
        lines = []
        for entry in transcript:
            text = entry.text.strip()
            if text:
                # 将时间戳转换为可读格式
                seconds = int(entry.start)
                minutes = seconds // 60
                hours = minutes // 60
                minutes = minutes % 60
                if hours > 0:
                    timestamp = f"[{hours:02d}:{minutes:02d}:{seconds%60:02d}]"
                else:
                    timestamp = f"[{minutes:02d}:{seconds%60:02d}]"
                lines.append(f"{timestamp} {text}")

        header = f"YouTube 字幕 - {video_id}\n"
        header += f"可用字幕: {', '.join(available)}\n"
        header += "=" * 60 + "\n\n"

        return header + "\n".join(lines), None

    except Exception as e:
        return None, f"youtube-transcript-api 错误: {e}"


def extract_youtube_ytdlp(url, languages, proxy=None):
    """使用 yt-dlp 下载字幕 (YouTube/B站通用 fallback)"""
    try:
        result = subprocess.run(
            ["yt-dlp", "--version"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return None, "yt-dlp 未安装"
    except FileNotFoundError:
        return None, "yt-dlp 未安装，请安装: pip install yt-dlp"

    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = [
            "yt-dlp",
            "--skip-download",
            "--write-sub",
            "--write-auto-sub",
            "--sub-lang", ",".join(languages),
            "--sub-format", "vtt/srt/best",
            "--convert-subs", "srt",
            "-o", os.path.join(tmpdir, "subtitle"),
        ]

        if proxy:
            cmd.extend(["--proxy", proxy])

        # B站需要 cookies，尝试从浏览器获取
        domain = urlparse(url).netloc.lower()
        if 'bilibili.com' in domain or 'b23.tv' in domain:
            for browser in ['chrome', 'edge', 'firefox']:
                cmd_test = cmd + [f"--cookies-from-browser", browser, url]
                try:
                    test = subprocess.run(
                        cmd_test, capture_output=True, text=True, timeout=30
                    )
                    if test.returncode == 0:
                        cmd = cmd_test
                        break
                except Exception:
                    continue

        if "--cookies-from-browser" not in str(cmd):
            cmd.append(url)

        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120,
                encoding='utf-8', errors='replace', env=env
            )

            if result.returncode != 0:
                stderr = result.stderr[:500] if result.stderr else "未知错误"
                return None, f"yt-dlp 错误: {stderr}"

            # 查找生成的字幕文件
            sub_files = list(Path(tmpdir).glob("subtitle*.srt"))
            if not sub_files:
                sub_files = list(Path(tmpdir).glob("subtitle*.vtt"))

            if not sub_files:
                return None, "yt-dlp 未找到字幕文件"

            # 读取并解析字幕
            content = sub_files[0].read_text(encoding='utf-8')
            lines = parse_srt(content)

            header = f"字幕 (yt-dlp)\n"
            header += f"来源: {url}\n"
            header += f"字幕文件: {sub_files[0].name}\n"
            header += "=" * 60 + "\n\n"

            return header + "\n".join(lines), None

        except subprocess.TimeoutExpired:
            return None, "yt-dlp 超时 (120s)"
        except Exception as e:
            return None, f"yt-dlp 错误: {e}"


def parse_srt(content):
    """解析 SRT 字幕文件"""
    lines = []
    blocks = re.split(r'\n\n+', content.strip())

    for block in blocks:
        block_lines = block.strip().split('\n')
        if len(block_lines) >= 3:
            # 第二行是时间戳
            time_line = block_lines[1]
            # 提取开始时间
            match = re.match(r'(\d{2}):(\d{2}):(\d{2})', time_line)
            if match:
                h, m, s = int(match.group(1)), int(match.group(2)), int(match.group(3))
                timestamp = f"[{h:02d}:{m:02d}:{s:02d}]" if h > 0 else f"[{m:02d}:{s:02d}]"

                # 剩余行是字幕文本
                text = ' '.join(block_lines[2:]).strip()
                # 去除 HTML 标签
                text = re.sub(r'<[^>]+>', '', text)
                if text:
                    lines.append(f"{timestamp} {text}")

    return lines


def extract_bilibili(url, languages, proxy=None):
    """提取 B站字幕 (直接调用 B站 API，无需额外依赖)"""
    import requests

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36',
        'Referer': 'https://www.bilibili.com'
    }

    # 解析短链接 b23.tv → 获取真实 BV 号
    if 'b23.tv' in url:
        try:
            resp = requests.head(url, headers=headers, allow_redirects=True, timeout=10)
            url = resp.url
        except Exception:
            pass

    # 提取 BV 号
    match = re.search(r'(BV[a-zA-Z0-9]+)', url)
    if not match:
        return None, f"无法从 URL 提取 BV 号: {url}"
    bv_id = match.group(1)

    # 获取 cid
    try:
        r = requests.get(
            f'https://api.bilibili.com/x/player/pagelist?bvid={bv_id}',
            headers=headers, timeout=10
        )
        pages = r.json().get('data', [])
        if not pages:
            return None, f"找不到视频页面: {bv_id}"
        cid = pages[0]['cid']
    except Exception as e:
        return None, f"获取视频信息失败: {e}"

    # 获取字幕
    try:
        r = requests.get(
            f'https://api.bilibili.com/x/player/v2?bvid={bv_id}&cid={cid}',
            headers=headers, timeout=10
        )
        data = r.json()
        subtitles = data.get('data', {}).get('subtitle', {}).get('subtitles', [])
    except Exception as e:
        return None, f"获取字幕信息失败: {e}"

    if not subtitles:
        # 尝试 yt-dlp fallback (支持 cookies)
        result, error = extract_youtube_ytdlp(url, languages, proxy)
        if result:
            return result.replace("YouTube 字幕", "Bilibili 字幕"), None
        return None, (
            "该视频没有可提取的字幕。\n"
            "提示: B站很多视频需要登录才能获取 AI 生成字幕。\n"
            "可尝试: yt-dlp --cookies-from-browser chrome <URL>"
        )

    # 按语言优先级选择字幕
    lang_priority = ['zh-Hans', 'zh-CN', 'zh-Hant', 'zh-TW', 'zh', 'en', 'ai-zh', 'ai-en']
    chosen = subtitles[0]
    for lang in lang_priority:
        for s in subtitles:
            if s.get('lan', '') == lang:
                chosen = s
                break

    # 下载字幕 JSON
    sub_url = chosen.get('subtitle_url', '')
    if sub_url.startswith('//'):
        sub_url = 'https:' + sub_url

    try:
        r = requests.get(sub_url, headers=headers, timeout=10)
        sub_data = r.json()
    except Exception as e:
        return None, f"下载字幕失败: {e}"

    body = sub_data.get('body', [])
    if not body:
        return None, "字幕内容为空"

    lines = []
    for item in body:
        start = item.get('from', 0)
        text = item.get('content', '').strip()
        if text:
            minutes = int(start) // 60
            seconds = int(start) % 60
            timestamp = f"[{minutes:02d}:{seconds:02d}]"
            lines.append(f"{timestamp} {text}")

    header = f"Bilibili 字幕 - {bv_id}\n"
    header += f"字幕语言: {chosen.get('lan_doc', chosen.get('lan', 'unknown'))}\n"
    header += f"共 {len(lines)} 条字幕\n"
    header += "=" * 60 + "\n\n"

    return header + "\n".join(lines), None


def extract_xiaoyuzhou(url, languages, proxy=None):
    """提取小宇宙播客字幕 (需要 Whisper 转录)"""
    # 小宇宙是音频播客，没有现成字幕，需要语音识别
    # 这里提供两种方案

    print("小宇宙是音频播客，需要语音识别转文字。")
    print("推荐方案:")
    print("1. 使用 whisper (OpenAI 开源): pip install openai-whisper")
    print("2. 使用 faster-whisper: pip install faster-whisper")
    print()

    # 尝试下载音频
    try:
        import requests
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        # 小宇宙页面包含音频 URL
        resp = requests.get(url, headers=headers, timeout=30)
        # 查找音频 URL
        audio_match = re.search(r'"enclosure":\s*\{"url":\s*"([^"]+)"', resp.text)
        if not audio_match:
            audio_match = re.search(r'src="(https://[^"]*\.m4a[^"]*)"', resp.text)

        if audio_match:
            audio_url = audio_match.group(1)
            print(f"找到音频: {audio_url[:100]}...")
            print()
            print("下载音频后运行:")
            print(f"  whisper audio.m4a --language zh --model medium")
            print(f"  或: faster-whisper audio.m4a --language zh --model medium")
            return None, "小宇宙需要语音识别，请先下载音频再用 Whisper 转录"
        else:
            return None, "无法从小宇宙页面提取音频 URL"

    except Exception as e:
        return None, f"小宇宙提取失败: {e}"


def main():
    parser = argparse.ArgumentParser(
        description="视频字幕提取工具 - 支持 YouTube, Bilibili, 小宇宙",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python extract_subtitles.py https://www.youtube.com/watch?v=xxxxx
  python extract_subtitles.py https://www.bilibili.com/video/BVxxxxx -o output.txt
  python extract_subtitles.py <URL> --proxy http://127.0.0.1:7890
  python extract_subtitles.py <URL> --lang en zh-Hans
        """
    )

    parser.add_argument("url", help="视频/播客 URL")
    parser.add_argument("-o", "--output", help="输出文件路径 (默认打印到终端)")
    parser.add_argument("--lang", nargs="+", default=["zh-Hans", "zh-Hant", "zh", "en"],
                        help="字幕语言优先级 (默认: zh-Hans zh-Hant zh en)")
    parser.add_argument("--proxy", help="HTTP 代理地址 (如 http://127.0.0.1:7890)")
    parser.add_argument("--method", choices=["auto", "transcript-api", "ytdlp"],
                        default="auto", help="提取方法 (默认 auto 自动选择)")
    parser.add_argument("--plain", action="store_true",
                        help="纯文本输出 (不带时间戳)")

    args = parser.parse_args()

    # 设置代理
    proxy = args.proxy or os.environ.get('HTTPS_PROXY') or os.environ.get('HTTP_PROXY')
    if proxy:
        os.environ['HTTPS_PROXY'] = proxy
        os.environ['HTTP_PROXY'] = proxy
        print(f"使用代理: {proxy}")

    url = args.url
    domain = urlparse(url).netloc.lower()

    result = None
    error = None

    # 根据平台选择提取方法
    if 'youtube.com' in domain or 'youtu.be' in domain:
        print(f"检测到 YouTube 视频: {url}")

        if args.method in ["auto", "transcript-api"]:
            print("尝试 youtube-transcript-api...")
            result, error = extract_youtube_transcript_api(url, args.lang, proxy)

        if not result and args.method in ["auto", "ytdlp"]:
            print("尝试 yt-dlp...")
            result, error = extract_youtube_ytdlp(url, args.lang, proxy)

    elif 'bilibili.com' in domain or 'b23.tv' in domain:
        print(f"检测到 Bilibili 视频: {url}")
        result, error = extract_bilibili(url, args.lang, proxy)

    elif 'xiaoyuzhoufm.com' in domain:
        print(f"检测到小宇宙播客: {url}")
        result, error = extract_xiaoyuzhou(url, args.lang, proxy)

    else:
        # 通用处理，尝试 yt-dlp
        print(f"尝试使用 yt-dlp 处理: {url}")
        result, error = extract_youtube_ytdlp(url, args.lang, proxy)

    # 输出结果
    if result:
        if args.plain:
            # 去除时间戳
            result = re.sub(r'\[\d{2}:\d{2}(?::\d{2})?\]\s*', '', result)

        if args.output:
            Path(args.output).write_text(result, encoding='utf-8')
            print(f"\n字幕已保存到: {args.output}")
        else:
            print("\n" + result)
    else:
        print(f"\n提取失败: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
