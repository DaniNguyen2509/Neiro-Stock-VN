# ADR-018: Đại Tu Tầng API & Data Crawling — Connection Pooling, Batch ExpertAZ, Tự Doanh Thực Chứng, BCTC Đa Ngành & Chuẩn Hóa Đơn Vị VPS

- **Trạng thái:** Accepted & Implemented
- **Ngày ban hành:** 2026-10-31
- **Phạm vi ảnh hưởng:** `src/collector/fialda_scanner.py`, `src/collector/vn_market_client.py`, `src/collector/google_sheets_client.py`, `src/sector_engine/market_breadth.py`, `src/hud/terminal.py`, `tests/test_api_crawl_resilience.py`

---

## 1. Bối Cảnh & Chẩn Đoán Thực Chiến (Root-Cause Audit)

Qua quá trình kiểm định trực tiếp (Live API Probing) trên toàn bộ các đầu mối thu thập dữ liệu của hệ thống (`Fialda VIP Swagger API`, `DNSE/Entrade Chart API`, `VPS Live Datafeed`, `Google Apps Script Webhook`), chúng tôi phát hiện **9 khiếm khuyết kỹ thuật và lệch chuẩn schema** làm suy giảm độ chính xác dữ liệu định lượng:

1. **Nghẽn cổ chai TCP/TLS Handshake & Sai lệch Rating ngầm (`FialdaScanner`):**
   - Toàn bộ truy vấn dùng `requests.get`/`requests.post` rời rạc không có `requests.Session` tái sử dụng kết nối, đồng thời bắn `60–80` luồng đồng thời (`max_workers=10`) tới `GetExpertRating`. Khi socket gặp lỗi `_ssl.c:1064: The handshake operation timed out`, khối `except` nuốt lỗi và gán ngầm `RS1M=50, Composite=50, Acc/Diss='C'`.
2. **Sai lệch đơn vị 1,000 lần trên dòng tiền Khối ngoại Live VPS (`src/hud/terminal.py`):**
   - API `bgapidatafeed.vps.com.vn/getliststockdata` trả về `fBValue` và `fSValue` theo đơn vị **1,000 VND** (ví dụ `FRT`: chênh lệch `+6.2676e6` tương ứng `+6.27 tỷ VND`), nhưng Client JS chia cho `1e9` thay vì `1e6`, làm Thẻ Smart Money bị ghi đè về `+0.0 Tỷ VND` ngay khi mở trang.
3. **Trường ảo `"PropTrade"` khiến dữ liệu Tự doanh luôn bằng `None`:**
   - Endpoint `Common/GetStockInfos` không hề chứa khóa `"PropTrade"`. Trong khi đó, Fialda cung cấp endpoint chuẩn `/api/services/app/Market/GetTuDoanhV2` trả về đầy đủ giá trị Tự doanh toàn thị trường (`indices`) và từng mã cổ phiếu (`stocks`, đơn vị VND).
4. **BCTC Ngân hàng / Chứng khoán / Bảo hiểm bị trả về `0.0 tỷ` Doanh thu:**
   - `get_income_statement()` chỉ gọi biểu mẫu `GetFS_IncomeStatement_General` (`isA1`/`isA3`), khiến nhóm Ngân hàng (`TPB`, `VCB`, `MBB`...) luôn bị hiển thị `0.0 tỷ` doanh thu và `0.0%` biên lợi nhuận do đặc thù báo cáo dùng mã chỉ tiêu `isB38` (Tổng thu nhập hoạt động — TOI) và `isB40` (Lợi nhuận thuần HĐKD trước dự phòng — PPOP) trên `GetFS_IncomeStatement_Bank`.
5. **Rò rỉ sự kiện cổ tức giả định (`2026-11-15`) vào báo cáo Live khi `UpcomingEvents` rỗng:**
   - Khi doanh nghiệp đang kết nối API thật nhưng không có lịch chốt quyền sắp tới (`result: []`), hàm rơi xuống `_fallback_mock_events` và chèn sự kiện giả `"chuẩn bị chi trả cổ tức đợt 1 — 2026-11-15"`.
6. **Sai tên trường khối lượng trung bình 20 phiên & thiếu nguồn dự phòng OHLCV:**
   - Mã cũ tìm `averageVolume20d` / `avgVolume20` không tồn tại, trong khi schema thực tế của `GetStockInfos` là `DailyStatistic.avgVol20D`. Ngoài ra `get_recent_ohlcv_batch` chỉ phụ thuộc duy nhất vào Entrade, chưa tận dụng `TradingView/GetOHLC` của Fialda làm nguồn dự phòng.
7. **Lệch khóa số ít `"noChange"` trong `parse_market_breadth_dict`:**
   - Fialda `GetIndexData` trả về `"noChange"` (số ít), khiến số mã đứng giá (`unchanged`) bị đọc thành `0`.
8. **Truy vấn thừa luôn lỗi `HTTP 400` trên `VNMarketClient`:**
   - Gọi `/chart-api/v2/ohlcs/stock?symbol=VN30F1M` luôn trả về `HTTP 400 BAD_REQUEST: invalid symbol`.
9. **False-Positive khi Google Sheets Webhook trả về trang HTML Đăng nhập & Định giá P/B-P/E tĩnh trên bảng CAMEL:**
   - Khi Google Apps Script chưa mở quyền `Anyone`, Google chuyển hướng `302 -> 200 OK` về trang HTML `accounts.google.com` nhưng client cũ vẫn báo đồng bộ thành công. Đồng thời bảng CAMEL cập nhật giá khớp live nhưng giữ nguyên P/B, P/E tĩnh dù `BasicInfo` đã có sẵn `bookValuePerShare` và `eps_TTM`.

---

## 2. Quyết Định Kiến Trúc & Giải Pháp Triệt Để

1. **HTTP Connection Pooling & Retry Adapter toàn hệ thống:**
   - Trang bị `requests.Session` gắn `HTTPAdapter(pool_connections=16, pool_maxsize=16)` và ` urllib3.util.retry.Retry` (`429, 500, 502, 503, 504`) cho cả `FialdaScanner` và `VNMarketClient`.
2. **Nạp Hàng Loạt `Expert/GetExpertAZ` (Giảm ~85% số lượng request):**
   - Gọi 1 request duy nhất tới `/api/services/app/Expert/GetExpertAZ` để nạp tức thì điểm IBD/RS/AccDiss của hơn 310 cổ phiếu dẫn dắt trong `~0.1s`, chỉ gọi bổ sung `GetExpertRating` (`max_workers=4`) cho vài mã nằm ngoài danh sách. Thời gian quét toàn thị trường giảm xuống chỉ còn `~3.6 giây` với tỷ lệ timeout `0%`.
3. **Kích hoạt Dữ liệu Tự doanh Thực tế qua `Market/GetTuDoanhV2`:**
   - Bổ sung `get_prop_trading_summary()` và `get_prop_trading_map()`, kết nối trực tiếp dòng tiền Tự doanh thực chứng (tỷ VND) vào `classify_dual_flow()` và hiển thị minh bạch nhãn `TD: +X.Xt` trên Bảng điều khiển Web HUD.
4. **Phân luồng BCTC Đa Ngành Tự Động (`General` / `Bank` / `Security` / `Insurance`):**
   - Tự động ánh xạ chuẩn xác chỉ tiêu kế toán theo ngành: Ngân hàng (`isB38` TOI, `isB40` PPOP), Chứng khoán (`isA1/isA3`, `isA5/isA11`), Bảo hiểm (`isI105/isI64`, `isI87`), Sản xuất/Thương mại (`isA3/isA1`, `isA5`), kèm cơ chế tự động chuyển luồng (cross-schema failover) khi doanh thu bằng `0`.
5. **Trung thực hóa Lịch Sự kiện & Lọc nhiễu Tin tức Doanh nghiệp:**
   - Khi đang online (`HTTP 200`), nếu `GetUpcomingEvents` rỗng sẽ tự động truy vấn `Event/GetRecentEvents` để lấy sự kiện CBTT gần nhất; nếu vẫn rỗng thì trả về `[]` và hiển thị thông báo trung thực, tuyệt đối không sinh lịch cổ tức giả. Lọc bỏ tin rác `relevance == 0` khi có tin đúng doanh nghiệp và chống lặp tiêu đề khi `shortContent=None`.
6. **Liên thông Đa Nguồn (Multi-Source Failover) cho Giá & OHLCV:**
   - Đọc chuẩn `DailyStatistic.avgVol20D`; bổ sung failover tự động từ `Entrade` sang `Fialda TradingView/GetOHLC` cho chuỗi nến 1D và kết hợp `VPS Batch Datafeed` + `Entrade` cho giá khớp công khai.
7. **Chuẩn hóa Đơn vị `1e6` trên Live VPS HUD & Chặn HTML Redirect trên Google Sheets:**
   - Đổi phép chia `(liveForeignBuyVal - liveForeignSellVal)` sang `/ 1e6`, thêm `{ cache: 'no-store' }`, đồng bộ trực tiếp từng ô `.live-foreign[data-sym]` trên cột `Khối Ngoại` khớp tuyệt đối với Thẻ Header Smart Money.
   - Kiểm tra URL `accounts.google.com` và tiền tố HTML (`<!DOCTYPE html` / `<html`) trong `GoogleSheetsLedgerClient.sync_signals()`.
   - Tính toán động `P/B` và `P/E` thực tế cho 10 ngân hàng CAMEL từ `BasicInfo.bookValuePerShare` và `BasicInfo.eps_TTM` không tốn thêm bất kỳ request nào.

---

## 3. Hệ Quả & Kiểm Chứng Chất Lượng

- **Tốc độ & Độ ổn định:** Toàn bộ chu trình quét thực tế hoàn tất trong **3.63 giây** (không còn lỗi SSL Handshake Timeout hay HTTP 400 thừa).
- **Độ toàn vẹn dữ liệu:** `TPB` hiển thị chính xác `TOI Q2/2026 = 5,195.2 tỷ VND` (thay vì `0.0 tỷ`), `FRT` hiển thị đúng dòng tiền Tự doanh `+3.28 tỷ VND` và sự kiện CBTT thật, Thẻ Smart Money trên Web HUD giữ đúng giá trị tỷ VND sau mỗi chu kỳ cập nhật 30 giây.
- **Kiểm thử tự động:** Bổ sung `11` kịch bản hồi quy chuyên sâu tại `tests/test_api_crawl_resilience.py`, nâng tổng số bài test toàn hệ thống lên **128/128 passed (100%)**.
