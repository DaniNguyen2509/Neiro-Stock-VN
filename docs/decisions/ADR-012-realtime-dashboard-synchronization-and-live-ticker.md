# ADR-012: Đồng Bộ Hóa Toàn Diện Dashboard, Xóa Bỏ Hardcode & Cập Nhật Live Ticker 30s Thời Gian Thực

- **Trạng thái:** Accepted
- **Ngày quyết định:** 2026-10-27
- **Tác giả:** Neiro Quant Team
- **Liên kết:** [ADR-008](ADR-008-client-side-auto-reload-and-live-countdown.md), [ADR-010](ADR-010-live-dynamic-price-polling-5min-cadence.md), [ADR-011](ADR-011-online-signal-ledger-and-ml-dataset-pipeline.md)

---

## 1. Bối Cảnh (Context)

Người dùng ghi nhận tình trạng Dashboard bị lệch pha và mất đồng bộ nghiêm trọng:
1. **Lệch pha thời gian hiển thị (Double Clock Confusion):** Huy hiệu `🟢 Live 5m (10:32:38)` đặt cạnh `🕒 Cập nhật: 10:07:14 • 27/10/2026` khiến người dùng nhầm lẫn hệ thống bị trễ 25 phút.
2. **Các thẻ chỉ số thống kê bị gán cứng (Hardcoded Static Metric Cards):**
   - Thẻ `Dòng Tiền Cá Mập Định Chế` ghi cố định `+427.5 Tỷ VND` (Khối ngoại + Tự doanh mua ròng), trong khi thực tế khối ngoại đang bán ròng rã và bảng Top 20 bên dưới hiển thị số âm.
   - Thẻ `Độ Rộng Thị Trường` ghi cố định `73.3%` (22/30 Cổ phiếu giữ xu hướng tăng).
   - Thẻ `Ngành Dẫn Dắt` ghi cố định `NÔNG NGHIỆP & CHỨNG KHOÁN (DBC, CTS bứt phá mạnh)`.
3. **Giá khớp chỉ cập nhật 1 lần lúc tải trang:** Hàm `fetchLivePrices()` trong JavaScript chỉ chạy 1 lần duy nhất lúc mở trang. Trong suốt 300 giây đếm lùi, giá hoàn toàn bị đóng băng.
4. **Bảng Top 20 thiếu % biến động và không phản ánh trạng thái mua:** Khi giá thay đổi, người dùng không thấy được % tăng/giảm so với tham chiếu, và trạng thái khuyến nghị không tự động cảnh báo nếu giá chạy vượt vùng mua (`MUA ĐUỔI ⚠️`) hoặc chạm cắt lỗ (`CHẠM SL 🔴`).

---

## 2. Quyết Định Kiến Trúc (Decision)

### 2.1. Xóa Bỏ Hoàn Toàn Hardcode & Tính Toán Động Phía Server (Python Rendering)
Trong [src/hud/terminal.py](file:///c:/Users/Daniel/Documents/My-Projects/Neiro-Stock-VN/src/hud/terminal.py):
1. **Dòng Tiền Cá Mập (Smart Money):** Tính tổng `sum(c.foreign_net_value_billion for c in fialda_candidates)`. Nếu âm, hiển thị màu vàng/đỏ kèm ghi chú `Ngoại bán ròng • Dòng tiền Nội gom cân hàng (Pha chân sóng)`, đồng bộ chính xác với Ma trận dòng tiền kép (ADR-011).
2. **Độ Rộng Danh Mục (Momentum Breadth):** Tính tỷ lệ cổ phiếu có xung lực bứt phá (`composite_rating >= 70` hoặc `rs_1m >= 70`) trên tổng số ứng viên.
3. **Ngành Dẫn Dắt (Leading Sector):** Xây dựng `SECTOR_MAP` gom nhóm ngành tự động dựa trên tọa độ RRG thực tế của các ứng viên, xuất ra các ngành dẫn dắt dòng tiền chuẩn xác (ví dụ: `CHỨNG KHOÁN & BẤT ĐỘNG SẢN`).
4. **Gán ID Semantic:** Bổ sung các ID `card-smart-money-val`, `card-smart-money-sub`, `card-breadth-val`, `card-breadth-sub`, `card-sector-val`, `sig-badge-{sym}` cho từng thẻ và hàng.

### 2.2. Vòng Lặp Polling 30 Giây Thời Gian Thực Phía Trình Duyệt (Client-Side Real-Time Ticker)
1. **Chu kỳ 30 giây (`setInterval(fetchLivePrices, 30000)`):** Kéo dữ liệu khớp lệnh VPS liên tục mỗi 30 giây mà không cần tải lại toàn bộ trang.
2. **Đồng bộ cột Giá Khớp & % Biến Động:** Hiển thị giá kèm `(+X.X%)` đổi màu chuẩn Sở Giao dịch (Xanh lá / Đỏ / Tím trần / Xanh lam sàn / Vàng tham chiếu).
3. **Đánh giá lại Vùng Mua / Cắt Lỗ thời gian thực:**
   - Giá $> entry\_high \times 1.03$: Bật cảnh báo `MUA ĐUỔI ⚠️`.
   - Giá $\le stop\_loss$: Kích hoạt cảnh báo `CHẠM SL 🔴`.
   - Giá $\ge tp1$: Hiển thị huy hiệu `ĐẠT TP1 🎯`.
4. **Đồng bộ thời gian thực cho Thẻ Thống Kê:** Tính tổng dòng tiền ngoại và số mã tăng/giảm trực tiếp từ payload VPS để cập nhật thẻ Smart Money và Độ Rộng tức thì.
5. **Hiển thị nhãn thời gian trực quan:** Phân định rõ giữa `🕒 Cập nhật: {scan_time_str}` (quét AI chuyên sâu toàn sàn) và `🟢 Live VPS: HH:MM:SS (30s)` (dòng giá khớp lệnh trực tuyến).

---

## 3. Hệ Quả & Đánh Giá (Consequences)

- **Trải nghiệm người dùng chân thực:** Bảng điện tử nhấp nháy cập nhật giá và chỉ số liên tục mỗi 30 giây, loại bỏ hoàn toàn cảm giác đơ cứng hoặc lệch pha số liệu.
- **Không tốn tài nguyên máy chủ:** Toàn bộ quá trình tính toán và kéo giá diễn ra trên trình duyệt máy khách (Client-Side Fetch qua VPS Datafeed CORS `*`), máy chủ GitHub Pages hoàn toàn tĩnh.
- **Độ tin cậy 100%:** Dữ liệu hiển thị luôn đồng nhất giữa các thẻ thống kê tổng quan và từng hàng chi tiết trong bảng.
