#!/usr/bin/env python3
"""
视频字幕提取工具 - GitHub Actions 版
======================================
支持平台: YouTube, Bilibili
输出格式: SRT (带时间戳) + TXT (纯文本，适合 AI 总结)

使用方法:
  # 单个 URL
  python extract_subtitles.py "https://www.youtube.com/watch?v=xxxxx"

  # 批处理
  python extract_subtitles.py --batch urls.txt

  # 指定语言和输出目录
  python extract_subtitles.py <URL> --lang zh-Hans,en --output subtitles/

策略:
  1. 优先用 yt-dlp 直接下载字幕 (最快，支持 YouTube + B站)
  2. 如果 yt-dlp 获取不到字幕 URL，回退到解析页面 HTML 提取
  3. 输出 SRT + 纯文本两种格式
"""

import argparse
import html
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse


# ── 工具函数 ──────────────────────────────────────────────

def extract_video_id(url):
    """从 YouTube URL 提取 video ID"""
    patterns = [
        r'(?:v=|/v/|/embed/|/shorts/|youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$'
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None


def extract_bvid(url):
    """从 B站 URL 提取 BV 号"""
    m = re.search(r'(BV[a-zA-Z0-9]+)', url)
    return m.group(1) if m else None


def sanitize_filename(name):
    """清理文件名，移除非法字符"""
    return re.sub(r'[<>:"/\\|?*]', '_', name)[:100]


def parse_srt(content):
    """解析 SRT 内容，提取纯文本"""
    blocks = re.split(r'\n\n+', content.strip())
    lines = []
    for block in blocks:
        block_lines = block.strip().split('\n')
        if len(block_lines) >= 3:
            text = ' '.join(block_lines[2:]).strip()
            text = re.sub(r'<[^>]+>', '', text)
            if text:
                lines.append(text)
    return '\n'.join(lines)


def parse_vtt(content):
    """解析 VTT/WebVTT 内容，提取纯文本"""
    lines = []
    for line in content.split('\n'):
        line = line.strip()
        # 跳过元数据行和时间戳
        if not line or line.startswith('WEBVTT') or '-->' in line or line.startswith('NOTE'):
            continue
        # 跳过纯数字（序号）
        if re.match(r'^\d+$', line):
            continue
        # 去除 HTML 标签
        line = re.sub(r'<[^>]+>', '', line)
        # 去除样式标签内容
        line = re.sub(r'\{[^}]*\}', '', line)
        if line:
            lines.append(line)
    return '\n'.join(lines)


# ── 方法1: yt-dlp ────────────────────────────────────────

def extract_via_ytdlp(url, lang, output_dir):
    """
    使用 yt-dlp 下载字幕
    返回: (success: bool, srt_path: str, txt_path: str, video_title: str)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 提取 video ID 用于命名
    domain = urlparse(url).netloc.lower()
    if 'bilibili' in domain or 'b23.tv' in domain:
        vid = extract_bvid(url) or 'bili_video'
    elif 'youtube' in domain or 'youtu.be' in domain:
        vid = extract_video_id(url) or 'yt_video'
    else:
        vid = 'video'

    base = output_dir / vid

    # 尝试下载字幕 (VTT 格式，不转码以减少出错)
    cmd = [
        'yt-dlp',
        '--skip-download',
        '--write-auto-subs',      # 自动生成字幕
        '--write-subs',           # 手动上传字幕
        '--sub-langs', lang,
        '--sub-format', 'vtt',
        '--sleep-requests', '2',
        '--sleep-interval', '3',
        '--max-sleep-interval', '8',
        '--retries', '3',
        '--fragment-retries', '3',
        '-o', str(base),
        url
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=120,
            encoding='utf-8', errors='replace'
        )

        # 查找生成的字幕文件
        sub_files = sorted(Path(output_dir).glob(f"{vid}*vtt"))
        if not sub_files:
            sub_files = sorted(Path(output_dir).glob(f"{vid}*srt"))

        if sub_files:
            vtt_path = sub_files[0]
            vtt_content = vtt_path.read_text(encoding='utf-8', errors='replace')

            # 生成纯文本
            txt_content = parse_vtt(vtt_content)
            txt_path = vtt_path.with_suffix('.txt')
            txt_path.write_text(txt_content, encoding='utf-8')

            # 获取标题
            title = "Unknown"
            for line in result.stdout.split('\n'):
                if 'title' in line.lower():
                    continue
            # 从 yt-dlp 输出获取标题
            output_lines = result.stdout.split('\n') + result.stderr.split('\n')
            for line in output_lines:
                if '[download]' in line and 'Destination' in line:
                    title = line.split('Destination:')[-1].strip()
                    break

            print(f"  ✓ yt-dlp 提取成功: {vtt_path.name}")
            print(f"    纯文本: {txt_path} ({len(txt_content)} 字符)")
            return True, str(vtt_path), str(txt_path), title

        else:
            # 检查 stderr 中是否有线索
            stderr = result.stderr[:300] if result.stderr else ''
            if '429' in stderr:
                print(f"  ⚠ yt-dlp 被限流 (429)，尝试方法2...")
            elif 'no subtitles' in stderr.lower():
                print(f"  ⚠ 该视频没有字幕")
            else:
                print(f"  ⚠ yt-dlp 未找到字幕文件: {stderr[:200]}")
            return False, '', '', ''

    except subprocess.TimeoutExpired:
        print(f"  ⚠ yt-dlp 超时")
        return False, '', '', ''
    except Exception as e:
        print(f"  ⚠ yt-dlp 异常: {e}")
        return False, '', '', ''


# ── 方法2: 直接解析 YouTube 页面 ──────────────────────────

def extract_via_page_parse(url, lang, output_dir):
    """
    直接解析 YouTube 页面 HTML，提取字幕数据
    作为 yt-dlp 的 fallback，适用于限流场景
    """
    try:
        import requests
    except ImportError:
        print("  ⚠ requests 未安装，跳过方法2")
        return False, '', '', ''

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    video_id = extract_video_id(url)
    if not video_id:
        print("  ⚠ 无法提取 video ID")
        return False, '', '', ''

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }

    try:
        # 1. 获取 YouTube 页面
        resp = requests.get(
            f'https://www.youtube.com/watch?v={video_id}',
            headers=headers, timeout=30
        )
        if resp.status_code != 200:
            print(f"  ⚠ 页面请求失败: HTTP {resp.status_code}")
            return False, '', '', ''

        # 2. 提取 ytInitialPlayerResponse
        match = re.search(
            r'var\s+ytInitialPlayerResponse\s*=\s*({.*?});\s*var\s+',
            resp.text, re.DOTALL
        )
        if not match:
            print("  ⚠ 未找到 ytInitialPlayerResponse")
            return False, '', '', ''

        player = json.loads(match.group(1))
        title = player.get('videoDetails', {}).get('title', video_id)

        # 3. 获取字幕 URL
        captions = player.get('captions', {}).get('playerCaptionsTracklistRenderer', {})
        tracks = captions.get('captionTracks', [])

        if not tracks:
            print("  ⚠ 该视频没有字幕")
            return False, '', '', ''

        # 优先选择中文
        lang_priority = [l.strip() for l in lang.split(',')] + ['zh-Hans', 'zh', 'en']
        chosen = None
        for l in lang_priority:
            for t in tracks:
                if t.get('languageCode') == l:
                    chosen = t
                    break
            if chosen:
                break
        if not chosen:
            chosen = tracks[0]

        # 4. 下载字幕 XML
        sub_url = chosen['baseUrl']
        if lang_priority[0] and lang_priority[0] != chosen.get('languageCode'):
            sub_url += f'&tlang={lang_priority[0]}'

        time.sleep(1)
        sub_resp = requests.get(sub_url, headers=headers, timeout=30)
        if sub_resp.status_code != 200:
            print(f"  ⚠ 字幕下载失败: HTTP {sub_resp.status_code}")
            return False, '', '', ''

        xml_content = sub_resp.text

        # 5. 解析字幕
        pattern = r'<text\s+start="([\d.]+)"\s+dur="([\d.]+)"[^>]*>(.*?)</text>'
        matches = re.findall(pattern, xml_content, re.DOTALL)

        srt_lines = []
        plain_lines = []
        idx = 0

        for start_str, dur_str, text in matches:
            start = float(start_str)
            dur = float(dur_str)
            text = html.unescape(text)
            text = re.sub(r'<[^>]+>', '', text).strip()
            if not text:
                continue

            idx += 1
            end = start + dur

            def fmt_t(t):
                h = int(t) // 3600
                m = (int(t) % 3600) // 60
                s = int(t) % 60
                ms = int((t - int(t)) * 1000)
                return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

            srt_lines.append(f"{idx}\n{fmt_t(start)} --> {fmt_t(end)}\n{text}\n")
            plain_lines.append(text)

        if not srt_lines:
            print("  ⚠ 字幕内容为空")
            return False, '', '', ''

        # 6. 保存文件
        base = output_dir / video_id
        srt_path = base.with_suffix('.zh-Hans.srt')
        srt_path.write_text('\n'.join(srt_lines), encoding='utf-8')

        txt_path = base.with_suffix('.txt')
        txt_path.write_text('\n'.join(plain_lines), encoding='utf-8')

        print(f"  ✓ 页面解析提取成功: {srt_path.name}")
        print(f"    纯文本: {txt_path} ({len('\n'.join(plain_lines))} 字符)")
        return True, str(srt_path), str(txt_path), title

    except Exception as e:
        print(f"  ⚠ 页面解析异常: {e}")
        return False, '', '', ''


# ── 主入口 ────────────────────────────────────────────────

def process_url(url, lang, output_dir):
    """处理单个 URL，返回是否成功"""
    print(f"\n{'='*60}")
    print(f"处理: {url}")
    print(f"语言: {lang}")

    # 方法1: yt-dlp
    print("方法1: yt-dlp...")
    ok, srt, txt, title = extract_via_ytdlp(url, lang, output_dir)
    if ok:
        return ok

    # 方法2: 页面解析 (仅 YouTube)
    domain = urlparse(url).netloc.lower()
    if 'youtube' in domain or 'youtu.be' in domain:
        print("方法2: 直接页面解析...")
        ok, srt, txt, title = extract_via_page_parse(url, lang, output_dir)
        if ok:
            return ok

    print(f"  ✗ 所有方法均失败")
    return False


def main():
    parser = argparse.ArgumentParser(
        description='视频字幕提取工具 (YouTube / B站)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python extract_subtitles.py https://www.youtube.com/watch?v=xxxxx
  python extract_subtitles.py --batch urls.txt --output subtitles/
  python extract_subtitles.py <URL> --lang zh-Hans,en
        """
    )
    parser.add_argument('url', nargs='?', help='视频 URL')
    parser.add_argument('--batch', help='批量 URL 文件 (每行一个)')
    parser.add_argument('--lang', default='zh-Hans,en', help='字幕语言 (默认: zh-Hans,en)')
    parser.add_argument('--output', '-o', default='subtitles', help='输出目录 (默认: subtitles)')
    args = parser.parse_args()

    urls = []
    if args.batch:
        batch_path = Path(args.batch)
        if batch_path.exists():
            urls = [line.strip() for line in batch_path.read_text(encoding='utf-8').split('\n')
                    if line.strip() and not line.strip().startswith('#')]
            print(f"从 {args.batch} 读取到 {len(urls)} 个 URL")
        else:
            print(f"错误: 文件不存在 {args.batch}")
            sys.exit(1)
    elif args.url:
        urls = [args.url]
    else:
        print("错误: 请提供 URL 或 --batch 参数")
        sys.exit(1)

    success = 0
    fail = 0
    for url in urls:
        if process_url(url, args.lang, args.output):
            success += 1
        else:
            fail += 1

    print(f"\n{'='*60}")
    print(f"完成: 成功 {success}, 失败 {fail}")

    if fail > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()