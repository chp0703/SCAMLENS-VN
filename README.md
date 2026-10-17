# SCAMLENS-VN

ScamLens VN hướng tới công cụ phân tích văn bản người dùng nhập thủ công, đánh giá dấu hiệu lừa đảo và cung cấp giải thích, hướng dẫn xác minh.

## Trạng thái

- `frontend/`: React + TypeScript dùng Vite. Xem [README frontend](frontend/README.md).
- `backend/`: pipeline preprocessing dùng chung cho ML/DL/JEV và khung FastAPI. API, training, model inference và benchmark chưa triển khai.
- Hai script `build_dataset.py` và `merge_team.py` đã có logic tạo/gộp CSV. Cấu trúc thư mục chưa chứng minh hệ thống chạy hoàn chỉnh.

## Cấu trúc

```text
SCAMLENS-VN/
├── frontend/                 # React + TypeScript
├── backend/
│   ├── app/                  # FastAPI: routes, config, schemas, services
│   ├── src/                  # Phát triển model: ML/, DL/, JEV/
│   ├── data/                 # raw/, processed/, splits/
│   ├── scripts/              # Tạo, gộp, chuẩn bị và chia dữ liệu
│   ├── evaluation/           # Metrics, bootstrap và benchmark chung
│   ├── experiments/          # Kết quả thí nghiệm local
│   ├── artifacts/            # Model đã lưu
│   ├── tests/                # Test preprocessing và khung test API/model
│   ├── requirements.txt
│   └── README.md
├── .gitignore
└── README.md
```

## Bắt đầu

Từ thư mục gốc, tạo môi trường backend và cài dependencies hiện có:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
```

Dependencies gồm FastAPI, Uvicorn và scikit-learn cho grouped splits. Chưa có API hoạt động hoặc dependencies training DL/JEV.

Xem [README backend](backend/README.md) để biết cấu trúc, hướng dẫn training với fold chung và các phần cần triển khai.

## Preprocessing

Đặt nguồn local tại `backend/data/raw/vietnamese_sms_dataset/full_dataset.csv` với các cột `message_id,message,label`, rồi chạy từ gốc repo:

```powershell
.\.venv\Scripts\python.exe backend/scripts/prepare_data.py --run-tests
```

Pipeline giữ nguyên raw, chuẩn hóa NFC/lowercase/khoảng trắng, thay URL/email/phone, xử lý duplicate và cách ly mâu thuẫn nhãn. Giữ dấu tiếng Việt, emoji, dấu câu và số không nhận diện là phone. Nhãn `1` của nguồn bao gồm **spam và scam**.

| Bộ dữ liệu | Nơi xuất trong `backend/data/splits/` | Tỷ lệ mục tiêu |
| --- | --- | --- |
| LR/SVM | `ml/train.csv`, `ml/test.csv`, `ml/cv_folds.csv` | 80/20 + CV 5 folds |
| DL/JEV | `dl_jev/train.csv`, `dl_jev/val.csv`, `dl_jev/test.csv` | 64/16/20 |

Hai bộ dùng **cùng test từng byte**. DL train + val bằng ML train; DL val là fold 0 của CV. Tỷ lệ thực tế có thể lệch do giữ nhóm gần trùng trong cùng tập. LR/SVM phải dùng bảng fold chung và fit TF-IDF bên trong từng fold.

Dữ liệu sạch và bảng truy vết nằm ở `backend/data/processed/`; hash, cấu hình và versions ở `backend/data/splits/manifest.json`. Mỗi lượt chạy thành công thêm một báo cáo `backend/report/preprocess_vN.md`. Dữ liệu sinh ra được Git ignore, báo cáo chỉ có thống kê. Trạng thái **provisional** cho đến khi nhóm hoàn tất review near-duplicate và outlier; ngưỡng tương đồng không bảo đảm phát hiện hết template leakage.

## Quy ước

- Dữ liệu nguồn ở `backend/data/raw/`, dữ liệu xử lý ở `processed/`, các tập train/validation/test ở `splits/`.
- Training nằm trong `backend/src/`; service trong `backend/app/` phục vụ API và load model đã lưu.
- Không commit secrets, dữ liệu cá nhân, môi trường Python, đầu ra thí nghiệm hoặc model nặng. Git giữ `.gitkeep` và hai file mẫu `data/raw/chp0703/ham.txt`, `scam.txt`.
- Chốt nhãn, cách chia dữ liệu và tiêu chí đánh giá trước khi so sánh model. Giải thích do LLM tạo không tự chứng minh kết quả phân loại là đúng.
