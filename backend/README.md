# ScamLens VN — Backend

Backend gồm ứng dụng FastAPI, công cụ chuẩn bị dữ liệu, các hướng phát triển model ML/DL/JEV và bộ đánh giá chung. Phạm vi dự kiến là phân tích văn bản người dùng nhập thủ công.

## Trạng thái hiện tại

Đây là **khung phát triển**, chưa phải backend chạy hoàn chỉnh:

- FastAPI app, endpoint và model inference chưa triển khai; service preprocessing đã có hàm dùng chung với pipeline offline.
- `scripts/build_dataset.py` và `scripts/merge_team.py` có logic từ `build_dataset/` cũ, được chuyển nguyên nội dung.
- `scripts/prepare_data.py` và `scripts/split_data.py` đã triển khai và có kiểm thử trong `tests/test_preprocessing.py`. Module trong `src/` và `evaluation/` vẫn là khung.
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

Dependencies gồm FastAPI, Uvicorn và `scikit-learn==1.7.2` cho grouped splits. Bổ sung dependencies training DL/JEV khi triển khai. `.env.example` là mẫu biến môi trường; module cấu hình chưa đọc các biến này.

Lệnh `uvicorn app.main:app --reload` từ `backend/` chỉ dùng được **sau khi** triển khai đối tượng `app` và routes. Hiện chưa có endpoint `/predict` hay API contract đã chốt.

## Script dữ liệu hiện có

`build_dataset.py` và `merge_team.py` đọc/ghi theo **thư mục làm việc hiện tại**. Chúng chỉ dùng thư viện chuẩn Python; không thay thế pipeline cleaning/split bên dưới và có thể bỏ trùng trước khi kiểm tra xung đột nhãn. Pipeline chính đọc trực tiếp `full_dataset.csv` để giữ truy vết.

## Pipeline preprocessing

Chạy từ gốc repo sau khi cài requirements:

```powershell
.\.venv\Scripts\python.exe backend/scripts/prepare_data.py --run-tests
```

Hoặc từ `backend/`: `..\.venv\Scripts\python.exe scripts/prepare_data.py --run-tests`. Đường dẫn mặc định được tính theo vị trí script, không phụ thuộc thư mục hiện tại. Có thể thay bằng Python từ môi trường đang dùng. Lượt triển khai này dùng `.venv-preprocessing` riêng vì `.venv` cũ không khởi động được.

Các tùy chọn: `--source PATH`, `--data-dir PATH`, `--report-dir PATH`, `--seed 42`, `--similarity-threshold 0.85`. Đổi nguồn/quy tắc/seed phải tạo lại cả hai bộ split, thông báo cho mọi người dùng dữ liệu và giữ báo cáo mới. Test nguồn cũ không được gộp thêm vào nguồn vì đã nằm trong `full_dataset.csv`.

### Cleaning và grouping

- Nguồn cần `message_id,message,label`; `date` không bắt buộc. ID thiếu/trùng hoặc CSV sai cấu trúc làm pipeline dừng để tránh truy vết mơ hồ. Mẫu thiếu text/label hoặc label ngoài `{0,1}` được ghi vào `rejected.csv`.
- `app.services.preprocessing.normalize_text(text)` dùng cho offline và inference: NFC, lowercase, trim/gom whitespace; token có sẵn được canonical uppercase theo whitelist `[URL]`, `[PHONE]`, `[EMAIL]`, `[NUMBER]`, `[BANK_ACC]`, `[MONEY]`, `[TIME]`, `[DATE]`, `[NAME]`, `[POINT]`.
- Nhận diện URL bắt đầu bằng `http(s)://` hoặc `www.`, email và phone Việt Nam mobile 03/05/07/08/09 (10 số), cố định 02 (11 số), hỗ trợ `+84`, `0084`, dấu cách/chấm/gạch nối. Thay lần lượt URL → email → phone bằng token tương ứng; giữ dấu câu ở cuối URL.
- Giữ dấu tiếng Việt, emoji, dấu câu ngoài thực thể và các số khác. `[NUMBER]` không được suy diễn thành `[PHONE]`; không sửa toàn bộ ký tự `Ã`/`Â` hoặc ép Unicode toán học sang ASCII. Không bỏ stopword, stemming, tách từ hay cắt văn bản theo độ dài ở bước chung.
- Kiểm tra trùng sau NFC/lowercase/whitespace và sau masking. Trùng cùng nhãn giữ ID nhỏ nhất theo thứ tự từ điển, lưu mapping; text trùng khác nhãn cách ly toàn nhóm trong `quarantine.csv`, không chọn nhãn đa số.
- Near-duplicate dùng Jaccard trên tập character 5-gram, ngưỡng `≥0.85`; text dưới 5 ký tự chỉ ghép khi giống hoàn toàn. Mọi cặp đạt ngưỡng tạo cạnh, connected components tạo `group_id` ổn định. Giữ các mẫu trong nhóm, không loại gần trùng như duplicate chính xác.
- `groups.csv` ghi trạng thái pending cho nhóm nhiều mẫu; đánh dấu thêm nhóm ≥10 mẫu và nhóm khác nhãn. Cần kiểm tra nối chuỗi làm nhóm lớn. `length_outliers.csv` đánh dấu ngoài `[Q1−1.5 IQR, Q3+1.5 IQR]` theo ký tự hoặc từ; giữ các mẫu này trong dữ liệu.

### Hai bộ split dùng chung test

```text
data/processed/
  clean.csv                 # message_id,text_raw,text,label,group_id
  accounting.csv            # một trạng thái cho mỗi ID nguồn
  duplicates.csv            # ID bị gộp → ID đại diện + trước/sau masking
  rejected.csv              # missing/invalid label
  quarantine.csv            # mâu thuẫn nhãn
  near_duplicate_pairs.csv  # cặp tương đồng, score và group_id
  groups.csv                # kích thước, phân bố nhãn và trạng thái review
  length_outliers.csv        # thống kê độ dài của mẫu cần review
data/splits/
  ml/train.csv
  ml/test.csv
  ml/cv_folds.csv            # message_id,fold_id (0..4)
  dl_jev/train.csv
  dl_jev/val.csv
  dl_jev/test.csv
  manifest.json
```

`StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)` chia toàn bộ dữ liệu sạch; fold 0 làm test chung, bốn fold còn lại làm ML train. Chạy tiếp 5-fold trên ML train; fold 0 làm DL/JEV val, phần còn lại làm DL/JEV train. Mục tiêu ML 80/20, DL/JEV 64/16/20; số thực tế được báo cáo. Nếu thiếu nhóm mỗi lớp hoặc bất kỳ train/validation fold nào thiếu lớp, pipeline dừng, không fallback sang random split.

CSV dữ liệu của cả hai bộ có cùng schema với `clean.csv`; hai test cùng hàng, thứ tự và hash. `ML train = DL train ∪ DL val`, hai phần DL không giao nhau. Không có ID, text chuẩn hóa hoặc `group_id` giao nhau giữa các tập hoặc giữa train/validation của mỗi CV fold. Nhãn `0 = Ham`, `1 = Scam`; nguồn thực tế gộp **spam/scam** trong nhãn `1` nên chưa đủ căn cứ diễn giải thành bộ phát hiện lừa đảo thuần túy.

**LR/SVM:** join `cv_folds.csv` với train bằng `message_id`, kiểm tra không mất/trùng ID và giữ đúng thứ tự X/y khi tạo `PredefinedSplit`. Truyền split này cho `GridSearchCV`; không tạo lại `StratifiedKFold`. TF-IDF nằm trong `sklearn.pipeline.Pipeline`, chỉ fit trên training fold. Sau tuning có thể refit trên toàn ML train.

**DL:** train trên `dl_jev/train.csv`, chọn cấu hình/early stopping trên `val.csv`. Tokenizer, tách từ và giới hạn độ dài là xử lý riêng cho model; vocabulary hoặc thống kê học từ dữ liệu chỉ được fit trên DL train. **JEV:** dùng cùng bộ split; chưa chốt phương pháp tích hợp hay khẳng định cần training.

Test chỉ dùng đánh giá cuối, không chọn hyperparameter, threshold, prompt hoặc ví dụ few-shot. Việc DL dùng ít mẫu train hơn ML phải được ghi nhận khi so sánh; có thể thiết kế refit trên train pool sau khi chốt cấu hình ở giai đoạn training sau này.

Nếu chỉ cần chia lại từ dữ liệu sạch:

```powershell
.\.venv\Scripts\python.exe backend/scripts/split_data.py
```

Lệnh này ghi manifest với `scope=split_only`, thay manifest full nếu cùng output; không thực hiện lại source audit hoặc tạo báo cáo preprocessing. Dùng lệnh `prepare_data.py --run-tests` để có trọn bộ provenance và báo cáo. Không coi file CSV cũ là hợp lệ nếu hash không khớp manifest hiện tại.

### Kiểm chứng và báo cáo

CSV đọc/ghi UTF-8 BOM (`encoding="utf-8-sig"`), JSON/Markdown UTF-8. Pipeline đọc lại toàn bộ CSV để xác minh từng ô, BOM, Unicode và text_raw; đối chiếu hash raw trước/sau. Chuẩn hóa có tính idempotent. Chỉ thay dữ liệu đầu ra sau khi cleaning, grouping, split và serialization đều đạt kiểm tra.

Manifest lưu hash nguồn/CSV đầu ra, rules version, cấu hình, versions Python/dependencies, số mẫu theo trạng thái, phân bố lớp, thống kê độ dài, từng split/fold và quan hệ giữa hai bộ. Manifest không chứa timestamp để chạy lại cùng nguồn/config/môi trường cho cùng bytes. Muốn tái lập trên máy khác, dùng cùng Python/dependency versions trong manifest, cùng nguồn và cấu hình.

Mỗi lượt full pipeline thành công tạo `report/preprocess_vN.md` mới; không ghi đè báo cáo cũ. Báo cáo chỉ có thống kê, không chứa nguyên văn tin nhắn. Chạy có `--run-tests` để ghi số test đã pass; không có cờ này sẽ ghi tests chưa chạy. Trạng thái luôn **provisional**: pipeline chưa có workflow phê duyệt thủ công, và Jaccard/grouping không bảo đảm phát hiện hết template leakage.

Chạy test độc lập:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend/tests -p test_preprocessing.py -v
```

Test dùng dữ liệu tổng hợp; kiểm tra normalizer, lỗi nguồn, xung đột trước/sau masking, near-duplicate nối chuỗi, leakage, quan hệ hai bộ split, CSV round-trip, hash tái lập, báo cáo nối tiếp và giữ kết quả cũ khi kiểm tra thất bại.

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

- Git lưu nguồn công khai `data/raw/vietnamese_sms_dataset/`, CSV trong `data/processed/`, các tập ML/DL/JEV và `data/splits/manifest.json`. Nguồn và giấy phép được ghi trong README nguồn và `source.json`; `.gitattributes` giữ nguyên byte dữ liệu để bảo toàn SHA-256. Các dữ liệu local khác vẫn được ignore.
- `experiments/` chỉ giữ `.gitkeep` trong Git. Muốn chia sẻ báo cáo cần thống nhất riêng file nào được commit.
- Model trong `artifacts/`, secrets, môi trường Python và cache được ignore. Chỉ commit `.env.example`, không commit `.env` thật.
- File khung và test trống chưa chứng minh hệ thống hoạt động; cần kiểm thử thực tế sau khi triển khai từng phần.
