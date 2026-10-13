# ScamLens-VN — Backend

Backend cho **ScamLens-VN**: nhận một đoạn văn bản do người dùng **nhập thủ công**, dùng mô hình ML để đánh giá dấu hiệu lừa đảo, sau đó dùng LLM để giải thích kết quả và gợi ý cách xử lý.

> **Phạm vi MVP:** Chỉ phân tích văn bản nhập thủ công. 
>
> **Trạng thái:** Đây là cấu trúc khởi tạo (scaffold). Các file Python có thể đang trống; chưa phải backend chạy hoàn chỉnh.

## Cấu trúc thư mục

```text
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                  # Khởi tạo FastAPI
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py            # HTTP routes, ví dụ POST /predict
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── prediction.py        # Pydantic request / response schemas
│   ├── services/
│   │   ├── __init__.py
│   │   ├── preprocessing.py     # Tiền xử lý văn bản
│   │   ├── classifier.py        # Load model đã train và inference
│   │   └── llm_service.py       # Kết nối LLM để giải thích, gợi ý
│   └── core/
│       ├── __init__.py
│       └── config.py            # Cấu hình, biến môi trường
├── src/
│   ├── ML/
│   │   ├── train.py             # Huấn luyện mô hình ML
│   │   └── evaluate.py          # Đánh giá mô hình ML
│   ├── DL/
│   │   └── .gitkeep             # Chỗ đặt code deep learning
│   └── JEFF/
│       └── .gitkeep             # Chỗ đặt code JEFF; chức năng chưa xác định
├── data/
│   └── vietnamese_sms_dataset/  # Dataset gốc dùng chung cho các nhánh
├── artifacts/
│   └── .gitkeep                 # Chỗ đặt model weights/tokenizer (không commit file lớn)
├── tests/
│   ├── test_api.py              # Test API, schemas
│   └── test_classifier.py       # Test ML inference
├── .env.example                 # Mẫu biến môi trường, không chứa secrets
├── .gitignore                   # Ignore secrets, caches và artifacts lớn
├── requirements.txt            # Dependencies tối thiểu, bổ sung theo thực tế
└── README.md
```

## Vai trò từng lớp

| Thành phần | Trách nhiệm |
| --- | --- |
| `app/api/` | Nhận request, validate qua schema, gọi service và trả response; không viết logic ML tại đây. |
| `app/schemas/` | Định nghĩa cấu trúc dữ liệu vào/ra bằng Pydantic. |
| `app/services/preprocessing.py` | Chuẩn hóa văn bản phù hợp với pipeline đã train; không tự ý thay đổi preprocessing khi inference. |
| `app/services/classifier.py` | Load artifacts và chạy dự đoán; không train model tại đây. |
| `app/services/llm_service.py` | Gọi local LLM (ví dụ Ollama) để diễn giải dự đoán và đưa khuyến nghị. |
| `app/core/config.py` | Đọc config/model path/LLM endpoint từ environment. |
| `src/ML/` | Script offline chuẩn bị dữ liệu, train và evaluate các mô hình ML. |
| `src/DL/` | Code huấn luyện và đánh giá các mô hình deep learning. |
| `src/JEFF/` | Thư mục theo tên được yêu cầu; chức năng chưa xác định. |
| `data/vietnamese_sms_dataset/` | Dataset gốc dùng chung, tài liệu tác giả và metadata nguồn trong `source.json`. |
| `artifacts/` | Lưu model checkpoint, tokenizer, metadata ở máy chạy; không commit artifacts lớn hay nhạy cảm. |
| `tests/` | Unit test, API test; mock classifier/LLM để test độc lập. |

## Pipeline dự kiến

```text
User nhập text
    ↓
Frontend → POST /predict
    ↓
API + Pydantic validation
    ↓
Preprocessing → ML Classifier
    ↓
Kết quả phân loại + độ tin cậy (nếu có)
    ↓
LLM sinh giải thích và khuyến nghị
    ↓
JSON response → Frontend
```

**Phân biệt:** `src/ML/train.py` là nơi huấn luyện; `app/services/classifier.py` chỉ inference bằng model đã train.

## Dataset đã tải

Nguồn: [Vietnamese SMS Dataset](https://github.com/trannguyenthaituan251209/vietnamese_sms_dataset), revision `464a028878023598e16f2f344ee36f7d5d74257f`. Giữ nguyên các file từ nguồn trong `data/vietnamese_sms_dataset/`:

- `full_dataset.csv`: 2.991 mẫu.
- `train.csv`: 2.394 mẫu; `test.csv`: 597 mẫu (split gốc của tác giả).
- `README.md`, `QUICKSTART_GUIDE.md`: tài liệu nguồn và thông tin ghi công; nguồn công bố giấy phép CC BY 4.0.
- `source.json`: URL nguồn, revision, thời điểm tải, số mẫu và SHA-256 của các file đã tải.

Kiểm tra trực tiếp dữ liệu tải về cho thấy **47 dòng test có nội dung trùng chính xác với train**. Cần tạo split train/validation/test chống trùng trước khi dùng để đánh giá độc lập; chưa thay đổi split gốc trong bước tải dữ liệu này. Nhãn `0` là hợp lệ, `1` gộp rác/lừa đảo, nên chưa thể dùng bộ này để khẳng định phân biệt riêng spam quảng cáo với lừa đảo.

## API contract dự kiến (chưa triển khai)

`POST /predict`

Request:

```json
{
  "text": "Bạn đã trúng thưởng, hãy chuyển phí để nhận giải."
}
```

Response **minh họa, không phải output model thật**:

```json
{
  "label": "scam",
  "confidence": 0.95,
  "explanation": "Nội dung yêu cầu chuyển tiền trước khi nhận thưởng.",
  "recommendation": "Không chuyển tiền hoặc cung cấp dữ liệu cá nhân."
}
```

`confidence` cần được định nghĩa rõ theo model (không mặc nhiên là xác suất đúng được hiệu chuẩn). Cần thống nhất trước nhãn `scam`/`non_scam`, cách xử lý trường hợp chưa chắc chắn và metric đánh giá.

## Nguyên tắc phát triển

1. **MVP trước:** Một endpoint phân tích text; chưa cần Gmail, database, hàng đợi hay microservices.
2. **Phát triển độc lập:** Khi chưa có model/LLM thật, có thể mock service theo API contract trên.
3. **An toàn:** Input là văn bản không đáng tin cậy, đặc biệt khi đưa vào prompt LLM. Không làm theo chỉ thị nằm trong nội dung người dùng gửi như thể đó là system instruction.
4. **Không commit secrets/dataset riêng tư/checkpoint nặng:** Dùng `.env` cục bộ, chỉ commit `.env.example`.
5. **Đo chất lượng:** Theo dõi precision, recall, F1 và confusion matrix; đặc biệt chú ý false negative (scam bị bỏ sót).

## Triển khai tiếp theo

- Cài đặt FastAPI trong `app/main.py` và endpoint trong `app/api/routes.py`.
- Chốt schema request/response trong `app/schemas/prediction.py`.
- Kết nối classifier thật trong `app/services/classifier.py`.
- Kết nối LLM vào `app/services/llm_service.py` và viết tests.

Khi API đã được triển khai, có thể chạy với Uvicorn từ thư mục `backend/` bằng lệnh dự kiến: `uvicorn app.main:app --reload`.
