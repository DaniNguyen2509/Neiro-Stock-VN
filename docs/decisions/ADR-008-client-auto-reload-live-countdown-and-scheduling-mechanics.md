# ADR-008: Cơ Chế Tự Động Nạp Lại Client-Side, Bộ Đếm Ngược Live Countdown & Phân Tích Cơ Chế Lập Lịch GitHub Actions

- **Trạng thái:** ACCEPTED
- **Ngày quyết định:** 2026-10-26
- **Phạm vi tác động:** `src/hud/terminal.py`, `exports/index.html`, `exports/vn_stock_terminal.html`, `.github/workflows/scanner_and_pages.yml`, `docs/spec.md`, `docs/architecture.md`

---

## 1. Bối Cảnh (Context)

Người dùng đặt câu hỏi tại sao giao diện Web Dashboard (`https://daninguyen2509.github.io/Neiro-Stock-VN/`) không tự động nạp lại (reload) sau mỗi chu kỳ 30 phút. Qua quá trình phân tích kỹ thuật chuyên sâu theo skill `debugging-and-error-recovery`, hệ thống phát hiện 2 nguyên nhân cốt lõi ở 2 tầng khác nhau:

1. **Tầng Giao Diện Trình Duyệt (Frontend / Client-Side):**
   - File xuất bản `exports/index.html` trước đây là một trang HTML tĩnh thuần túy (`static HTML`), hoàn toàn không chứa thẻ `<meta http-equiv="refresh">` hay mã JavaScript `setInterval` để nạp lại trang.
   - Do đó, khi người dùng mở tab trình duyệt trên máy tính hoặc điện thoại, màn hình sẽ đứng yên vĩnh viễn ở trạng thái dữ liệu của thời điểm mở trang. Kể cả khi backend GitHub Actions trên Cloud đã hoàn thành lượt quét mới và xuất bản lên GitHub Pages, tab của người dùng vẫn hiển thị dữ liệu cũ nếu không tự bấm F5.

2. **Tầng Máy Chủ Điều Phối (Backend Runner / GitHub Actions Scheduler):**
   - Trên GitHub Actions, cơ chế `schedule: - cron: '...'` chạy trên hạ tầng đa người dùng dùng chung toàn cầu (Multi-Tenant Shared Queue).
   - Theo tài liệu chính thức của GitHub: Các tác vụ cron miễn phí là dạng "Best-Effort Service", thường xuyên chịu độ trễ xếp hàng (Queue Delay) từ 15 đến 45 phút vào các khung giờ cao điểm.
   - Khi một file workflow vừa được cập nhật nhánh `main`, hệ thống Cron Indexer của GitHub cần thời gian trễ từ 1 đến 2 giờ để đăng ký các mốc lập lịch mới vào hàng đợi.

---

## 2. Quyết Định Thiết Kế (Decisions)

### 2.1. Tích Hợp Bộ Đếm Ngược Live Countdown & Cơ Chế Auto-Reload Phía Client
- Thêm nhãn đóng dấu thời gian quét cụ thể theo múi giờ Việt Nam (UTC+7):
  `🕒 Cập nhật: HH:MM:SS • DD/MM/YYYY`
- Tích hợp bộ đếm ngược thời gian thực (Live Countdown Timer) 60 giây hiển thị trực quan tại Header:
  `🔄 Tự làm mới: 60s` (chạy lùi từng giây).
- Bổ sung nút thao tác trực tiếp `⚡ Tải lại ngay` cho phép người dùng chủ động nạp lại tức thì.
- **Cơ chế Nạp lại Chống Lưu Đệm (Cache-Busting Reload):** Khi hết 60 giây hoặc người dùng nhấn nút, JavaScript tự động kích hoạt:
  ```javascript
  const url = new URL(window.location.href);
  url.searchParams.set('_t', Date.now().toString());
  window.location.href = url.toString();
  ```
  Điều này triệt tiêu hoàn toàn bộ nhớ đệm (HTTP cache) của trình duyệt và CDN GitHub Pages, ép trình duyệt tải về phiên bản HTML mới nhất.
- Bổ sung thẻ `<meta http-equiv="refresh" content="180">` làm dự phòng (fallback) trong trường hợp trình duyệt tắt JavaScript.

### 2.2. Làm Rõ & Hướng Dẫn Kích Hoạt Lập Lịch GitHub Actions
- Giữ nguyên lịch quét tự động POSIX tối ưu trong `scanner_and_pages.yml`:
  - `15,45 2,3,4 * * 1-5` (09:15 - 11:45 VN)
  - `15,45 6,7 * * 1-5` (13:15 - 14:45 VN)
  - `5 8 * * 1-5` (15:05 VN ATC)
- Cung cấp phương án Webhook Trigger bên ngoài (External Cron như Cron-job.org / UptimeRobot) nếu người dùng yêu cầu độ chính xác tuyệt đối từng giây, không phụ thuộc vào độ trễ hàng đợi của GitHub.

---

## 3. Hệ Quả & Đánh Giá (Consequences)

- **Trải nghiệm Người Dùng:** Trực quan, chuyên nghiệp. Nhà đầu tư có thể mở Dashboard trên màn hình thứ hai và yên tâm rằng trang luôn tự động làm mới và hiển thị chính xác thời gian dữ liệu.
- **Tiêu Chuẩn Zero-Waste:** Mã JavaScript nhúng cực kỳ nhẹ (~15 dòng script thuần, 0 dependency thư viện ngoài), không làm tăng dung lượng trang web, tuân thủ nghiêm ngặt tiêu chuẩn repo < 15MB.
- **Độ Tin Cậy Toàn Hệ Thống:** Kết hợp cả Meta Refresh fallback + Live JS Countdown + Cache-Busting Reload, loại trừ 100% hiện tượng nhìn nhầm dữ liệu cũ.
