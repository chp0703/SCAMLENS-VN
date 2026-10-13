"""Append numbered Markdown run reports without rewriting existing history."""

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path


def write_preprocess_report(report_dir: Path, audit=None, manifest=None, *, unit_tests=None, failure=None) -> Path:
    report_dir = report_dir.resolve()
    report_dir.mkdir(parents=True, exist_ok=True)
    pattern = re.compile(r"preprocess_v(\d+)\.md$")
    numbers = [int(match.group(1)) for path in report_dir.iterdir() if (match := pattern.fullmatch(path.name))]
    number = max(numbers, default=0) + 1
    recorded_at = datetime.now(timezone(timedelta(hours=7))).isoformat(timespec="seconds")
    status = "FAIL" if failure else "PASS"
    lines = [f"# Preprocess v{number}", "", "## Lượt chạy", "",
             f"- Thời điểm: {recorded_at} (Asia/Ho_Chi_Minh).",
             f"- Trạng thái kiểm tra tự động: **{status}**.",
             "- Số vN là số lượt báo cáo; phiên bản thuật toán được ghi riêng trong manifest."]
    if unit_tests is not None:
        lines.append(f"- Unittest: **{unit_tests['status']}**, {unit_tests['tests_run']} test, exit code {unit_tests['return_code']}.")
    else:
        lines.append("- Unittest: chưa chạy trong lệnh này; kết quả PASS chỉ bao gồm các kiểm tra tích hợp của pipeline.")
    if failure:
        lines += ["", "## Lỗi", "", f"{failure}", "", "Lượt này không xác nhận đầu ra mới hợp lệ. Đầu ra cũ nếu còn tồn tại không phải bằng chứng chạy thành công.", ""]
    else:
        lines += ["", "## Nguồn và cấu hình", "",
                  f"- Dataset: {manifest.get('source_repository', manifest['source_file'])}.",
                  f"- Revision: `{manifest.get('source_revision', 'không có metadata')}`.",
                  f"- SHA-256 nguồn: `{manifest['source_sha256']}`.",
                  f"- Python: `{manifest['python_version']}`.",
                  f"- Preprocessing: `{manifest['preprocessing_version']}`.",
                  f"- Preparation: `{manifest['preparation_version']}`.",
                  f"- CSV encoding: `{manifest['csv_encoding']}`; JSON/Markdown: UTF-8.",
                  f"- Seed: `{manifest['seed']}`; Jaccard: `{manifest['jaccard_threshold']}`; split mục tiêu 70/15/15.",
                  "", "## Kết quả", "", "| Chỉ tiêu | Giá trị |", "| --- | ---: |"]
        for label, key in [
            ("Dòng nguồn", "raw_rows"), ("Bản lặp cùng nhãn đã bỏ", "removed_duplicate_extra_rows"),
            ("Dòng bất đồng nhãn tách riêng", "quarantined_source_rows"), ("Mẫu duy nhất", "clean_unique_rows"),
            ("Nhóm template", "template_groups"), ("Nhóm template nhãn hỗn hợp", "mixed_label_template_groups"),
            ("Nhóm template lớn nhất", "largest_template_group"), ("Ứng viên cần rà ẩn danh", "privacy_candidate_rows"),
            ("Dòng nguồn chứa U+FFFD", "source_unicode_replacement_rows"), ("Dòng nguồn chứa control C1", "source_c1_control_rows"),
            ("Dòng nguồn chứa mathematical Unicode", "source_mathematical_unicode_rows"),
        ]:
            lines.append(f"| {label} | {audit[key]} |")
        lines += [f"| Dòng nguồn thiếu ngày | {audit['missing_by_column']['date']} |", "",
                  "| Split | Tổng | Hợp lệ | Spam/scam |", "| --- | ---: | ---: | ---: |"]
        for name in ("train", "validation", "test"):
            part = audit["splits"][name]
            lines.append(f"| {name} | {part['rows']} | {part['labels']['0']} | {part['labels']['1']} |")
        lines += ["", "## Kiểm tra đầu ra trên đĩa", ""]
        for key, value in audit["serialization_checks"].items():
            lines.append(f"- `{key}`: `{value}`.")
        for pair, values in audit["leakage_checks"].items():
            lines.append(f"- `{pair}`: `{values}`.")
        lines += ["", "## Giới hạn và bước tiếp theo", "",
                  f"- Split: `{audit['split_status']}`; cần rà template và ẩn danh trước khi khóa benchmark.",
                  "- Regex ẩn danh chỉ gắn cờ ứng viên, có thể báo nhầm và bỏ sót; chưa tự che nội dung model.",
                  "- Chữ mathematical Unicode có từ nguồn; giữ lại như tín hiệu viết biến dạng, chưa coi là lỗi encoding.",
                  "- CSV có BOM hỗ trợ nhận diện UTF-8 khi mở trên Windows. Đọc bằng Python dùng encoding='utf-8-sig'. Không xác nhận hiển thị trực tiếp trên mọi ứng dụng.",
                  "- Nhãn dương gộp spam/scam; chưa huấn luyện hoặc đánh giá classifier trong bước này.",
                  "", "## Hash đầu ra", "", "| File | SHA-256 |", "| --- | --- |"]
        for name, digest in manifest["artifacts_sha256"].items():
            lines.append(f"| `{name}` | `{digest}` |")
        lines += ["", f"- Hash prepare_data.py: `{manifest['preparation_script_sha256']}`.",
                  f"- Hash preprocessing.py: `{manifest['preprocessing_script_sha256']}`.",
                  f"- Hash reporting.py: `{manifest['reporting_script_sha256']}`.", "",
                  "## Cách chạy lại", "", "Từ thư mục backend:", "", "```powershell",
                  "python src/ML/prepare_data.py --run-tests", "```", "",
                  "Mỗi lượt CLI lưu một preprocess_vN.md mới. Dataset CSV hiện hành được cập nhật ở data/processed/sms_v1; đây không phải kho snapshot dataset cho từng lượt.", ""]
    while True:
        target = report_dir / f"preprocess_v{number}.md"
        lines[0] = f"# Preprocess v{number}"
        try:
            with target.open("x", encoding="utf-8", newline="") as handle:
                handle.write("\n".join(lines))
            break
        except FileExistsError:
            number += 1
    return target
