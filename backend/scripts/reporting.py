"""Append-only, aggregate reports without raw message contents."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import re


def append_report(directory: Path, manifest: dict, test_result: dict) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    versions = [int(match.group(1)) for path in directory.glob("preprocess_v*.md")
                if (match := re.fullmatch(r"preprocess_v(\d+)\.md", path.name))]
    version = max(versions, default=0) + 1
    lines = [f"# Preprocessing v{version}", "", "**Trạng thái: provisional — chưa đóng băng benchmark.**", "",
             f"Thời gian chạy (Asia/Ho_Chi_Minh): {datetime.now(timezone(timedelta(hours=7))).isoformat()}", "",
             f"SHA-256 nguồn: `{manifest['source']['sha256']}`", "",
             f"Rules version: `{manifest['rules']['version']}`; seed: `{manifest['split']['random_state']}`.", "",
             "Nhãn `0 = Ham`, `1 = Scam`; nhãn 1 của nguồn bao gồm spam và scam.", "",
             "## Cleaning và truy vết", "", "| Trạng thái | Số mẫu |", "|---|---:|"]
    for name, count in manifest["counts"]["accounting"].items():
        lines.append(f"| {name} | {count} |")
    lines += ["", f"Tổng nguồn: **{manifest['counts']['source']}**; sạch: **{manifest['counts']['clean']}**.", "",
              "| Phân bố lớp | Ham | Scam |", "|---|---:|---:|",
              f"| Nguồn | {manifest['counts']['source_labels'].get('0', 0)} | {manifest['counts']['source_labels'].get('1', 0)} |",
              f"| Sạch | {manifest['counts']['clean_distribution']['ham']} | {manifest['counts']['clean_distribution']['scam']} |", "",
              "Mỗi dòng nguồn có đúng một trạng thái trong `data/processed/accounting.csv`. "
              "Các bảng rejected/quarantine, duplicate và review là dữ liệu local được Git ignore.", "",
              "## Hai bộ split", "", "| Tập | Số mẫu | Ham | Scam | Tỷ lệ trên dữ liệu sạch |",
              "|---|---:|---:|---:|---:|"]
    total = manifest["counts"]["clean"]
    for name, stats in manifest["partitions"].items():
        lines.append(f"| {name} | {stats['rows']} | {stats['ham']} | {stats['scam']} | {stats['rows'] / total:.2%} |")
    lines += ["", "ML test và DL/JEV test giống từng byte. ML train = DL train ∪ DL val. "
              "DL val là validation fold 0 của ML; cả hai model ML phải dùng bảng fold chung.", "",
              "| CV validation fold | Số mẫu | Ham | Scam |", "|---|---:|---:|---:|"]
    for fold, stats in manifest["checks"]["cv_validation_statistics"].items():
        lines.append(f"| {fold} | {stats['rows']} | {stats['ham']} | {stats['scam']} |")
    lines += ["", "## Độ dài và review", "", "| Độ dài | Min | P25 | Median | P75 | P95 | Max |",
              "|---|---:|---:|---:|---:|---:|---:|"]
    for name, stats in manifest["length_statistics"].items():
        values = " | ".join(f"{stats[key]:.2f}" for key in ("min", "p25", "median", "p75", "p95", "max"))
        lines.append(f"| {name} | {values} |")
    review = manifest["review"]
    lines += ["", f"- Nhóm cần review: **{review['pending_groups']}**; nhóm lớn (≥10 mẫu): **{review['large_groups']}**.",
              f"- Nhóm gần trùng khác nhãn: **{review['mixed_label_groups']}**; outlier IQR: **{review['length_outliers']}** mẫu (giữ lại).",
              f"- Nhóm lớn nhất: **{review['largest_group']}** mẫu; cặp gần trùng: **{review['near_duplicate_pairs']}**.", "",
              "Review các bảng `groups.csv`, `near_duplicate_pairs.csv`, `length_outliers.csv` trước khi đóng băng. "
              "Connected components có thể nối chuỗi; ngưỡng Jaccard 0.85 không bảo đảm phát hiện hết template leakage.", "",
              "## Kiểm chứng", ""]
    for name, passed in manifest["checks"].items():
        if isinstance(passed, bool):
            lines.append(f"- `{name}`: {'PASS' if passed else 'FAIL'}")
    lines += [f"- Unit/integration tests: {test_result['status']}" +
              (f" ({test_result['tests_run']} tests)" if "tests_run" in test_result else ""), "",
              "Hash tất cả CSV, cấu hình và phiên bản dependencies có trong `data/splits/manifest.json`. "
              "CSV đã được đọc lại để kiểm tra BOM, UTF-8 và giá trị từng ô. "
              "Test giữ riêng cho đánh giá cuối; không dùng để tuning, chọn threshold, prompt hoặc few-shot.", ""]
    while True:
        path = directory / f"preprocess_v{version}.md"
        try:
            with path.open("x", encoding="utf-8", newline="\n") as stream:
                lines[0] = f"# Preprocessing v{version}"
                stream.write("\n".join(lines))
            return path
        except FileExistsError:
            version += 1
