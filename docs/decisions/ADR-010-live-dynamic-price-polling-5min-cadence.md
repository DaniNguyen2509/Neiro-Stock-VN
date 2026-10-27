# ADR-010: Cơ Chế Cập Nhật Giá Tự Động 5 Phút (Live Dynamic Price Polling & Local Watcher Daemon)

- **Trạng thái:** ACCEPTED
- **Ngày quyết định:** 2026-10-27
- **Phạm vi tác động:** `src/hud/terminal.py`, `exports/index.html`, `exports/vn_stock_terminal.html`, `exports/404.html`, `tests/test_terminal_hud.py`, `docs/spec.md`, `docs/architecture.md`, `README.md`

---

## 1. Bối Cảnh (Context)

Người dùng đặt vấn đề giá trên Web Dashboard chưa cập nhật tự động trong phiên giao dịch và yêu cầu cấu hình chu kỳ cập nhật tự động thành **5 phút**.

Qua phân tích kiến trúc theo quy trình `debugging-and-error-recovery`:
1. **Trước đây:** Hệ thống xuất bản file HTML tĩnh lên GitHub Pages dựa trên lịch quét của GitHub Actions (mỗi 30 phút/mẻ). Các con số giá trên bảng được ghi cứng (hardcoded text) vào HTML tại thời điểm chạy.
2. **Hạn chế:** Bộ đếm ngược 60s trước đây chỉ tải lại (`reload`) file HTML tĩnh từ máy chủ. Giữa hai mẻ quét của GitHub Actions (khoảng cách 30 phút), file HTML trên GitHub Pages không đổi, nên người dùng nhìn thấy giá đứng yên dù trang web tự reload.
3. **Mục tiêu:** Cung cấp cơ chế cập nhật giá trực tiếp theo chu kỳ **5 phút (300 giây)**:
   - Trên Web/Mobile (GitHub Pages): Tự động nạp giá khớp mới nhất trực tiếp từ sàn vào các ô bảng giá mà không làm đứng trang.
   - Trên Máy tính cục bộ (Local): Cung cấp cờ `--watch` chạy ngầm định kỳ 5 phút/lần.

---

## 2. Quyết Định Thiết Kế (Decisions)

### 2.1. Tích Hợp Client-Side Dynamic Live Price Polling (Chu Kỳ 5 Phút = 300s)
- **Datafeed Mở Chuẩn Trao Đổi:** Tận dụng Public Datafeed có mở sẵn `Access-Control-Allow-Origin: *` của Bảng giá VPS (`https://bgapidatafeed.vps.com.vn/getliststockdata/SYM1,SYM2,...`).
- **Gắn Định Danh Cột Giá:** Bổ sung thuộc tính `class="live-price" data-sym="{symbol}"` cho tất cả các ô hiển thị giá trong:
  - Bảng Top 20 Siêu cổ phiếu chân sóng (Fialda VIP).
  - Bảng Phân tích Cơ bản Quantamental (Piotroski F-Score).
  - Bảng Định lượng Ngân hàng CAMEL & Basel II/III.
- **Hàm `fetchLivePrices()` JavaScript:**
  - Tự động kích hoạt ngay khi mở trang để nạp giá khớp mới nhất tức thì.
  - Cập nhật số liệu giá `lastPrice` với 2 chữ số thập phân (`toFixed(2)`).
  - Tự động đổi màu chữ theo chuẩn quy định của Sở Giao dịch Chứng khoán Việt Nam:
    - 🟣 Tím trần: `p >= ceil` (`#ea39b8`)
    - 🔵 Xanh lam sàn: `p <= floor` (`#00e5ff`)
    - 🟢 Xanh lá tăng: `p > ref` (`#00e676`)
    - 🔴 Đỏ giảm: `p < ref` (`#ff5252`)
    - 🟡 Vàng tham chiếu: `p == ref` (`#ffb300`)
- **Đồng Bộ Bộ Đếm Ngược 5 Phút (300s):**
  - Cập nhật biến đếm ngược: `let secondsLeft = 300;`
  - Thẻ dự phòng: `<meta http-equiv="refresh" content="300">`
  - Đèn báo trạng thái trực quan: `🟢 Live 5m (HH:MM:SS)` hiển thị thời gian khớp lệnh mới nhất.

### 2.2. Bổ Sung Local Watcher Daemon Cho Môi Trường Cục Bộ
- Bổ sung tham số dòng lệnh `--watch` và `--interval 300` trong `src/hud/terminal.py`:
  ```bash
  python -m src.hud.terminal --watch --interval 300
  ```
- Cho phép người dùng chạy vòng lặp ngầm trên máy tính cá nhân để tự động quét và tái tạo file HTML mỗi 5 phút mà không cần can thiệp thủ công.

---

## 3. Hệ Quả & Đánh Giá (Consequences)

- **Trải Nghiệm Thời Gian Thực:** Người dùng mở Web Dashboard trên điện thoại hoặc máy tính luôn thấy giá nhảy khớp lệnh chuẩn xác mỗi 5 phút (hoặc bấm `⚡ Tải lại ngay` để nạp ngay tức thì).
- **Tuân Thủ Zero-Waste:** Đoạn mã script tích hợp chỉ ~40 dòng JavaScript thuần, không cài thêm bất kỳ thư viện NPM nào, dung lượng dự án tiếp tục được bảo toàn ở mức siêu nhẹ (< 15MB).
- **Tính Bền Vững:** Nếu mất kết nối internet hoặc API ngoài trục trặc, hệ thống hiển thị đèn `🟡 Offline` và giữ nguyên giá gốc của mẻ quét Fialda gần nhất một cách an toàn.
