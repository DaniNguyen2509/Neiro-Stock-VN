# ADR-031: Cố Định Khung Cột Freeze Panes, Bảng Đơn Sắc Monochromatic & Tách Bạch 18 Cột Chỉ Số Riêng Biệt (Tab 2)

- **Trạng thái:** `ACCEPTED & IMPLEMENTED`
- **Ngày quyết định:** 2026-11-12
- **Tác giả:** AI Quant Assistant & Dani Nguyen
- **Phạm vi:** `src/hud/terminal.py`, `tests/test_positions_tracker_tab.py`, `exports/index.html`, `exports/404.html`

---

## 1. Bối Cảnh (Context)

Tại Tab 2 (Sổ Cái Vị Thế & Khuyến Nghị Toàn Vòng), người dùng đưa ra 3 yêu cầu cốt lõi nhằm nâng tầm trải nghiệm theo chuẩn Institutional Screener (TradingView / Bloomberg):
1. **"Cho bảng 1 màu":** Toàn bộ bảng vị thế phải có một nền màu tối duy nhất (`#0b111e`), triệt tiêu các dải màu vằn vện (zebra striping) hoặc các mảng card tương phản lộn xộn, tạo cảm giác sang trọng, thanh thoát và liền mạch.
2. **"Tách các chỉ số ra thành các cột riêng biệt":** Trước đây, các chỉ số tại T0 và dòng tiền bị gộp chung vào 2 cột tổng hợp (`Chỉ Số Đánh Giá Tại T0` và `Dòng Tiền & Nền POC T0`), khiến người dùng phải căng mắt đọc nhiều chỉ số nhồi nhét trong một ô. Người dùng yêu cầu tách mỗi chỉ số định lượng thành một cột độc lập.
3. **"Cố định khung cột để kéo ngang kéo xuống không bị che" (Freeze Panes):** Khi cuộn dọc danh sách dài các vị thế, hàng tiêu đề cột phải được giữ cố định trên cùng (`position: sticky; top: 0`). Khi cuộn ngang để soi các chỉ số kỹ thuật/dòng tiền ở phía sau, cột `STT` và cột `MÃ CP` phải được giữ cố định ở mép trái (`position: sticky; left: ...`), không bị che khuất mã cổ phiếu đang xem.

---

## 2. Quyết Định Thiết Kế (Decision & Implementation)

### 2.1. Cố Định Khung Cột (Dual-Axis Freeze Panes Grid)
Triển khai kỹ thuật CSS Sticky 2 chiều với kiến trúc container và bảng độc lập:
- **Container cuộn có giới hạn:** `.table-container-sticky` có `max-height: 72vh; overflow-x: auto; overflow-y: auto; position: relative; background: #0b111e;`.
- **Cố định hàng tiêu đề (Vertical Sticky Header):**
  - Tất cả thẻ `th` đều có `position: sticky; top: 0; z-index: 20; background: #0b111e; border-bottom: 2px solid #334155;`.
- **Cố định 2 cột đầu tiên (Horizontal Sticky Columns):**
  - Cột 1 (`STT`): `th.col-sticky-stt` và `td.col-sticky-stt` có `position: sticky; left: 0; min-width: 44px; width: 44px; text-align: center;`.
  - Cột 2 (`Mã CP`): `th.col-sticky-sym` và `td.col-sticky-sym` có `position: sticky; left: 44px; min-width: 96px; border-right: 2px solid #334155; box-shadow: 4px 0 8px -2px rgba(0,0,0,0.6);`.
  - Đổ bóng nhẹ `box-shadow` tạo cảm giác phân tầng nổi bật khi dữ liệu các cột bên phải cuộn trượt bên dưới.
- **Ô góc giao thoa (Top-Left Corners):**
  - `th.col-sticky-stt` và `th.col-sticky-sym` có `z-index: 35` (cao hơn cả `th` thông thường `z-index: 20` và `td` cố định `z-index: 15`), đảm bảo khi cuộn chéo cả 2 trục thì tiêu đề góc không bị đè.
- **Đồng bộ hiệu ứng rê chuột (Hover Synchronization):**
  - Khi rê chuột vào dòng `.unified-pos-row:hover td`, cả các ô sticky `td.col-sticky-stt` và `td.col-sticky-sym` đều chuyển sang cùng một nền sáng nhẹ `#131c2e !important;`, tránh hiện tượng lệch màu giữa các ô cố định và ô cuộn.

### 2.2. Bảng Đơn Sắc Đồng Nhất (Monochromatic Unified Theme)
- Loại bỏ toàn bộ CSS `nth-child(even)` zebra striping.
- Áp dụng một tông nền tối duy nhất `#0b111e` cho toàn bộ container, table, `thead th`, `tbody td`, và thanh cuộn tùy biến Webkit scrollbar.
- Đường kẻ viền mỏng tinh tế `1px solid #182232` và `border-collapse: separate; border-spacing: 0;` giúp viền hiển thị hoàn hảo khi cuộn sticky.

### 2.3. Tách Bạch 18 Cột Chỉ Số Độc Lập
Tái cấu trúc bảng Tab 2 từ 8 cột gộp thành **18 cột chỉ số chuyên biệt**:
1. `STT`: Số thứ tự (Cố định trái)
2. `Mã CP`: Mã cổ phiếu & Huy hiệu chân sóng / thể chế / đột biến GT (Cố định trái)
3. `Trạng Thái & Chu Kỳ (Ngày Vào T0 • Ngày Đóng)`: Huy hiệu kết quả & số phiên T+x
4. `Giá Vốn`: Giá mua chuẩn tại T0
5. `Giá Thoát/Live`: Giá đóng hoặc giá realtime cập nhật tự động từ VPS API
6. `Lãi/Lỗ PnL %`: PnL% hiện tại kèm chỉ số MFE (đỉnh lãi cao nhất) / MAE (đáy sâu nhất)
7. `Cắt Lỗ (SL)`: Ngưỡng dừng lỗ hiện tại (tự động hiển thị Hòa vốn khi đã đạt TP1)
8. `Chốt Lời (TP)`: Mục tiêu TP1 và TP2
9. `Điểm AI`: Điểm tổng hợp AI Ranking Score tại thời điểm T0
10. `Điểm IBD`: Điểm sức mạnh cơ bản & dòng tiền IBD Composite Rating
11. `RS 1M`: Điểm sức mạnh giá tương quan 1 tháng
12. `Tích Lũy`: Xếp hạng gom hàng Acc/Dist Rating (A, B, C, D)
13. `Chu Kỳ RRG`: Tọa độ RS-Ratio / RS-Momentum & Pha ngành (Dẫn dắt, Cải thiện, Suy yếu, Tụt hậu)
14. `Khối Ngoại`: Giá trị mua/bán ròng của NĐT nước ngoài tại T0 (tỷ VNĐ)
15. `Tự Doanh`: Giá trị mua/bán ròng của Khối tự doanh CTCK tại T0 (tỷ VNĐ)
16. `Nền POC (ATR)`: Mức giá Volume Profile POC tại T0 và khoảng cách theo ATR
17. `Thanh Khoản`: Giá trị giao dịch trung bình 20 phiên ADTV20 (tỷ VNĐ)
18. `AI Chẩn Đoán & Quyết Nghị`: Phân tích điểm mạnh/yếu T0 và khuyến nghị hành động thời gian thực

---

## 3. Kết Quả Kiểm Thử & Kiểm Định (Verification)

1. **Unit Test Bổ Sung:** Tạo test `test_tab2_freeze_panes_monochromatic_and_decomposed_columns` trong `tests/test_positions_tracker_tab.py`, xác thực 100% các cột, lớp CSS sticky, và màu đơn sắc.
2. **Quality Gate:** Toàn bộ test suite `pytest tests/` đạt **167/167 passed (100%)**.
3. **Zero-Waste Mandate:** Đã dọn dẹp sạch sẽ thư mục tạm `tests_temp`, tổng dung lượng repo đạt **5.00 MB** (< 15MB).
4. **Tương thích Live WebSocket/Polling:** Cơ chế cập nhật giá trực tiếp VPS `fetchLivePrices` tiếp tục hoạt động mượt mà qua các selector `.live-price[data-sym]` và `.live-pnl[data-sym]`.
