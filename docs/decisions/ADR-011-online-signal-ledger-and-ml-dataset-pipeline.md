# ADR-011: Sổ Cái Tín Hiệu Trực Tuyến & Chuẩn Hóa Dataset Cho Machine Learning

- **Trạng thái:** ACCEPTED
- **Ngày quyết định:** 2026-10-27
- **Phạm vi tác động:** `src/collector/google_sheets_client.py`, `src/risk_engine/signal_tracker.py`, `src/collector/fialda_scanner.py`, `.github/workflows/scanner_and_pages.yml`, `docs/google_sheets_setup.md`, `docs/spec.md`, `docs/architecture.md`, `README.md`

---

## 1. Bối Cảnh (Context)

Hệ thống Neiro-Stock-VN đã có Sổ Cái Tín Hiệu Ngầm ([ADR-009](file:///c:/Users/Daniel/Documents/My-Projects/Neiro-Stock-VN/docs/decisions/ADR-009-background-anti-fomo-signal-ledger-and-chasing-prevention.md)) lưu trữ cục bộ tại `data/active_signals.jsonl` để kiểm soát rủi ro mua đuổi. Tuy nhiên, người dùng yêu cầu:
1. **Lưu trữ Online tự động và Phân tích trực quan miễn phí:** Cần một kênh lưu trữ trực tuyến không tốn dung lượng máy tính (0 MB local, tuân thủ Zero-Waste Mandate < 15MB) và dễ dàng theo dõi trực quan bằng các công cụ phân tích của Google ("Google Analysis" / Google Looker Studio).
2. **Mục tiêu dài hạn phục vụ Machine Learning (ML):** Cần một tập dữ liệu chuẩn hóa dạng bảng (Tabular Feature Store) ghi nhận trọn vẹn đặc trưng vi cấu trúc & cơ bản tại thời điểm $T_0$ (Feature Vector $X$) song song với việc tự động theo dõi, gán nhãn kết quả thực tế theo chu kỳ thanh toán $T+2.5$ đến $T+20$ (Ground Truth Labels $y$).

---

## 2. Quyết Định Thiết Kế (Decisions)

### 2.1. Kiến Trúc Đồng Bộ Siêu Nhẹ Qua Google Apps Script Webhook
- Thay vì cài đặt các gói SDK cồng kềnh (`google-cloud-sdk`, `gspread`, `google-auth` nặng > 40MB vi phạm Zero-Waste Mandate), xây dựng module độc lập [src/collector/google_sheets_client.py](file:///c:/Users/Daniel/Documents/My-Projects/Neiro-Stock-VN/src/collector/google_sheets_client.py) (< 100 dòng code) chỉ sử dụng thư viện `requests` có sẵn.
- **Cơ chế Webhook:** Người dùng tạo Google Sheet và dán đoạn mã Google Apps Script mẫu (được cung cấp tại [docs/google_sheets_setup.md](file:///c:/Users/Daniel/Documents/My-Projects/Neiro-Stock-VN/docs/google_sheets_setup.md)). Khi hệ thống chạy trên GitHub Actions (mỗi 30 phút trong giờ giao dịch), `GoogleSheetsLedgerClient` gửi HTTP POST payload JSON lên Webhook để tự động thêm mới hoặc cập nhật trạng thái các dòng cổ phiếu.
- **Graceful Offline Mode:** Nếu chưa cấu hình biến `GOOGLE_SHEET_WEBHOOK_URL`, client tự động bỏ qua đồng bộ trực tuyến mà không gây crash pipeline.

### 2.2. Mở Rộng Cấu Trúc Dữ Liệu Phục Vụ Machine Learning
Dataclass `ActiveSignal` trong [src/risk_engine/signal_tracker.py](file:///c:/Users/Daniel/Documents/My-Projects/Neiro-Stock-VN/src/risk_engine/signal_tracker.py) được mở rộng thành 2 phân hệ rõ rệt:

1. **Feature Vector tại $T_0$ (Bất biến, ngăn chặn rò rỉ dữ liệu - Data Leakage):**
   - `signal_type`: Chân sóng, Đột biến GTGD, RRG Leading...
   - `composite_rating`, `rs_1m`, `acc_diss_rating`: Các chỉ tiêu sức mạnh giá và tích lũy/phân phối.
   - `rrg_r`, `rrg_m`: Tọa độ luân chuyển dòng tiền ngành RRG.
   - `foreign_net_value_billion`: Mua/bán ròng của khối ngoại.
   - `ranking_score`, `catalyst`, `adtv20_billion`, `adv20_shares`, `liquidity_score`, `t25_exposure_level`.

2. **Ground Truth Labels ($y$ - Cập nhật liên tục theo thời gian):**
   - `max_price_reached` & `mfe_pct` (Max Favorable Excursion): Đo lường biên độ lợi nhuận cực đại đạt được.
   - `min_price_reached` & `mae_pct` (Max Adverse Excursion): Đo lường mức sụt giảm tối đa phải chịu đựng.
   - `pnl_t25_pct`: Tỷ suất sinh lời thực tế tại mốc $T+2.5$ khi cổ phiếu khả dụng để bán.
   - `outcome_label`: `WIN_TP1`, `WIN_TP2`, `STOP_LOSS`, `TIME_OUT`, `ACTIVE`.
   - `target_win_binary`: Gán nhãn $1$ nếu cổ phiếu đạt lãi $\ge +5.0\%$ trước khi chạm cắt lỗ ban đầu, ngược lại $0$ (chuẩn cho bài toán phân loại Binary Classification).

### 2.3. Xuất Bản Tự Động `data/ml_signals_dataset.csv` & Kết Nối Looker Studio
- Mỗi chu kỳ quét, hệ thống tự động xuất bản tập dữ liệu phẳng [data/ml_signals_dataset.csv](file:///c:/Users/Daniel/Documents/My-Projects/Neiro-Stock-VN/data/ml_signals_dataset.csv).
- Tệp này được tự động `git add` và commit ngầm trên GitHub Actions, cho phép nhà nghiên cứu tải trực tiếp vào Google Colab qua 1 dòng lệnh `pd.read_csv()` để train mô hình Machine Learning.
- Bảng tính trên Google Sheets được kết nối trực tiếp với **Google Looker Studio** để hiển thị Dashboard phân tích động hoàn toàn miễn phí.

---

## 3. Hệ Quả & Đánh Giá (Consequences)

- **Không Tiêu Tốn Tài Nguyên Máy Local:** Toàn bộ quá trình quét, ghi nhận và đồng bộ diễn ra trên Cloud (GitHub Actions $\rightarrow$ Google Sheets $\rightarrow$ Looker Studio).
- **Zero-Waste Tuyệt Đối:** Mã nguồn chỉ bổ sung ~1.5 KB, không kéo thêm bất kỳ dependency nào vào môi trường.
- **Nền Tảng Vững Chắc Cho AI/ML:** Bộ dữ liệu thu thập theo thời gian thực giải quyết triệt để vấn đề thiếu dữ liệu huấn luyện hoặc thiên kiến nhìn trộm tương lai (Lookahead Bias).
