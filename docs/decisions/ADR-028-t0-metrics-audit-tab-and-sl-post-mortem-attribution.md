# ADR-028: Tab Vị Thế Đã Khuyến Nghị (TP/SL), Hiển Thị Chỉ Số Đánh Giá Tại T0 & Bộ Máy Tự Học Hậu Kiểm (T0 SL vs TP Attribution)

- **Trạng thái:** Accepted & Implemented
- **Ngày:** 2026-11-11
- **Tác giả:** Neiro-Stock-VN Architecture Team

## 1. Bối cảnh (Context)

Trong quá trình vận hành thực chiến hệ thống khuyến nghị Quantamental, đội ngũ đầu tư đặt ra hai bài toán trọng tâm:
1. **Minh bạch toàn diện các chỉ số tại thời điểm khuyến nghị ($T_0$ Snapshot):** Khi không nhìn lại biểu đồ nến của từng mã, nhà đầu tư cần một giao diện trực quan hiển thị **toàn bộ các vị thế đã từng được khuyến nghị** (bao gồm cả lệnh đã chốt lời `TP1`/`TP2`, lệnh bị cắt lỗ `SL`, lệnh tất toán `Time-Out T+7`, và lệnh đang nắm giữ `Active`) đi kèm **đầy đủ bộ chỉ số đánh giá tại đúng thời điểm khuyến nghị $T_0$** (`Điểm AI`, `IBD Composite`, `RS 1M`, `Tích lũy A-E`, `RRG Ratio/Mom`, `Khối ngoại / Tự doanh / Nhãn dòng tiền`, `Thanh khoản ADTV20`, `Khoảng cách POC theo ATR`, `Độ rộng TT & Basis VN30F1M`).
2. **Tự học và tái đánh giá trên các lệnh bị SL ngay cả khi số lượng mẫu còn nhỏ (Small-Sample Deterministic Attribution):** Trước khi đủ hàng trăm mẫu để chạy Reinforcement Learning hoàn chỉnh (sau 2-3 tháng), hệ thống cần cơ chế **Rule-Based Feature Attribution & Post-Mortem Diagnosis** đối chiếu trực tiếp trung bình chỉ số $T_0$ giữa nhóm lệnh thắng (`TP`) và nhóm lệnh thua (`SL`), từ đó chỉ ra chỉ số nào quan trọng nhất khiến lệnh bị SL và đề xuất ngưỡng lọc cải thiện cho các kèo tiếp theo.

## 2. Quyết định Kiến trúc (Decision)

### 2.1. Bộ Máy Chẩn Đoán & Tự Học Hậu Kiểm T0 (`src/risk_engine/signal_tracker.py`)
1. **Hàm `evaluate_t0_signal_quality_and_diagnosis(sig)`:**
   - Chuẩn hóa phân loại kết quả (`TP`, `SL`, `TIMEOUT`, `ACTIVE`) và bảo toàn bất biến miền Cắt Lỗ (PnL thực tế của lệnh `STOPPED_OUT` tính theo `min(current_price, stop_loss)` luôn $\le 0$).
   - Đánh giá từng chiều chỉ số tại $T_0$ (`ranking_score`, `composite_rating`, `rs_1m`, `acc_diss_rating`, `rrg_r / rrg_m`, `foreign_net_value_billion + prop_net_value_billion`, `adtv20_billion`, `atr_dist_from_poc_t0`, `market_breadth_pct_t0`, `vn30_basis_t0`) để tách bạch **Điểm mạnh tại T0** và **Điểm yếu / Nguyên nhân rủi ro tại T0**.
2. **Hàm `analyze_t0_sl_vs_tp_attribution(signals)`:**
   - Tập hợp toàn bộ vị thế từ `data/active_signals.jsonl` và `data/signal_history_ml.jsonl`.
   - Tính toán trung bình các chỉ số $T_0$ của nhóm `TP` so với nhóm `SL`, độ lệch $\Delta (\text{TP} - \text{SL})$ và chấm điểm mức độ ảnh hưởng (`importance_score` thang 100) để xếp hạng các yếu tố quyết định thắng/thua và sinh quy tắc nâng cấp bộ lọc.

### 2.2. Nâng Cấp Giao Diện Terminal HUD (`src/hud/terminal.py`)
1. **Bổ sung cột `Chỉ Số Đánh Giá Tại T0` trên Tab 2 (`#hud-tab-positions`):**
   - Cả bảng **Vị Thế Đang Nắm Giữ** (`#active-positions-table`) và bảng **Lịch Sử Vị Thế Đã Đóng Toàn Vòng (TP2 / Cắt Lỗ / Hết Sóng T+7)** (`#closed-positions-table`, mặc định mở sẵn `<details open>`) đều hiển thị thẻ tóm tắt các chỉ số tại $T_0$.
2. **Xây dựng Tab 3 chuyên biệt: `🧬 TAB 3: VỊ THẾ ĐÃ KHUYẾN NGHỊ (TP / SL) & CHỈ SỐ ĐÁNH GIÁ TẠI T0` (`#hud-tab-t0-audit`):**
   - **4 Thẻ KPI Tổng hợp:** Tổng số vị thế đã khuyến nghị, số lệnh Chốt lời (`TP1`/`TP2`), số lệnh Cắt lỗ (`SL`) + Hết sóng (`T+7`), và Tỷ lệ thắng thực chiến (`Closed Win Rate %`).
   - **Bảng AI Tự Học & Tái Đánh Giá Chỉ Số T0 (`#t0-attribution-table`):** So sánh trực tiếp từng chỉ số tại $T_0$ giữa nhóm lệnh `TP` và nhóm lệnh `SL`, xếp hạng độ quan trọng và khuyến nghị quy tắc siết bộ lọc.
   - **Bảng Toàn Bộ Vị Thế Đã Khuyến Nghị & Ma Trận 14 Cột Chỉ Số Tại T0 (`#t0-recommended-positions-table`):** Hỗ trợ bộ lọc nhanh Client-Side JS (`filterT0AuditRows('ALL' | 'TP' | 'SL' | 'ACTIVE' | 'TIMEOUT')`) để nhà đầu tư tra cứu tức thì mọi mã đã khuyến nghị cùng chẩn đoán nguyên nhân thắng/thua tại $T_0$.

## 3. Hệ quả & Kiểm chứng (Consequences & Verification)
- **Minh bạch 100% lịch sử khuyến nghị:** Nhà đầu tư có thể đối chiếu bất kỳ lệnh `TP` hay `SL` nào với bộ chỉ số gốc tại thời điểm mua $T_0$ mà không cần mở lại chart lịch sử.
- **Tự học ngay từ mẫu nhỏ:** Cung cấp thông tin định lượng rõ ràng về sự khác biệt giữa lệnh thắng và lệnh thua ngay trong giai đoạn tích lũy mẫu cho mô hình Machine Learning.
- **Kiểm thử tự động:** Bổ sung `test_t0_evaluation_metrics_and_attribution_tab` trong `tests/test_positions_tracker_tab.py`, đảm bảo 100% test suite pass và dung lượng dự án giữ vững chuẩn Zero-Waste `< 15MB`.

