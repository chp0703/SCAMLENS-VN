# ScamLens VN — Backend

Backend gồm ứng dụng FastAPI, công cụ chuẩn bị dữ liệu, các hướng phát triển model ML/DL/JEV và bộ đánh giá chung. Phạm vi dự kiến là phân tích văn bản người dùng nhập thủ công.

## Trạng thái hiện tại

Đây là **khung phát triển**, chưa phải backend chạy hoàn chỉnh:

- `app/` và các test hiện có là file khung, chưa có FastAPI app, endpoint hoặc inference thật.
- `scripts/build_dataset.py` và `scripts/merge_team.py` có logic từ `build_dataset/` cũ, được chuyển nguyên nội dung.
- Module mới trong `src/`, `evaluation/`, `scripts/prepare_data.py`, `scripts/split_data.py` chỉ có docstring đánh dấu chưa triển khai. Chạy chúng chưa tạo kết quả.
- `lr.yaml` và `svm.yaml` là cấu hình rỗng (`{}`); chưa có hyperparameter mặc định hay loader YAML.
- `JEV/` là tên khu vực theo thiết kế; chưa chốt thư viện, giao thức hoặc tiêu chí tích hợp. Chưa có kết nối JEV thật.

## Cấu trúc thư mục

```text
backend/
├── app/
│   ├── api/
│   │   └── routes.py
│   ├── core/
│   │   └── config.py
│   ├── schemas/
│   │   └── prediction.py
│   ├── services/
│   │   ├── classifier.py
│   │   ├── preprocessing.py
│   │   └── llm_service.py
│   └── main.py
├── src/
│   ├── __init__.py
│   ├── ML/
│   │   ├── __init__.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── logistic_regression.py
│   │   │   └── svm.py
│   │   ├── train_lr.py
│   │   ├── train_svm.py
│   │   └── configs/
│   │       ├── lr.yaml
│   │       └── svm.yaml
│   ├── DL/
│   │   ├── __init__.py
│   │   ├── train.py
│   │   ├── inference.py
│   │   └── configs/
│   └── JEV/
│       ├── __init__.py
│       ├── client.py
│       ├── criteria.py
│       └── inference.py
├── data/
│   ├── raw/
│   ├── processed/
│   └── splits/
├── scripts/
│   ├── build_dataset.py
│   ├── merge_team.py
│   ├── prepare_data.py
│   └── split_data.py
├── evaluation/
│   ├── __init__.py
│   ├── metrics.py
│   ├── bootstrap.py
│   └── benchmark.py
├── experiments/
├── artifacts/
├── tests/
│   ├── test_api.py
│   └── test_classifier.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

Các package trong `app/` giữ `__init__.py` hiện có. Thư mục chưa có nội dung được giữ bằng `.gitkeep`.

## Trách nhiệm

| Khu vực | Vai trò dự kiến |
| --- | --- |
| `app/api/`, `app/schemas/` | Nhận request, kiểm tra schema, trả response. |
| `app/core/` | Đọc biến môi trường và cấu hình dịch vụ. |
| `app/services/preprocessing.py` | Chuẩn hóa input inference nhất quán với training. |
| `app/services/classifier.py` | Load artifacts và dự đoán; không train trong request. |
| `app/services/llm_service.py` | Diễn giải từ kết quả và bằng chứng đã chọn, có phương án dự phòng khi lỗi. |
| `src/ML/` | Logistic Regression/SVM, entrypoint train và cấu hình riêng. |
| `src/DL/` | Training, inference và cấu hình deep learning. |
| `src/JEV/` | Client, tiêu chí quyết định và inference cho hướng JEV. |
| `scripts/` | Tạo/gộp dữ liệu, chuẩn bị và chia tập offline. |
| `evaluation/` | Metrics, khoảng tin cậy bằng bootstrap và benchmark các model trên cùng bộ đánh giá. |
| `experiments/` | Log, cấu hình và kết quả từng lượt thí nghiệm. |
| `artifacts/` | Model, vectorizer/tokenizer và metadata cho inference. |
| `tests/` | Kiểm thử dữ liệu, API và model khi được triển khai. |

## Cài môi trường

Từ gốc repo, dùng Python 3.10 trở lên:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
```

Dependencies hiện chỉ gồm FastAPI và Uvicorn. Bổ sung dependencies ML/DL/JEV khi triển khai. `.env.example` là mẫu biến môi trường; module cấu hình chưa đọc các biến này.

Lệnh `uvicorn app.main:app --reload` từ `backend/` chỉ dùng được **sau khi** triển khai đối tượng `app` và routes. Hiện chưa có endpoint `/predict` hay API contract đã chốt.

## Script dữ liệu hiện có

Hai script đọc/ghi theo **thư mục làm việc hiện tại**, không theo vị trí script. Chúng chỉ dùng thư viện chuẩn Python.

## Luồng phát triển dự kiến

```text
data/raw/ → scripts/ → data/processed/ → data/splits/
                                              ↓
                               src/ML/ hoặc src/DL/ hoặc src/JEV/
                                              ↓
                               evaluation/ → experiments/
                                              ↓
                                         artifacts/
                                              ↓
Frontend → app/api/ → app/services/ → response
```

Chốt nhãn và cách chia dữ liệu trước; rà trùng nội dung/template để hạn chế leakage. Fit preprocessing/vectorizer trên train, chọn cấu hình trên validation, giữ test cho đánh giá cuối. Các model cần dùng chung split và định nghĩa metric để so sánh có ý nghĩa.

## Dữ liệu và Git

- `experiments/` chỉ giữ `.gitkeep` trong Git. Muốn chia sẻ báo cáo cần thống nhất riêng file nào được commit.
- Model trong `artifacts/`, secrets, môi trường Python và cache được ignore. Chỉ commit `.env.example`, không commit `.env` thật.
- File khung và test trống chưa chứng minh hệ thống hoạt động; cần kiểm thử thực tế sau khi triển khai từng phần.
