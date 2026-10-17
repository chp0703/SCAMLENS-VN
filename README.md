# SCAMLENS-VN

ScamLens VN hướng tới công cụ phân tích văn bản người dùng nhập thủ công, đánh giá dấu hiệu lừa đảo và cung cấp giải thích, hướng dẫn xác minh.

## Trạng thái

- `frontend/`: React + TypeScript dùng Vite. Xem [README frontend](frontend/README.md).
- `backend/`: khung FastAPI, phát triển ML/DL/JEV, chuẩn bị dữ liệu và đánh giá chung. API, training, inference và benchmark chưa triển khai.
- Hai script `build_dataset.py` và `merge_team.py` đã có logic tạo/gộp CSV. Cấu trúc thư mục chưa chứng minh hệ thống chạy hoàn chỉnh.

## Cấu trúc

```text
SCAMLENS-VN/
├── frontend/                 # React + TypeScript
├── backend/
├── .gitignore
└── README.md
```

## Bắt đầu

Từ thư mục gốc, tạo môi trường backend và cài dependencies hiện có:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
```

Dependencies hiện chỉ gồm FastAPI và Uvicorn; chưa đủ để train ML/DL hay tích hợp JEV. Chưa có API hoạt động để chạy thử bằng Uvicorn.

Xem [README backend](backend/README.md) để biết cấu trúc chi tiết, cách chạy script dữ liệu và các phần cần triển khai. Hướng dẫn này không khôi phục pipeline preprocessing từ branch `baseline`.

## Quy ước

- Dữ liệu nguồn ở `backend/data/raw/`, dữ liệu xử lý ở `processed/`, các tập train/validation/test ở `splits/`.
- Training nằm trong `backend/src/`; service trong `backend/app/` phục vụ API và load model đã lưu.
- Không commit secrets, dữ liệu cá nhân, môi trường Python, đầu ra thí nghiệm hoặc model nặng. 
- Chốt nhãn, cách chia dữ liệu và tiêu chí đánh giá trước khi so sánh model. Giải thích do LLM tạo không tự chứng minh kết quả phân loại là đúng.
