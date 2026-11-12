# ADR-030: Thiết Kế Bảng Màu Dark Cockpit Chống Chói Mắt & Chuẩn Hóa Typography Giao Diện Terminal

- **Trạng thái:** `ACCEPTED & IMPLEMENTED`
- **Ngày quyết định:** 2026-11-12
- **Tác giả:** AI Quant Assistant & Dani Nguyen
- **Phạm vi:** `src/hud/terminal.py`, `src/risk_engine/signal_tracker.py`, `exports/index.html`, `exports/404.html`

---

## 1. Bối Cảnh (Context)

Sau khi hoàn thành hợp nhất Tab 2 & Tab 3 thành một bảng duy nhất (ADR-029), giao diện người dùng hiển thị đầy đủ 8 cột dữ liệu chi tiết. Tuy nhiên, người dùng phản hồi rằng giao diện bị **chói mắt, gây mỏi thị giác khi theo dõi liên tục ("sữa lại màu chữ mà giao diện đi em, chói mắt quá =))")**.

Qua kiểm tra hình ảnh thực tế, các nguyên nhân kỹ thuật gây chói mắt được xác định:
1. **Lỗi Neon Rainbow Clashing (Xung đột màu neon quá đà):** Trong cột *Chỉ Số Đánh Giá Tại T0* và *Dòng Tiền*, mỗi con số/từ viết tắt (`AI`, `IBD`, `RS`, `TL`, `RRG`, `POC`, `Ngoại`) bị gán một màu neon cường độ cao độc lập (`#00e676`, `#ef4444`, `#ffb300`, `#38bdf8`, `#7c3aed`), khiến mắt người dùng không có điểm nghỉ và tạo cảm giác như "cây thông noel nhấp nháy".
2. **Mã cổ phiếu bị gán màu vàng gắt (`#ffb300`):** Toàn bộ mã cổ phiếu hiển thị màu vàng cam rực trên nền đen tạo độ tương phản gay gắt không cần thiết.
3. **Nút Tab & Bộ lọc dùng màu nền vàng đặc (`#ffb300`) trên chữ đen:** Khiến thanh công cụ bị chói lóa so với tổng thể theme tối.
4. **Huy hiệu khối màu đặc (Solid Colored Pills):** Các huy hiệu trạng thái dùng nền màu đậm đặc (`#1b5e20`, `#0284c7`, `#b71c1c`) cạnh nhau tạo cảm giác nặng nề, bí bách.
5. **Số 0.0t ngoại khối bị tô xanh neon:** Giá trị khối ngoại ròng xấp xỉ 0 vẫn bị tô xanh chói mắt.
6. **Cảnh báo giả "Xung lực T0 yếu":** Các mã có giá trị mặc định `IBD 50 / RS 50` bị sinh chuỗi chẩn đoán cảnh báo vàng dày đặc trên toàn bộ các dòng.

---

## 2. Quyết Định Thiết Kế (Decision & Implementation)

Chuyển đổi toàn diện hệ thống bảng màu Terminal sang chuẩn **Institutional Pro Dark Theme (Bloomberg / TradingView Dark Pro)**:

### 2.1. Chuẩn Hóa Phân Cấp Typography & Mã Cổ Phiếu
- **Mã cổ phiếu (`s_sym`):** Chuyển từ màu vàng cam sang màu trắng sáng tinh tế `#f8fafc` (`font-weight: 800; font-size: 13.5px; letter-spacing: 0.3px;`).
- **Nhãn mô tả (`AI:`, `IBD:`, `RS:`, `TL:`, `RRG:`, `POC:`, `TK:`, `SL:`, `TP:`):** Dùng màu xám dịu `#64748b` (`font-weight: 500; font-size: 10-11px;`). Mắt người đọc chỉ tập trung vào giá trị số thay vì bị hút vào các nhãn viết tắt.
- **Giá trị chỉ số:** Tối ưu màu trung tính `#cbd5e1` hoặc `#e2e8f0`. Giá trị trung bình/chưa kích hoạt không bị tô đỏ gắt mà dùng `#94a3b8`.

### 2.2. Bảng Màu Dịu Mắt (Subdued & Translucent Accents)
- **Xanh Lãi / Tăng (Profit/Bullish):** Thay thế `#00e676` (laser green) bằng **Mint/Emerald Green `#34d399`**.
- **Đỏ Lỗ / Giảm (Loss/Bearish):** Thay thế `#ff0000` / `#ff5252` bằng **Coral/Rose Red `#f87171`**.
- **Hòa vốn / Tham chiếu:** Dùng màu Slate `#94a3b8` thay vì vàng cam `#ffb300`.
- **Huy hiệu mờ (Translucent Badges):** Áp dụng kỹ thuật nền mờ `rgba(R, G, B, 0.12 - 0.15)` kết hợp viền mỏng cùng tông `border: 1px solid rgba(R, G, B, 0.25 - 0.30)`, triệt tiêu hoàn toàn các mảng màu đặc gây ngợp mắt.

### 2.3. Tinh Chỉnh Thanh Điều Hướng & Bộ Lọc
- **Nút Tab & Filter:** Bỏ nền vàng cam đặc; chuyển sang chuẩn Dark Pill UI hiện đại:
  - Trạng thái Active: `background: #1e293b; color: #38bdf8; border: 1px solid #0284c7; box-shadow: 0 0 10px rgba(56,189,248,0.15);`.
  - Trạng thái Inactive: `background: #111722; color: #94a3b8; border: 1px solid #1e293b;`.

### 2.4. Khử Nhiễu Cảnh Báo Chẩn Đoán T0
- Điều chỉnh ngưỡng chẩn đoán tại `signal_tracker.py`: Loại trừ các mã có điểm mặc định `IBD 50 / RS 50` khỏi nhóm cảnh báo xung lực yếu; thay thế icon vàng gắt bằng dòng text phân tích nhã nhặn `#94a3b8`.

---

## 3. Kết Quả Kiểm Thử & Kiểm Định (Verification)

1. **Quality Gate:** Toàn bộ test suite `pytest` vượt qua 100% (**166/166 passed**).
2. **Zero-Waste:** Dung lượng thư mục sạch sẽ duy trì ở mức **5.13 MB** (< 15MB).
3. **Trải nghiệm người dùng:** Giao diện tối dịu mắt, độ tương phản hài hòa, đọc lâu không mỏi mắt, chuẩn phong cách Terminal định chế tài chính.

