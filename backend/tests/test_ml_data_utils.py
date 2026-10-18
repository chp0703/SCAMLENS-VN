"""Synthetic unit tests for ML shared-split loading and validation."""

import csv
from pathlib import Path
import sys
import tempfile
import unittest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from src.ML.data_utils import DataValidationError, load_ml_data


class MLDataUtilsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp.name)
        self.train = [
            ["t2", "raw", "second", 1, "g2"], ["t1", "raw", "first", 0, "g1"],
            ["t3", "raw", "third", 0, "g3"], ["t4", "raw", "fourth", 1, "g4"],
        ]
        self.test = [["e1", "raw", "test ham", 0, "g5"], ["e2", "raw", "test scam", 1, "g6"]]
        self.folds = [["t1", 0], ["t2", 1], ["t3", 1], ["t4", 0]]
        self._write_valid()

    def tearDown(self):
        self.temp.cleanup()

    def _write(self, name, header, rows):
        with (self.data_dir / name).open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(header)
            writer.writerows(rows)

    def _write_valid(self):
        self._write("train.csv", ["message_id", "text_raw", "text", "label", "group_id"], self.train)
        self._write("test.csv", ["message_id", "text_raw", "text", "label", "group_id"], self.test)
        self._write("cv_folds.csv", ["message_id", "fold_id"], self.folds)

    def test_loads_and_preserves_train_order_for_predefined_split(self):
        data = load_ml_data(self.data_dir)
        self.assertEqual(data.X_train, ["second", "first", "third", "fourth"])
        self.assertEqual(data.y_train.tolist(), [1, 0, 0, 1])
        self.assertEqual(data.fold_ids.tolist(), [1, 0, 1, 0])
        splits = list(data.cv.split())
        self.assertEqual(len(splits), 2)
        self.assertEqual(splits[0][1].tolist(), [1, 3])
        self.assertEqual(splits[1][1].tolist(), [0, 2])

    def test_missing_file_or_column_fails(self):
        (self.data_dir / "test.csv").unlink()
        with self.assertRaisesRegex(DataValidationError, "test.csv"):
            load_ml_data(self.data_dir)
        self._write("test.csv", ["message_id", "text", "label", "group_id"], self.test)
        with self.assertRaisesRegex(DataValidationError, "text_raw"):
            load_ml_data(self.data_dir)

    def test_duplicate_id_invalid_label_and_blank_text_fail(self):
        self.train[1][0] = "t2"
        self._write_valid()
        with self.assertRaisesRegex(DataValidationError, "duplicate message_id"):
            load_ml_data(self.data_dir)
        self.train[1][0], self.train[1][3] = "t1", 7
        self._write_valid()
        with self.assertRaisesRegex(DataValidationError, "invalid label"):
            load_ml_data(self.data_dir)
        self.train[1][3], self.train[1][2] = 0, "  "
        self._write_valid()
        with self.assertRaisesRegex(DataValidationError, "blank text"):
            load_ml_data(self.data_dir)

    def test_missing_extra_and_duplicate_fold_assignments_fail(self):
        self.folds = self.folds[:-1]
        self._write_valid()
        with self.assertRaisesRegex(DataValidationError, "missing fold assignments"):
            load_ml_data(self.data_dir)
        self.folds = [["t1", 0], ["t2", 1], ["t3", 1], ["t4", 0], ["extra", 0]]
        self._write_valid()
        with self.assertRaisesRegex(DataValidationError, "outside train"):
            load_ml_data(self.data_dir)
        self.folds = [["t1", 0], ["t1", 1], ["t3", 1], ["t4", 0]]
        self._write_valid()
        with self.assertRaisesRegex(DataValidationError, "duplicate fold assignment"):
            load_ml_data(self.data_dir)

    def test_train_test_id_or_group_leakage_fails(self):
        self.test[0][0] = "t1"
        self._write_valid()
        with self.assertRaisesRegex(DataValidationError, "overlap on message_id"):
            load_ml_data(self.data_dir)
        self.test[0][0], self.test[0][4] = "e1", "g1"
        self._write_valid()
        with self.assertRaisesRegex(DataValidationError, "overlap on group_id"):
            load_ml_data(self.data_dir)

    def test_fold_must_support_scam_metrics_and_contiguous_convention(self):
        self.folds = [["t1", 0], ["t2", 1], ["t3", 1], ["t4", 1]]
        self._write_valid()
        with self.assertRaisesRegex(DataValidationError, "fold 0 must contain both"):
            load_ml_data(self.data_dir)
        self.folds = [["t1", 0], ["t2", 2], ["t3", 2], ["t4", 0]]
        self._write_valid()
        with self.assertRaisesRegex(DataValidationError, "contiguous range"):
            load_ml_data(self.data_dir)


if __name__ == "__main__":
    unittest.main()
