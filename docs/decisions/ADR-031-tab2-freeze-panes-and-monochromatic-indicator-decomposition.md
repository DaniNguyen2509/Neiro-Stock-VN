# ADR-031: Cố Định Khung Cột Freeze Panes, Bảng Đơn Sắc Monochromatic & Tách Bạch 19 Cột Chỉ Số Riêng Biệt (Tab 2)

- **Trạng thái:** `ACCEPTED & IMPLEMENTED`
- **Ngày quyết định:** 2026-11-12
- **Tác giả:** AI Quant Assistant & Dani Nguyen
- **Phạm vi:** `src/hud/terminal.py`, `tests/test_positions_tracker_tab.py`, `exports/index.html`, `exports/404.html`

---

## 1. Bối Cảnh (Context)

Tại Tab 2 (Sổ Cái Vị Thế & Khuyến Nghị Toàn Vòng), người dùng đưa ra các yêu cầu cốt lõi nhằm nâng tầm trải nghiệm theo chuẩn Institutional Screener (TradingView / Bloomberg):
1. **"Cho bảng 1 màu":** Toàn bộ bảng vị thế phải có một nền màu tối duy nhất (`#0b111e`), triệt tiêu các dải màu vằn vện (zebra striping) hoặc các mảng card tương phản lộn xộn, tạo cảm giác sang trọng, thanh thoát và liền mạch.
2. **"Tách các chỉ số ra thành các cột riêng biệt":** Các chỉ số tại T0 và dòng tiền được tách độc lập từng cột (Điểm AI, IBD, RS 1M, Tích Lũy, Chu Kỳ RRG, Khối Ngoại, Tự Doanh, Nền POC, Thanh Khoản, AI Chẩn Đoán).
3. **"Trạng Thái & Chu Kỳ (Ngày Vào T0 • Ngày Đóng) tách luôn đi em, đừng có gộp":** Người dùng yêu cầu tách dứt điểm thông tin Trạng thái vị thế (huy hiệu Đang nắm giữ / Đạt TP / Cắt lỗ / Tất toán T+7) và Chu kỳ nắm giữ (T+x cùng mốc ngày vào - ngày đóng) thành 2 cột riêng rẽ, không dồn 2 hàng vào một ô.
4. **"Cố định khung cột cho đến cột Chốt Lời (TP)" (Expanded Freeze Panes):** Khi cuộn dọc danh sách dài các vị thế, hàng tiêu đề cột phải được giữ cố định trên cùng (`position: sticky; top: 0`). Khi cuộn ngang để soi các chỉ số kỹ thuật/dòng tiền sâu ở phía sau, toàn bộ phân vùng quản trị lệnh cốt lõi từ cột 1 (`STT`) cho đến hết cột 9 (`Chốt Lời TP`) phải được neo cứng cố định ở mép trái (`position: sticky; left: ...`), tạo thành bảng điều khiển vị thế cố định vững chắc không bị che khuất.

---

## 2. Quyết Định Thiết Kế (Decision & Implementation)

### 2.1. Cố Định Khung Cột Toàn Diện Đến Cột Chốt Lời TP (Dual-Axis Freeze Panes Grid - 9 Sticky Columns)
Triển khai kỹ thuật CSS Sticky 2 chiều với kiến trúc container và bảng độc lập:
- **Container cuộn có giới hạn:** `.table-container-sticky` có `max-height: 72vh; overflow-x: auto; overflow-y: auto; position: relative; background: #0b111e;`.
- **Cố định hàng tiêu đề (Vertical Sticky Header):**
  - Tất cả thẻ `th` đều có `position: sticky; top: 0; z-index: 20; background: #0b111e; border-bottom: 2px solid #334155;`.
- **Cố định 9 cột đầu tiên từ STT đến Chốt Lời TP (Horizontal Sticky Columns 1 - 9):**
  - Cột 1 (`STT`): `left: 0; width: 44px; text-align: center; border-right: 1px solid #1e293b;`
  - Cột 2 (`Mã CP`): `left: 44px; width: 96px; border-right: 1px solid #1e293b;`
  - Cột 3 (`Trạng Thái`): `left: 140px; width: 110px; text-align: center; border-right: 1px solid #1e293b;`
  - Cột 4 (`Chu Kỳ (Ngày Vào T0 • Ngày Đóng)`): `left: 250px; width: 135px; text-align: center; border-right: 1px solid #1e293b;`
  - Cột 5 (`Giá Vốn`): `left: 385px; width: 75px; text-align: right; border-right: 1px solid #1e293b;`
  - Cột 6 (`Giá Thoát/Live`): `left: 460px; width: 85px; text-align: right; border-right: 1px solid #1e293b;`
  - Cột 7 (`Lãi/Lỗ PnL %`): `left: 545px; width: 95px; text-align: right; border-right: 1px solid #1e293b;`
  - Cột 8 (`Cắt Lỗ SL`): `left: 640px; width: 85px; text-align: right; border-right: 1px solid #1e293b;`
  - Cột 9 (`Chốt Lời TP`): `left: 725px; width: 95px; text-align: right; border-right: 2px solid #334155 !important; box-shadow: 4px 0 8px -2px rgba(0,0,0,0.6);`
  - Đổ bóng đậm `box-shadow` tại mép phải của cột Chốt Lời TP tạo ranh giới phân tách trực quan rõ rệt khi 10 cột dữ liệu định lượng phía sau (`Điểm AI`, `IBD`, `RS 1M`, `Tích Lũy`, `RRG`, `Ngoại`, `Tự Doanh`, `POC`, `Thanh Khoản`, `AI Chẩn Đoán`) cuộn trượt bên dưới.
- **Ô góc giao thoa (Top-Left Corners):**
  - Tất cả các ô tiêu đề cột 1-9 trong `thead th` đều có `z-index: 35` (cao hơn cả `th` thông thường `z-index: 20` và `td` cố định `z-index: 15`), đảm bảo khi cuộn chéo cả 2 trục thì tiêu đề góc không bao giờ bị đè.
- **Đồng bộ hiệu ứng rê chuột (Hover Synchronization):**
  - Khi rê chuột vào dòng `.unified-pos-row:hover td.col-sticky-pane`, toàn bộ 9 cột cố định đều chuyển sang cùng một nền sáng nhẹ `#131c2e !important;`, đồng bộ tuyệt đối với các cột đang cuộn.

### 2.2. Bảng Đơn Sắc Đồng Nhất (Monochromatic Unified Theme)
- Loại bỏ toàn bộ CSS `nth-child(even)` zebra striping.
- Áp dụng một tông nền tối duy nhất `#0b111e` cho toàn bộ container, table, `thead th`, `tbody td`, và thanh cuộn tùy biến Webkit scrollbar.
- Đường kẻ viền mỏng tinh tế `1px solid #182232` và `border-collapse: separate; border-spacing: 0;` giúp viền hiển thị hoàn hảo khi cuộn sticky.

### 2.3. Tách Bạch 19 Cột Chỉ Số Độc Lập
Tái cấu trúc bảng Tab 2 thành **19 cột chỉ số chuyên biệt**:
1. `STT`: Số thứ tự (Cố định trái - Col 1)
2. `Mã CP`: Mã cổ phiếu & Huy hiệu chân sóng / thể chế / đột biến GT (Cố định trái - Col 2)
3. `Trạng Thái`: Huy hiệu vị thế (🟢 ĐANG NẮM GIỮ, 🎯 ĐẠT TP1, 🛑 CẮT LỖ, ⏱️ HẾT SÓNG T+7) (Cố định trái - Col 3)
4. `Chu Kỳ (Ngày Vào T0 • Ngày Đóng)`: Số phiên nắm giữ T+x và ngày vào / ngày tất toán (Cố định trái - Col 4)
5. `Giá Vốn`: Giá mua chuẩn tại T0 (Cố định trái - Col 5)
6. `Giá Thoát/Live`: Giá đóng hoặc giá realtime cập nhật tự động từ VPS API (Cố định trái - Col 6)
7. `Lãi/Lỗ PnL %`: PnL% hiện tại kèm chỉ số MFE (đỉnh lãi cao nhất) / MAE (đáy sâu nhất) (Cố định trái - Col 7)
8. `Cắt Lỗ (SL)`: Ngưỡng dừng lỗ hiện tại (tự động hiển thị Hòa vốn khi đã đạt TP1) (Cố định trái - Col 8)
9. `Chốt Lời (TP)`: Mục tiêu TP1 và TP2 (Cố định trái - Col 9, biên giới hạn Freeze Pane)
10. `Điểm AI`: Điểm tổng hợp AI Ranking Score tại thời điểm T0 (Cuộn ngang)
11. `Điểm IBD`: Điểm sức mạnh cơ bản & dòng tiền IBD Composite Rating (Cuộn ngang)
12. `RS 1M`: Điểm sức mạnh giá tương quan 1 tháng (Cuộn ngang)
13. `Tích Lũy`: Xếp hạng gom hàng Acc/Dist Rating (A, B, C, D) (Cuộn ngang)
14. `Chu Kỳ RRG`: Tọa độ RS-Ratio / RS-Momentum & Pha ngành (Dẫn dắt, Cải thiện, Suy yếu, Tụt hậu) (Cuộn ngang)
15. `Khối Ngoại`: Giá trị mua/bán ròng của NĐT nước ngoài tại T0 (tỷ VNĐ) (Cuộn ngang)
16. `Tự Doanh`: Giá trị mua/bán ròng của Khối tự doanh CTCK tại T0 (tỷ VNĐ) (Cuộn ngang)
17. `Nền POC (ATR)`: Mức giá Volume Profile POC tại T0 và khoảng cách theo ATR (Cuộn ngang)
18. `Thanh Khoản`: Giá trị giao dịch trung bình 20 phiên ADTV20 (tỷ VNĐ) (Cuộn ngang)
19. `AI Chẩn Đoán & Quyết Nghị`: Phân tích điểm mạnh/yếu T0 và khuyến nghị hành động thời gian thực (Cuộn ngang)

---

## 3. Kết Quả Kiểm Thử & Kiểm Định (Verification)

1. **Unit Test Bổ Sung:** Tạo test `test_tab2_freeze_panes_monochromatic_and_decomposed_columns` trong `tests/test_positions_tracker_tab.py`, xác thực 100% 19 cột, các lớp CSS sticky `col-sticky-1` đến `col-sticky-9`, và màu đơn sắc.
2. **Quality Gate:** Toàn bộ test suite `pytest tests/` đạt **167/167 passed (100%)**.
3. **Zero-Waste Mandate:** Đã dọn dẹp sạch sẽ thư mục tạm `tests_temp`, tổng dung lượng repo đạt **5.32 MB** (< 15MB).
4. **Tương thích Live WebSocket/Polling:** Cơ chế cập nhật giá trực tiếp VPS `fetchLivePrices` tiếp tục hoạt động mượt mà qua các selector `.live-price[data-sym]` và `.live-pnl[data-sym]`.

