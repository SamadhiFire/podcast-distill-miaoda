import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.generate_daily_report import (
    DIGEST_CACHE_VERSION,
    is_context_length_error,
    load_digest_cache,
    metadata_fallback_enabled,
    should_use_direct_fileid,
    validate_final_digest,
)
from scripts.report_contract import enrich_report_from_legacy_markdown, normalize_digest
from scripts.publish_feishu import FEISHU_API, update_wiki_node_title


class ReportValidationTests(unittest.TestCase):
    def test_context_classifier_does_not_hide_unrelated_invalid_parameters(self) -> None:
        self.assertFalse(is_context_length_error(RuntimeError("invalid_parameter_error: bad temperature")))
        self.assertTrue(
            is_context_length_error(
                RuntimeError("invalid_parameter_error: input length exceeds token limit")
            )
        )

    def test_metadata_fallback_can_be_disabled_for_required_runs(self) -> None:
        with patch.dict(os.environ, {"LLM_METADATA_FALLBACK_ENABLED": "0"}, clear=False):
            self.assertFalse(metadata_fallback_enabled())

    @patch("scripts.publish_feishu.requests.post")
    def test_wiki_title_update_uses_official_update_title_endpoint(self, post) -> None:
        post.return_value.json.return_value = {"code": 0, "msg": "success"}
        with patch.dict(os.environ, {"FEISHU_WIKI_SPACE_ID": "space-1"}, clear=False):
            update_wiki_node_title("tenant-token", "node-1", "日报")
        post.assert_called_once()
        self.assertEqual(
            post.call_args.args[0],
            f"{FEISHU_API}/wiki/v2/spaces/space-1/nodes/node-1/update_title",
        )
        self.assertEqual(post.call_args.kwargs["json"], {"title": "日报"})

    def test_legacy_markdown_enrichment_never_crosses_item_boundaries(self) -> None:
        report = {
            "items": [
                {
                    "url": "https://example.test/future",
                    "short_title": "未来三年的真实图景",
                    "summary": ["未来原摘要"],
                    "core_points": [],
                    "guests": ["Steve"],
                },
                {
                    "url": "https://example.test/aldi",
                    "short_title": "阿尔迪如何压低食品成本",
                    "summary": ["阿尔迪原摘要"],
                    "core_points": [],
                    "guests": ["Scott"],
                },
            ]
        }
        markdown = """# 全部更新

## 商业 / 财经 / 投资

### 1. 阿尔迪如何压低食品成本

**链接**：https://example.test/aldi

**嘉宾与机构**

- Scott Patton

**完整摘要 · 深读**

阿尔迪摘要一。
阿尔迪摘要二。

## 产品 / 创业 / 管理

### 1. 未来三年的真实图景

**链接**：https://example.test/future

**嘉宾与机构**

- Steve Jurvetson

**完整摘要 · 深读**

未来摘要一。
未来摘要二。
"""
        enriched = enrich_report_from_legacy_markdown(report, markdown)
        future, aldi = enriched["items"]
        self.assertEqual(future["summary"], ["未来摘要一。", "未来摘要二。"])
        self.assertEqual(future["guests"], ["Steve Jurvetson"])
        self.assertEqual(aldi["summary"], ["阿尔迪摘要一。", "阿尔迪摘要二。"])
        self.assertEqual(aldi["guests"], ["Scott Patton"])

    def test_long_transcripts_use_direct_fileid_without_default_maximum(self) -> None:
        env = {
            "LLM_FILEID_DIRECT_ENABLED": "1",
            "LLM_FILEID_DIRECT_MIN_DURATION_SECONDS": "300",
            "LLM_FILEID_DIRECT_MIN_CHARS": "1",
            "LLM_FILEID_DIRECT_MAX_DURATION_SECONDS": "0",
            "LLM_FILEID_DIRECT_MAX_CHARS": "0",
        }
        with patch.dict(os.environ, env, clear=False):
            self.assertTrue(should_use_direct_fileid({"duration": 3601}, "x" * 1000))
            self.assertTrue(should_use_direct_fileid({"duration": 600}, "x" * 155863))

    def test_direct_fileid_optional_maximum_is_still_enforced(self) -> None:
        env = {
            "LLM_FILEID_DIRECT_ENABLED": "1",
            "LLM_FILEID_DIRECT_MIN_DURATION_SECONDS": "300",
            "LLM_FILEID_DIRECT_MIN_CHARS": "1",
            "LLM_FILEID_DIRECT_MAX_DURATION_SECONDS": "1800",
            "LLM_FILEID_DIRECT_MAX_CHARS": "30000",
        }
        with patch.dict(os.environ, env, clear=False):
            self.assertFalse(should_use_direct_fileid({"duration": 3601}, "x" * 1000))
            self.assertFalse(should_use_direct_fileid({"duration": 600}, "x" * 30001))
            self.assertTrue(should_use_direct_fileid({"duration": 600}, "x" * 1000))

    def test_key_fact_context_numbers_must_exist_in_cited_segment(self) -> None:
        raw = {
            "short_title": "测试",
            "one_liner": {"text": "结论", "source_refs": ["S001"]},
            "why_it_matters": {"text": "原因", "source_refs": ["S001"]},
            "content_density": "brief",
            "summary": [
                {"text": "摘要一", "source_refs": ["S001"]},
                {"text": "摘要二", "source_refs": ["S001"]},
                {"text": "摘要三", "source_refs": ["S001"]},
            ],
            "core_points": [
                {"text": "观点一", "source_refs": ["S001"]},
                {"text": "观点二", "source_refs": ["S001"]},
                {"text": "观点三", "source_refs": ["S001"]},
            ],
            "key_facts": [
                {
                    "label": "年份",
                    "value": "17 次",
                    "context": "最近一次为 1971 年",
                    "source_refs": ["S001"],
                }
            ],
            "takeaways": ["回到原文核对。"],
            "guests": [{"text": "嘉宾", "source_refs": ["S001"]}],
            "topics": ["测试"],
            "tensions": [],
            "quote": None,
            "importance_score": 3,
        }
        contract = {
            "content_density": "brief",
            "summary_min": 3,
            "summary_max": 5,
            "summary_char_limit": 280,
            "core_points_min": 3,
            "core_points_max": 5,
        }
        with self.assertRaisesRegex(ValueError, "1971"):
            validate_final_digest(raw, {}, {"S001": "the constitution changed 17 times"}, contract)

    def test_us_constitution_scope_is_corrected(self) -> None:
        raw = {
            "short_title": "美国宪法的困境",
            "one_liner": "修宪机制长期停滞。",
            "why_it_matters": "理解制度僵化。",
            "summary": ["摘要。"],
            "core_points": ["观点一。", "观点二。"],
            "key_facts": [
                {
                    "label": "宪法修正次数",
                    "value": "17 次",
                    "context": "自 1787 年以来仅修正 17 次，最近一次为 1971 年。",
                }
            ],
            "takeaways": ["区分正式修正与实质性修宪。"],
            "guests": [],
            "topics": ["美国宪法"],
            "tensions": [],
            "quote": None,
        }
        digest = normalize_digest(raw, {"title": "Historian on the US Constitution"})
        fact = digest["key_facts"][0]
        self.assertIn("27", fact["value"])
        self.assertIn("1992", fact["context"])

    def test_old_digest_cache_is_invalidated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            item = {"video_id": "abc", "url": "https://example.test/abc"}
            path = root / "2026-07-04" / "abc.json"
            path.parent.mkdir(parents=True)
            path.write_text(
                json.dumps({"cache_version": DIGEST_CACHE_VERSION - 1, "model": "m", "digest": {"x": 1}}),
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"LLM_MODEL": "m"}):
                self.assertIsNone(load_digest_cache(root, "2026-07-04", item))


if __name__ == "__main__":
    unittest.main()
