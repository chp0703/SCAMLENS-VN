"""Regression checks for SMS signal preservation and split integrity."""

import csv
import json
import sys
import tempfile
import unittest
import unicodedata
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.preprocessing import duplicate_key, normalize_text, template_tokens
from src.ML.prepare_data import (
    OUTPUT_COLUMNS, REQUIRED_COLUMNS, SPLIT_NAMES, audit_source, deduplicate,
    group_templates, read_source, run, sha256_file, split_groups, verify_splits,
    verify_serialized_outputs, write_csv,
)
from src.ML.reporting import write_preprocess_report


def row(identifier, text, label="0", date="28/05/2026"):
    return {"message_id": identifier, "date": date, "message": text, "label": label}


def distinct_rows(count=40):
    return [row(f"m{i:03d}", f"nộidung{chr(97 + i // 26)}{chr(97 + i % 26)}", str(i % 2)) for i in range(count)]


class TextNormalizationTests(unittest.TestCase):
    def test_preserves_vietnamese_numbers_urls_punctuation_placeholders_and_emoji(self):
        message = "Mã OTP 123456! https://Bank.vn/Verify?ID=ABC [MONEY] 👨‍👩‍👦"
        decomposed = unicodedata.normalize("NFD", message)
        self.assertEqual(normalize_text("\ufeff \t" + decomposed + "\r\n"), message)
        self.assertEqual(normalize_text(normalize_text(decomposed)), message)

    def test_collapses_whitespace_and_removes_invisible_separators(self):
        self.assertEqual(normalize_text(" \tXin\u200b  chào\r\n bạn\u00a0! "), "Xin chào bạn !")
        self.assertEqual(normalize_text(" \n\t\u200b"), "")

    def test_casefold_is_a_separate_dedup_key(self):
        self.assertNotEqual(normalize_text("Xin CHÀO"), normalize_text("xin chào"))
        self.assertEqual(duplicate_key(" Xin CHÀO\n"), duplicate_key("xin chào"))
        self.assertNotEqual(duplicate_key("không gửi OTP"), duplicate_key("gửi OTP"))
        self.assertNotEqual(duplicate_key("má"), duplicate_key("ma"))

    def test_template_mask_does_not_change_model_text(self):
        first = "Mã OTP 123456 của bạn: https://bank.vn/a account@example.org [TIME]."
        second = "Mã OTP 654321 của bạn: https://bank.vn/b other@example.org [TIME]."
        self.assertEqual(template_tokens(first), template_tokens(second))
        self.assertIn("123456", normalize_text(first))
        self.assertIn("https://bank.vn/a", normalize_text(first))
        self.assertIn("[TIME]", normalize_text(first))

    def test_rejects_non_string_input(self):
        with self.assertRaises(TypeError):
            normalize_text(None)


class DatasetPreparationTests(unittest.TestCase):
    def test_csv_has_one_utf8_bom_and_round_trips_vietnamese_and_valid_capitals(self):
        message = "ƯU ĐÃI CHĂM CÂY — Mã OTP 123456! https://Bank.vn/Verify [MONEY] 👨‍👩‍👦"
        with tempfile.TemporaryDirectory(prefix="preprocessing-", dir=BACKEND / "tests") as task_temp:
            target = Path(task_temp) / "vietnamese.csv"
            write_csv(target, REQUIRED_COLUMNS, [row("A", message)])
            content = target.read_bytes()
            self.assertTrue(content.startswith(b"\xef\xbb\xbf"))
            self.assertFalse(content.startswith(b"\xef\xbb\xbf\xef\xbb\xbf"))
            parsed = read_source(target)
            self.assertEqual(parsed[0]["message"], message)
            self.assertNotIn("\ufffd", parsed[0]["message"])
            self.assertNotIn("áº", parsed[0]["message"])

    def test_conflicts_are_quarantined_and_duplicates_keep_all_source_ids(self):
        rows = [row("A", "Xin chào"), row("B", " XIN CHÀO\n"),
                row("C", "Gửi mã OTP", "0"), row("D", "gửi mã otp", "1")]
        clean, quarantine, mapping = deduplicate(rows)
        self.assertEqual(len(clean), 1)
        self.assertEqual(clean[0]["source_count"], 2)
        self.assertEqual(json.loads(clean[0]["source_ids"]), ["A", "B"])
        self.assertEqual({r["message_id"] for r in quarantine}, {"C", "D"})
        self.assertEqual(len(mapping) + len(quarantine), len(rows))

    def test_exact_template_and_near_duplicates_share_groups_without_removal(self):
        clean, _, _ = deduplicate([
            row("A", "Mã OTP 123456 dùng cho giao dịch chuyển khoản ngân hàng"),
            row("B", "Mã OTP 654321 dùng cho giao dịch chuyển khoản ngân hàng"),
            row("C", "Mã OTP 654321 dùng cho giao dịch chuyển khoản ngân hàng nhé", "1"),
            row("D", "Hôm nay trời đẹp"),
        ])
        groups, edges = group_templates(clean)
        self.assertEqual(len(groups), 2)
        self.assertEqual(len({r["group_id"] for r in clean[:3]}), 1)
        self.assertNotEqual(clean[0]["group_id"], clean[3]["group_id"])
        self.assertEqual(len(clean), 4)
        self.assertEqual({e["method"] for e in edges}, {"exact_masked_template", "token_set_jaccard"})

    def test_grouping_is_transitive(self):
        clean, _, _ = deduplicate([
            row("A", "alpha beta gamma delta epsilon zeta eta theta iota kappa"),
            row("B", "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"),
            row("C", "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu"),
        ])
        groups, _ = group_templates(clean)
        self.assertEqual(len(groups), 1)

    def test_short_unrelated_messages_are_not_joined_by_common_token(self):
        clean, _, _ = deduplicate([row("A", "gửi OTP"), row("B", "không gửi OTP")])
        groups, _ = group_templates(clean)
        self.assertEqual(len(groups), 2)

    def test_whole_group_split_is_reproducible_balanced_and_has_no_leakage(self):
        clean, _, _ = deduplicate(distinct_rows())
        groups, edges = group_templates(clean)
        first = split_groups(groups, 42)
        second = split_groups(groups, 42)
        self.assertEqual(first, second)
        self.assertEqual(sum(map(len, first.values())), len(clean))
        for part in first.values():
            self.assertEqual({r["label"] for r in part}, {"0", "1"})
        self.assertEqual(verify_splits(first, edges)["detected_template_edges_crossing_splits"], 0)

    def test_leakage_guard_rejects_normalized_text_and_duplicate_source_ids(self):
        first = {**row("A", "Xin chào"), "text": "Xin chào", "group_id": "g1", "source_ids": '["A"]'}
        second = {**row("B", "XIN CHÀO"), "text": "XIN CHÀO", "group_id": "g2", "source_ids": '["B"]'}
        with self.assertRaisesRegex(ValueError, "Split leakage"):
            verify_splits({"train": [first], "validation": [second], "test": []}, [])
        second["text"] = "Khác nội dung"
        second["source_ids"] = '["A"]'
        with self.assertRaisesRegex(ValueError, "source ID"):
            verify_splits({"train": [first], "validation": [second], "test": []}, [])

    def test_privacy_review_is_metadata_only_and_missing_dates_are_retained(self):
        records = [row("A", "Mã OTP là 123456. Gọi 0912345678 hoặc help@example.org", date="")]
        report, review = audit_source(records)
        self.assertEqual(report["missing_by_column"]["date"], 1)
        self.assertEqual(report["privacy_candidate_rows"], 1)
        self.assertEqual(report["privacy_candidates_by_category"]["otp_or_pin_candidate"], 1)
        self.assertEqual(set(review[0]), {"message_id", "categories"})
        self.assertNotIn("123456", json.dumps(review))
        self.assertEqual(len(deduplicate(records)[0]), 1)

    def test_invalid_input_and_changed_source_hash_are_rejected_before_writes(self):
        with tempfile.TemporaryDirectory(prefix="preprocessing-", dir=BACKEND / "tests") as task_temp:
            folder = Path(task_temp)
            source = folder / "input.csv"
            write_csv(source, REQUIRED_COLUMNS, [row("A", "Valid"), row("A", "Other", "1")])
            with self.assertRaisesRegex(ValueError, "message_id"):
                read_source(source)
            write_csv(source, REQUIRED_COLUMNS, [row("A", "Valid")])
            (folder / "source.json").write_text(json.dumps({"sha256": {"input.csv": "wrong"}}))
            output = folder / "out"
            with self.assertRaisesRegex(ValueError, "hash"):
                run(source, output)
            self.assertFalse(output.exists())

    def test_end_to_end_repeats_identically_and_is_independent_of_input_order(self):
        with tempfile.TemporaryDirectory(prefix="preprocessing-", dir=BACKEND / "tests") as task_temp:
            folder = Path(task_temp)
            source = folder / "input.csv"
            rows = distinct_rows()
            rows += [row("dup", rows[0]["message"])]
            write_csv(source, REQUIRED_COLUMNS, rows)
            before = sha256_file(source)
            first_dir, repeat_dir, reversed_dir = folder / "first", folder / "repeat", folder / "reverse"
            report = run(source, first_dir)
            run(source, repeat_dir)
            self.assertEqual(sha256_file(source), before)
            self.assertEqual(report["clean_unique_rows"], 40)
            self.assertEqual(report["removed_duplicate_extra_rows"], 1)
            self.assertTrue(report["serialization_checks"]["normalized_text_round_trip"])
            for path in first_dir.iterdir():
                self.assertEqual(path.read_bytes(), (repeat_dir / path.name).read_bytes(), path.name)
            write_csv(source, REQUIRED_COLUMNS, list(reversed(rows)))
            run(source, reversed_dir)
            for name in ("clean", *SPLIT_NAMES):
                self.assertEqual((first_dir / f"{name}.csv").read_bytes(), (reversed_dir / f"{name}.csv").read_bytes())
            with (first_dir / "train.csv").open(encoding="utf-8-sig", newline="") as handle:
                self.assertEqual(csv.DictReader(handle).fieldnames, list(OUTPUT_COLUMNS))

    def test_serialization_checks_reject_a_csv_without_bom(self):
        with tempfile.TemporaryDirectory(prefix="preprocessing-", dir=BACKEND / "tests") as task_temp:
            folder = Path(task_temp)
            source = folder / "input.csv"
            rows = distinct_rows()
            write_csv(source, REQUIRED_COLUMNS, rows)
            output = folder / "output"
            run(source, output)
            target = output / "train.csv"
            target.write_bytes(target.read_bytes()[3:])
            clean, conflicts, _ = deduplicate(rows)
            with self.assertRaisesRegex(ValueError, "BOM"):
                verify_serialized_outputs(output, rows, clean, conflicts)

    def test_numbered_reports_preserve_history_and_record_failed_runs(self):
        with tempfile.TemporaryDirectory(prefix="preprocessing-", dir=BACKEND / "tests") as task_temp:
            folder = Path(task_temp)
            original = folder / "preprocess_v3.md"
            original.write_text("Previous report", encoding="utf-8")
            first = write_preprocess_report(folder, failure="Fixture validation failed")
            second = write_preprocess_report(folder, failure="Another fixture failed")
            self.assertEqual(first.name, "preprocess_v4.md")
            self.assertEqual(second.name, "preprocess_v5.md")
            self.assertEqual(original.read_text(encoding="utf-8"), "Previous report")
            self.assertIn("**FAIL**", first.read_text(encoding="utf-8"))

    def test_success_report_records_only_actual_checks_and_optional_test_results(self):
        with tempfile.TemporaryDirectory(prefix="preprocessing-", dir=BACKEND / "tests") as task_temp:
            folder = Path(task_temp)
            source = folder / "input.csv"
            write_csv(source, REQUIRED_COLUMNS, distinct_rows())
            output = folder / "output"
            audit = run(source, output)
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            reports = folder / "report"
            first = write_preprocess_report(reports, audit, manifest)
            second = write_preprocess_report(reports, audit, manifest, unit_tests={"status": "PASS", "tests_run": 7, "return_code": 0})
            self.assertEqual(first.name, "preprocess_v1.md")
            self.assertEqual(second.name, "preprocess_v2.md")
            self.assertIn("chưa chạy trong lệnh này", first.read_text(encoding="utf-8"))
            self.assertIn("7 test", second.read_text(encoding="utf-8"))
            self.assertIn("utf-8-sig", second.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
