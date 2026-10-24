# HƯỚNG DẪN TÁC CHIẾN: 3 PROMPT NÂNG CẤP LÊN QUY MÔ "QUỸ TRIỆU ĐÔ"
> Tài liệu lưu trữ bộ 3 Prompt định hướng nâng cấp hệ thống **Neiro-Stock-VN** cho các phiên làm việc độc lập kế tiếp, áp dụng cấu trúc Slash Commands (`/goal`, `/planning-and-task-breakdown`, `/using-agent-skills`).

---

## 📌 Tổng Quan Lộ Trình 3 Bước

| Phiên | Mục Tiêu Chiến Thuật | Tệp Liên Quan | Độ Ưu Tiên |
| :--- | :--- | :--- | :--- |
| **Phiên 1** | **Cảnh báo Tín hiệu tức thì (Telegram / Discord Bot)** | `src/alert/telegram_bot.py`, `.github/workflows/scanner_and_pages.yml` | 🔴 **Ưu tiên 1 (Làm trước)** |
| **Phiên 2** | **Bộ lọc Thanh khoản & Sức chứa Danh mục (Liquidity & Capacity Sizer)** | `src/risk_engine/liquidity_sizer.py`, `src/collector/fialda_scanner.py` | 🟡 **Ưu tiên 2** |
| **Phiên 3** | **Kiểm định Quá khứ (Walk-Forward Backtesting Engine T+2.5)** | `src/backtesting/engine.py`, `reports/backtest_results.md` | 🟢 **Ưu tiên 3** |

---

## 1. PROMPT PHIÊN 1: TELEGRAM / DISCORD BOT ALERT ENGINE
*(Sao chép nguyên khối bên dưới vào phiên mới)*

```markdown
/goal /planning-and-task-breakdown /using-agent-skills

Chào em, tiếp nối dự án Neiro-Stock-VN tại repository này, anh muốn triển khai Module Cảnh Báo Tín Hiệu Tức Thì qua Telegram Bot (hoặc Discord Webhook) tích hợp trực tiếp vào quy trình GitHub Actions quét định kỳ 30 phút/lần (.github/workflows/scanner_and_pages.yml).

YÊU CẦU ĐẶC TẢ CHI TIẾT:
1. Tích hợp Telegram Alert Engine (src/alert/telegram_bot.py):
   - Đọc cấu hình bí mật từ môi trường: TELEGRAM_BOT_TOKEN và TELEGRAM_CHAT_ID (đã thiết lập trong GitHub Secrets).
   - Nếu không có token hoặc chạy ở môi trường dev không có mạng, module phải fallback sang chế độ Mock/Log an toàn, không được làm văng lỗi chương trình.
2. Định dạng thông báo chuẩn Định Chế (Institutional Clean Format):
   - Khi quét ra Top 5 Siêu cổ phiếu chân sóng hoặc Ngân hàng đạt chuẩn Tier A (CAMEL >= 80): Gửi ngay tin nhắn Markdown tóm tắt:
     + Mã CP & Ngành nghề.
     + Vùng giá gom khuyến nghị & Điểm cắt lỗ cứng T+2.5.
     + Lý do định lượng: Điểm Piotroski F-Score (x/9), CAMEL Tier, Order Flow Imbalance (OFI), Lực mua ròng Khối ngoại.
     + Kèm link trực tiếp đến Web Dashboard: https://daninguyen2509.github.io/Neiro-Stock-VN/
   - Bộ lọc chống spam (Anti-Spam Filter): Chỉ gửi cảnh báo khi có mã mới xuất hiện hoặc có sự thay đổi trạng thái (tránh gửi lặp lại 1 mã mỗi 30 phút nếu không có biến động mới).
3. Tích hợp vào Workflow GitHub Actions:
   - Cập nhật .github/workflows/scanner_and_pages.yml để truyền biến môi trường Telegram.
4. Kiểm thử & Tiêu chuẩn chất lượng:
   - Viết unit test hoàn chỉnh tests/test_telegram_alert.py đạt 100% pass với pytest.
   - Tuân thủ Zero-Waste Mandate (< 15MB) và Documentation-First Mandate (cập nhật docs/spec.md và docs/architecture.md).
```

---

## 2. PROMPT PHIÊN 2: BỘ LỌC THANH KHOẢN & SỨC CHỨA DANH MỤC (LIQUIDITY & CAPACITY SIZER)
*(Sao chép nguyên khối bên dưới vào phiên mới)*

```markdown
/goal /planning-and-task-breakdown /using-agent-skills

Chào em, tiếp nối dự án Neiro-Stock-VN, anh muốn nâng cấp năng lực quản trị rủi ro danh mục lên quy mô Quỹ Đầu Tư thông qua Module: Bộ Lọc Thanh Khoản & Sức Chứa Danh Mục (Liquidity & Capacity Sizer).

YÊU CẦU ĐẶC TẢ CHI TIẾT:
1. Xây dựng Module Liquidity Sizer (src/risk_engine/liquidity_sizer.py):
   - Bộ lọc ADTV20 (Average Daily Trading Value 20 phiên): Giới hạn chỉ chọn cổ phiếu có giá trị giao dịch trung bình 20 ngày >= 15 - 30 tỷ đồng/phiên. Loại bỏ hoàn toàn cổ phiếu thanh khoản mỏng dễ bị kẹp hàng khi thị trường biến động.
   - Mô hình Sức chứa Danh mục (Portfolio Capacity Model): Giới hạn tỷ trọng mua của 1 vị thế không được vượt quá 10% - 15% khối lượng giao dịch trung bình ngày của cổ phiếu đó để đảm bảo thoát hàng an toàn trong chu kỳ T+2.5.
2. Mô hình Ước lượng Trượt giá (Slippage Model):
   - Tính toán hàm trượt giá phi tuyến: Slippage (%) = k * (Order_Size / ADTV20)^alpha dựa trên độ dày sổ lệnh (Order Book Depth) và chênh lệch Spread Bid/Ask.
   - Cảnh báo trực tiếp trên Terminal khi quy mô lệnh vượt ngưỡng chịu đựng của cổ phiếu.
3. Tích hợp vào Pipeline Quét Fialda:
   - Gắn điểm thanh khoản và cột "Khối Lượng Mua Tối Đa Khuyến Nghị" vào bảng Top 20 trên Terminal HTML và báo cáo Markdown.
4. Kiểm thử & Tiêu chuẩn chất lượng:
   - Viết unit test tests/test_liquidity_sizer.py bao phủ toàn bộ các ngưỡng biên và kiểm tra tính toán toán học.
   - Đảm bảo toàn bộ test suite pass, repo duy trì < 15MB, cập nhật đầy đủ docs/spec.md.
```

---

## 3. PROMPT PHIÊN 3: MODULE KIỂM ĐỊNH QUÁ KHỨ (WALK-FORWARD BACKTESTING T+2.5)
*(Sao chép nguyên khối bên dưới vào phiên mới)*

```markdown
/goal /planning-and-task-breakdown /using-agent-skills

Chào em, tiếp nối dự án Neiro-Stock-VN, anh muốn xây dựng Module Kiểm Định Quá Khứ (Walk-Forward Backtesting Engine) cho hệ thống Quantamental Neiro-Stock-VN.

YÊU CẦU ĐẶC TẢ CHI TIẾT:
1. Xây dựng Backtest Engine (src/backtesting/engine.py):
   - Chạy mô phỏng lại các tín hiệu mua của hệ thống (Piotroski F-Score >= 7 + CAMEL Tier A + OFI dương + Breakout Volume) trên dữ liệu các cổ phiếu VN30 và Midcap từ 2021 đến nay.
   - Ràng buộc thực tế khắc nghiệt của TTCK Việt Nam:
     + Bắt buộc mô hình hóa độ trễ thanh toán T+2.5 (cổ phiếu chỉ được phép bán từ chiều ngày T+2).
     + Giới hạn biên độ trần/sàn theo sàn giao dịch (HOSE 7%, HNX 10%, UPCoM 15%).
     + Phí giao dịch (0.15%) và thuế bán chứng khoán (0.1%).
2. Hệ thống Thước đo Hiệu suất (Performance Metrics Suite):
   - Tỷ lệ thắng (Win Rate %) và Tỷ lệ Lời/Lỗ (Profit Factor).
   - Tăng trưởng kép hàng năm (CAGR %).
   - Hệ số Sharpe Ratio và Sortino Ratio (đo lường lợi nhuận trên độ rủi ro).
   - Mức sụt giảm tài sản tối đa (Maximum Drawdown - MDD).
3. Xuất Báo Cáo Trực Quan:
   - Tự động sinh biểu đồ đường cong vốn (Equity Curve) so sánh đối chiếu với chỉ số VN-Index (Benchmark).
   - Xuất báo cáo hiệu suất dưới dạng Markdown reports/backtest_results.md và tích hợp tab xem kết quả trên Web Terminal.
4. Kiểm thử & Tiêu chuẩn chất lượng:
   - Viết unit test tests/test_backtest_engine.py kiểm tra tính toàn vẹn toán học và các trường hợp biên.
   - Duy trì Zero-Waste Mandate (< 15MB) và cập nhật tài liệu docs/spec.md.
```
