# ADR-026: In-Memory Multi-Year Real Historical Backtesting Engine (2024 - 2026) with Zero Look-Ahead Bias & Zero-Waste Enforcement

## Trạng thái (Status)
**Accepted** — 2026-11-08

## Bối cảnh (Context)
Nhà đầu tư định chế và trader cần kiểm định (backtest) hệ thống trên chuỗi dữ liệu thực tế của TTCK Việt Nam trong 3 năm liên tiếp (**2024, 2025, 2026**) mà tuyệt đối **không được nhìn trước dữ liệu tương lai** (Zero Look-Ahead Bias). Đồng thời, toàn bộ quá trình backtest phải tuân thủ nghiêm ngặt **Quy định Bảo tồn Dung lượng (Zero-Waste Mandate)**: không ghi file CSV/JSON lịch sử nặng hàng chục MB vào ổ cứng người dùng, giữ dung lượng repository luôn `< 15MB`.

## Quyết định Kỹ thuật (Architectural Decisions)

1. **Nạp Dữ liệu Trực tiếp trên RAM (In-Memory Fetching — `src/backtesting/historical_data.py`):**
   - Kéo trực tiếp chuỗi nến ngày (`1D`) từ API công khai DNSE Entrade (`services.entrade.com.vn/chart-api/v2/ohlcs`) cho `VNINDEX` và rổ 30–40 cổ phiếu thanh khoản lớn đại diện 12 nhóm ngành chủ lực từ `2023-10-01` đến `2026-11-08` (772 phiên).
   - Q4/2023 (65 phiên) đóng vai trò **Warm-Up Buffer** để tính toán sẵn MA20, ATR14, ADTV20, Volume Profile trước phiên mở cửa đầu năm 2024 (`2024-01-02`).
   - Xử lý 100% trong bộ nhớ RAM, 0 byte dữ liệu lưu ra ổ cứng.

2. **5 Chốt Chặn Toán Học Chống Look-Ahead (Zero Look-Ahead Invariants):**
   - **Khớp lệnh trễ Next-Bar Open:** Tín hiệu đóng phiên ngày $t$ (`bar.close`) chỉ được khớp tại giá mở cửa phiên $t+1$ (`bar.open`). Nếu phiên sau nhảy Gap $> 2.5 \times \text{ATR}_{14}$ hoặc kịch trần thì tự động hủy lệnh.
   - **Cắt cụt nhân quả (Strict Causal Truncation Proof):** Mọi chỉ báo tại ngày $t$ chỉ dùng dữ liệu $\le t$. Kiểm chứng bằng bài test cắt cụt tại $t_{\text{mid}}$ và đối chiếu trùng khớp 100% NAV và Trade Records.
   - **Point-in-Time BCTC:** Báo cáo tài chính Quý $Q$ chỉ được nạp vào tính điểm F-Score/CAMEL sau ngày nộp công khai thực tế (`filing_date`: Q1 ngày 28/04, Q2 ngày 30/07, Q3 ngày 30/10, Q4 ngày 30/01 năm sau).
   - **Ràng buộc T+2.5 & Khóa Sàn:** Cổ phiếu mua tại $T_0$ chỉ được bán từ chiều $T+2$; nếu chạm giá sàn kịch biên (`bar.close <= floor_price`), lệnh bán bị khóa kẹt, buộc phải chờ phiên tiếp theo có cầu giải cứu.
   - **Thoát Lệnh Thực Chiến ADR-024:** Cắt lỗ theo đáy thật trong ngày (`True Low SL: bar.low <= current_stop_loss`), nâng Stop Loss hòa vốn khi chạm TP1 (`1.5R`), và tất toán xoay vòng vốn `Time-Stop T+7` nếu nắm giữ $\ge 7$ phiên mà lãi $< +3.0\%$.

3. **Phân rã Kết quả Độc lập Từng Năm & CLI Trực tiếp:**
   - Hỗ trợ phương thức `coord.run_multi_year_2024_2026()` bóc tách hiệu suất từng năm lịch `2024`, `2025`, `2026` và tổng kỳ 3 năm.
   - Tích hợp CLI trực tiếp `python -m src.backtesting.walk_forward --real-data`.

## Kết quả Thực Nghiệm (Consequences & Empirical Findings)

Khi chạy kiểm định không nhìn trước dữ liệu trên chuỗi giá thật 2024–2026:
- Tỷ lệ lệnh thoát qua `TIME_STOP_T7` đạt $\sim 45\% - 50\%$, phản ánh đặc tính thị trường chứng khoán Việt Nam thường xuyên đi ngang tích lũy sau các cây nến bùng nổ giả.
- Cơ chế `True Low SL` và `Khóa Sàn Trắng Bên Mua` phản ánh chân thực các rủi ro kẹt hàng T+2.5 thực tế của nhà đầu tư nhỏ lẻ.
- Repository không phát sinh bất kỳ file rác nào, hoàn toàn sạch sẽ và tuân thủ Zero-Waste.
