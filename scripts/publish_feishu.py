#!/usr/bin/env python3
"""Publish a Markdown daily report to Feishu Wiki and notify a group bot."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import requests


FEISHU_API = "https://open.feishu.cn/open-apis"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def get_tenant_access_token() -> str:
    resp = requests.post(
        f"{FEISHU_API}/auth/v3/tenant_access_token/internal",
        json={
            "app_id": required_env("FEISHU_APP_ID"),
            "app_secret": required_env("FEISHU_APP_SECRET"),
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"Feishu token error: {data}")
    return data["tenant_access_token"]


def feishu_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"}


def create_wiki_doc(token: str, title: str) -> tuple[str, str | None]:
    space_id = required_env("FEISHU_WIKI_SPACE_ID")
    body: dict[str, Any] = {
        "obj_type": "docx",
        "node_type": "origin",
        "title": title,
    }
    parent = os.getenv("FEISHU_PARENT_NODE_TOKEN")
    if parent:
        body["parent_node_token"] = parent
    resp = requests.post(
        f"{FEISHU_API}/wiki/v2/spaces/{space_id}/nodes",
        headers=feishu_headers(token),
        json=body,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"Feishu create wiki node error: {data}")
    node = data.get("data", {}).get("node", {})
    doc_token = node.get("obj_token") or node.get("token")
    node_token = node.get("node_token")
    if not doc_token:
        raise RuntimeError(f"Cannot find document token in Feishu response: {data}")
    return doc_token, node_token


def text_element(content: str) -> dict[str, Any]:
    return {"text_run": {"content": content, "text_element_style": {}}}


def block(block_type: int, key: str, content: str) -> dict[str, Any]:
    return {"block_type": block_type, key: {"elements": [text_element(content)]}}


def markdown_to_blocks(markdown: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    in_code = False
    code_lines: list[str] = []
    for raw in markdown.splitlines():
        line = raw.rstrip()
        if line.startswith("```"):
            if in_code:
                blocks.append({"block_type": 14, "code": {"elements": [text_element("\n".join(code_lines))]}})
                code_lines = []
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
            continue
        if not line.strip():
            continue
        if line.startswith("# "):
            blocks.append(block(3, "heading1", line[2:].strip()))
        elif line.startswith("## "):
            blocks.append(block(4, "heading2", line[3:].strip()))
        elif line.startswith("### "):
            blocks.append(block(5, "heading3", line[4:].strip()))
        elif re.match(r"^\d+\.\s+", line):
            blocks.append(block(2, "text", "  " + line.strip()))
        elif line.startswith("- "):
            blocks.append(block(2, "text", "  • " + line[2:].strip()))
        elif line.startswith("> "):
            blocks.append(block(2, "text", "  ▎" + line[2:].strip()))
        else:
            blocks.append(block(2, "text", strip_markdown_emphasis(line)))
    if code_lines:
        blocks.append({"block_type": 14, "code": {"elements": [text_element("\n".join(code_lines))]}})
    return blocks


def strip_markdown_emphasis(line: str) -> str:
    return line.replace("**", "").replace("__", "")


def append_blocks(token: str, document_id: str, blocks: list[dict[str, Any]]) -> None:
    # For Feishu docx, the document token is also the root block id in the children API.
    root_block_id = document_id
    for start in range(0, len(blocks), 50):
        batch = blocks[start : start + 50]
        resp = requests.post(
            f"{FEISHU_API}/docx/v1/documents/{document_id}/blocks/{root_block_id}/children",
            headers=feishu_headers(token),
            json={"index": start, "children": batch},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"Feishu append blocks error: {data}")


def notify(text: str) -> None:
    webhook = os.getenv("FEISHU_NOTIFY_WEBHOOK")
    if not webhook:
        return
    resp = requests.post(
        webhook,
        json={"msg_type": "text", "content": {"text": text}},
        timeout=30,
    )
    resp.raise_for_status()


def list_root_nodes(token: str) -> list[dict[str, Any]]:
    """List all top-level nodes (no parent) in the wiki space."""
    space_id = required_env("FEISHU_WIKI_SPACE_ID")
    all_nodes: list[dict[str, Any]] = []
    page_token = ""
    while True:
        params: dict[str, Any] = {"page_size": 50}
        if page_token:
            params["page_token"] = page_token
        resp = requests.get(
            f"{FEISHU_API}/wiki/v2/spaces/{space_id}/nodes",
            headers=feishu_headers(token),
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"Feishu list nodes error: {data}")
        items = data.get("data", {}).get("items") or []
        all_nodes.extend(items)
        if not data.get("data", {}).get("has_more"):
            break
        page_token = data.get("data", {}).get("page_token", "")
        if not page_token:
            break
    return all_nodes


def delete_wiki_node(token: str, node_token: str) -> bool:
    """Delete a wiki node. Returns True on success."""
    space_id = required_env("FEISHU_WIKI_SPACE_ID")
    try:
        resp = requests.delete(
            f"{FEISHU_API}/wiki/v2/spaces/{space_id}/nodes/{node_token}",
            headers=feishu_headers(token),
            timeout=30,
        )
        data = resp.json()
        return data.get("code") == 0
    except Exception:
        return False


def cleanup_old_daily_reports(token: str, current_title: str) -> int:
    """Delete old daily report nodes (title starts with '日报 '). Returns count deleted."""
    nodes = list_root_nodes(token)
    deleted = 0
    for node in nodes:
        title = node.get("title", "")
        node_token = node.get("node_token", "")
        if not title or not node_token:
            continue
        # Delete nodes that look like old daily reports
        is_old_report = (
            "播客/视频更新日报" in title or
            title.startswith("日报 ") or
            title == "DEBUG" or title == "DEBUG2" or
            title.startswith("TEST_")
        )
        # But keep the current report and 播客蒸馏室
        if is_old_report and title != current_title and title != "播客蒸馏室":
            print(f"  Deleting old node: {title}")
            if delete_wiki_node(token, node_token):
                deleted += 1
    return deleted


def main() -> int:
    args = parse_args()
    markdown_path = Path(args.file)
    markdown = markdown_path.read_text(encoding="utf-8")
    if args.dry_run or not os.getenv("FEISHU_APP_ID"):
        print(f"Dry run: would publish {markdown_path} as {args.title}")
        notify(f"今日日报已完成：{args.title}\n飞书发布处于 dry-run，本地文件已生成。")
        return 0

    try:
        token = get_tenant_access_token()
        document_id, node_token = create_wiki_doc(token, args.title)
        append_blocks(token, document_id, markdown_to_blocks(markdown))
        # Clean up old daily reports so only the latest remains below 播客蒸馏室
        deleted = cleanup_old_daily_reports(token, args.title)
        print(f"Cleaned up {deleted} old report node(s)")
        suffix = f"\nhttps://my.feishu.cn/wiki/{node_token}" if node_token else ""
        notify(f"今日日报已完成：{args.title}\n飞书知识库已更新{suffix}")
        print(f"Published to Feishu Wiki: document={document_id} node={node_token}")
        return 0
    except Exception as exc:
        notify(f"今日日报生成完成，但发布飞书失败：{args.title}\n{exc}")
        raise


if __name__ == "__main__":
    raise SystemExit(main())
