# ScamLens-VN — Backend

Backend cho **ScamLens-VN**: nhận một đoạn văn bản do người dùng **nhập thủ công**, dùng mô hình ML để đánh giá dấu hiệu lừa đảo, sau đó dùng LLM để giải thích kết quả và gợi ý cách xử lý.

> **Phạm vi MVP:** Chỉ phân tích văn bản nhập thủ công. 
>
> **Trạng thái:** Preprocessing/audit/split đã chạy được và có kiểm thử. Training, classifier inference, rules và API vẫn đang khởi tạo; chưa có backend phân tích end-to-end.

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
│   │   ├── prepare_data.py      # Audit, xử lý trùng, split và báo cáo lượt chạy
│   │   ├── reporting.py         # Lưu báo cáo Markdown có số thứ tự
│   │   ├── train.py             # Huấn luyện mô hình ML
│   │   └── evaluate.py          # Đánh giá mô hình ML
│   ├── DL/
│   │   └── .gitkeep             # Chỗ đặt code deep learning
│   └── JEFF/
│       └── .gitkeep             # Chỗ đặt thí nghiệm Jeff
├── data/
│   ├── vietnamese_sms_dataset/  # Dataset gốc dùng chung cho các nhánh
│   └── processed/sms_v1/        # CSV hiện hành, audit và manifest
├── report/
│   ├── preprocess_v1.md         # Báo cáo lượt đầu, bổ sung từ đầu ra đã có
│   └── preprocess_v2.md         # Báo cáo sau khi sửa CSV encoding
├── artifacts/
│   └── .gitkeep                 # Chỗ đặt model weights/tokenizer (không commit file lớn)
├── tests/
│   ├── test_preprocessing.py    # Unicode, BOM, split và báo cáo có version
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
| `src/JEFF/` | Thí nghiệm classifier Jeff theo kế hoạch. |
| `data/vietnamese_sms_dataset/` | Dataset gốc dùng chung, tài liệu tác giả và metadata nguồn trong `source.json`. |
| `data/processed/sms_v1/` | Đầu ra preprocessing hiện hành ở máy local. |
| `report/` | Báo cáo Markdown từng lượt chạy và kiểm thử; giữ lịch sử trong Git. |
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

## Preprocessing và split dự kiến

Chạy từ thư mục `backend/` bằng Python 3.10 trở lên; bước này chỉ dùng thư viện chuẩn:

```powershell
python src/ML/prepare_data.py --run-tests
```

Có thể chọn `--input`, `--output-dir`, `--seed` (mặc định 42), `--jaccard-threshold` (mặc định 0.85) và `--report-dir` (mặc định `report/`). `--run-tests` chạy unittest trước khi xử lý; bỏ cờ này vẫn chạy kiểm tra dữ liệu trên đĩa và ghi rõ chưa chạy unittest trong báo cáo. Các đầu ra trong `data/processed/sms_v1/`:

| File | Mục đích |
| --- | --- |
| `clean.csv` | Một đại diện cho mỗi nội dung chuẩn hóa cùng nhãn; giữ toàn bộ `source_ids` và `source_count`. |
| `train.csv`, `validation.csv`, `test.csv` | Split dự kiến theo nhóm template, mục tiêu 70/15/15 và cân bằng số mẫu từng lớp. |
| `quarantine.csv` | Các dòng trùng sau chuẩn hóa nhưng bất đồng nhãn; chưa tự sửa hoặc chọn nhãn. |
| `duplicate_map.csv` | Ánh xạ từng ID gốc sang mẫu đại diện. |
| `template_review.csv`, `template_edges.csv` | Các nhóm và cặp template cần rà; chỉ chứa ID, số lượng và phương pháp khớp. |
| `privacy_review.csv` | ID và loại dấu hiệu có thể chưa được ẩn danh; không chứa giá trị OTP/email/số thực. |
| `audit_report.json`, `manifest.json` | Kết quả audit, seed, version, hash dữ liệu/code/đầu ra và kiểm tra giao nhau. |

`app/services/preprocessing.py` dùng chung cho train/inference: NFC, gộp khoảng trắng và bỏ U+200B/U+FEFF. Giữ chữ hoa/thường, dấu tiếng Việt, số, URL, dấu câu, emoji và placeholder. Hàm `duplicate_key` có thêm casefold để audit; `template_tokens` che URL/email/số **chỉ để gom nhóm**, không làm input ML. Evidence/rules cần dùng văn bản gốc vì chuẩn hóa thay đổi vị trí ký tự.

Chỉ dùng cột `text` làm đầu vào classifier. ID, ngày, nhóm, `source_count` và danh sách ID nguồn là metadata. Không nhân trọng số theo số bản lặp mặc định. Những dòng thiếu ngày vẫn được giữ vì ngày chưa phải feature.

Gom cùng nhóm các signature template giống nhau và cặp có Jaccard token-set ≥ 0.85 với ít nhất 5 token khác nhau; giữ nguyên cả nhóm liên thông trong một split. Các mẫu gần giống vẫn được giữ để đo biến thể, chỉ bỏ bản lặp theo `duplicate_key`. Không fit TF-IDF hoặc model ở bước này.

**Trạng thái split là dự kiến**, chưa khóa benchmark chính thức: phải rà các nhóm template lớn/nhãn hỗn hợp và các dấu hiệu ẩn danh, sau đó quyết định giữ/che/loại theo quy tắc có version. Regex có báo nhầm và có thể bỏ sót; Jaccard không đảm bảo tách được mọi template tương đồng về nghĩa. Các kiểm tra tự động đảm bảo không giao ID, text chuẩn hóa, group và các cạnh template đã phát hiện giữa các split. Không dùng test để tune preprocessing học từ dữ liệu, threshold hoặc model.

### Encoding tiếng Việt

CSV đầu ra dùng `utf-8-sig` (**UTF-8 có BOM**); JSON và Markdown dùng UTF-8. Lượt đầu xuất CSV không BOM, có thể bị ứng dụng Windows đoán sai encoding dù văn bản đọc bằng UTF-8 vẫn đúng. [Microsoft hướng dẫn dùng BOM khi mở CSV UTF-8 trực tiếp trong Excel](https://support.microsoft.com/en-us/excel/opening-csv-utf-8-files-correctly-in-excel).

Đọc dữ liệu bằng Python:

```python
import csv

with open("data/processed/sms_v1/train.csv", encoding="utf-8-sig", newline="") as handle:
    rows = list(csv.DictReader(handle))
```

Sau khi ghi, pipeline đọc lại CSV để kiểm tra BOM, UTF-8 strict, tên cột, nội dung `message` và `text`, đầy đủ ID nguồn và tính nhất quán của split. Không thay `Ã`/`Â` hàng loạt: chúng có thể là chữ tiếng Việt đúng trong “ĐÃ”, “CÂY”. Ký tự mathematical Unicode trong tin gốc được giữ để bảo toàn tín hiệu viết biến dạng. Nếu ứng dụng đã mở và lưu sai encoding, mở lại file vừa được pipeline sinh; BOM không khôi phục bản đã bị lưu hỏng.

### Lịch sử báo cáo

Mỗi lượt chạy CLI tạo `report/preprocess_vN.md` mới bằng chế độ không ghi đè. Lỗi unittest hoặc pipeline được ghi FAIL và trả exit code 1. Báo cáo PASS xác nhận các kiểm tra đã chạy, không chứng nhận mọi nhãn/ẩn danh/template đều đã được rà thủ công.

- [preprocess_v1.md](report/preprocess_v1.md): báo cáo bổ sung từ kết quả lượt đầu, ghi rõ thiếu thời điểm/log riêng của lượt cũ.
- [preprocess_v2.md](report/preprocess_v2.md): kết quả lượt sửa encoding và kiểm thử.

Số lượt báo cáo độc lập với `preparation_version` và `preprocessing_version`; các version, seed, hash nguồn/code/đầu ra được ghi trong báo cáo. Không chép tin nhắn đầy đủ, OTP hoặc thông tin cá nhân vào Markdown. Báo cáo được Git theo dõi; dữ liệu trong `data/` vẫn là local. CSV hiện hành được cập nhật tại chỗ nên báo cáo không phải snapshot của mọi dataset cũ.

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

- Rà template/ẩn danh/nhãn bất đồng và khóa split trước khi train.
- Triển khai LR/SVM trong `src/ML/train.py` và metrics trong `src/ML/evaluate.py`.
- Xây rules/evidence và policy dùng chung cho các classifier.
- Cài đặt FastAPI trong `app/main.py` và endpoint trong `app/api/routes.py`.
- Chốt schema request/response trong `app/schemas/prediction.py`.
- Kết nối classifier thật trong `app/services/classifier.py`.
- Kết nối LLM vào `app/services/llm_service.py` và viết tests.

Khi API đã được triển khai, có thể chạy với Uvicorn từ thư mục `backend/` bằng lệnh dự kiến: `uvicorn app.main:app --reload`.
