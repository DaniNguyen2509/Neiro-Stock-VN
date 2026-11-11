# ADR-027: Tự Động Lưu Trữ Vòng Đời Tín Hiệu Đã Đóng & Chuẩn Hóa Logic Hiển Thị Bảng Lịch Sử Vị Thế

## 1. Trạng Thái
**ĐÃ CHẤP NHẬN (ACCEPTED)** - Ngày 11/11/2026

## 2. Bối Cảnh & Vấn Đề (Context & Problem Statement)
Người dùng và nhà đầu tư khi mở rộng ngăn *"Lịch Sử Vị Thế Đã Hoàn Thành Toàn Vòng TP2 / Hết Sóng Cơ Cấu / Đã Đóng Bảo Toàn Vốn"* trên Dashboard phát hiện các điểm bất thường gây hiểu lầm nghiêm trọng:
1. **Thiếu dòng thời gian khuyến nghị (Timeline Blindspot):** Bảng lịch sử chỉ hiển thị `Mã CP | Kết Quả | Giá Vào T0 | Giá Đóng | Lợi Nhuận PnL % | Số Ngày T+ | Lý Do Đóng`. Hoàn toàn không có cột *"Ngày Vào T0"* hay *"Ngày Đóng"*, khiến nhà đầu tư không biết các mã này được khuyến nghị từ khi nào.
2. **Ồn ứ dữ liệu test cũ (Data Pollution):** Có tới 71 bản ghi thử nghiệm từ giai đoạn đầu (26/10 - 30/10/2026, chuẩn cũ `v1_legacy` khi chưa siết chặt bộ lọc IBD Composite $\ge 75$) bị đối soát ngày 04/11 chuyển thành `STOPPED_OUT` và kẹt vĩnh viễn trong `data/active_signals.jsonl`.
3. **Lỗi logic thoát lệnh (Domain Logic Inconsistency):** Nhiều mã (như PDR, SZC, CTG) bị dán nhãn `🛑 CẮT LỖ` nhưng cột PnL lại hiển thị số dương màu xanh (ví dụ PDR `+1.74%`), do bảng hiển thị lấy `current_price` (thị giá đã hồi phục) thay vì giá chạm ngưỡng Stop Loss thực tế.
4. **Khiếm khuyết kiến trúc thu gom rác (Pruning Gap in SignalTracker):** Trong `SignalTracker.update_signals`, việc chuyển vị thế đã đóng sang `signal_history_ml.jsonl` chỉ được kích hoạt khi mã đó xuất hiện trở lại trong Top mua mới (`can_open_new_wave = True`). Nếu mã không bao giờ lọt lại vào Top mua, nó bị kẹt vĩnh viễn trong `active_signals.jsonl`.

## 3. Quyết Định Thiết Kế (Design Decisions)

### 3.1. Cơ chế Tự động Lưu trữ Vòng đời (Automatic Lifecycle Archival)
- Trong `SignalTracker.update_signals`: Sau mỗi chu kỳ quét, hệ thống tự động kiểm tra toàn bộ vị thế có `is_closed == True`. Nếu đã qua hết 3 phiên giao dịch thực tế (`cooldown_sessions = 3`), vị thế sẽ tự động được lưu trữ bất biến vào `data/signal_history_ml.jsonl` và xóa khỏi `data/active_signals.jsonl`.
- Sổ cái `data/active_signals.jsonl` luôn được giữ tinh gọn, chỉ chứa các vị thế đang thực sự hoạt động (`ACTIVE`, `TP1_REACHED`) hoặc các vị thế vừa đóng trong vòng 3 phiên gần nhất để nhà đầu tư kịp theo dõi.

### 3.2. Nâng cấp Bảng Lịch Sử Vị Thế trên Dashboard (`src/hud/terminal.py`)
- Bổ sung 2 cột thời gian rõ ràng:
  - **Ngày Vào T0:** Ngày/tháng phát tín hiệu bùng nổ khuyến nghị ban đầu.
  - **Ngày Đóng:** Ngày/tháng vị thế chạm ngưỡng thoát lệnh (TP2, Stop Loss hoặc Time-Out).
- Khắc phục triệt để lỗi PnL dương ở vị thế Cắt Lỗ:
  - Với vị thế `STOPPED_OUT`: Giá Đóng bắt buộc phải là giá chạm ngưỡng Stop Loss thực tế `min(current_price, stop_loss)`, PnL được tính chuẩn theo mức giá thoát này, đảm bảo luôn mang dấu âm hoặc hòa vốn, không bao giờ hiển thị PnL dương màu xanh gây hiểu lầm.
- Lọc hiển thị Archive thông minh: Khi sổ cái ngầm không có mã đóng nào, hệ thống chỉ lấy tối đa các vị thế chuẩn `schema_version == "v2"` từ kho lưu trữ, tuyệt đối loại trừ các bản ghi test legacy cũ.

## 4. Hệ Quả & Lợi Ích (Consequences & Benefits)
- **Minh bạch 100% dòng thời gian:** Nhà đầu tư đối chiếu được ngày vào lệnh và ngày đóng lệnh cụ thể của từng khuyến nghị.
- **Tính toàn vẹn của dữ liệu (Data Integrity):** Chấm dứt hoàn toàn tình trạng nhãn Cắt Lỗ nhưng số liệu lãi dương.
- **Bảo tồn dung lượng Zero-Waste (< 15MB):** Sổ cái ngầm `active_signals.jsonl` giảm từ 130KB xuống dưới 15KB, toàn bộ dữ liệu lịch sử được chuyển sang kho ML chuyên dụng.
- **Pass 100% Test Suite:** Đã bổ sung unit test kiểm tra bất biến miền `test_closed_positions_stopped_out_exit_price_and_negative_pnl_invariant` trong `tests/test_positions_tracker_tab.py`.

