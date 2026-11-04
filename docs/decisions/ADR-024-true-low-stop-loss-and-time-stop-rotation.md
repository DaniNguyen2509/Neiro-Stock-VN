# ADR-024: Kiểm Toán Chân Thực Vòng Đời Tín Hiệu (True Holding-Period Low Stop Loss & Time-Stop Capital Rotation)

## 1. Trạng thái
- **Trạng thái:** `ACCEPTED & IMPLEMENTED`
- **Ngày quyết định:** 2026-11-04
- **Người đề xuất:** Chief Quant Architect / Financial Advisor Persona
- **Phạm vi áp dụng:** `src/risk_engine/signal_tracker.py`, `src/collector/fialda_scanner.py`, `src/hud/terminal.py`, `data/active_signals.jsonl`, `docs/spec.md`, `docs/architecture.md`.

---

## 2. Bối cảnh & Điểm mù Nghiêm trọng (Context & Severe Blindspots)

1. **Điểm mù lấy giá tức thời (Snapshot Polling Blindspot — Case VCI):**
   - Vị thế `VCI` được kích hoạt ngày 2026-10-26 tại giá `19.15`, ngưỡng cắt lỗ bảo toàn vốn `18.58`.
   - Trong đợt rung lắc cuối tháng 10, thị giá thực tế của VCI trên sàn HOSE rơi xuống đáy nến `18.05` (`18.05 < 18.58`). Trong thực tế giao dịch, lệnh Stop Loss của nhà đầu tư đã bị kích hoạt và cắt lỗ bảo vệ tài khoản.
   - Tuy nhiên, do hệ thống trước đây chỉ kiểm tra thị giá tức thời (`cur_price`) tại các thời điểm quét 30 phút một lần (lúc thị giá đang hồi ở 18.85 - 19.00), bot đã **bỏ lọt nhịp rơi đáy nến 18.05**.
   - Đến ngày 04/11/2026, khi thị trường kéo VCI tăng trần lên `20.20`, hệ thống lại lấy giá `20.20 >= tp1 (20.00)` và công bố `🎯 ĐÃ ĐẠT TP1 (LÃI +5.48%)`!
   - Đây là lỗi nghiêm trọng về **Survivorship Bias (Thiên kiến sống sót / Nhận vơ lợi nhuận ảo)**: Một cổ phiếu đã chết lâm sàng (vi phạm SL) lại được "hồi sinh" và báo lãi, phá vỡ hoàn toàn niềm tin của nhà đầu tư thực chiến.
2. **Hiện tượng danh mục phình to vô hạn ("Bảng rối nùi" với 38 mã):**
   - Sổ cái Tab 2 tích tụ tới 38 mã cổ phiếu mở từ 9–10 phiên trước mà không có cơ chế đóng vị thế khi hết sóng.
   - Nhà đầu tư bị ngập chìm trong thông tin rác, không phân biệt được đâu là mã chiến lược cần theo dõi và đâu là mã đã hết động lượng.

---

## 3. Quyết định Kiến trúc (Architectural Decisions)

Hệ thống thiết lập 3 chuẩn mực kiểm toán tài chính bắt buộc:

### 3.1. Cơ chế Bắt Dính Cắt Lỗ Theo Đáy Chu Kỳ Nắm Giữ (True Holding-Period Low Stop Loss)
- Khi đánh giá vi phạm cắt lỗ, hệ thống không chỉ so sánh `cur_price <= stop_loss` mà bắt buộc kiểm tra:
  $$\text{effective\_low} = \min(\text{cur\_price}, \text{low\_price}, \text{min\_price\_reached})$$
- **Quy tắc phân định thời gian:**
  - Với vị thế mở mới hôm nay ($T_0$): Chỉ so sánh với giá thấp nhất trong ngày (`PriceInfo.lowPrice`). Không áp dụng đáy của các ngày trước khi mua.
  - Với vị thế đã nắm giữ ($T \ge 1$): Đối chiếu với toàn bộ mức giá thấp nhất kể từ ngày $T_0$ (`min_price_reached` hoặc `adjLow5DCandle` nếu nến nằm trọn trong thời gian nắm giữ).
- **Nguyên tắc khóa vĩnh viễn (Terminal State Latch):**
  - Ngay khi $\text{effective\_low} \le \text{stop\_loss}$, vị thế lập tức chuyển trạng thái `STOPPED_OUT`, ghi nhận `outcome_label = "STOP_LOSS"`, `is_closed = True`, và ghi thời điểm `closed_at`.
  - Tuyệt đối không cho phép bất kỳ vị thế nào đã chạm SL được mở lại hoặc đổi sang nhãn TP1/TP2 khi thị giá hồi phục sau đó.

### 3.2. Cơ chế Quản Trị Thời Gian & Xoay Vòng Vốn (Time-Stop & Capital Rotation)
- Một vị thế lướt sóng chân sóng chuẩn chỉ có hiệu lực tối đa $T+5$ đến $T+7$ phiên.
- Nếu một vị thế đã trải qua $\ge 7$ phiên giao dịch thực tế (`trading_days >= 7`) mà vẫn chưa chạm tới mục tiêu TP1 ($\text{pnl} < +3.0\%$):
  - Hệ thống chuyển trạng thái sang `status = "TIME_OUT"`, `outcome_label = "TIME_OUT"`, `is_closed = True`.
  - Quyết nghị hành động: `⏱️ TẤT TOÁN VỊ THẾ QUÁ HẠN T+7 — CƠ CẤU VỐN / THU HỒI SỨC MUA`.
  - Mã tự động rời khỏi Bảng Đang Nắm Giữ của Tab 2 và chuyển vào ngăn lưu trữ lịch sử, giải phóng bảng điều khiển.

### 3.3. Tinh Gọn Bảng Tab 2 Thành Danh Mục Trọng Tâm (Active Focus Portfolio $\le 7$ mã)
- Bảng Tab 2 chia tách rạch ròi 2 khu vực:
  1. **Danh Mục Trọng Tâm Đang Nắm Giữ (Active Focus Portfolio):** Chỉ chứa các mã thực sự đang chạy và còn hiệu lực ($T_0$ đến $T+5$), sắp xếp theo ngày mua mới nhất $T_0$ lên đầu.
  2. **Ngăn Lưu Trữ Lịch Sử Vòng Đời (Closed Positions Archive):** Phân loại rõ ràng:
     - 🏆 Đạt TP2 hoàn tất toàn vòng (+15% - +35%)
     - ⏱️ Tất toán cơ cấu vốn quá hạn T+7 (Time-Out)
     - 🛑 Cắt lỗ bảo toàn vốn (Stop Loss — bao gồm case VCI, CTS, BVS...)

---

## 4. Kế hoạch Xử lý Dữ liệu Sổ Cái (`data/active_signals.jsonl`)
- Căn cứ chỉ đạo của Owner: *"nếu dữ liệu cũ chưa đầy đủ hoặc sai thì em có thể xóa luôn để không bị nhầm"*.
- Hệ thống rà soát toàn bộ 38 mã cũ:
  - Các mã đã vi phạm SL ở đáy nến (như VCI) chuyển thành `STOPPED_OUT` và đóng vị thế.
  - Các mã quá hạn $T+7$ không đạt TP1 chuyển thành `TIME_OUT` và đóng vị thế.
  - Chỉ giữ lại các vị thế thực sự chuẩn xác và hợp lệ (như `VCK` mua hôm nay $T_0$, và các vị thế chưa vi phạm).

