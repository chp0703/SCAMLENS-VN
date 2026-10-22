# Model dùng chung của ScamLens VN

## Bản đang ghim

Bundle `ml-evaluated-20261022-v1` gồm đúng hai pipeline đã đánh giá trong benchmark `20261022T151307621096Z-5198d4ec`. Dataset vẫn `provisional`; đây là bản dùng chung để phát triển/tái lập kết quả, chưa phải tuyên bố sẵn sàng production.

| Model key | Run ID | Siêu tham số đã chọn bằng CV |
|---|---|---|
| `logistic_regression` | `20261020T111352332347Z-493e9e46` | `C=10`, `class_weight=balanced` |
| `svm` | `20261020T181805443565Z-82737509` | `C=1`, `class_weight=balanced` |

`backend/models.lock.json` là nguồn xác định bản dùng chung. Nó ghi đường dẫn snapshot, SHA-256 model/metadata, nguồn train/CV, preprocessing, runtime và smoke cases. Cùng tên model hoặc cùng hyperparameter chưa đủ: các thành viên cần cùng commit chứa lock file và tải đúng binary LFS.

```text
backend/
├── models.lock.json
├── requirements-models.lock.txt
├── artifacts/
│   ├── approved/
│   │   ├── logistic_regression/<run_id>/{model.joblib,metadata.json}
│   │   ├── svm/<run_id>/{model.joblib,metadata.json}
│   │   └── smoke_cases.json
│   ├── logistic_regression/   # Output training local, được ignore
│   └── svm/                   # Output training local, được ignore
└── scripts/verify_models.py
```

Pipeline lưu cả TF-IDF đã fit và classifier. Normalization raw text nằm tại `app/services/preprocessing.py`, được kiểm tra cả rules version và SHA-256 sau chuẩn hóa line ending LF. Hash của binary/metadata được kiểm tra theo byte chính xác.

## Thành viên tải về và kiểm tra

Chạy từ gốc repo sau khi đã cài Git LFS:

```powershell
git lfs install --local
git pull --ff-only
git lfs pull
```

Chọn cùng nhánh/commit đã được team chốt. Nhánh tích hợp hiện tại là `feat/baseline-ml`, hợp nhất preprocessing và cả ba nhánh Member 1/2/3; khi PR được merge, team chuyển về commit tương ứng trên `main`. LFS lưu binary ngoài Git object thông thường; phải tải được cả binary, không chỉ pointer.

Môi trường chính thức cho bundle này: Python 3.12.x (đã kiểm chứng 3.12.14), cùng phiên bản package khóa trong `requirements-models.lock.txt`. Dùng môi trường riêng nếu môi trường dev có dependencies khác:

```powershell
py -3.12 -m venv .venv-models
.\.venv-models\Scripts\python.exe -m pip install -r backend/requirements-models.lock.txt
.\.venv-models\Scripts\python.exe -B backend/scripts/verify_models.py
```

Nếu đang dùng `.venv-preprocessing` đã khớp lock, có thể dùng Python của môi trường đó. Linux/macOS dùng `python3.12` để tạo venv và đường dẫn `.venv-models/bin/python`. Cài thêm `backend/requirements.txt` khi cần công cụ training/backend; chạy lại verifier sau khi cài để phát hiện package bị đổi. Verifier kiểm tra Python major/minor và exact version của sklearn, NumPy, SciPy, joblib, threadpoolctl.

Kết quả thành công phải có `status: PASS`, đúng bundle ID và 6 cases cho mỗi model. Đây là input tổng hợp để phát hiện lệch pipeline; nhãn lưu trong fixture là đầu ra tham chiếu, không phải ground truth hay phép đo chất lượng. Verifier không đọc `test.csv`, không train model và không tính lại benchmark.

## Inference thống nhất

Chạy Python từ `backend/`:

```python
from src.ML.approved_models import predict_approved_texts

result = predict_approved_texts("logistic_regression", ["Tin nhắn người dùng nhập"])
print(result["labels"])
print(result["bundle_id"], result["run_id"])
```

`predict_approved_texts()` nhận raw text, normalize bằng code đã ghim, rồi gọi `pipeline.predict()`. Label 0 là Ham, label 1 là spam/scam gộp của nguồn. Cả hai dùng decision boundary mặc định 0 của `decision_function`; score không phải xác suất. Không tự sigmoid SVM hoặc đổi threshold ở từng service.

Nếu đã có dữ liệu normalized từ pipeline chung (như benchmark), dùng `load_approved_artifact(model_key)` để lấy fitted pipeline và metadata, rồi gọi `predict()` trực tiếp. Hàm này không normalize input. Model được xác minh trước khi deserialize; không lấy bản khác từ `current.json` local nếu kiểm tra thất bại.

Benchmark mặc định dùng cả hai artifact đã ghim. Override đồng thời `--lr-artifact-dir` và `--svm-artifact-dir` chỉ dành cho thí nghiệm local; JSON kết quả ghi nguồn artifact. Không chạy lại final test để chọn hyperparameter/threshold sau khi đã xem kết quả.

## Rule phát hành và cập nhật

1. Người phụ trách model train/tune trong thư mục local được ignore; không output trực tiếp vào `artifacts/approved`.
2. Chọn cấu hình bằng train/CV theo protocol đã chốt. Bundle hiện tại chọn theo F1 lớp 1, beta = 1. Đổi sang F2/ưu tiên recall cần protocol và lượt train/chọn cấu hình mới; không sửa nhãn metric của model cũ.
3. Khi cần chia sẻ, tạo thư mục snapshot mới theo run ID, sao chép nguyên `model.joblib` và `metadata.json`; không ghi đè version cũ. Nếu version cũ chỉ có ở máy khác, phải tải về trước thay vì tự train một bản thay thế.
4. Cập nhật lock trong cùng PR: đường dẫn/run ID, SHA-256 của hai file, training source hash, bundle ID, preprocessing/runtime liên quan và provenance. Không bịa commit hoặc runtime training còn thiếu; metadata gốc của hai bản đầu tiên được giữ nguyên byte, runtime đã kiểm chứng được ghi riêng trong lock.
5. Tạo lại smoke fixture từ raw text tổng hợp; review nhãn/score tham chiếu và hash fixture. Không lấy tin nhắn của final test hoặc dữ liệu riêng tư làm fixture chia sẻ.
6. Đính kèm báo cáo validation, chạy verifier và unit tests. Reviewer kiểm tra model/metadata/lock đi cùng nhau và thư mục version cũ không bị sửa.
7. Người tích hợp duyệt PR rồi chốt commit dùng chung. Việc bắt buộc reviewer/branch protection cần cài trong GitHub; triển khai hiện tại cung cấp rule và kiểm tra local, chưa cấu hình bảo vệ nhánh trên server.
8. Các thành viên pull commit đã chốt, chạy `git lfs pull`, rồi verifier trước khi inference. Thiếu file, sai hash, lệch môi trường/preprocessing thì sửa nguyên nhân; không tự động train hoặc fallback sang model local.
9. Log/báo cáo phải ghi bundle ID, run ID, hash artifact, dữ liệu và decision rule. Threshold mới phải được đánh giá và version riêng, với code thực hiện tương ứng; loader hiện từ chối threshold khác mặc định.
10. Chỉ load joblib từ nguồn team tin cậy. Hash giúp phát hiện sai file; nó không chứng minh nguồn đáng tin nếu chính lock file đã bị thay từ nguồn không tin cậy.

Binary `.joblib` được LFS quản lý; JSON, lock, code và báo cáo nằm trong Git thường. `.gitignore` chỉ cho phép chia sẻ snapshot và fixture đã chọn, các output training khác vẫn local. Git LFS có quota storage/bandwidth của chủ repo; không đẩy toàn bộ checkpoints hoặc mọi lượt thử nghiệm. GitHub Releases có thể bổ sung khi phát hành demo; lượt này dùng Git LFS cùng commit, chưa tạo Release riêng.

## Chuyển đổi từ artifact legacy

Hai file LR ở đường dẫn legacy được bỏ tracking từ commit triển khai, giữ nguyên trên máy đang làm việc; SVM local cũng được giữ. Snapshot mới chứa đúng các byte đã benchmark và được lưu qua LFS. Không rewrite lịch sử hoặc force-push; binary LR cũ vẫn tồn tại trong các commit trước.

Loader thí nghiệm `src.ML.artifacts.load_artifact()` vẫn hỗ trợ cấu trúc legacy và `runs/current.json`. Loader dùng chung `src.ML.approved_models.load_approved_artifact()` luôn theo lock, nên tuning local không đổi model của team.

## Nguồn hướng dẫn

- [Git LFS FAQ: pointer, tracking và file đã tồn tại](https://github.com/git-lfs/git-lfs/blob/main/docs/man/git-lfs-faq.adoc).
- [GitHub: quota storage và bandwidth LFS](https://docs.github.com/en/billing/concepts/product-billing/git-lfs).
- [scikit-learn: model persistence, môi trường và nguồn tin cậy](https://scikit-learn.org/stable/model_persistence.html).
