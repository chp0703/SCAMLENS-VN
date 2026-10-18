# Bộ dữ liệu SMS lừa đảo tiếng Việt được đảm bảo chất lượng (Official Release)
*(English Below)*

Chào mừng bạn đến với kho lưu trữ chính thức của **Bộ dữ liệu SMS lừa đảo tiếng Việt được đảm bảo chất lượng**.
Đây là một bộ dữ liệu được xây dựng nhằm phục vụ nghiên cứu trong các lĩnh vực **an ninh mạng**, **xử lý ngôn ngữ tự nhiên (NLP)** và **học máy**, với trọng tâm là bài toán **phát hiện tin nhắn SMS rác/lừa đảo**.

Bộ dữ liệu này được tổng hợp từ các tin nhắn SMS thực tế trong cuộc sống. Không AI-Generated hay dịch từ ngôn ngữ khác về. Chúng tôi thu thập từ nhiều nguồn khác nhau đã được sự đồng ý của người cung cấp tin nhắn
Chúng tôi chân thành cảm ơn Team Chống Lừa Đảo đã cho phép chúng tôi sử dụng tập dữ liệu gồm 50,000 URL để làm tiêu chí đánh giá nhãn. Chúng tôi cũng vô cùng cảm ơn những người đã đóng góp những đoạn tin nhắn cực kỳ quý giá và ý nghĩa cho học thuật

---

## Nhóm tác giả
* **Trần Nguyễn Thái Tuấn** – Trưởng nhóm nghiên cứu, Nghiên cứu phương pháp xây dựng tập dữ liệu, thiết kế khung làm việc, điều phối công việc, tham gia tìm kiếm nguồn tin nhắn
* **Lê Hoàng Khang** – Đồng tác giả sáng lập bộ quy tắc gán nhãn, thiết kế và điều phối các thành viên tham gia gán nhãn, xử lý dữ liệu, nhập dữ liệu, tìm kiếm nguồn tin nhắn
* **Nguyễn Minh Tài** – Nghiên cứu viên, đồng tác giả sáng lập bộ quy tắc gán nhãn, tham gia gán nhãn tin nhắn, xử lý dữ liệu tin nhắn, đóng gói sản phẩm đầu ra, hỗ trợ tìm kiếm nguồn tin nhắn, phụ trách tiền xử lý dữ liệu
* **Nguyễn Văn Thắng** – Nghiên cứu viên, quản lý và tổ chức dữ liệu, tối ưu khung làm việc, tham gia gán nhãn tin nhắn, hỗ trợ tìm kiếm nguồn tin nhắn, phụ trách tiền xử lý dữ liệu 
* **Mai Hoàng Đỉnh** – Cố vấn khoa học, Giảng viên hướng dẫn

---

## Tổng quan bộ dữ liệu
| Thuộc tính             | Thông tin                                                                                                                                       |
| :--------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------- |
| **Ngôn ngữ**           | Tiếng Việt (`vi`)                                                                                                                               |
| **Bài toán**           | Phân loại nhị phân tin nhắn SMS (`0` = Hợp lệ, `1` = Rác/Lừa đảo)                                                                               |
| **Ẩn danh dữ liệu**    | Toàn bộ thông tin định danh cá nhân (PII) được chuẩn hóa bằng các token như `[PHONE]`, `[BANK_ACC]`, `[MONEY]`, `[NUMBER]`, `[TIME]`, `[DATE]`. |
| **Đảm bảo chất lượng** | Kiểm tra thủ công trên các mẫu ngẫu nhiên cho thấy **không phát hiện thông tin định danh cá nhân còn sót lại** sau quá trình ẩn danh hóa.       |
| **Giấy phép**          | Creative Commons Attribution 4.0 International (CC BY 4.0)                                                                                      |

---

## Cấu trúc bộ dữ liệu

Bộ dữ liệu được phát hành dưới nhiều tệp nhằm phục vụ các mục đích nghiên cứu khác nhau.

| Tệp                | Mô tả                                                                                                                        | Quy mô    |
| :----------------- | :--------------------------------------------------------------------------------------------------------------------------- | :-------- |
| `full_dataset.csv` | Bộ dữ liệu hoàn chỉnh sau khi hoàn tất quy trình gán nhãn và kiểm định chất lượng (`message_id`, `date`, `message`, `label`) | 2.991 mẫu |
| `train.csv`        | Tập dữ liệu dành cho huấn luyện (`message`, `label`)                                                                         | 2.394 mẫu |
| `test.csv`         | Tập dữ liệu đánh giá độc lập, được thiết kế nhằm hạn chế hiện tượng rò rỉ dữ liệu giữa các tập                               | 597 mẫu   |

---

## Kết quả Đánh giá Benchmark các Mô hình (Model Benchmark Results)

Dưới đây là kết quả kiểm định 5-Fold Cross-Validation trên tập dữ liệu Unique Benchmark chính thức (sau khi lọc trùng lặp Jaccard J ≥ 0.85):

| Mô hình (Architecture) | Độ chính xác (Accuracy) | Precision (%) | Recall (%) | F1-Score (%) | 95% Bootstrap CI |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **PhoBERT-base** | **97.28% ± 0.88%** | **96.85% ± 1.10%** | **96.42% ± 1.25%** | **96.63% ± 1.05%** | [95.60%, 97.65%] |
| **Char (3–5 gram) SVM** | 96.34% ± 0.68% | 93.31% ± 2.06% | 93.55% ± 2.24% | **93.40% ± 1.21%** | [91.86%, 94.87%] |
| **RBF SVM** | 95.93% ± 0.23% | 95.29% ± 0.97% | 89.75% ± 1.62% | **92.42% ± 0.50%** | [90.77%, 93.99%] |
| **Linear SVM** | 95.79% ± 0.44% | 93.57% ± 1.39% | 91.07% ± 0.81% | **92.30% ± 0.79%** | [90.68%, 93.81%] |
| **MLP (Neural Network)** | 95.52% ± 0.47% | 91.79% ± 1.48% | 92.07% ± 1.34% | **91.92% ± 0.83%** | [90.43%, 93.47%] |
| **Logistic Regression** | 93.96% ± 0.80% | 95.25% ± 1.60% | 82.31% ± 2.80% | **88.28% ± 1.69%** | [86.38%, 90.19%] |
| **Multinomial Naive Bayes** | 89.02% ± 0.91% | 86.41% ± 2.94% | 71.74% ± 2.93% | **78.32% ± 1.86%** | [75.57%, 81.08%] |

---
## Đạo đức nghiên cứu (Ethics)

Quá trình thu thập và xử lý dữ liệu trong dự án được thực hiện theo các nguyên tắc đạo đức nghiên cứu đối với dữ liệu có nguồn gốc từ con người. Đề cương nghiên cứu đã được **Hội đồng Đạo đức của tổ chức** xem xét và xác nhận thuộc diện **miễn thẩm định (IRB Exemption)** theo **Mã hồ sơ: `IRB-2026-NLP-0428`**. Toàn bộ các tin nhắn do cộng đồng đóng góp đều được thu thập trên cơ sở **tự nguyện** và **đồng thuận sau khi đã được cung cấp đầy đủ thông tin** (informed consent).

---
## Trích dẫn (Citation)

Nếu bộ dữ liệu này hỗ trợ cho công trình nghiên cứu hoặc sản phẩm của bạn, vui lòng trích dẫn bài báo đi kèm:

```bibtex
@article{tuan2026vietnamese_sms_phishing,
  title={Vietnamese SMS Dataset with Quality Assurance},
  author={Tran, Nguyen Thai Tuan and Le, Hoang Khang and Nguyen, Minh Tai and Nguyen, Van Thang and Mai, Hoang Dinh},
  journal={IEEE Access},
  year={2026}
}
```



---

# Vietnamese Quality-Assured SMS Scam Dataset (Official Release)

*(Tiếng Việt bên trên)*

Welcome to the official repository of the **Vietnamese Quality-Assured SMS Scam Dataset**.

This dataset was developed to support research in **cybersecurity**, **natural language processing (NLP)**, and **machine learning**, with a primary focus on **SMS spam and scam detection**.

The dataset is compiled entirely from **real-world Vietnamese SMS messages**. It is **not AI-generated** and **not translated from other languages**. Messages were collected from multiple legitimate sources with the explicit consent of the contributors.

We sincerely thank **Team Chống Lừa Đảo** for granting permission to use their collection of **50,000 malicious URLs** as a reference resource for the labeling and verification process. We are also deeply grateful to everyone who voluntarily contributed valuable SMS messages, making this dataset possible and supporting future academic research.

---

## Authors

- **Tran Nguyen Thai Tuan** – Lead Researcher; responsible for dataset construction methodology, framework design, project coordination, and SMS data collection.
- **Le Hoang Khang** – Co-author; co-developed the annotation guidelines, coordinated the annotation team, performed data processing and data entry, and contributed to SMS collection.
- **Nguyen Minh Tai** – Researcher; co-developed the annotation guidelines, participated in message annotation, data processing, dataset packaging, SMS collection, and data preprocessing.
- **Nguyen Van Thang** – Researcher; responsible for dataset management and organization, workflow optimization, message annotation, SMS collection, and data preprocessing.
- **Mai Hoang Dinh** – Scientific Advisor and Academic Supervisor.

---

## Dataset Overview

| Attribute | Description |
| :-------- | :---------- |
| **Language** | Vietnamese (`vi`) |
| **Task** | Binary SMS classification (`0` = Legitimate, `1` = Spam/Scam) |
| **Data Anonymization** | All personally identifiable information (PII) has been replaced with standardized placeholder tokens such as `[PHONE]`, `[BANK_ACC]`, `[MONEY]`, `[NUMBER]`, `[TIME]`, and `[DATE]`. |
| **Quality Assurance** | Manual inspection of randomly sampled messages confirmed that **no residual personally identifiable information (PII)** was detected after the anonymization process. |
| **License** | Creative Commons Attribution 4.0 International (CC BY 4.0) |

---

## Dataset Structure

The dataset is released in multiple files to support different research purposes.

| File | Description | Size |
| :--- | :---------- | :--: |
| `full_dataset.csv` | Complete dataset after annotation and quality assurance (`message_id`, `date`, `message`, `label`) | 2,991 samples |
| `train.csv` | Training dataset (`message`, `label`) | 2,394 samples |
| `test.csv` | Independent testing dataset designed to minimize data leakage | 597 samples |

---

## Model Benchmark Results

The following results were obtained using **5-fold cross-validation** on the official **Unique Benchmark Dataset** after duplicate removal using a **Jaccard similarity threshold of J ≥ 0.85**.

| Architecture | Accuracy | Precision (%) | Recall (%) | F1-Score (%) | 95% Bootstrap CI |
| :----------- | :------: | :-----------: | :--------: | :----------: | :--------------: |
| **PhoBERT-base** | **97.28% ± 0.88%** | **96.85% ± 1.10%** | **96.42% ± 1.25%** | **96.63% ± 1.05%** | [95.60%, 97.65%] |
| **Char (3–5 gram) SVM** | 96.34% ± 0.68% | 93.31% ± 2.06% | 93.55% ± 2.24% | **93.40% ± 1.21%** | [91.86%, 94.87%] |
| **RBF SVM** | 95.93% ± 0.23% | 95.29% ± 0.97% | 89.75% ± 1.62% | **92.42% ± 0.50%** | [90.77%, 93.99%] |
| **Linear SVM** | 95.79% ± 0.44% | 93.57% ± 1.39% | 91.07% ± 0.81% | **92.30% ± 0.79%** | [90.68%, 93.81%] |
| **MLP (Neural Network)** | 95.52% ± 0.47% | 91.79% ± 1.48% | 92.07% ± 1.34% | **91.92% ± 0.83%** | [90.43%, 93.47%] |
| **Logistic Regression** | 93.96% ± 0.80% | 95.25% ± 1.60% | 82.31% ± 2.80% | **88.28% ± 1.69%** | [86.38%, 90.19%] |
| **Multinomial Naive Bayes** | 89.02% ± 0.91% | 86.41% ± 2.94% | 71.74% ± 2.93% | **78.32% ± 1.86%** | [75.57%, 81.08%] |

---

## Research Ethics

The data collection and processing procedures followed established research ethics principles for human-derived data. The study protocol was reviewed by the **Institutional Ethics Committee** and determined to qualify for **IRB Exemption** under **Protocol ID:** **`IRB-2026-NLP-0428`**.

All community-contributed SMS messages were collected on a **voluntary basis** with **informed consent** obtained from every contributor before submission.

---

## Citation

If this dataset contributes to your research or application, please cite the accompanying paper:

```bibtex
@article{tuan2026vietnamese_sms_phishing,
  title={Vietnamese SMS Dataset with Quality Assurance},
  author={Tran, Nguyen Thai Tuan and Le, Hoang Khang and Nguyen, Minh Tai and Nguyen, Van Thang and Mai, Hoang Dinh},
  journal={IEEE Access},
  year={2026}
}
```
