# ADR-003: Bộ Lọc Thanh Khoản & Mô Hình Sức Chứa Danh Mục (Liquidity & Capacity Sizer) Cho Quy Mô Quỹ

## 1. Trạng Thái (Status)
Đã duyệt (Approved) - Ngày: 2026-10-24

## 2. Bối Cảnh (Context)
Trong quản trị quỹ đầu tư định chế tại Thị trường Chứng khoán Việt Nam (TTCK VN), thanh khoản là yếu tố sống còn do ràng buộc **chu kỳ thanh toán T+2.5**:
1. **Rủi ro kẹp hàng thanh khoản mỏng (Illiquidity Trap):** Các cổ phiếu vốn hóa nhỏ (Penny) hoặc thanh khoản thấp (< 15 tỷ đồng/phiên) rất dễ bị tắc nghẽn lệnh sàn khi thị trường biến động mạnh, khiến nhà đầu tư không thể bán cắt lỗ.
2. **Tác động trượt giá phi tuyến (Nonlinear Market Impact & Slippage):** Khi quy mô quỹ lớn giải ngân vào một mã cổ phiếu, việc đặt lệnh vượt quá độ dày của sổ lệnh (Order Book Depth) sẽ đẩy giá khớp trung bình lên cao (trượt giá mua) và dìm giá khớp xuống thấp khi bán (trượt giá bán).
3. **Giới hạn tỷ lệ tham gia thị trường (Participation Rate Limit):** Một lệnh giải ngân trong phiên không được vượt quá 10% - 15% khối lượng giao dịch trung bình ngày (ADV20) để đảm bảo thời gian thanh lý toàn bộ vị thế không vượt quá 1 phiên giao dịch ($ExitDays \le 1.0$), tương thích với yêu cầu phòng vệ rủi ro T+2.5.

## 3. Quyết Định Kiến Trúc (Decision)
1. **Xây Dựng Module `src/risk_engine/liquidity_sizer.py`:**
   - **Bộ lọc $ADTV20$ (Average Daily Trading Value 20 phiên):**
     $$\text{ADTV20} = \frac{1}{20} \sum_{t=1}^{20} (\text{Close}_t \times \text{Volume}_t)$$
     - $\text{ADTV20} \ge 30.0$ tỷ đồng/phiên: Đạt chuẩn Quỹ Định Chế (Institutional Grade).
     - $15.0 \le \text{ADTV20} < 30.0$ tỷ đồng/phiên: Đạt chuẩn Biên (Borderline Liquid), kiểm soát chặt quy mô lệnh.
     - $\text{ADTV20} < 15.0$ tỷ đồng/phiên: Loại bỏ hoàn toàn khỏi danh mục giải ngân của Quỹ.
   - **Mô Hình Sức Chứa Danh Mục (Portfolio Capacity Model):**
     $$\text{ADV20} = \frac{\text{ADTV20}}{\text{Current Price}}$$
     $$\text{Max Shares Capacity} = \left\lfloor \frac{\text{ADV20} \times P_{\max}}{100} \right\rfloor \times 100$$
     Với $P_{\max} \in [10\%, 15\%]$, làm tròn xuống bội số của lô 100 cổ phiếu (quy chuẩn HOSE/HNX).
   - **Mô Hình Ước Lượng Trượt Giá Phi Tuyến (Nonlinear Slippage Model):**
     Dựa trên mô hình vi cấu trúc thị trường Almgren-Chriss / Square-Root Law:
     $$\text{Slippage} (\%) = \text{Spread}_{\text{bid-ask}} + k \cdot \left( \frac{\text{Order Shares}}{\text{ADV20}} \right)^\alpha$$
     với $k = 2.5$, $\alpha = 0.60$ (độ lồi sổ lệnh thực tế tại TTCK VN).
     - Cảnh báo `CRITICAL_OVER_CAPACITY` nếu $\frac{\text{Order Shares}}{\text{ADV20}} > 15\%$.
     - Cảnh báo `HIGH_SLIPPAGE` nếu $\text{Slippage} \ge 1.50\%$.
   - **Hệ Thống Chấm Điểm Thanh Khoản (Liquidity Score 0 - 100):**
     Phân tầng từ Siêu thanh khoản ($\ge 100$ tỷ: 90-100 điểm) đến Thanh khoản dưới chuẩn (< 15 tỷ: < 60 điểm).

2. **Tích Hợp Vào Pipeline Quét Fialda & Tactical Web Terminal:**
   - Bổ sung các chỉ số `adtv20_billion`, `adv20_shares`, `max_shares_capacity`, `liquidity_score`, `slippage_est_pct` vào `FialdaCandidate`.
   - Lọc bỏ tự động các mã không đạt ngưỡng ADTV20 tối thiểu 15 tỷ đồng/phiên.
   - Hiển thị cột `ADTV20 (Tỷ)`, `Điểm TK`, `KL Mua Max (Sức Chứa)`, và `Trượt Giá` trên cả Terminal HTML (`exports/index.html`) và báo cáo Markdown (`reports/latest_scan.md`).

3. **Kiểm Thử Toàn Diện (`tests/test_liquidity_sizer.py`):**
   - Kiểm tra 100% nghiệm biên, chuẩn hóa giá, tính đơn điệu của hàm trượt giá và quy tắc làm tròn lô 100.

## 4. Hệ Quả (Consequences)
- **Tích cực:** Nâng cấp năng lực quản trị rủi ro danh mục của Neiro-Stock-VN lên quy chuẩn Quỹ triệu USD; ngăn chặn triệt để rủi ro kẹt hàng và thiệt hại do trượt giá lớn trong chu kỳ thanh toán T+2.5.
- **Tuân thủ Zero-Waste:** Code tinh gọn, tính toán bằng công thức giải tích thuần túy (O(1)), không sinh cache hay dữ liệu rác, dung lượng repo giữ vững < 15MB.
