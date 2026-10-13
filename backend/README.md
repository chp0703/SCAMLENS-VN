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
├── ml/
│   ├── train.py                 # Training / fine-tuning
│   └── evaluate.py              # Đánh giá mô hình
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
| `ml/` | Script offline chuẩn bị dữ liệu, train và evaluate. Có thể thêm `prepare_data.py` khi cần. |
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

**Phân biệt:** `ml/train.py` là nơi huấn luyện; `app/services/classifier.py` chỉ inference bằng model đã train.

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
