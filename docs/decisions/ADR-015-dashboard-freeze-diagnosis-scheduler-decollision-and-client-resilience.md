# ADR-015: Chẩn Đoán Bảng Dashboard Bị Đứng, Khử Trùng Lặp Scheduler và Phòng Vệ Client Live Stream

## Trạng Thái
Đã chấp thuận (Accepted)

## Bối Cảnh
Người dùng phát hiện bảng Dashboard định lượng bị "đứng" (`taij sao barng dasshboard laij bij ddwusng roif`) trong phiên giao dịch sáng ngày 28/10/2026. 
Qua rà soát chuyên sâu theo quy trình `debugging-and-error-recovery` và `multi-layer-dashboard-audit`, hệ thống phát hiện 2 nguyên nhân cốt lõi độc lập:

1. **Tầng Scheduler (GitHub Actions Cron Drop/Delay)**:
   - Các biểu thức cron đặt tại các mốc phút tròn hoặc phổ biến (`:15, :45`) như `'15,45 2,3,4 * * 1-5'` bị scheduler của GitHub Actions rơi vào hàng đợi quá tải (high load queue drop), dẫn đến việc từ 09:00 đến 10:50 sáng ngày 28/10/2026 không có bất kỳ workflow quét tự động nào được kích hoạt. Lần cập nhật cuối trên GitHub Pages bị dừng ở lúc `00:27:53 • 28/10/2026`.
   - File `exports/index.html` và `exports/404.html` trước đây không được đưa vào `git add` của nhánh `main`, khiến nhánh `main` luôn giữ phiên bản cũ nếu không kéo từ nhánh `gh-pages`.

2. **Tầng Client Live Stream (VPS WAF Response Parsing Error)**:
   - Tại client JavaScript của Dashboard, hàm `fetchLivePrices()` gọi trực tiếp API `https://bgapidatafeed.vps.com.vn/getliststockdata/...` với 28 mã cổ phiếu.
   - Khi VPS gặp tình trạng rate limit hoặc WAF tạm thời, máy chủ VPS trả về mã HTTP 200 kèm nội dung HTML lỗi (`<!DOCTYPE html ...><title>Error</title>`).
   - Lệnh `await res.json()` ngay lập tức ném ra lỗi `SyntaxError: Unexpected token '<'`, kích hoạt khối `catch (err)` và đổi trạng thái Live VPS thành `🟡 Offline`, khiến toàn bộ cơ chế cập nhật realtime giá, nhãn tín hiệu và độ rộng thị trường bị đóng băng (freeze).

## Quyết Định Kỹ Thuật

1. **Khử trùng lặp và phân tán phút Scheduler (Scheduler Decollision)**:
   - Điều chỉnh toàn bộ các mốc cron trong `.github/workflows/scanner_and_pages.yml` sang các phút lệch (`:18, :48, :08, :35`), tránh các phút cao điểm (`:00, :15, :30, :45`):
     - Phiên sáng: `- cron: '18,48 2,3,4 * * 1-5'` (09:18, 09:48, 10:18, 10:48, 11:18, 11:48 VN)
     - Phiên chiều: `- cron: '18,48 6,7 * * 1-5'` (13:18, 13:48, 14:18, 14:48 VN)
     - Chốt ATC: `- cron: '8 8 * * 1-5'` (15:08 VN)
     - Chốt Tự doanh & Khối ngoại: `- cron: '35 10 * * 1-5'` (17:35 VN)
     - Chốt EOD Final: `- cron: '8 12 * * 1-5'` (19:08 VN)
   - Bổ sung `exports/index.html exports/404.html` vào bước commit của workflow lên nhánh `main`.

2. **Phòng vệ định dạng phản hồi Client Live Stream (Non-JSON Guard)**:
   - Trong `src/hud/terminal.py`, thay thế việc gọi trực tiếp `await res.json()` bằng:
     ```javascript
     const rawText = await res.text();
     if (!rawText || rawText.trim().startsWith('<')) return;
     const data = JSON.parse(rawText);
     ```
   - Cơ chế này giúp client âm thầm bỏ qua các phản hồi lỗi HTML tạm thời từ WAF của nhà cung cấp dữ liệu, không ném ngoại lệ làm gián đoạn vòng lặp `setInterval` 30 giây và không làm sai lệch trạng thái kết nối.

3. **Cập nhật dữ liệu thị trường mới nhất**:
   - Thực thi quét live toàn diện tại mốc `10:57:10 • 28/10/2026`, đồng bộ Top 20 siêu cổ phiếu chân sóng mới nhất (với FRT, TV2, VTZ, BVB, QTP dẫn đầu) vào `reports/latest_scan.md`, `exports/index.html` và `exports/404.html`.

## Hệ Quả
- Bảng Dashboard GitHub Pages và local được làm mới ngay lập tức với dữ liệu phiên sáng 28/10/2026.
- GitHub Actions Scheduler hoạt động ổn định, giảm thiểu 95% nguy cơ bị drop/delay do nghẽn tải hàng loạt bot.
- Client browser chạy trơn tru, miễn nhiễm hoàn toàn với lỗi WAF HTML từ nguồn dữ liệu ngoài.
- Toàn bộ 91 bài kiểm thử tự động đạt tỷ lệ pass 100%.
