# Báo cáo đánh giá cuối cùng LR/SVM trên tập test

- Ngày lập báo cáo: 22/10/2026 22:15:52 UTC+07:00.
- Nhánh thực hiện: `feat/member3-evaluation`; commit mã đánh giá: `87466bd61067c04606861e508d859c4a6b11b7e8`.
- Benchmark run ID: `20261022T151307621096Z-5198d4ec`.
- Trạng thái thực thi: thành công trên hai artifact local đã được người dùng cho phép đánh giá. Trạng thái dữ liệu trong manifest vẫn là `provisional`.

## 1. Kết quả chính

LR đạt F1 94.74%, SVM đạt 93.98%. Chênh lệch quan sát là 0.7519 điểm phần trăm theo chiều LR − SVM. Khoảng tin cậy paired bootstrap 95% của chênh lệch chứa 0; kết quả này chưa đủ để khẳng định LR vượt SVM một cách rõ ràng.

| Model | Accuracy | Precision lớp 1 | Recall lớp 1 | F1 lớp 1 | CI 95% của F1 |
|---|---:|---:|---:|---:|---:|
| Logistic Regression | 97.51% | 92.65% | 96.92% | 94.74% | [91.67%; 97.26%] |
| Linear SVM (LinearSVC) | 97.16% | 91.91% | 96.15% | 93.98% | [90.71%; 96.75%] |

Lớp 0 = Ham; lớp 1 = nhãn spam/scam gộp của nguồn dữ liệu. Không diễn giải F1 lớp 1 thành khả năng nhận diện riêng mọi hình thức lừa đảo ngoài thực tế.

## 2. Dữ liệu và protocol

- Train: 2.001 tin nhắn; test: 563 tin nhắn, gồm 433 Ham và 130 spam/scam (23.09%).
- Test gồm 432 nhóm `group_id`; nhóm lớn nhất có 67 tin; 162 tin nằm trong nhóm có nhiều hơn một tin.
- `load_ml_data()` đã kiểm tra hash train/test/CV theo manifest, ID và group không giao nhau giữa train/test, cùng cấu trúc fold hợp lệ.
- Hash train và CV trong metadata của cả hai model khớp dữ liệu hiện tại; metadata ghi nhận cùng 2.001 mẫu train và `PredefinedSplit` 5 fold.
- Phiên đánh giá này chỉ load pipeline đã fit và gọi `predict()` trên cùng test set; không train, tune, fit lại TF-IDF hay chỉnh threshold.
- Dùng dự đoán nhị phân mặc định của artifact. Không chọn lại siêu tham số hoặc threshold sau khi xem test.
- Bootstrap percentile: 2.000 lần, confidence level 0,95, seed 42. Paired bootstrap dùng cùng chỉ số lấy mẫu cho LR/SVM. Mẫu bootstrap thiếu một lớp vẫn được giữ với `zero_division=0`.

## 3. Confusion matrix và các lỗi

| Model | TN | FP: Ham bị báo lớp 1 | FN: lớp 1 bị bỏ sót | TP | Tổng lỗi |
|---|---:|---:|---:|---:|---:|
| LR | 423 | 10 | 4 | 126 | 14 |
| SVM | 422 | 11 | 5 | 125 | 16 |

LR có ít hơn SVM 1 false positive và 1 false negative trên tập test này. Đây là chênh lệch quan sát trên một tập test cố định.

## 4. Khoảng tin cậy và so sánh cặp

| Metric | LR: estimate và CI 95% | SVM: estimate và CI 95% | LR − SVM (điểm phần trăm) | CI 95% của chênh lệch (điểm phần trăm) |
|---|---:|---:|---:|---:|
| Accuracy | 97.51% [96.09%; 98.76%] | 97.16% [95.74%; 98.58%] | 0.3552 | [0.0000; 0.8881] |
| Precision lớp 1 | 92.65% [87.83%; 96.69%] | 91.91% [86.96%; 96.06%] | 0.7353 | [0.0000; 2.3719] |
| Recall lớp 1 | 96.92% [93.55%; 99.31%] | 96.15% [92.59%; 99.22%] | 0.7692 | [0.0000; 2.4793] |
| F1 lớp 1 | 94.74% [91.67%; 97.26%] | 93.98% [90.71%; 96.75%] | 0.7519 | [0.0000; 1.9950] |

Không diễn giải khoảng tin cậy chạm/bao gồm 0 thành bằng chứng hai model tương đương; cũng không khẳng định có khác biệt rõ ràng từ kết quả này.

## 5. Artifact và dấu vết tái lập

| Model | Artifact run ID | Siêu tham số đã chốt từ CV |
|---|---|---|
| LR | `20261020T111352332347Z-493e9e46` | `C=10`, `class_weight=balanced` |
| SVM | `20261020T181805443565Z-82737509` | `C=1`, `class_weight=balanced` |

- Runtime đánh giá: Python 3.12.14, scikit-learn 1.7.2, NumPy 2.5.4, joblib 1.6.0.
- Metadata của cả hai artifact ghi Python train 3.13.16; runtime đánh giá là Python 3.12.14. Phiên bản scikit-learn/NumPy/joblib khớp metadata; load và predict thực tế đã thành công.
- Hai artifact local ở dạng legacy `model.joblib` + `metadata.json`, không có `current.json`. SHA-256 dưới đây ghi nhận đúng cặp file đã dùng trong phiên này; cả bốn file không đổi trước/sau benchmark.

| File (tương đối từ backend/) | SHA-256 |
|---|---|
| `artifacts/logistic_regression/metadata.json` | `779ee4cb5666c2fc440b502635b90a23b26a1aa2e5684047290338797f80d975` |
| `artifacts/logistic_regression/model.joblib` | `ddeacc87611d85d09992c6c5c58b8b1a5fac7e7607faba8123b42d50b6c95e9f` |
| `artifacts/svm/metadata.json` | `2e31ff51374cf515622887412b9186678eb526e03af21154f3dc563058f18512` |
| `artifacts/svm/model.joblib` | `f1b8aa616cc119e0882e72f38a1bcbcfc1f7b3c4bafaf119be2cb4c66d02717b` |
| `data/splits/ml/train.csv` | `f584db089f3558b382a7ce0707a31a31cc5eae0835ad05374fd86c6e5f09fa12` |
| `data/splits/ml/test.csv` | `9cad49dd254f6a9db41f72593a379b80c646ba421c00fd8ac7cc86a1d83c7ec8` |
| `data/splits/ml/cv_folds.csv` | `a773f95871c200e62c0f4209877b7926a43d34e94c3aa9cb466dd842e3f69e44` |
| `data/splits/manifest.json` | `75396a483de7763f3ad4f9391f789a3240313c6fa38b33260a0c578c6d4d81a0` |

- Test message-ID sequence SHA-256: `222e1858a751c6d4a8109990e9b727d4918180fa40993f706163e6007aebbf50`.
- [Kết quả JSON đầy đủ](benchmark/20261022T151307621096Z-5198d4ec.json).
- [Bảng benchmark gốc do CLI xuất](benchmark/20261022T151307621096Z-5198d4ec.md).

## 6. Giới hạn và cách sử dụng kết quả

1. Manifest còn `provisional`, ghi 172 nhóm cần review trên toàn dữ liệu. Trong test hiện có 31 nhóm pending, tương ứng 162 tin. Chưa có bằng chứng review thủ công đã đóng hết các trường hợp này.
2. Bootstrap hiện lấy mẫu theo từng tin nhắn, chưa bootstrap theo `group_id`. Vì test có nhóm gần trùng, các CI trên chỉ phản ánh phương pháp theo tin nhắn này; chưa bao quát độ bất định khi lấy mẫu theo nhóm.
3. Nhãn nguồn gộp spam/scam; chưa đo riêng scam-only, tin nhắn từ nguồn khác hoặc dữ liệu xuất hiện trong tương lai.
4. Không điều chỉnh model bằng tập test đã mở. Nếu cần phát triển tiếp, dùng train/CV và một tập đánh giá mới cho lần xác nhận độc lập tiếp theo.
5. Kiểm tra metadata/hash xác nhận dữ liệu phù hợp và artifact không đổi trong phiên này; không tự chứng minh toàn bộ lịch sử trước đó chưa từng xem test. Khẳng định không train/tune trên test áp dụng cho phiên chạy được ghi nhận ở báo cáo này.
6. LR nhỉnh hơn về điểm quan sát; chưa có cơ sở từ CI hiện tại để tuyên bố LR vượt trội hoặc hai model tương đương. Không dùng bảng test làm vòng chọn cấu hình mới.

## 7. Kiểm chứng và tái lập

- Chạy lại `python -B -m unittest backend.tests.test_evaluation -v` trên nhánh member 3: 9/9 test pass.
- Benchmark thực tế trên hai artifact local và 563 mẫu test: thành công.
- Đối soát độc lập Accuracy/Precision/Recall/F1 bằng TN/FP/FN/TP trong JSON: khớp; tổng confusion matrix và số lượng từng lớp khớp test CSV.
- Hash test khớp manifest và JSON; chuỗi message ID khớp JSON; hash train/CV khớp metadata của cả hai model.
- Đã so hash cả bốn file model/metadata trước và sau benchmark: không đổi.

Để tái lập đúng phiên bản và dữ liệu đã ghi ở trên, dùng lệnh dưới đây. Chỉ chạy lại khi có nhu cầu kiểm chứng; không dùng kết quả để chỉnh mô hình.

```powershell
# Từ thư mục gốc repository
Set-Location backend
..\.venv-preprocessing\Scripts\python.exe -B -m evaluation.benchmark `
  --confirm-final-test `
  --data-dir data/splits/ml `
  --manifest data/splits/manifest.json `
  --lr-artifact-dir artifacts/logistic_regression `
  --svm-artifact-dir artifacts/svm `
  --report-dir report/benchmark `
  --bootstrap-replicates 2000 `
  --confidence-level 0.95 `
  --seed 42
```

- [Nhật ký thực hiện Member 3](../docs/work/member3_final_evaluation_2026-10-22.md).
