# SCAMLENS-VN

ScamLens VN hướng tới công cụ phân tích văn bản người dùng nhập thủ công, đánh giá dấu hiệu lừa đảo và cung cấp giải thích, hướng dẫn xác minh.

## Trạng thái

Nhánh `feat/baseline-ml` hợp nhất `preprocessing`, `feat/member1-lr`, `feat/member2-svm` và `feat/member3-evaluation`, gồm dữ liệu/fold dùng chung, LR/SVM, đánh giá cuối cùng và artifact được ghim qua Git LFS.

- `frontend/`: React + TypeScript dùng Vite. Xem [README frontend](frontend/README.md).
- `backend/`: đã có preprocessing, training/tuning LR/SVM, inference từ artifact được ghim và final benchmark. Hai pipeline dùng chung được lưu qua Git LFS. API và training DL/JEV chưa triển khai.
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

## Dùng chung model LR/SVM qua Git LFS

Mỗi thành viên cần cài Git LFS, checkout cùng nhánh/commit đã chốt và dùng Python 3.12.x. Kích hoạt môi trường Python rồi cài đúng dependencies của model, chạy từ thư mục gốc repo:

```powershell
python -m pip install -r backend/requirements-models.lock.txt
```

Sau khi clone hoặc pull, tải model và kiểm tra bằng đủ ba lệnh:

```powershell
git lfs install --local
git lfs pull
python backend/scripts/verify_models.py
```

Kết quả phải báo `status: PASS`, bundle `ml-evaluated-20261022-v1` và 6 cases cho mỗi model. Lệnh kiểm tra hash model/metadata, môi trường, preprocessing và dự đoán mẫu; không train lại hoặc mở tập test.

Phiên bản dùng chung được ghim trong [models.lock.json](backend/models.lock.json). Xem [hướng dẫn cài môi trường, inference và rule cập nhật model](backend/docs/SHARED_MODELS.md) trước khi thay artifact. Chỉ dùng `python` trong các lệnh trên khi nó trỏ đúng môi trường đã cài dependencies theo lock.

## Preprocessing

Nguồn được lưu tại `backend/data/raw/vietnamese_sms_dataset/full_dataset.csv` với các cột `message_id,message,label`. Để tạo lại dữ liệu xử lý, chạy từ gốc repo:

```powershell
.\.venv\Scripts\python.exe backend/scripts/prepare_data.py --run-tests
```

Pipeline giữ nguyên raw, chuẩn hóa NFC/lowercase/khoảng trắng, thay URL/email/phone, xử lý duplicate và cách ly mâu thuẫn nhãn. Giữ dấu tiếng Việt, emoji, dấu câu và số không nhận diện là phone. Nhãn `1` của nguồn bao gồm **spam và scam**.

| Bộ dữ liệu | Nơi xuất trong `backend/data/splits/` | Tỷ lệ mục tiêu |
| --- | --- | --- |
| LR/SVM | `ml/train.csv`, `ml/test.csv`, `ml/cv_folds.csv` | 80/20 + CV 5 folds |
| DL/JEV | `dl_jev/train.csv`, `dl_jev/val.csv`, `dl_jev/test.csv` | 64/16/20 |

Hai bộ dùng **cùng test từng byte**. DL train + val bằng ML train; DL val là fold 0 của CV. Tỷ lệ thực tế có thể lệch do giữ nhóm gần trùng trong cùng tập. LR/SVM phải dùng bảng fold chung và fit TF-IDF bên trong từng fold.

Dữ liệu sạch và bảng truy vết nằm ở `backend/data/processed/`; hash, cấu hình và versions ở `backend/data/splits/manifest.json`. Mỗi lượt chạy thành công thêm một báo cáo `backend/report/preprocess_vN.md`. Git lưu bộ nguồn `vietnamese_sms_dataset`, các CSV xử lý và các tập chia ML/DL/JEV cùng manifest; `.gitattributes` giữ nguyên byte để bảo toàn hash. Trạng thái **provisional** cho đến khi nhóm hoàn tất review near-duplicate và outlier; ngưỡng tương đồng không bảo đảm phát hiện hết template leakage.

## Quy ước

- Dữ liệu nguồn ở `backend/data/raw/`, dữ liệu xử lý ở `processed/`, các tập train/validation/test ở `splits/`.
- Training nằm trong `backend/src/`; service trong `backend/app/` phục vụ API và load model đã lưu.
- Model dùng chung đã được duyệt được lưu theo version qua Git LFS; metadata, lock và báo cáo được lưu trong Git thường. Không commit secrets, dữ liệu cá nhân mới thu thập, môi trường Python hoặc các output training/checkpoint chưa được chọn. Bộ dữ liệu nguồn công khai được giữ kèm README và `source.json` ghi nguồn, revision và giấy phép do nguồn công bố.
- Chốt nhãn, cách chia dữ liệu và tiêu chí đánh giá trước khi so sánh model. Giải thích do LLM tạo không tự chứng minh kết quả phân loại là đúng.
