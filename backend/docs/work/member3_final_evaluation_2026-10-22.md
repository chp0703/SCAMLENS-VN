# Nhật ký Member 3 — đánh giá cuối cùng LR/SVM

- Thời gian ghi nhận: 22/10/2026 22:15:52 UTC+07:00.
- Nhánh: `feat/member3-evaluation`.
- Commit framework: `87466bd61067c04606861e508d859c4a6b11b7e8`.
- Benchmark run ID: `20261022T151307621096Z-5198d4ec`.

## Yêu cầu và phạm vi

Kéo nhánh Member 3, sử dụng hai artifact LR/SVM đã có trên máy để đánh giá tập test cố định; ghi báo cáo Markdown trong `backend/docs/work` và `backend/report`. Người dùng đã yêu cầu chạy đánh giá cuối cùng, đáp ứng xác nhận cho cờ `--confirm-final-test`.

## Việc đã thực hiện

1. Fetch origin và tạo nhánh local `feat/member3-evaluation` theo dõi `origin/feat/member3-evaluation` tại commit nêu trên. Giữ nguyên thay đổi local và artifact có sẵn.
2. Đối soát hash train/CV của hai metadata với dữ liệu hiện tại; xác nhận test 563 tin (433 Ham, 130 spam/scam), train 2.001 tin và train/test không trùng ID/group.
3. Chạy 9 test evaluation trên nhánh hiện tại: 9/9 pass.
4. Chạy final benchmark trên hai pipeline có sẵn, percentile và paired bootstrap 2.000 lần, mức tin cậy 95%, seed 42. Không train/tune/fit TF-IDF/chọn threshold trong phiên này.
5. Xuất JSON và Markdown gốc vào `backend/report/benchmark`; lập báo cáo diễn giải trong `backend/report`.
6. Tính lại metrics từ confusion matrix và kiểm tra hash sau chạy: kết quả khớp, bốn file artifact/metadata không đổi.

## Kết quả

| Model | Accuracy | Precision lớp 1 | Recall lớp 1 | F1 lớp 1 | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| LR | 97.51% | 92.65% | 96.92% | 94.74% | 10 | 4 |
| SVM | 97.16% | 91.91% | 96.15% | 93.98% | 11 | 5 |

F1 LR − SVM = 0.7519 điểm phần trăm; CI paired bootstrap 95% = [0.0000; 1.9950] điểm phần trăm. LR nhỉnh hơn trên tập này; CI chứa 0 nên chưa khẳng định khác biệt rõ ràng.

## Hồ sơ kết quả

- [Báo cáo đánh giá đầy đủ](../../report/final_benchmark_lr_svm_2026-10-22.md).
- [JSON benchmark](../../report/benchmark/20261022T151307621096Z-5198d4ec.json).
- [Markdown benchmark gốc](../../report/benchmark/20261022T151307621096Z-5198d4ec.md).

## Điểm cần theo dõi

- Dữ liệu vẫn `provisional`; test có 31 nhóm pending (162 tin). Kết quả phụ thuộc nhãn hiện tại.
- CI hiện bootstrap theo tin nhắn, chưa theo group; nguồn gộp spam/scam nên không phải benchmark scam-only.
- Artifact legacy; báo cáo đầy đủ lưu hash chính xác của model/metadata. Metadata ghi Python train 3.13.16; đánh giá chạy thành công bằng Python 3.12.14 với cùng phiên bản sklearn/NumPy/joblib.
- Không dùng test vừa mở để tune hoặc chọn lại threshold. Chưa chạy benchmark DL/JEV; báo cáo này chỉ gồm LR/SVM.
- Phạm vi commit kết quả: hai báo cáo Markdown trong `docs/work` và `report`, cùng cặp JSON/Markdown benchmark gốc trong `report/benchmark`. Hash artifact dùng để đánh giá được ghi trong báo cáo đầy đủ.

## Lệnh đã chạy

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
