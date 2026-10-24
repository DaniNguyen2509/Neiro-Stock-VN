# HƯỚNG DẪN TÁC CHIẾN: LỘ TRÌNH PROMPT NÂNG CẤP "QUỸ TRIỆU ĐÔ"
> Tài liệu lưu trữ bộ Prompt định hướng nâng cấp hệ thống **Neiro-Stock-VN** cho các phiên làm việc độc lập kế tiếp, thuần định lượng (Pure Quantamental), không phụ thuộc ứng dụng bên thứ 3 (Telegram/Discord), tập trung tối đa vào **Web Terminal GitHub Pages** và **Quản trị rủi ro danh mục Quỹ**.

---

## 📌 Tổng Quan Lộ Trình Nâng Cấp Tinh Gọn

| Phiên | Mục Tiêu Chiến Thuật | Tệp Liên Quan | Độ Ưu Tiên |
| :--- | :--- | :--- | :--- |
| **Phiên 1** | **Bộ lọc Thanh khoản & Sức chứa Danh mục (Liquidity & Capacity Sizer)** | `src/risk_engine/liquidity_sizer.py`, `src/collector/fialda_scanner.py` | 🔴 **Ưu tiên 1 (Làm trước)** |
| **Phiên 2** | **Kiểm định Quá khứ (Walk-Forward Backtesting Engine T+2.5)** | `src/backtesting/engine.py`, `reports/backtest_results.md` | 🟡 **Ưu tiên 2** |
| **Phiên 3** | **Quản trị Rủi ro Động & Điểm Thoát Lệnh T+2.5 (Dynamic Risk-Reward & ATR Trailing Stop)** | `src/risk_engine/trailing_stop.py`, `src/hud/terminal.py` | 🟢 **Ưu tiên 3** |

---

## 1. PROMPT PHIÊN 1: BỘ LỌC THANH KHOẢN & SỨC CHỨA DANH MỤC (LIQUIDITY & CAPACITY SIZER)
*(Sao chép nguyên khối bên dưới vào phiên mới)*

```markdown
/goal /planning-and-task-breakdown /using-agent-skills

Chào em, tiếp nối dự án Neiro-Stock-VN tại repository này, anh muốn nâng cấp năng lực quản trị rủi ro danh mục lên quy mô Quỹ Đầu Tư thông qua Module: Bộ Lọc Thanh Khoản & Sức Chứa Danh Mục (Liquidity & Capacity Sizer).

YÊU CẦU ĐẶC TẢ CHI TIẾT:
1. Xây dựng Module Liquidity Sizer (src/risk_engine/liquidity_sizer.py):
   - Bộ lọc ADTV20 (Average Daily Trading Value 20 phiên): Giới hạn chỉ chọn cổ phiếu có giá trị giao dịch trung bình 20 ngày >= 15 - 30 tỷ đồng/phiên. Loại bỏ hoàn toàn cổ phiếu thanh khoản mỏng dễ bị kẹp hàng khi thị trường biến động.
   - Mô hình Sức chứa Danh mục (Portfolio Capacity Model): Giới hạn tỷ trọng mua của 1 vị thế không được vượt quá 10% - 15% khối lượng giao dịch trung bình ngày của cổ phiếu đó để đảm bảo thoát hàng an toàn trong chu kỳ T+2.5.
2. Mô hình Ước lượng Trượt giá (Nonlinear Slippage Model):
   - Tính toán hàm trượt giá phi tuyến: Slippage (%) = k * (Order_Size / ADTV20)^alpha dựa trên độ dày sổ lệnh (Order Book Depth) và chênh lệch Spread Bid/Ask.
   - Cảnh báo trực tiếp trên Terminal khi quy mô lệnh vượt ngưỡng chịu đựng của cổ phiếu.
3. Tích hợp trực tiếp vào Pipeline Quét Fialda & Web Terminal:
   - Gắn điểm thanh khoản và cột "Khối Lượng Mua Tối Đa Khuyến Nghị" vào bảng Top 20 trên Terminal HTML (exports/index.html) và báo cáo Markdown (reports/latest_scan.md).
4. Kiểm thử & Tiêu chuẩn chất lượng:
   - Viết unit test tests/test_liquidity_sizer.py bao phủ toàn bộ các ngưỡng biên và kiểm tra tính toán toán học.
   - Đảm bảo toàn bộ test suite pass 100%, repo duy trì < 15MB, cập nhật đầy đủ docs/spec.md và docs/architecture.md.
```

---

## 2. PROMPT PHIÊN 2: MODULE KIỂM ĐỊNH QUÁ KHỨ (WALK-FORWARD BACKTESTING T+2.5)
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
3. Xuất Báo Cáo Trực Quan Lên Web Terminal:
   - Tự động sinh biểu đồ đường cong vốn (Equity Curve) so sánh đối chiếu với chỉ số VN-Index (Benchmark).
   - Tích hợp tab kết quả Backtest trực tiếp vào trang Web Terminal tĩnh exports/index.html hiển thị trên GitHub Pages.
4. Kiểm thử & Tiêu chuẩn chất lượng:
   - Viết unit test tests/test_backtest_engine.py kiểm tra tính toàn vẹn toán học và các trường hợp biên.
   - Duy trì Zero-Waste Mandate (< 15MB) và cập nhật tài liệu docs/spec.md.
```

---

## 3. PROMPT PHIÊN 3: QUẢN TRỊ RỦI RO ĐỘNG & ĐIỂM THOÁT LỆNH T+2.5 (DYNAMIC TRAILING STOP)
*(Sao chép nguyên khối bên dưới vào phiên mới)*

```markdown
/goal /planning-and-task-breakdown /using-agent-skills

Chào em, tiếp nối dự án Neiro-Stock-VN, anh muốn hoàn thiện Module Quản Trị Rủi Ro Động & Điểm Thoát Lệnh T+2.5 (Dynamic Trailing Stop & Risk-Reward Optimizer) cho các vị thế được gợi ý lướt sóng.

YÊU CẦU ĐẶC TẢ CHI TIẾT:
1. Xây dựng Module Trailing Stop (src/risk_engine/trailing_stop.py):
   - Tính toán ngưỡng Cắt Lỗ Cứng ban đầu (Initial Stop Loss) dựa trên ATR(14) và đáy nến gần nhất (Swing Low).
   - Cơ chế Khóa Lợi Nhuận Tự Động (Chandelier Exit / ATR Trailing Stop): Khi giá tăng vượt 1.5R hoặc 2R, tự động nâng Stop Loss lên điểm hòa vốn (Break-even) và bám sát theo biên độ biến động.
2. Tích hợp Ràng Buộc T+2.5:
   - Cảnh báo "Vùng Đóng Băng T+0 đến T+2": Trong khoảng thời gian hàng chưa về tài khoản, tính toán rủi ro qua biến động phái sinh VN30F1M để đánh giá mức độ phơi nhiễm (Exposure Risk).
3. Hiển thị Trực Quan trên Web Terminal:
   - Thêm cột Stop Loss, Take Profit 1 (Target R1), Take Profit 2 (Target R2), và Tỷ lệ R:R (Risk/Reward >= 1:2.5) vào bảng Top 20 trên giao diện Web GitHub Pages.
4. Kiểm thử & Tiêu chuẩn chất lượng:
   - Viết unit test tests/test_trailing_stop.py kiểm tra toàn bộ logic toán học.
   - Bảo đảm 100% test pass, repo < 15MB, cập nhật docs/spec.md.
```
