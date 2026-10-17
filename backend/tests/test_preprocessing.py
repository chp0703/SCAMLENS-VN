"""Behavior and integration checks using synthetic messages only."""

import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unicodedata
import unittest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.services.preprocessing import normalize_text
from scripts.dataset import clean_source, group_similar, length_analysis, read_csv, sha256
from scripts.prepare_data import prepare
from scripts.split_data import create_splits, validate_splits


class NormalizationTests(unittest.TestCase):
    def test_vietnamese_nfc_lower_whitespace(self):
        raw = unicodedata.normalize("NFD", "  ĐÃ\n\tCÓ   CÂY  ")
        self.assertEqual(normalize_text(raw), "đã có cây")

    def test_url_punctuation_and_emoji(self):
        self.assertEqual(normalize_text("Xem (HTTPS://example.vn/a?q=12), www.example.com! 😀"),
                         "xem ([URL]), [URL]! 😀")
        self.assertEqual(normalize_text("https://example.vn😀"), "[URL]😀")

    def test_email_before_phone(self):
        self.assertEqual(normalize_text("Gửi 0901234567@example.vn, nhé!"), "gửi [EMAIL], nhé!")

    def test_url_before_email_and_phone(self):
        self.assertEqual(normalize_text("https://example.vn/0901234567?a=user@example.vn."), "[URL].")

    def test_vietnamese_phones(self):
        for value in ("0901234567", "090 123 4567", "090.123.4567", "+84 90-123-4567", "0084 90 123 4567",
                      "02812345678", "+842812345678", "00842812345678"):
            with self.subTest(value=value):
                self.assertEqual(normalize_text("Gọi " + value + "!"), "gọi [PHONE]!")

    def test_not_all_numbers_are_phones(self):
        for value in ("1234567890", "0000000000", "090123456789", "2026", "abc0901234567", "0901234567abc", "0123456789"):
            with self.subTest(value=value):
                self.assertEqual(normalize_text(value), value)

    def test_keep_placeholders(self):
        raw = "[number] [BANK_ACC] [money] [DATE] [Time] [name] [POINT] [URL] [phone] [email]"
        self.assertEqual(normalize_text(raw), raw.upper())

    def test_punctuation_unicode_and_emoji(self):
        self.assertEqual(normalize_text("ĐÃ CÓ CÂY!!! 😀 💵 𝟡 [NUMBER]"), "đã có cây!!! 😀 💵 𝟡 [NUMBER]")

    def test_idempotence(self):
        for raw in ("  ĐÃ\nGỬI +84901234567!!!", "[url] https://a.vn, a@b.com", "[NUMBER] 1234", "", "😀💵"):
            with self.subTest(raw=raw):
                self.assertEqual(normalize_text(normalize_text(raw)), normalize_text(raw))

    def test_type_error(self):
        with self.assertRaises(TypeError):
            normalize_text(None)


class WorkspaceTest(unittest.TestCase):
    def setUp(self):
        temporary_root = BACKEND / "tests/.tmp"
        temporary_root.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=temporary_root)
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def source(self, rows, name="source.csv"):
        path = self.root / name
        with path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["message_id", "message", "label"])
            writer.writerows(rows)
        return path

    def synthetic_source(self, n=100, name="source.csv"):
        return self.source([(f"id_{i:04}", "Tin nhắn \"hợp lệ\", 😀\n" + hashlib.sha256(str(i).encode()).hexdigest(), i % 2)
                            for i in range(n)], name)


class CleaningTests(WorkspaceTest):
    def test_missing_invalid_label_and_accounting(self):
        source = self.source([("a", "", "1"), ("b", "abc", ""), ("c", "abc", "2"), ("d", "OK", "0")])
        rows, accounts, duplicates = clean_source(source)
        self.assertEqual([r["message_id"] for r in rows], ["d"])
        self.assertEqual([r["status"] for r in accounts], ["rejected"] * 3 + ["kept"])
        self.assertEqual(duplicates, [])

    def test_dedup_representative_and_original_preserved(self):
        raw = "  TIN\nNhắn \"hợp lệ\", 😀\n"
        source = self.source([("z", "tin nhắn \"hợp lệ\", 😀", 0), ("a", raw, 0)])
        rows, accounts, duplicates = clean_source(source)
        self.assertEqual(rows[0]["message_id"], "a")
        self.assertEqual(rows[0]["text_raw"], raw)
        self.assertEqual(duplicates, [dict(message_id="z", representative_id="a", stage="before_masking")])

    def test_masking_duplicate(self):
        source = self.source([("b", "Gọi 0901234567", 0), ("a", "Gọi 0911234567", 0)])
        rows, accounts, duplicates = clean_source(source)
        self.assertEqual(len(rows), 1)
        self.assertEqual(duplicates[0]["stage"], "after_masking")

    def test_conflict_before_masking_quarantines_entire_final_group(self):
        source = self.source([("a", "Gọi 0901234567", 0), ("b", "gọi 0901234567", 1), ("c", "gọi 0911234567", 1)])
        rows, accounts, duplicates = clean_source(source)
        self.assertFalse(rows or duplicates)
        self.assertTrue(all(a["status"] == "quarantined" for a in accounts))
        self.assertTrue(all(a["reason"] == "label_conflict_before_masking" for a in accounts))

    def test_conflict_after_masking(self):
        source = self.source([("a", "Gọi 0901234567", 0), ("b", "Gọi 0911234567", 1)])
        rows, accounts, duplicates = clean_source(source)
        self.assertFalse(rows)
        self.assertTrue(all(a["reason"] == "label_conflict_after_masking" for a in accounts))

    def test_duplicate_or_empty_id_fails(self):
        for ids in (("a", "a"), ("a", "")):
            source = self.source([(ids[0], "x", 0), (ids[1], "y", 1)])
            with self.assertRaisesRegex(ValueError, "message_id"):
                clean_source(source)

    def test_malformed_csv_fails(self):
        path = self.root / "bad.csv"
        path.write_text("message_id,message,label\na,abc\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Malformed"):
            clean_source(path)


class GroupingTests(unittest.TestCase):
    def test_connected_chain_and_mixed_label_review(self):
        base = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        texts = ["!!!!" + base[4:], base, base[:-4] + "????"]
        rows = [dict(message_id=str(i), text=text, label=i % 2) for i, text in enumerate(texts)]
        edges, groups = group_similar(rows)
        self.assertEqual(len(edges), 2)
        self.assertEqual(len(groups), 1)
        self.assertIn("mixed_labels", groups[0]["review_reason"])
        self.assertEqual(len({r["group_id"] for r in rows}), 1)

    def test_short_text_only_exact_and_stable_group_ids(self):
        rows = [dict(message_id=str(i), text=text, label=0) for i, text in enumerate(["abc", "abd", "abc"])]
        edges, groups = group_similar(rows)
        mapping = {r["message_id"]: r["group_id"] for r in rows}
        self.assertEqual(len(edges), 1)
        self.assertNotEqual(rows[0]["group_id"], rows[1]["group_id"])
        group_similar(list(reversed(rows)))
        self.assertEqual(mapping, {r["message_id"]: r["group_id"] for r in rows})

    def test_outlier_retained(self):
        rows = [dict(message_id=str(i), text="abc", label=0) for i in range(8)]
        rows.append(dict(message_id="long", text="abc " * 100, label=1))
        stats, outliers = length_analysis(rows)
        self.assertEqual([r["message_id"] for r in outliers], ["long"])
        self.assertEqual(len(rows), 9)
        self.assertEqual(stats["char"]["median"], 3)


class SplitTests(WorkspaceTest):
    def rows(self):
        rows, _, _ = clean_source(self.synthetic_source())
        group_similar(rows)
        # Make a real near-duplicate group with both classes for split integrity.
        rows[1]["group_id"] = rows[0]["group_id"]
        return rows

    def test_shared_test_cv_and_dl_union(self):
        rows = self.rows()
        splits = create_splits(rows)
        checks = validate_splits(rows, splits)
        self.assertTrue(all(value for value in checks.values()))
        self.assertEqual(splits["ml/test.csv"], splits["dl_jev/test.csv"])
        self.assertEqual(splits, create_splits(list(reversed(rows))))

    def test_insufficient_groups_fails(self):
        rows = self.rows()[:8]
        with self.assertRaisesRegex(ValueError, "needs at least 5"):
            create_splits(rows)

    def test_missing_class_in_fold_fails_without_fallback(self):
        rows = [dict(message_id=str(i), text=str(i), text_raw=str(i), label=i % 2, group_id=str(i)) for i in range(10)]
        with self.assertRaisesRegex(ValueError, "must contain both classes; no random fallback"):
            create_splits(rows)

    def test_leakage_is_rejected(self):
        rows = self.rows()
        splits = create_splits(rows)
        splits["ml/train.csv"].append(splits["ml/test.csv"][0])
        with self.assertRaisesRegex(ValueError, "Leakage"):
            validate_splits(rows, splits)

    def test_cv_membership_tampering_is_rejected(self):
        rows = self.rows()
        splits = create_splits(rows)
        splits["ml/cv_folds.csv"][0] = splits["ml/cv_folds.csv"][1].copy()
        with self.assertRaisesRegex(ValueError, "every ML train ID"):
            validate_splits(rows, splits)


class PipelineTests(WorkspaceTest):
    def test_split_cli_preserves_shared_artifacts(self):
        data, reports = self.root / "data", self.root / "reports"
        manifest, _ = prepare(self.synthetic_source(), data, reports)
        output = self.root / "split_only"
        result = subprocess.run([sys.executable, str(BACKEND / "scripts/split_data.py"), "--input",
                                 str(data / "processed/clean.csv"), "--output-dir", str(output)],
                                cwd=BACKEND, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        for name, digest in manifest["output_sha256"].items():
            if name.startswith("splits/"):
                self.assertEqual(sha256(output / name.removeprefix("splits/")), digest)
        self.assertEqual(json.loads((output / "manifest.json").read_text(encoding="utf-8"))["scope"], "split_only")

    def test_end_to_end_repeatability_serialization_and_append_only_reports(self):
        source = self.synthetic_source()
        before = sha256(source)
        data, reports = self.root / "data", self.root / "reports"
        first, report1 = prepare(source, data, reports)
        report_content = report1.read_bytes()
        manifest_content = (data / "splits/manifest.json").read_bytes()
        second, report2 = prepare(source, data, reports)
        self.assertEqual(first, second)
        self.assertEqual(manifest_content, (data / "splits/manifest.json").read_bytes())
        self.assertEqual(report_content, report1.read_bytes())
        self.assertEqual(report2.name, "preprocess_v2.md")
        self.assertEqual(before, sha256(source))
        for name, digest in first["output_sha256"].items():
            self.assertEqual(sha256(data / name), digest)
            self.assertTrue((data / name).read_bytes().startswith(b"\xef\xbb\xbf"))
        self.assertEqual((data / "splits/ml/test.csv").read_bytes(), (data / "splits/dl_jev/test.csv").read_bytes())
        original = {r["message_id"]: r["message"] for r in read_csv(source)}
        for row in read_csv(data / "processed/clean.csv"):
            self.assertEqual(row["text_raw"], original[row["message_id"]])
        self.assertNotIn(next(iter(original.values())), report1.read_text(encoding="utf-8"))

    def test_failure_does_not_replace_previous_success(self):
        data, reports = self.root / "data", self.root / "reports"
        original, report = prepare(self.synthetic_source(), data, reports)
        manifest_bytes = (data / "splits/manifest.json").read_bytes()
        with self.assertRaises(ValueError):
            prepare(self.synthetic_source(8, "too_small.csv"), data, reports)
        self.assertEqual(manifest_bytes, (data / "splits/manifest.json").read_bytes())
        self.assertEqual(len(list(reports.glob("*.md"))), 1)
        for name, digest in original["output_sha256"].items():
            self.assertEqual(sha256(data / name), digest)

    def test_raw_output_path_is_rejected(self):
        source = self.synthetic_source()
        with self.assertRaisesRegex(ValueError, "raw/source"):
            prepare(source, self.root / "data", source.parent)


if __name__ == "__main__":
    unittest.main()
