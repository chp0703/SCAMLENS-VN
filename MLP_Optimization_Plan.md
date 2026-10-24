# Kế hoạch TF-IDF + MLP cho ScamLens VN

## 1. Mục tiêu và đầu ra

Xây dựng MLP từ baseline, cải tiến từng bước, chọn theo **F1 lớp spam/scam** và xuất model để repo dùng khi deploy. MLP không mặc định tốt hơn LR/SVM; kết quả thực nghiệm quyết định bước cải tiến nào được giữ lại.

**Phạm vi hiện tại chỉ tạo file kế hoạch này.** Các bước triển khai sau dùng PyTorch, scikit-learn và Optuna, gồm:

- Một notebook duy nhất: `backend/notebooks/mlp_optimization.ipynb`, chạy trên Google Colab từ chuẩn bị dữ liệu đến export; bảng kết quả, biểu đồ và phân tích nằm trong notebook.
- Module định nghĩa mạng dùng chung và module inference trong `backend/src/DL/`; notebook import lại để tránh lệch kiến trúc khi deploy. Training/tuning được điều phối trong notebook.
- Bundle của MLP tốt nhất, tải và dự đoán được trên CPU. Chưa mở rộng sang pretrained embedding, LLM hoặc xây API.

## 2. Dữ liệu và quy tắc đánh giá

Bộ chia hiện có đã được kiểm tra số dòng và SHA-256 khớp manifest:

| Tập trong `backend/data/splits/dl_jev/` | Số mẫu | Vai trò |
| --- | ---: | --- |
| `train.csv` | 1.582 | Fit TF-IDF và trọng số model |
| `val.csv` | 419 | Early stopping, chọn cấu hình và threshold |
| `test.csv` | 563 | Đánh giá sau khi khóa lựa chọn |

- Giữ nguyên split, kiểm tra schema, nhãn `{0,1}` và không giao nhau về ID, text chuẩn hóa, `group_id`. Đọc CSV bằng `utf-8-sig`; dùng normalization tại `backend/app/services/preprocessing.py` cho cả training và inference. Chỉ fit vocabulary/IDF trên train.
- Nhãn `1` gộp **spam + scam**; dữ liệu vẫn provisional, còn các nhóm gần trùng cần review. Kết quả chưa chứng minh khả năng phát hiện lừa đảo ngoài thực tế.
- Tiêu chí chính là F1 lớp 1. Báo thêm precision, recall, confusion matrix, thời gian inference CPU và dung lượng bundle; theo dõi loss/F1 từng epoch.
- LR/SVM đã lưu được train trên 2.001 mẫu, gồm phần DL validation. Vì vậy phải train lại baseline đối chiếu trên đúng 1.582 mẫu; không dùng model đã lưu để so validation với MLP.
- Test đã được benchmark LR/SVM trước đây. Tiếp tục dùng để đối chiếu nhưng không gọi đây là kiểm định mới hoàn toàn độc lập; không sửa cấu hình sau khi xem kết quả test.

## 3. Lộ trình trong một notebook

| Bước | Thực hiện | Đầu ra cần giữ |
| --- | --- | --- |
| **0. Chuẩn bị** | Checkout commit cụ thể, kiểm tra manifest và split; đặt seed 42; ghi Python, dependencies, thiết bị. Cài bộ phiên bản đã kiểm tra tương thích, tránh tự nâng toàn bộ thư viện mỗi lần chạy. Gắn Drive làm nơi lưu log/checkpoint. | Commit, hash dữ liệu/preprocessing, cấu hình và kết quả kiểm tra. |
| **1. Baseline** | TF-IDF word unigram, tối đa 10.000 features, `min_df=2`, L2. Train Logistic Regression và LinearSVC với `C=1`. MLP: `input → 128 → ReLU → 1 logit`; Adam `lr=1e-3`, weight decay 0, batch 64, `BCEWithLogitsLoss`, threshold 0,5. | Bảng baseline, checkpoint và đường loss/F1. |
| **2. Cải tiến có kiểm soát** | Lần lượt thử weight decay `1e-4`; so Adam và AdamW tại cùng mức decay; dropout `0,3`; hidden `[256,128]`; word unigram+bigram; character `char_wb` 3–5 gram; loss có `pos_weight=N0/N1` tính trên train. Mỗi lượt đổi một yếu tố từ cấu hình tốt nhất hiện tại, giữ bước tăng F1 validation. | Bảng trước/sau, thay đổi cụ thể, F1, thời gian và số tham số; giữ cả lượt thất bại. |
| **3. Tuning** | Optuna tối đa 20 trials trên loại TF-IDF tốt nhất ở bước 2; tìm trong không gian bên dưới. Baseline và ứng viên tốt ở bước 2 vẫn được giữ trong danh sách lựa chọn. | Leaderboard, cấu hình, log và checkpoint của trial hoàn thành. |
| **4. Chọn model** | Chạy hai cấu hình khác baseline tốt nhất và baseline với seeds `42,43,44`; dùng lại run đã có nếu cùng cấu hình/seed. Chọn theo F1 validation trung bình ở threshold 0,5; hòa thì ưu tiên ít tham số. Lấy checkpoint seed 42 của cấu hình thắng, tìm threshold trên validation. | Mean ± std, cấu hình thắng, threshold và lý do chọn. |
| **5. Test và export** | Khóa cấu hình, checkpoint và threshold, đánh giá test một lần cho model cuối cùng và baseline đối chiếu. Xuất bundle, reload trên CPU và kiểm tra dự đoán. | Bảng test, confusion matrix, đo inference và bundle có version. |

**Cấu hình training chung:** tối đa 50 epochs, early stopping patience 7 theo F1 validation tại threshold 0,5; hòa F1 thì chọn validation loss thấp hơn. Sigmoid chỉ dùng để chuyển logit thành score khi đánh giá. Giữ ma trận TF-IDF dạng sparse, chỉ chuyển từng batch sang dense `float32`; không chuyển toàn bộ tập sang dense để đưa lên GPU.

**Không gian Optuna:** hidden `[128]` hoặc `[256,128]`; dropout `0/0,2/0,4`; Adam hoặc AdamW; learning rate log-uniform `1e-4–3e-3`; weight decay `0/1e-5/1e-4/1e-3`; batch `32/64/128`. Giữ giới hạn TF-IDF và lựa chọn class weighting của cấu hình thắng bước 2. Objective là F1 validation tốt nhất tại threshold 0,5; dùng TPE seed 42 và pruning theo F1 từng epoch. Lưu study SQLite, cấu hình, checkpoint và trạng thái trial vào Drive để tiếp tục các trial còn lại khi Colab ngắt.

**Chốt threshold:** quét `0,10–0,90`, bước `0,01`, tối đa hóa F1 validation của checkpoint đã chọn; hòa thì chọn gần 0,5 nhất, sau đó ngưỡng nhỏ hơn. Không refit trên train + validation ở phiên bản đầu để tránh đổi checkpoint và threshold đã kiểm chứng. Chọn theo trung bình ba seed nên tuning vẫn có thể thua baseline. Validation chỉ có 419 mẫu và được dùng nhiều lần: ghi rõ nguy cơ overfit vào validation, không hứa mức tăng F1 trước khi chạy.

Cell đánh giá test có cờ `RUN_FINAL_TEST=False` mặc định; chỉ bật sau khi lưu lựa chọn đã khóa. Baseline LR/SVM cùng split dùng quy tắc dự đoán mặc định, baseline MLP dùng threshold 0,5. Benchmark LR/SVM cũ được trích riêng và ghi rõ lượng dữ liệu train khác nhau. Lưu kết quả cuối vào Drive để không cần mở lại test khi chỉ export hoặc kiểm tra reload.

## 4. Bundle và cách repo dùng lại

Bundle theo run ID gồm:

| File | Nội dung |
| --- | --- |
| `model.pt` | `state_dict` của checkpoint được chọn, lưu tensor trên CPU |
| `vectorizer.joblib` | TF-IDF đã fit; vocabulary và IDF tương ứng với weights |
| `config.json` | Kiến trúc, input dimension, threshold và mapping `0=Ham`, `1=Spam/Scam` |
| `metadata.json` | Run ID, seed, metrics, commit, hash dữ liệu/preprocessing và các file payload |
| `requirements-inference.txt` | Phiên bản runtime cần thiết, đã kiểm tra load trên CPU |
| `smoke_cases.json` | Input tổng hợp và label/score kỳ vọng để kiểm tra tính nhất quán |

Module inference cung cấp `load_bundle(path, device="cpu")`, trả predictor có `predict_texts(texts)`. Kết quả mỗi input gồm **label, score lớp 1, threshold, model version**. Predictor kiểm tra hash và kích thước input, dùng normalization chung, vectorizer đã lưu, `eval()` và chế độ không tính gradient. Load weights bằng `weights_only=True`; score sigmoid chưa được coi là xác suất đã hiệu chỉnh.

Lưu bundle trong `backend/artifacts/mlp/runs/<run_id>/`, dùng pointer riêng `backend/artifacts/mlp/current.json`. Chỉ cập nhật pointer sau khi reload kiểm tra thành công; giữ nguyên model đang dùng nếu bundle mới lỗi. Khi đưa model đã chọn vào Git, bổ sung quy tắc Git LFS cho `.pt` và ngoại lệ ignore phù hợp; vectorizer `.joblib` dùng quy tắc LFS hiện có. Không thay lock/bundle LR/SVM hiện tại. Deployment chỉ cài dependencies inference, load bundle và gọi predictor; không cần Colab, notebook, dữ liệu train hoặc GPU.

## 5. Tiêu chí hoàn thành khi triển khai

- Notebook chạy tuần tự từ runtime sạch, có bảng baseline → từng cải tiến → model cuối; lưu cấu hình, seed và môi trường để chạy lại. Không cam kết GPU tái lập từng bit giữa các phần cứng.
- Tuning không đọc nội dung test; test chỉ mở sau khi khóa lựa chọn. Kiểm tra hash file trước training không được dùng làm đầu vào lựa chọn model.
- Reload CPU giữ nguyên label, score sai lệch tối đa `1e-5` so với trước export; kiểm tra ở đúng threshold đã lưu.
- Smoke test gồm tiếng Việt, URL/phone, text ngoài vocabulary; input rỗng báo lỗi rõ ràng. Bundle thiếu file, sai hash hoặc sai dimension phải bị từ chối.
- Đo inference CPU sau warm-up, ghi thiết bị, batch size, số lượt và thời gian; ghi tổng dung lượng bundle. Báo cáo trung thực cả khi MLP kém LR/SVM.

Tham khảo triển khai: [lưu/load model PyTorch](https://docs.pytorch.org/tutorials/beginner/saving_loading_models), [Optuna pruning](https://optuna.readthedocs.io/en/stable/tutorial/10_key_features/003_efficient_optimization_algorithms.html).
