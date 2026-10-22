# Preprocessing v3

**Trạng thái: provisional — chưa đóng băng benchmark.**

Thời gian chạy (Asia/Ho_Chi_Minh): 2026-10-18T00:56:22.337832+07:00

SHA-256 nguồn: `710cd7b56ef1b4aa82e72c1be0f46a5c89a5fdce8382b30874b3cea494d16e3e`

Rules version: `1.0.0`; seed: `42`.

Nhãn `0 = Ham`, `1 = Scam`; nhãn 1 của nguồn bao gồm spam và scam.

## Cleaning và truy vết

| Trạng thái | Số mẫu |
|---|---:|
| kept | 2564 |
| duplicate | 423 |
| quarantined | 4 |
| rejected | 0 |

Tổng nguồn: **2991**; sạch: **2564**.

| Phân bố lớp | Ham | Scam |
|---|---:|---:|
| Nguồn | 2193 | 798 |
| Sạch | 1868 | 696 |

Mỗi dòng nguồn có đúng một trạng thái trong `data/processed/accounting.csv`. Các bảng rejected/quarantine, duplicate và review là dữ liệu local được Git ignore.

## Hai bộ split

| Tập | Số mẫu | Ham | Scam | Tỷ lệ trên dữ liệu sạch |
|---|---:|---:|---:|---:|
| ml/train.csv | 2001 | 1435 | 566 | 78.04% |
| ml/test.csv | 563 | 433 | 130 | 21.96% |
| dl_jev/train.csv | 1582 | 1129 | 453 | 61.70% |
| dl_jev/val.csv | 419 | 306 | 113 | 16.34% |
| dl_jev/test.csv | 563 | 433 | 130 | 21.96% |

ML test và DL/JEV test giống từng byte. ML train = DL train ∪ DL val. DL val là validation fold 0 của ML; cả hai model ML phải dùng bảng fold chung.

| CV validation fold | Số mẫu | Ham | Scam |
|---|---:|---:|---:|
| 0 | 419 | 306 | 113 |
| 1 | 414 | 318 | 96 |
| 2 | 390 | 264 | 126 |
| 3 | 396 | 289 | 107 |
| 4 | 382 | 258 | 124 |

## Độ dài và review

| Độ dài | Min | P25 | Median | P75 | P95 | Max |
|---|---:|---:|---:|---:|---:|---:|
| char | 1.00 | 127.00 | 166.00 | 254.00 | 379.00 | 881.00 |
| word | 1.00 | 24.00 | 33.00 | 50.00 | 75.00 | 180.00 |

- Nhóm cần review: **172**; nhóm lớn (≥10 mẫu): **4**.
- Nhóm gần trùng khác nhãn: **2**; outlier IQR: **64** mẫu (giữ lại).
- Nhóm lớn nhất: **67** mẫu; cặp gần trùng: **1251**.

Review các bảng `groups.csv`, `near_duplicate_pairs.csv`, `length_outliers.csv` trước khi đóng băng. Connected components có thể nối chuỗi; ngưỡng Jaccard 0.85 không bảo đảm phát hiện hết template leakage.

## Kiểm chứng

- `id_text_group_disjoint`: PASS
- `clean_rows_accounted`: PASS
- `shared_test_identical`: PASS
- `dl_union_equals_ml_train`: PASS
- `cv_train_ids_once`: PASS
- `cv_fold0_equals_dl_val`: PASS
- `all_partitions_have_both_classes`: PASS
- `source_accounting_complete`: PASS
- `normalized_raw_roundtrip`: PASS
- `normalization_idempotent`: PASS
- `source_sha256_unchanged`: PASS
- `csv_utf8_bom_roundtrip`: PASS
- `shared_test_hash_identical`: PASS
- Unit/integration tests: PASS (29 tests)

Hash tất cả CSV, cấu hình và phiên bản dependencies có trong `data/splits/manifest.json`. CSV đã được đọc lại để kiểm tra BOM, UTF-8 và giá trị từng ô. Test giữ riêng cho đánh giá cuối; không dùng để tuning, chọn threshold, prompt hoặc few-shot.
