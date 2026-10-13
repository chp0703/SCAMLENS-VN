# Preprocess v2

## Lượt chạy

- Thời điểm: 2026-10-14T01:14:02+07:00 (Asia/Ho_Chi_Minh).
- Trạng thái kiểm tra tự động: **PASS**.
- Số vN là số lượt báo cáo; phiên bản thuật toán được ghi riêng trong manifest.
- Unittest: **PASS**, 18 test, exit code 0.

## Nguồn và cấu hình

- Dataset: https://github.com/trannguyenthaituan251209/vietnamese_sms_dataset.
- Revision: `464a028878023598e16f2f344ee36f7d5d74257f`.
- SHA-256 nguồn: `710cd7b56ef1b4aa82e72c1be0f46a5c89a5fdce8382b30874b3cea494d16e3e`.
- Python: `3.12.14`.
- Preprocessing: `sms-nfc-whitespace-v1`.
- Preparation: `sms-grouped-preparation-v2-utf8bom`.
- CSV encoding: `utf-8-sig`; JSON/Markdown: UTF-8.
- Seed: `42`; Jaccard: `0.85`; split mục tiêu 70/15/15.

## Kết quả

| Chỉ tiêu | Giá trị |
| --- | ---: |
| Dòng nguồn | 2991 |
| Bản lặp cùng nhãn đã bỏ | 392 |
| Dòng bất đồng nhãn tách riêng | 2 |
| Mẫu duy nhất | 2597 |
| Nhóm template | 1985 |
| Nhóm template nhãn hỗn hợp | 3 |
| Nhóm template lớn nhất | 75 |
| Ứng viên cần rà ẩn danh | 285 |
| Dòng nguồn chứa U+FFFD | 0 |
| Dòng nguồn chứa control C1 | 0 |
| Dòng nguồn chứa mathematical Unicode | 2 |
| Dòng nguồn thiếu ngày | 15 |

| Split | Tổng | Hợp lệ | Spam/scam |
| --- | ---: | ---: | ---: |
| train | 1818 | 1321 | 497 |
| validation | 390 | 283 | 107 |
| test | 389 | 283 | 106 |

## Kiểm tra đầu ra trên đĩa

- `csv_utf8_bom`: `True`.
- `strict_utf8_decode`: `True`.
- `raw_message_round_trip`: `True`.
- `normalized_text_round_trip`: `True`.
- `source_ids_accounted_for`: `2991`.
- `serialized_split_accounting`: `True`.
- `serialized_split_leakage_checks`: `True`.
- `train__validation`: `{'group_id': 0, 'message_id': 0, 'text': 0}`.
- `train__test`: `{'group_id': 0, 'message_id': 0, 'text': 0}`.
- `validation__test`: `{'group_id': 0, 'message_id': 0, 'text': 0}`.
- `detected_template_edges_crossing_splits`: `0`.

## Giới hạn và bước tiếp theo

- Split: `provisional_pending_template_and_privacy_review`; cần rà template và ẩn danh trước khi khóa benchmark.
- Regex ẩn danh chỉ gắn cờ ứng viên, có thể báo nhầm và bỏ sót; chưa tự che nội dung model.
- Chữ mathematical Unicode có từ nguồn; giữ lại như tín hiệu viết biến dạng, chưa coi là lỗi encoding.
- CSV có BOM hỗ trợ nhận diện UTF-8 khi mở trên Windows. Đọc bằng Python dùng encoding='utf-8-sig'. Không xác nhận hiển thị trực tiếp trên mọi ứng dụng.
- Nhãn dương gộp spam/scam; chưa huấn luyện hoặc đánh giá classifier trong bước này.

## Hash đầu ra

| File | SHA-256 |
| --- | --- |
| `audit_report.json` | `d03dfaae5b8f45771bfc00c6d0dfebe114668662b736f1d2d60c30dbe68c4161` |
| `clean.csv` | `cad6faeac0591fe523238dd811674705bc7ce61bb776592538bb703a2d2d3720` |
| `duplicate_map.csv` | `c04644867977f9685a590773c89874c148d780175075f33a90048ce1682c7b37` |
| `privacy_review.csv` | `d014a90c2925ae5026bf5d64ace6cdafc36bfac7aa473589cc932926b67a7cb4` |
| `quarantine.csv` | `1659eff3e0f24ad56658f8ab9f064f364111a56459da6cc68fe59eb9153c23bd` |
| `template_edges.csv` | `5c3dfed06953571922c4a91631741d5478b9ece001b36db7873aa5e863b73447` |
| `template_review.csv` | `41a372b31a7a25f3341d02c6a855b205fce7636b66f76c73966b7a82a67371ec` |
| `test.csv` | `74f768bd409af82c7ad43737a3d71253b139dc502654610fc8d293e80db70c75` |
| `train.csv` | `a7a3e55c852aef6a6bdf9be137399daf156de03388fc191ed3a66d5e5ba7625c` |
| `validation.csv` | `1e4597d098cde62f763039c56fae8fd346d8fe3c2d14d4308790898c989472d9` |

- Hash prepare_data.py: `e479015ffe0a4d2e637576c70c712ce8fcf80578b9d428c007e590f4eb298d0f`.
- Hash preprocessing.py: `f143bd198ee20cc3156d6cc935d09b30127bf5a24866cd644c29a2b8c7708942`.
- Hash reporting.py: `95c6cb7c54f296e71c500ed2b5f6151a60bfdcaf585cb27d74b1e4590b69a276`.

## Cách chạy lại

Từ thư mục backend:

```powershell
python src/ML/prepare_data.py --run-tests
```

Mỗi lượt CLI lưu một preprocess_vN.md mới. Dataset CSV hiện hành được cập nhật ở data/processed/sms_v1; đây không phải kho snapshot dataset cho từng lượt.

## Chẩn đoán lỗi hiển thị và kiểm tra bổ sung

CSV v1 đọc đúng bằng UTF-8: toàn bộ 2.597 trường text khớp normalize_text của message gốc; không có ký tự thay thế U+FFFD. Dữ liệu nguồn có BOM, đầu ra v1 không có BOM. Thiếu tín hiệu nhận diện encoding là nguyên nhân khả dĩ khi mở CSV trực tiếp bằng ứng dụng Windows; chưa quan sát trực tiếp ứng dụng đã hiển thị lỗi trên máy người dùng.

Đã chuyển writer sang utf-8-sig và sinh lại toàn bộ 9 CSV. Với từng file v2, bỏ đúng 3 byte BOM rồi tính SHA-256 thu được hash CSV v1 được lưu trong preprocess_v1.md. Như vậy thay đổi encoding không làm đổi nội dung CSV, số mẫu, nhãn hoặc split.

Kiểm tra bổ sung trên dataset thật sau lượt CLI:

- Cả 9 CSV có BOM đúng, đọc UTF-8 strict được và tên cột không dính ký tự BOM.
- Chạy lại toàn pipeline bằng cùng seed cho tất cả artifact có hash giống nhau.
- SHA-256 dữ liệu gốc giữ nguyên; các hash artifact và code khớp manifest.
- Hai báo cáo đã có không bị ghi đè khi kiểm tra lại qua API run().
- Các link local trong README tổng thể và README backend đều tồn tại.
- Hai mẫu COM_1006 và COM_1063 có mathematical Unicode ngay từ nguồn; giữ nguyên nội dung để không xóa tín hiệu viết biến dạng. Các chữ Ã/Â trong nhiều mẫu là tiếng Việt hợp lệ (ví dụ ĐÃ, CÂY), không phải bằng chứng mojibake.

Mở lại CSV mới sinh. Nếu mở bằng Excel qua chức năng import, chọn UTF-8. Không thể sửa bản đã bị lưu sai encoding chỉ bằng cách thêm BOM vào bản hỏng.

Tài liệu: [Microsoft về CSV UTF-8 và BOM trong Excel](https://support.microsoft.com/en-us/excel/opening-csv-utf-8-files-correctly-in-excel), [Python utf-8-sig](https://docs.python.org/3/library/codecs.html#encodings.utf_8_sig).
