# Worklog — phkhoiit-1508

Nhật ký kỹ thuật ngắn gọn của `phkhoiit-1508`, sắp xếp entry mới nhất lên trước.

**2026-10-21 — Model Evaluation & Benchmark**

- Implemented shared final-test metrics for Accuracy, Scam Precision, Scam Recall, Scam F1, and TN/FP/FN/TP counts.
- Implemented percentile bootstrap confidence intervals and paired bootstrap differences using a shared random-index strategy.
- Implemented the LR/SVM final benchmark CLI with a confirmation gate, artifact loading, provenance, JSON output, and Markdown output.
- Added unit tests for metrics, zero-division handling, bootstrap reproducibility, paired comparison, and invalid inputs.
- Tests:
  - `python -m unittest backend.tests.test_evaluation -v` — PASS (9/9).
  - `python -m unittest discover -s backend/tests -p "test_*.py" -v` — PASS (71/71).
  - `python -m compileall -q backend/evaluation backend/tests/test_evaluation.py` — PASS.
  - `git diff --check` — PASS.
- Final benchmark: not run; SVM artifact and Leader approval were not confirmed. The confirmation gate was verified and blocks execution without `--confirm-final-test`.
- Remaining: install `backend/requirements.txt`, run the test suite, then run the approved final benchmark only after both artifacts and protocol are confirmed.

## Mẫu entry

**YYYY-MM-DD — Tên task**

- Thay đổi: Tóm tắt implementation hoặc quyết định quan trọng.
- Bug/Fix: Ghi ngắn root cause và fix nếu thực sự có bug; nếu không có thì bỏ dòng này.
- Test: `command` — kết quả thực tế; không ghi PASS nếu chưa chạy.
- Tiếp theo: Việc quan trọng còn lại hoặc trạng thái review.
