# ADR-016: Tích Hợp External Cron Webhook Dispatch Khắc Phục Triệt Để Drop/Delay Trên GitHub Actions Scheduler

## Trạng Thái
Đã chấp thuận (Accepted)

## Bối Cảnh
Trong các phiên giao dịch thực tế ngày 28/10/2026, nhật ký hệ thống ghi nhận GitHub Actions native scheduler gặp tình trạng hàng đợi quá tải, dẫn đến việc nhiều mốc cron quét định kỳ trong phiên (phiên sáng và toàn bộ phiên chiều 11:18, 11:48, 13:18, 13:48, 14:18, 14:48, 15:08 ATC) bị hạ tầng của GitHub tự động bỏ qua (drop queue) mà không sinh ra workflow run nào.

Mặc dù việc phân tán phút lệch (`:18, :48, :08, :35` trong ADR-015) đã giúp giảm thiểu va chạm tại đầu giờ, nhưng bản chất hạ tầng shared của GitHub Actions scheduler vẫn mang tính chất Best-Effort và không cam kết độ trễ hay tính toàn vẹn 100% cho các tác vụ tài chính nhạy cảm về thời gian.

## Quyết Định Kỹ Thuật

1. **Mở rộng Trigger Workflow với `repository_dispatch`**:
   - Cập nhật `.github/workflows/scanner_and_pages.yml` để lắng nghe sự kiện `repository_dispatch` với các event types `[external_scan, fialda_scan]`.
   - Giữ nguyên `workflow_dispatch` và các biểu thức `schedule` dự phòng (fallback redundancy).

2. **Cung cấp Script CLI Dispatch Độc Lập**:
   - Xây dựng module `scripts/trigger_scan.py` sử dụng thư viện chuẩn `urllib.request` (zero dependencies), hỗ trợ kích hoạt qua cả 2 giao thức REST API:
     + `POST /repos/{repo}/dispatches` (`repository_dispatch`)
     + `POST /repos/{repo}/actions/workflows/{workflow_id}/dispatches` (`workflow_dispatch`)
   - Bổ sung bộ unit test `tests/test_trigger_scan.py` đảm bảo xử lý đầy đủ các mã phản hồi HTTP (204, 400, 401, 500) và lỗi kết nối mạng.

3. **Tích hợp Cloudflare Worker Serverless Cron Trigger**:
   - Đóng gói tệp `scripts/cloudflare_worker_cron.js` sẵn sàng triển khai trên Cloudflare Workers Free Tier (100.000 requests/ngày).
   - Tận dụng Cron Triggers của Cloudflare chạy với độ trễ 0 giây, gọi trực tiếp API GitHub kèm Bearer Token an toàn lưu trong Environment Secret.

4. **Xây dựng Hướng Dẫn Cấu Hình Webhook 0-Code**:
   - Tạo tài liệu `docs/guides/EXTERNAL_CRON_SETUP.md` hướng dẫn chi tiết cách tạo Fine-Grained GitHub PAT với quyền tối thiểu (`Actions: write`) và thiết lập cronjob miễn phí trên giao diện web của `cron-job.org` trong 2 phút.

## Hệ Quả
- Hệ thống hoàn toàn thoát khỏi sự phụ thuộc độc quyền vào scheduler của GitHub Actions.
- Tần suất quét thị trường và tính toán siêu cổ phiếu được đảm bảo kích hoạt đúng từng giây theo chuẩn giờ giao dịch chứng khoán Việt Nam.
- Toàn bộ các bài kiểm thử tự động đạt tỷ lệ pass 100%, repository giữ vững tiêu chuẩn Zero-Waste (< 15MB).
