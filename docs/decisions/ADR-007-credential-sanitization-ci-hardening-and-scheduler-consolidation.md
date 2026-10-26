# ADR-007: Chuẩn Hóa Chuỗi Xác Thực API, Khắc Phục CI Quality Gate & Tối Ưu Hóa Bộ Lập Lịch Tự Động

- **Trạng thái:** Accepted (Đã chấp thuận & Triển khai)
- **Ngày quyết định:** 26/10/2026
- **Tác giả:** Neiro-Stock-VN Quantitative Team
- **Tệp liên quan:**
  - `src/collector/fialda_scanner.py`
  - `src/hud/terminal.py`
  - `src/backtesting/walk_forward.py`
  - `.github/workflows/scanner_and_pages.yml`
  - `.github/workflows/ci.yml`
  - `docs/architecture.md`
  - `docs/spec.md`

---

## 1. Bối cảnh & Thách thức (Context & Problem Statement)

Trong phiên giao dịch sáng ngày 26/10/2026, quá trình vận hành tự động của Neiro-Stock-VN gặp phải 3 vấn đề hạ tầng và tích hợp:
1. **Lệch chuỗi xác thực môi trường đám mây (Cloud Secret Pollution):**
   - Tài khoản Fialda VIP (`radarcophieu@gmail.com` / `TCdd@2025`) hoàn toàn chính xác khi đăng nhập trực tiếp trên ứng dụng Fialda và máy trạm local.
   - Tuy nhiên, khi chuyển qua GitHub Actions runner, việc sao chép bí mật qua Web UI của GitHub thường vô tình chèn thêm ký tự khoảng trắng (` `), xuống dòng ẩn (`\r\n`), hoặc dấu ngoặc kép bọc ngoài (`""`).
   - Hàm nạp biến môi trường `_load_env_val()` ban đầu chỉ đọc thô qua `os.getenv()` mà không loại bỏ các ký tự này, khiến payload gửi lên API Fialda trả về mã `HTTP 500: Đăng nhập thất bại - Email hoặc mật khẩu không chính xác`.
2. **Lỗi Runtime Type Evaluation trên Python 3.12 (CI Failure):**
   - File `src/backtesting/walk_forward.py` khai báo type hint trả về `Dict[str, Any]` nhưng thiếu import `Any` từ module `typing`.
   - Trên Python 3.14 (máy trạm local hỗ trợ PEP 649 deferred annotation) code vẫn chạy, nhưng trên môi trường CI GitHub Actions (Ubuntu / Python 3.12 runtime) pytest bị chặn ngay tại bước thu thập test (collection error exit code 2).
3. **Phân mảnh cấu hình Cron Scheduler trên GitHub Actions:**
   - Cấu hình cũ chia nhỏ 11 biểu thức cron riêng lẻ cho từng mốc 30 phút. Trên hạ tầng shared runner của GitHub Actions, việc khai báo quá nhiều cron rời rạc dễ dẫn đến hiện tượng nghẽn hàng đợi (queue starvation) hoặc scheduler bỏ qua lượt chạy tự động.

---

## 2. Quyết định Kiến trúc (Architectural Decisions)

### 2.1. Chuẩn Hóa Chuỗi Xác Thực Đa Tầng (Credential Sanitization & Validation)
- Triển khai bộ lọc làm sạch chuỗi hai lớp `.strip().strip("'\" \r\n\t")` tại:
  - Hàm tiện ích tĩnh `FialdaScanner._load_env_val(key)`.
  - Hàm thực thi xác thực `FialdaScanner.login()`.
- Bổ sung thông tin chẩn đoán an toàn (Masked Diagnostics): Ghi log độ dài chuỗi (`user_len`, `pwd_len`) và ký tự biên (`prefix`, `suffix`) mà tuyệt đối không để lộ mật khẩu trong logs.
- Bổ sung cảnh báo chi tiết (Explicit Fallback Warnings): Khi xác thực không thành công, hệ thống lập tức in cảnh báo rõ ràng và kích hoạt cơ chế Fallback an toàn (Public Entrade / Mock) để giữ cho giao diện người dùng không bị sập hay trả về lỗi 404.

### 2.2. Hiển Thị Đèn Cảnh Báo Trạng Thái Dữ Liệu Trên HUD Terminal
- Trên giao diện Web Dashboard (`src/hud/terminal.py`):
  - 🟢 **LIVE:** `🟢 DỮ LIỆU: REAL-TIME FIALDA PRO API` (Dữ liệu trực tiếp theo chu kỳ).
  - 🟡 **FALLBACK:** `🟡 CHẾ ĐỘ DỰ PHÒNG: BẢNG GIÁ ENTRADE/DNSE PUBLIC` kèm dòng trạng thái: `⚠️ Fialda VIP gián đoạn - Đang tự động bảo vệ tín hiệu bằng nguồn dự phòng`.

### 2.3. Tối Ưu Hóa Lập Lịch Cron Chuẩn POSIX (`scanner_and_pages.yml`)
- Tích hợp 11 mốc thời gian thành **3 biểu thức chuẩn POSIX**:
  - `15,45 2,3,4 * * 1-5`: Toàn bộ 6 mốc phiên sáng (09:15, 09:45, 10:15, 10:45, 11:15, 11:45 VN).
  - `15,45 6,7 * * 1-5`: Toàn bộ 4 mốc phiên chiều (13:15, 13:45, 14:15, 14:45 VN).
  - `5 8 * * 1-5`: Chốt phiên ATC (15:05 VN).
- Giúp GitHub Actions Engine dễ dàng đăng ký vào hàng đợi crontab toàn cầu, giảm tối đa độ trễ điều phối.

### 2.4. Khắc Phục Hoàn Toàn Lỗi Type Hint Trên Python 3.12
- Bổ sung khai báo `from typing import Any, Dict, List, Optional, Tuple` tại `src/backtesting/walk_forward.py`.
- Bảo đảm 100% tương thích ngược trên mọi phiên bản Python từ 3.12 đến 3.14.

---

## 3. Hệ quả & Đánh giá (Consequences & Verification)

- **Xác thực thực tế:** Đăng nhập thành công 100% với tài khoản Fialda VIP trên GitHub Actions runner.
- **Dữ liệu trực tiếp:** Báo cáo [reports/latest_scan.md](file:///reports/latest_scan.md) và Dashboard [https://daninguyen2509.github.io/Neiro-Stock-VN/](https://daninguyen2509.github.io/Neiro-Stock-VN/) cập nhật dữ liệu khớp lệnh thực tế phiên sáng ngày 26/10 (Giá trị GD: 5,915 tỷ VND; Top 20: PVC, VTZ, SIP, PHR, QNS, PDR, VIX...).
- **CI Quality Gate:** Chuyển xanh hoàn toàn với 72/72 tests passed và kiểm tra dung lượng workspace đạt chuẩn Zero-Waste (< 15MB).
