# Preprocess v1

## Phạm vi và xuất xứ

Báo cáo bổ sung từ đầu ra preprocessing v1 đang có trong repo và bằng chứng kiểm thử ở lượt làm trước. Không chạy lại hoặc gán thời gian giả cho lượt chạy cũ. Thời điểm dưới đây là lúc lưu báo cáo.

- Lưu báo cáo: 2026-10-14T01:09:54+07:00.
- Python ghi trong manifest đang có: `3.11.9`.
- Preprocessing: `sms-nfc-whitespace-v1`.
- Preparation: `sms-grouped-preparation-v1`.
- Dataset revision: `464a028878023598e16f2f344ee36f7d5d74257f`.
- SHA-256 nguồn: `710cd7b56ef1b4aa82e72c1be0f46a5c89a5fdce8382b30874b3cea494d16e3e`.
- Seed: `42`; Jaccard: `0.85`.

## Kết quả

| Chỉ tiêu | Giá trị |
| --- | ---: |
| Dòng nguồn | 2991 |
| Bản lặp cùng nhãn đã bỏ | 392 |
| Dòng bất đồng nhãn tách riêng | 2 |
| Mẫu duy nhất dùng chia split | 2597 |
| Dòng thiếu ngày trong nguồn | 15 |
| Ứng viên cần rà ẩn danh | 285 |

| Split | Tổng | Hợp lệ | Spam/scam |
| --- | ---: | ---: | ---: |
| train | 1818 | 1321 | 497 |
| validation | 390 | 283 | 107 |
| test | 389 | 283 | 106 |

## Kiểm thử đã ghi nhận

- Lượt làm trước trong chat: 14 unittest đạt; chạy lại toàn dataset có hash đầu ra giống nhau; kiểm tra độc lập không có cặp template đã phát hiện giao split. Không có log unittest riêng gắn với lượt chạy Python 3.11.9 hiện ghi trong manifest.
- Kiểm tra lại trước khi sửa v2: toàn bộ 2.597 cột text khớp chuẩn hóa từ message gốc, không có ký tự thay thế U+FFFD; nguồn không có control code C1.
- CSV v1 viết UTF-8 không BOM. CSV nguồn có BOM. Do đó v1 có thể hiển thị sai tiếng Việt khi ứng dụng đoán nhầm encoding.
- Dataset gốc có 2 dòng chứa chữ mathematical Unicode: COM_1006 và COM_1063. Đây là đặc điểm nguồn, chưa kết luận là lỗi font do preprocessing.

## Vấn đề cần xử lý

- Thêm BOM vào CSV xuất ra và kiểm thử hồi quy đọc/ghi Unicode ở v2.
- Hai ID COM_2990 và COM_2055 có cùng duplicate_key nhưng khác nhãn; chưa tự gán nhãn mới.
- Có 3 nhóm template nhãn hỗn hợp; nhóm lớn nhất 75 mẫu duy nhất.
- Các regex ẩn danh chỉ xác định ứng viên, có báo nhầm và bỏ sót. Không kết luận tất cả là PII bị lộ.
- Split vẫn dự kiến, cần rà template và ẩn danh trước khi khóa benchmark; chưa train model hoặc fit TF-IDF.

## Hash đầu ra v1 tại lúc lưu báo cáo

| File | SHA-256 |
| --- | --- |
| `audit_report.json` | `e0c3abb443816ffa240c1cddd3c3d878df888f689de2512a13fcd5a8b256877c` |
| `clean.csv` | `aaec33b64c2cce8c0d51e4b18c808d829476b1992a221e35180ab3e36aa88827` |
| `duplicate_map.csv` | `c8d88bac35bc92f9c61b3e76edd996d04e7b5078186bb8dab6e5586bcd473443` |
| `privacy_review.csv` | `ab09038f225c25168188129d4dc82a5d658e559f2128b5eb734bbde96bfa69e3` |
| `quarantine.csv` | `5f261a56f15de46163da485a2c8f90391a7821842bb436db78c78fb581e048c4` |
| `template_edges.csv` | `a7ee1444daa6e89adda45864f496bdab39b52f562eb29aa86ad768c414e2377d` |
| `template_review.csv` | `9ba4be1b52056b60f29ce387f13082c16c4c821f8ddc04d8a05c3826a273d2e8` |
| `test.csv` | `1e4ce8c628350924e213c3d39b055f4ddd3daeab58b8e7610a3b128a11740cca` |
| `train.csv` | `c8f844dd50d33dd60276e60a7990513975851379db3b17ac6d647c2707485f44` |
| `validation.csv` | `3b8a7f5c4990ae169a7caf3c4366be0ebd2be3fd080136ffcd393f21f76e03dd` |

- Hash prepare_data.py: `8f34d6684e7043f94f42833a4fc57bd3ab1780e41847de01d5de9240d1af0c09`.
- Hash preprocessing.py: `f143bd198ee20cc3156d6cc935d09b30127bf5a24866cd644c29a2b8c7708942`.

## Tài liệu encoding

- [Microsoft: mở CSV UTF-8 trong Excel](https://support.microsoft.com/en-us/excel/opening-csv-utf-8-files-correctly-in-excel).
- [Python: utf-8-sig](https://docs.python.org/3/library/codecs.html#encodings.utf_8_sig).
