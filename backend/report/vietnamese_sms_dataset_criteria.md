# Báo cáo Trích xuất Tiêu chí Phân loại và Đặc trưng Dữ liệu: `vietnamese_sms_dataset`

- **Nguồn dữ liệu:** [`trannguyenthaituan251209/vietnamese_sms_dataset`](https://github.com/trannguyenthaituan251209/vietnamese_sms_dataset) (Hugging Face: `trannguyenthaituan/vietnamese_sms_phishing_dataset` / `vietnamese_sms_phishing_sample`)
- **Bản sao lưu trong repo:** `backend/data/raw/vietnamese_sms_dataset/` (revision `464a028878023598e16f2f344ee36f7d5d74257f`, SHA-256 `full_dataset.csv`: `710cd7b56ef1b4aa82e72c1be0f46a5c89a5fdce8382b30874b3cea494d16e3e`)
- **Nhóm tác giả bộ dữ liệu:** Trần Nguyễn Thái Tuấn (Trưởng nhóm), Lê Hoàng Khang, Nguyễn Minh Tài, Nguyễn Văn Thắng; Cố vấn khoa học: Mai Hoàng Đỉnh
- **Bài báo đi kèm:** *Vietnamese SMS Dataset with Quality Assurance* / *Quality-Assured Vietnamese SMS Phishing Dataset: Closed-Loop Human Adjudication Framework and Leakage-Controlled Transformer Benchmarking* (2026)
- **Giấy phép & Đạo đức nghiên cứu:** CC BY 4.0 | Mã miễn thẩm định đạo đức: `IRB-2026-NLP-0428`

---

## 1. Các tiêu chí phân loại và xây dựng dữ liệu do nhóm tác giả công bố

Dựa trên tài liệu chính thức của nhóm tác giả (`README.md`, `QUICKSTART_GUIDE.md` và Dataset Card trên Hugging Face), bộ dữ liệu được thiết kế và gán nhãn theo **6 tiêu chí phương pháp luận** sau:

### 1.1. Định nghĩa bài toán và hệ nhãn nhị phân (Binary Classification Schema)
Bộ dữ liệu định nghĩa bài toán phân loại nhị phân trên tin nhắn SMS tiếng Việt với cột `label` nhận hai giá trị:
- **Nhãn `0` — Hợp lệ (`Legitimate` / `HAM`):** Tin nhắn SMS thông thường, hợp pháp và không mang tính chất lừa đảo hay phát tán rác trái phép (bao gồm thông báo giao dịch ngân hàng, mã OTP, thông báo nhà mạng, quảng cáo chính thống có đăng ký của nhà mạng, thông báo hành chính/tiện ích và tin nhắn cá nhân).
- **Nhãn `1` — Rác / Lừa đảo (`Spam / Scam` / `SPAM`):** Nhãn dương tính **gộp chung** cả hai nhóm hành vi:
  1. **Tin nhắn lừa đảo (Scam / Phishing / Smishing):** Giả mạo ngân hàng, cơ quan nhà nước, đơn vị vận chuyển, tuyển dụng việc nhẹ lương cao, đầu tư tài chính, vay tín dụng đen, đe dọa đòi nợ hoặc mạo danh người quen để chiếm đoạt tài sản/thông tin.
  2. **Tin nhắn rác thương mại / dịch vụ trái phép (Spam):** Quảng cáo cờ bạc, cá cược trực tuyến, game đổi thưởng, gạ gẫm tình dục/hẹn hò, hoặc phát tán quảng cáo hàng loạt không qua kênh Brandname hợp chuẩn của nhà mạng.

### 1.2. Tiêu chí về tính xác thực của nguồn tin (Source Authenticity Criteria)
- **100% tin nhắn thực tế (Real-world Vietnamese SMS):** Toàn bộ mẫu được thu thập từ tin nhắn SMS thực tế tại Việt Nam.
- **Không dùng dữ liệu nhân tạo hay dịch máy:** Nhóm tác giả đặt tiêu chí loại trừ hoàn toàn văn bản do AI tự sinh (*No AI-generated text*) và văn bản dịch từ ngôn ngữ khác sang tiếng Việt (*No machine-translated text*).
- **Đồng thuận tự nguyện (Informed Consent):** Tin nhắn do cộng đồng đóng góp được thu thập trên cơ sở tự nguyện và có sự đồng ý của người cung cấp.

### 1.3. Tiêu chí đối chiếu đường dẫn độc hại (External URL Verification Criteria)
- Nhóm tác giả sử dụng bộ dữ liệu **50.000 URL độc hại** được **Team Chống Lừa Đảo (`chongluadao.vn`)** cấp phép làm nguồn tham chiếu chuẩn để xác minh, kiểm chứng và gán nhãn `1` cho các tin nhắn có chứa liên kết nghi ngờ (phishing, malware, cờ bạc, giả mạo thương hiệu).

### 1.4. Quy trình gán nhãn đa tác giả và phân xử vòng kín (Closed-Loop Human Adjudication)
- **Bộ quy tắc gán nhãn (Annotation Guidelines):** Do Lê Hoàng Khang và Nguyễn Minh Tài đồng sáng lập, dưới sự điều phối của Trần Nguyễn Thái Tuấn và cố vấn khoa học Mai Hoàng Đỉnh.
- **Đồng thuận nhiều người gán nhãn (Multi-Annotator Agreement):** Các mẫu tin nhắn được gán nhãn độc lập bởi nhiều thành viên (Nguyễn Minh Tài, Nguyễn Văn Thắng, Lê Hoàng Khang) và đưa qua vòng phân xử thủ công khép kín (*closed-loop adjudication*) để giải quyết các trường hợp biên hoặc văn bản bị làm rối đối kháng.

### 1.5. Tiêu chí khử trùng lặp và kiểm soát rò rỉ dữ liệu (Deduplication & Leakage Control)
- Nhóm tác giả áp dụng độ đo tương đồng **Jaccard với ngưỡng $J \ge 0.85$** để lọc các tin nhắn trùng lặp theo mẫu (*near-duplicate template deduplication*) khi xây dựng tập Unique Benchmark và phân chia tập huấn luyện (`train.csv` — 2.394 mẫu) / tập kiểm thử độc lập (`test.csv` — 597 mẫu) từ tập gốc (`full_dataset.csv` — 2.991 mẫu).

### 1.6. Tiêu chí ẩn danh hóa thông tin định danh cá nhân (PII Anonymization Criteria)
- Theo công bố của nhóm tác giả, mọi thông tin định danh cá nhân (PII) xuất hiện trong tin nhắn đều được thay thế bằng các token chuẩn hóa như `[PHONE]`, `[BANK_ACC]`, `[MONEY]`, `[NUMBER]`, `[TIME]`, `[DATE]` và được kiểm tra thủ công trên các mẫu ngẫu nhiên (200 mẫu) để bảo đảm quyền riêng tư.

---

## 2. Phân tích thực nghiệm: Các tiêu chí phân loại thực tế trong `full_dataset.csv`

Qua kiểm tra trực tiếp toàn bộ **2.991 mẫu** trong `full_dataset.csv` (**2.193 mẫu nhãn `0` [73,32%]** và **798 mẫu nhãn `1` [26,68%]**), có thể trích xuất chi tiết bộ quy tắc ngầm định và hệ phân loại (taxonomy) mà nhóm tác giả đã áp dụng trong thực tế:

### 2.1. Phân nhóm theo tiền tố mã định danh (`message_id` Prefixes)
Cột `message_id` trong `full_dataset.csv` được đánh mã theo 3 tiền tố nguồn thu thập:

| Tiền tố | Ý nghĩa / Đặc điểm nhóm mẫu | Nhãn `0` (Ham) | Nhãn `1` (Spam/Scam) | Tổng cộng |
| :--- | :--- | ---: | ---: | ---: |
| **`COM_`** | Nhóm thu thập cộng đồng & thương mại tổng hợp (Community / Commercial) | 2.189 | 760 | **2.949** |
| **`TE_`** | Nhóm kiểm thử viễn thông & giả mạo thương hiệu (Telecom / Test batch, ngày `28/05/2026`) | 4 | 23 | **27** |
| **`NEW_`** | Nhóm mẫu lừa đảo mới bổ sung (New phishing batch, ngày `04/06/2026`) | 0 | 15 | **15** |
| **Tổng** | **Toàn bộ `full_dataset.csv`** | **2.193** | **798** | **2.991** |

### 2.2. Quy tắc ranh giới quan trọng: Quảng cáo hợp lệ (Nhãn `0`) vs. Quảng cáo rác/Lừa đảo (Nhãn `1`)
Một đặc trưng cốt lõi trong tiêu chí gán nhãn của nhóm tác giả là **không đánh đồng mọi tin nhắn quảng cáo với Spam (`label = 1`)**:

| Tiêu chí đối chiếu | Xếp vào Nhãn `0` (Hợp lệ / `HAM`) | Xếp vào Nhãn `1` (Rác & Lừa đảo / `SPAM`) |
| :--- | :--- | :--- |
| **Nhãn tiền tố nhà mạng** | Có tiền tố **`[QC]`**, **`(QC)`** (359/360 mẫu thuộc nhãn `0`) hoặc **`[TB]`**, **`(TB)`** (748/749 mẫu thuộc nhãn `0`). | Không có tiền tố `[QC]` chuẩn của nhà mạng, hoặc tự chèn nhãn thương hiệu giả mạo ở đầu tin (ví dụ: `[BĐS_ĐấtNền]`, `[Spa_LamDep]`, `[Techcom6ank]`). |
| **Cú pháp từ chối quảng cáo (Opt-out)** | Có cú pháp từ chối chuẩn theo Nghị định 91/2020/NĐ-CP ở cuối tin: *`Từ chối QC, soạn TC... gửi 199 / 9241`* (349/350 mẫu thuộc nhãn `0`). | Không có cú pháp từ chối hợp lệ, hoặc yêu cầu nhắn tin đến đầu số dịch vụ tính phí ngầm `8xxx` (*`Soạn DK gửi 8x28`*, *`8x51`*, *`8x00`*). |
| **Quảng cáo vay tiêu dùng / mở thẻ tín dụng** | **Gán nhãn `0`** nếu là tin `[QC]` do nhà mạng phát hành hợp tác với định chế tài chính chính thống (Viettel Money, MoMo, VNPT, VIB, VPBank, FE Credit, Home Credit, TNEX, Mcredit) kèm link/đầu số chính thức (49/50 mẫu). | **Gán nhãn `1`** nếu là tin mời vay tín dụng đen, giải ngân qua app lạ/link ngoài, yêu cầu đóng phí bảo hiểm khoản vay trước vào số tài khoản cá nhân, hoặc đe dọa đòi nợ. |
| **Quảng cáo dân sinh (BĐS, Spa, Khóa học, Đông y)** | Chỉ gán nhãn `0` khi nằm trong chương trình ưu đãi tích hợp chính thức của nhà mạng (ví dụ voucher khóa học tặng kèm gói cước 5G gửi `191`). | **100% gán nhãn `1`** đối với tin nhắn rác rao bán Bất động sản (16 mẫu), Spa làm đẹp (6 mẫu), Khóa học tiếng Anh/Forex (7 mẫu), Thuốc nam, Gia sư... phát tán qua SĐT cá nhân hoặc link `.vip`/`.top`. |

### 2.3. Hệ phân loại chi tiết các nhóm nội dung thuộc Nhãn `0` (Hợp lệ — 2.193 mẫu)

| STT | Nhóm nội dung Nhãn `0` (`Legitimate` / `HAM`) | Số mẫu | Tỷ lệ (%) | Dấu hiệu / Tiêu chí nhận diện điển hình trong tập dữ liệu |
| :-: | :--- | ---: | ---: | :--- |
| 1 | **Thông báo nhà mạng viễn thông** | 1.082 | 49,34% | Tiền tố `[TB]`, `Viettel TB`; thông báo đăng ký/gia hạn gói cước (`ST30K`, `5G`, `*098#`), khuyến mãi nạp thẻ, điểm `Viettel++`, xác thực thông tin thuê bao theo Thông tư `08/TT-BKHCN`, liên hệ tổng đài `198`, `191`, `197`, tên miền `viettel.vn`, `my.vnpt.com.vn`. |
| 2 | **Quảng cáo dịch vụ chính thống của nhà mạng** | 369 | 16,83% | Tiền tố `[QC]` hoặc `(QC)`, giới thiệu dịch vụ Internet cáp quang, gói data, bảo hiểm, tài chính liên kết (Viettel Money, MoMo, VIB, FE Credit), luôn kèm cú pháp `Từ chối QC, soạn TC... gửi 199`. |
| 3 | **Thương mại điện tử, giao hàng & đặt xe** | 353 | 16,10% | Thông báo trạng thái đơn hàng, xác nhận giao hàng thành công, ưu đãi từ các nền tảng chính thức (Shopee, Lazada, Grab, MoMo...). |
| 4 | **Giao dịch ngân hàng, ví điện tử & mã OTP** | 273 | 12,45% | Cung cấp mã xác thực `OTP` (235 mẫu), thông báo biến động số dư, chuyển khoản nhanh 24/7 (`VCB Digibank`, `Sacombank`, `TPBank`, `MyVIB`, `TrustCA`) kèm cảnh báo bảo mật không cung cấp OTP cho bất kỳ ai. |
| 5 | **Hội thoại cá nhân, công việc & khảo sát CSKH** | 103 | 4,70% | Tin nhắn hỏi thăm đời sống, trao đổi công việc, chúc mừng sinh nhật khách hàng (`VNDIRECT`), khảo sát chất lượng dịch vụ (`[KHAO SAT] VIETTEL`). |
| 6 | **Tiện ích, hành chính công & tuyên truyền nhà nước** | 13 | 0,59% | Tin nhắn tuyên truyền an toàn giao thông dịp lễ Quốc khánh, cuộc thi tìm hiểu Luật phòng chống ma túy, hoặc tin `[CẢNH BÁO]` chính thức từ Cục An ninh mạng (A05) cảnh báo người dân về các thủ đoạn tội phạm. |

### 2.4. Hệ phân loại chi tiết các nhóm nội dung thuộc Nhãn `1` (Rác / Lừa đảo — 798 mẫu)

| STT | Nhóm nội dung Nhãn `1` (`Spam / Scam`) | Số mẫu | Tỷ lệ (%) | Thủ đoạn & Dấu hiệu nhận diện điển hình trong tập dữ liệu |
| :-: | :--- | ---: | ---: | :--- |
| 1 | **Cờ bạc, cá cược, game đổi thưởng & spam biến dạng ký tự** | 166 | 20,80% | Quảng cáo nhà cái (`8qbet`, `PKWIN`, `79CLUB`, `NOHU`, `TDTC`, `F8BET`, `W88`, `Hi88`, `789BET`), tặng code tân thủ/lì xì, hoàn trả 100% nạp đầu; thường dùng kỹ thuật làm rối ký tự để lách bộ lọc nhà mạng. |
| 2 | **Giả mạo ngân hàng (Bank Phishing)** | 157 | 19,67% | Mạo danh `Vietcombank`, `Techcombank`, `BIDV`, `VietinBank`, `ACB`, `VPBank`, `MB Bank`, `Agribank` báo đăng nhập thiết bị lạ, khóa tài khoản, chưa cập nhật sinh trắc học, đổi điểm thưởng `Priority`/`Diamond` sắp hết hạn, hoặc giả nhân viên CSKH yêu cầu đọc mã OTP 6 số để "hủy giao dịch đáng ngờ". |
| 3 | **Tín dụng đen, lừa phí giải ngân & đe dọa đòi nợ** | 78 | 9,77% | Mời vay nhanh không thế chấp; báo hồ sơ vay đã duyệt nhưng bắt chuyển trước "phí bảo hiểm khoản vay" vào TK cá nhân; hoặc đe dọa trả nợ trước `[TIME]` nếu không sẽ phát tán hình ảnh, liên hệ danh bạ/đồng nghiệp, khép tội "chiếm đoạt tài sản". |
| 4 | **Lừa đảo tuyển dụng & cộng tác viên (Job / Task Scam)** | 75 | 9,40% | Mạo danh trưởng phòng nhân sự hoặc sàn TMĐT (`Shopee`, `Lazada`, `TikTok`, `Amazon`, `Booking`) tuyển CTV làm việc tại nhà, chốt đơn ảo, like video nhận hoa hồng 10–15% / lương trả theo ngày qua Zalo/Telegram. |
| 5 | **Giả mạo cơ quan nhà nước & tiện ích công** | 63 | 7,89% | Giả mạo CSGT báo phạt nguội (`dichvucong-vn.com`, `phatnguoi.cucduongbo.top`), Bộ Công an gửi lệnh triệu tập/bắt tạm giam liên quan rửa tiền, yêu cầu cập nhật VNeID/sổ hộ khẩu điện tử, Cục Đăng kiểm gia hạn online, Cục Thuế báo hoàn thuế TNCN, nhận tiền hỗ trợ BHTN theo Nghị quyết 116, Điện lực/Cấp nước báo cắt điện/nước. |
| 6 | **Giả mạo vận chuyển, tài khoản số & trúng thưởng** | 63 | 7,89% | Giả mạo `ViettelPost`, `GHTK`, `J&T`, `FedEx`, `EMS` báo đơn hàng kẹt hải quan/rách tem/nộp phí lưu kho; giả mạo `Apple iCloud` báo tìm thấy iPhone bị mất; cảnh báo khóa `Telegram`, `WhatsApp`, `Zalo`, `Gmail`, `Netflix`; báo trúng thưởng xe SH/quà mỹ phẩm yêu cầu trả phí ship. |
| 7 | **Lừa đảo đầu tư tài chính, chứng khoán & tiền ảo** | 40 | 5,01% | Mạo danh quỹ đầu tư (`VNDIRECT`, `SSI`, `MBS`, `VinaCapital`, `Finhay`), khóa học Forex, nhóm tín hiệu Crypto/USDT, đồng thuận đổi `Pi Network`, hoặc dự án "nuôi bò ảo/trồng cây ảo" cam kết lợi nhuận 2%/ngày hoặc 30%/tháng. |
| 8 | **Gạ gẫm tình dục & hẹn hò nhạy cảm (Adult Scam)** | 9 | 1,13% | Tin nhắn gạ gẫm Sugar Baby, gái gọi, xem livestream nhạy cảm, hoặc báo "nhận được 3 ảnh riêng tư từ bạn nữ ẩn danh" dẫn dụ truy cập Telegram/link độc hại. |
| 9 | **Mạo danh cá nhân & quảng cáo rác dân sinh khác** | 147 | 18,42% | Mạo danh con báo cấp cứu bệnh viện cần chuyển viện phí gấp; mạo danh sếp đang họp nhờ chuyển tiền cho đối tác; kế toán báo chuyển khoản nhầm/dư xin hoàn lại vào STK lạ; nhờ bình chọn cuộc thi "Nữ sinh thanh lịch"; cùng các mẫu quảng cáo rác BĐS, Spa, Khóa học, khuyến mãi gửi đầu số `8xxx` và chuỗi spam mã hóa. |

---

## 3. Các chỉ dấu kỹ thuật (Technical Indicators) đặc trưng của Nhãn `1`

Ngoài ngữ nghĩa nội dung, nhóm tác giả đã thu thập và gán nhãn `1` dựa trên **4 nhóm chỉ dấu kỹ thuật** điển hình của tội phạm mạng tại Việt Nam:

1. **Tên miền giả mạo (Typosquatting / Lookalike Domains) và TLD rủi ro cao:**
   - Giả mạo tên thương hiệu kèm từ khóa phụ hoặc sai lệch 1 ký tự: `vietinbamk.com`, `vietcombank.vn-gll.top`, `techcombank.huy-the-visa-vn.com`, `vndichvucong-gov.com`, `vneid.hethong-chinhphu.top`, `bocongan.apk-chinhphu.cc`, `shopee.tuyendung-ctv.top`, `whastxpp.vip`, `ICloud.co`.
   - Sử dụng các đuôi tên miền giá rẻ/rủi ro cao hầu như không xuất hiện ở nhóm hợp lệ: `.top`, `.vip`, `.cc`, `.xyz`, `.icu`, `.online`, `.bid`, `.club`, `.de`, `.me`, `.run`, `.band`, `.sh`, `.tech`.
2. **Giả mạo định danh người gửi bằng ngoặc vuông kèm biến đổi ký tự (Homoglyph Brand Spoofing):**
   - Trong khi nhóm `0` chỉ dùng `[TB]`, `[QC]`, `[KHAO SAT]`, `[CẢNH BÁO]` và một số tên dịch vụ thật, nhóm `1` có tới **223 mẫu** mở đầu bằng `[Tên_Thương_Hiệu]` tự tạo, thường cố tình thay chữ `I` bằng `l`, `O` bằng `0`, `B` bằng `6`, `c` bằng `¢` để qua mặt bộ lọc từ khóa nhà mạng:
     - Ví dụ: `[VlETCOMBANK]`, `[Techcom6ank]`, `[M.B.B.A.N.K]`, `[B0_C0NG_AN]`, `[FPT_Tele¢om]`, `[Vietnam_Alrlines]`, `[Travel0ka_VN]`, `[Google_St0rage]`, `[Zal0-Security]`, `[B]WASE_NuocSach]`, `[Sh0pee_CTV]`, `[TikT0k_Media]`, `[VlNDlRECT_Group]`, `[Ssl_Securjtjes]`.
3. **Kỹ thuật làm rối văn bản đối kháng (Adversarial Text Obfuscation — 57+ mẫu):**
   - **Nhân bản ký tự xen kẽ hoa-thường:** `NhHậẬnNLLLuUôônnNNNggaAayTTámTrRRăămM...` (`COM_070`).
   - **Chèn ký tự đặc biệt/dấu câu vào giữa từ:** `RepMS&Li`xi~phO;ng,Bj`D:o?-b;A;y?` (`COM_450`), `d!eu k!en NHAN'TIEN` (`NEW_054`).
   - **Leetspeak / thay chữ bằng số và viết sai dấu Telex:** `c0 g4i live sTre4m... t3Le` (`COM_469`), `Lj;xjTamchujc` (`COM_506`), `TÁimqtẠjmNgarn` (`COM_597`).
   - **Chuỗi ký tự ngẫu nhiên đính kèm mã số:** `zLhFVQCDieunIkJyezlEnbeJOU.>.> .>385!!2<-<-<-hNjOOwWVrMyUxCoKMaV` (`COM_2070`–`COM_2076`).
4. **Cơ chế thao túng tâm lý (Social Engineering Triggers):**
   - **Khẩn cấp / Đe dọa (Urgency & Fear):** Đe dọa khóa tài khoản, cắt điện/nước, phạt nguội, lệnh bắt tạm giam, cấp cứu bệnh viện, phát tán danh bạ trước `[TIME]` hôm nay.
   - **Lợi ích tài chính bất thường (Greed / Lure):** Tặng tiền/code miễn phí, hoàn thuế TNCN, trợ cấp BHTN, điểm thưởng sắp hết hạn, việc nhẹ lương cao, lợi nhuận đầu tư 30%/tháng.
   - **Yêu cầu hành động rủi ro (High-Risk Call-to-Action):** Yêu cầu truy cập link lạ, cài đặt file `.apk`, đọc mã OTP 6 số, hoặc chuyển khoản phí ứng trước (phí bảo hiểm vay, phí lưu kho, phí hoàn thuế) vào số tài khoản cá nhân.

---

## 4. Các phát hiện kiểm toán dữ liệu (Audit Findings) cần lưu ý khi sử dụng trong ScamLens VN

Khi đối chiếu giữa **tài liệu công bố của nhóm tác giả** và **nội dung thực tế trong `full_dataset.csv`**, pipeline tiền xử lý của dự án (`backend/scripts/prepare_data.py` và `backend/report/preprocess_v3.md`) đã ghi nhận 4 điểm khác biệt quan trọng:

1. **Khác biệt giữa danh sách token PII công bố và thực tế:**
   - `README.md` của tác giả liệt kê 6 token: `[PHONE]`, `[BANK_ACC]`, `[MONEY]`, `[NUMBER]`, `[TIME]`, `[DATE]`.
   - Tuy nhiên, kiểm tra toàn bộ `full_dataset.csv` cho thấy **không có bất kỳ token `[PHONE]` (0 lần) hay `[BANK_ACC]` (0 lần) nào**. Thực tế nhóm tác giả đã gộp SĐT và số tài khoản vào `[NUMBER]` (2.618 lần), đồng thời sử dụng thêm các token không được liệt kê trong bảng tổng quan gồm `[POINT]` (221 lần), `[NAME]` (141 lần) và `[URL]` (1 lần).
2. **Thực thể và thông tin nhạy cảm chưa được che kín hoàn toàn trong bản gốc:**
   - Trong `full_dataset.csv` vẫn còn tồn tại **1.336 mẫu chứa URL nguyên bản** (`http://`, `https://`, `www.`), **6 mẫu chứa địa chỉ email**, **7 mẫu chứa chuỗi số dạng SĐT**, **18 mẫu nhãn `1` chứa nguyên số tài khoản ngân hàng (9–16 chữ số)** (ví dụ `COM_1484`, `COM_1812`, `COM_1838`...) và **173 mẫu chứa nguyên mã OTP 4–6 chữ số**. Do đó, bước chuẩn hóa `normalize_text()` của ScamLens VN bắt buộc phải tiếp tục mask `[URL]`, `[EMAIL]`, `[PHONE]`.
3. **Trùng lặp mẫu và rò rỉ giữa `train.csv` / `test.csv` gốc:**
   - Trong `full_dataset.csv` (2.991 dòng) chỉ có **2.630 nội dung tin nhắn duy nhất** (tồn tại 423 mẫu trùng lặp trước/sau chuẩn hóa).
   - Giữa `train.csv` (2.394 mẫu) và `test.csv` (597 mẫu) do tác giả chia sẵn vẫn còn **47 dòng trong `test.csv` trùng khớp 100% nội dung với `train.csv`** (đã được ghi nhận trong `backend/data/raw/vietnamese_sms_dataset/source.json`). Vì lý do này, ScamLens VN không dùng bản chia `train.csv`/`test.csv` gốc mà thực hiện làm sạch và chia lại theo nhóm tương đồng (`StratifiedGroupKFold` trên cụm Jaccard 5-gram ký tự $\ge 0.85$).
4. **Mâu thuẫn nhãn (Label Noise / Inconsistencies) trong dữ liệu gốc:**
   - **2 cặp mẫu trùng nội dung nhưng ngược nhãn** (đã bị pipeline ScamLens VN cách ly vào `backend/data/processed/quarantine.csv`):
     - Mẫu cờ bạc `8qbet`: `COM_1222` được gán nhãn `0` trong khi `COM_072` (cùng mẫu câu, chỉ khác subdomain) được gán nhãn `1`.
     - Mẫu cảnh báo mở khóa thiết bị `account@ezviz.com`: `COM_2990` được gán nhãn `0` trong khi `COM_2055` (trùng hoàn toàn câu chữ) được gán nhãn `1`.
   - **2 cụm gần trùng (near-duplicate) bị gán nhãn bất nhất** (ghi nhận trong `backend/data/processed/near_duplicate_pairs.csv`):
     - Tin `[TB] Ứng dụng Tuyên giáo và Dân vận...`: `COM_1746` bị gán nhãn `1`, trong khi 3 mẫu giống hệt (`COM_1243`, `COM_2429`, `COM_2970`) được gán nhãn `0`.
     - Tin cờ bạc `Ban vao ngay pkwin... trải nghiệm casino, nổ hũ hay nhất`: `COM_2991` bị gán nhầm nhãn `0`, trong khi `COM_2057` được gán nhãn `1`.
   - **Trường hợp biên của tin `[QC]` vay tiêu dùng:** Mẫu `COM_2025` (`[QC]QK du dieu kien vay tieu dung... tu EASY CREDIT... soan TC EASY CREDIT gui [NUMBER]`) được gán nhãn `1`, trong khi 49 mẫu `[QC]` vay tiêu dùng tương tự từ FE Credit, Home Credit, TNEX, TINVAY, Mcredit được gán nhãn `0`.
