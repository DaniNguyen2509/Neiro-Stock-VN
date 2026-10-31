# ADR-017: Lộ Trình Khắc Phục Điểm Mù Rủi Ro T+2.5, Chống Mua Đuổi & Định Cỡ Vị Thế Nhỏ Lẻ

## 1. Trạng thái (Status)
**Accepted** *(Đã triển khai & nghiệm thu toàn bộ 5 Giai đoạn tại [`docs/plans/RETAIL_T25_BLINDSPOT_REMEDIATION_PLAN.md`](../plans/RETAIL_T25_BLINDSPOT_REMEDIATION_PLAN.md) — `117 / 117` Unit & Integration Tests Passing 100%)*

## 2. Ngày lập (Date)
`2026-10-31`

## 3. Bối cảnh & Điểm mù phát hiện (Context)

Qua đợt kiểm định phản biện độc lập (`doubt-driven-development` kết hợp `multi-layer-dashboard-audit`) dưới góc nhìn **Nhà đầu tư cá nhân nhỏ lẻ Việt Nam** (`NAV 50 – 300 triệu VND`, Long-only cổ phiếu cơ sở, khởi đầu `0%` đệm hàng `T+0`, chịu ràng buộc lô tối thiểu `100 cp` HOSE và độ trễ thanh toán `T+2.5`), hệ thống ghi nhận **8 điểm mù trọng yếu** trên snapshot thực tế `2026-10-30`:

1. **Vùng mua tịnh tiến & Đứt gãy Sổ cái Anti-FOMO (`ADR-009` Isolation):** `fialda_scanner.py` tính lại vùng mua `cur_price * [0.98, 1.01]` mỗi 30 phút cho `19/20` mã. Do `signal_tracker.py` chạy ngầm tách biệt hoàn toàn với `terminal.py` và `latest_scan.md`, có **7/20 mã** đã bị ghi nhận `STOPPED_OUT` (`VIX`, `ORS`, `VSC`, `DIG`, `GEX`, `TCX`, `PNJ`) vẫn tiếp tục xuất hiện như khuyến nghị mua mới.
2. **Mù độ cao Pre-T0 & Đu đỉnh phân phối:** `18/20 mã (90%)` trong Top 20 mang hạng phân phối nặng nhất `Acc/Diss = E` (bao gồm `VIC` ở `239.70` với khối ngoại xả `-241.7 tỷ`) do `volume_profile.py` chưa nối vào vòng chấm điểm và chưa phạt điểm phân phối `D/E`.
3. **Ước lượng dòng tiền nội giả định:** `classify_dual_flow` nhân `abs(foreign_net) * 1.5` khi ngoại bán ròng khiến nhánh `RUI_RO_XA` trở thành dead code (`0%` kích hoạt) và tạo số liệu giả `+362.5 tỷ` nội gom khi ngoại xả `-241.7 tỷ`.
4. **Bỏ qua bộ lọc thanh khoản `ADTV20`:** Phép kẹp `max(..., 20.0)` trước ngưỡng kiểm tra `15.0 tỷ` khiến `100%` ứng viên luôn vượt qua bài kiểm tra thanh khoản.
5. **Cắt lỗ cứng `-3.0%` phi thực tế dưới `T+2.5`:** Truyền `swing_low = 0.98 * price` và `atr_14 = 0.035 * price` ép `20/20` mã về cùng mức `SL = -3.0%` (`TP1 = +4.5%`). Khi cổ phiếu kẹt `T+2.5`, mức lỗ cắt thực tế trượt xuống `-3.8%` đến `-9.7%`, làm đảo ngược tỷ lệ R:R thực nhận.
6. **Tê liệt Radar `T+2.5` & Hardcode Basis:** Không truyền độ rộng thị trường thực tế (`83 Tăng / 248 Giảm = 25.1%`) và Basis thực vào `evaluate_t25_exposure`, khiến `20/20` mã báo `T+0 (SAFE)` giữa phiên thị trường phân phối diện rộng; `terminal.py` hardcode `Basis = -3.30 ĐIỂM`; thiếu module `src/sector_engine/market_breadth.py`.
7. **Định cỡ vị thế Quỹ lệch chuẩn Nhỏ lẻ:** `position_sizer.py` thiếu trần tỷ trọng dẫn tới khuyến nghị `50% NAV`/mã, thiếu kiểm tra lô chẵn `100 cp` cho mã thị giá cao và mặc định nhà đầu tư có sẵn `>= 35%` hàng `T+0` hoặc Short được `VN30F1M`.
8. **Backtest thoát sàn ảo:** Điều kiện `price < band.floor_price` cho phép khớp bán `100%` khối lượng tại đúng giá sàn cứng (`price == floor_price`, trắng bên mua) vào chiều `T+2.5`.

---

## 4. Quyết định Kiến trúc Đề xuất (Proposed Decisions)

1. **Nâng cấp `ADR-009` — Hợp nhất Sổ cái `SignalTracker` lên Dashboard & Báo cáo Công khai:**
   - Thay đổi quyết định tách biệt ngầm của `ADR-009`: Neo cứng `Vùng Mua` trên Dashboard theo `entry_original` tại ngày bùng nổ gốc `T0`, chặn các mã đang `STOPPED_OUT` trong cửa sổ cooldown 3 phiên, và khóa trạng thái Bull-Trap bằng `max_favorable_pct (MFE)`.
2. **Kiểm soát Độ cao Pre-T0 thuần Vi cấu trúc (Không dùng chỉ báo trễ RSI/MACD):**
   - Tích hợp `Volume Profile (POC, VAL, VAH)` và khoảng cách chuẩn hóa theo `ATR(14)` trực tiếp vào `scan_top_rockets` (chỉ tính trên Top 35–40 ứng viên sơ loại để bảo toàn tốc độ `< 25s`), phạt/loại bỏ tổ hợp phân phối `Acc/Diss = D/E` và khôi phục nhánh `RUI_RO_XA` trung thực.
3. **Chuẩn hóa Cắt lỗ cấu trúc `T+2.5` & Cầu chì Độ rộng Thị trường (`market_breadth.py`):**
   - Mở biên SL cấu trúc theo `ATR(14)` thực tế và hỗ trợ `VAL` (`-4.5%` đến `-7.5%`) đảm bảo sống sót qua độ nhiễu 2.5 ngày và giữ `Net R:R >= 1:1.8` sau `0.40%` phí thuế.
   - Bổ sung `src/sector_engine/market_breadth.py` và nối Basis sống để kích hoạt cầu chì `PAUSE_NEW_BUYING` khi độ rộng thị trường `< 35%`.
4. **Hồ sơ Quản trị Vốn Nhỏ lẻ (`Retail Cold-Start Profile`):**
   - Áp trần `max_position_pct <= 20% NAV`/mã khi `0%` đệm `T+0`, `0% Margin` trên hàng chờ về, kiểm tra tính khả thi chia lệnh theo lô `100 cp` HOSE.
5. **Mô hình hóa Khóa Sàn (`Floor-Lock`) trong `T25BacktestEngine`:**
   - Chặn khớp bán khi `price <= band.floor_price + 1e-4` và kiểm tra chạm SL qua `bar.low` / Gap-Down ngày hàng về.

---

## 5. Các Phương án Đã Cân nhắc (Alternatives Considered)

- **Phương án A (Bị từ chối): Dùng chỉ báo RSI(14) > 70 hoặc Stochastic > 80 để chặn mua giá cao.**
  - *Lý do từ chối:* Vi phạm trực tiếp Luật bất di bất dịch Mục 3.2 của `Neiro-Stock-VN` (cấm dùng chỉ báo dao động trễ đơn lẻ đoán đỉnh đáy; siêu cổ phiếu chân sóng thực sự thường giữ RSI > 70 nhiều tuần liên tiếp). Dùng khoảng cách tới `Volume Profile POC/VAL` theo bội số `ATR(14)` kết hợp hạng phân phối `Acc/Diss` phản ánh chính xác bản chất cung cầu định chế.
- **Phương án B (Bị từ chối): Giữ nguyên Sổ cái `SignalTracker` chạy ngầm theo `ADR-009` để bảng Top 20 luôn có 20 mã "tươi mới".**
  - *Lý do từ chối:* Gây thiệt hại trực tiếp cho nhà đầu tư cá nhân chỉ xem Dashboard GitHub Pages khi vô tình mua phải mã đã gãy SL hoặc đã trượt xa nền `T0`.
- **Phương án C (Được chọn): Triển khai theo 5 Giai đoạn độc lập kèm Ma trận Đối chiếu Trước - Sau (`PLAN-2026-T25-RETAIL`).**
  - *Ưu điểm:* Khóa chặt số liệu hiện trạng trước khi sửa, kiểm thử độc lập từng tầng từ dữ liệu gốc -> rủi ro vĩ mô -> giao diện -> backtest, dễ dàng đo kiểm hiệu quả cải thiện.

---

## 6. Hệ quả Thực tế Sau Triển khai (Consequences)

- Toàn bộ 8 điểm mù (`BM-01`..`BM-08`) đã được khắc phục triệt để và đối chiếu định lượng Trước/Sau qua 12 chỉ số nghiệm thu trong [`docs/plans/RETAIL_T25_BLINDSPOT_REMEDIATION_PLAN.md`](../plans/RETAIL_T25_BLINDSPOT_REMEDIATION_PLAN.md).
- `ADR-017` chính thức kế thừa và nâng cấp `ADR-009`: Sổ cái [`SignalTracker`](../../src/risk_engine/signal_tracker.py) không còn chạy ngầm tách biệt mà đồng bộ trực tiếp lên Bảng Top 20 (`reports/latest_scan.md` và `exports/index.html`), khóa bất biến vùng mua gốc `T0`, chặn 100% mã đang `STOPPED_OUT` trong 3 phiên cooldown, khóa `BULL_TRAP_REJECT` theo `MFE`, kích hoạt cầu chì độ rộng thị trường `< 35%` qua [`market_breadth.py`](../../src/sector_engine/market_breadth.py) và trung thực hóa khóa sàn trắng bên mua (`Floor-Lock`) trên Tab 2 Walk-Forward.

