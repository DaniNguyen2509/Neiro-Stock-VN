# Từ Điển Thuật Ngữ Quantamental & Vi Cấu Trúc TTCK Việt Nam

Tài liệu này tổng hợp và đối chiếu các thuật ngữ định lượng (Quantitative) và phân tích cơ bản (Fundamental) ứng dụng thực chiến trong thị trường chứng khoán Việt Nam (HOSE, HNX, UPCoM, VN30F1M).

---

## 1. Cấu Trúc Vi Mô Sổ Lệnh & Khối Lượng (Market Microstructure & Volume)

### Point of Control (POC)
- **Định nghĩa:** Mức giá có tổng khối lượng cổ phiếu được giao dịch nhiều nhất trong một khoảng thời gian xác định (phiên, tuần hoặc tháng).
- **Ý nghĩa định chế:** Đây là mức giá "đồng thuận cao nhất" giữa phe Mua và phe Bán (Fair Value thực tế). Khi giá quay lại POC, nó đóng vai trò là một nam châm hút giá hoặc bệ đỡ hỗ trợ / kháng cự cực mạnh.

### Value Area (VA) - Vùng Giá Trị 70%
- Bao gồm $VAH$ (Value Area High - Biên trên) và $VAL$ (Value Area Low - Biên dưới).
- Chiếm đúng $70\%$ tổng khối lượng khớp lệnh của phiên. Nếu giá bứt phá ra ngoài VA và duy trì được thanh khoản, thị trường đang bước vào trạng thái mất cân bằng (Imbalance Trend).

### High Volume Nodes (HVN - Thành Trì Thanh Khoản)
- Các mức giá có khối lượng giao dịch đột biến cao vượt trội so với mức trung bình xung quanh.
- Là nơi dòng tiền lớn (Big Boys / Tay to) tích lũy hoặc hấp thụ (Absorption). Giá thường di chuyển chậm lại và phản ứng đảo chiều hoặc tích lũy đi ngang tại HVN.

### Low Volume Nodes (LVN / Air Pockets - Vùng Chân Không Thanh Khoản)
- Các khoảng giá có rất ít khối lượng giao dịch tích lũy.
- **Hiện tượng Slicing:** Khi giá đi vào vùng LVN, giá sẽ trượt cực nhanh (chạy như chân không) vì thiếu lệnh đối ứng, dẫn tới các cú rớt giá thảng thốt hoặc tăng tốc thần tốc (Gap / Fast Breakout).

### Order Flow Imbalance (OFI - Áp Lực Lệnh Chủ Động)
- Đo lường mức độ áp đảo giữa lệnh Mua chủ động (lệnh ăn thẳng vào giá Ask) và Bán chủ động (lệnh xả thẳng vào giá Bid).
- $OFI > +0.30$: Lực gom hàng chủ động quyết liệt.
- $OFI < -0.30$: Áp lực bán tháo thoát hàng quyết liệt.

### Large Block Orders (Lệnh Cá Mập Khớp Lô Lớn)
- Các lệnh khớp lệnh đơn lẻ có quy mô $\ge 100,000$ cổ phiếu hoặc giá trị $\ge 2$ tỷ VND trong một tích tắc. Thường phản ánh hành vi giải ngân hoặc chốt lời của các Quỹ đầu tư hoặc Tự doanh CTCK.

---

## 2. Dòng Tiền Thể Chế & Bối Cảnh Việt Nam (Smart Money & Domestic Institutional Flow)

### Khối Ngoại (Foreign Net Flow)
- Chênh lệch giá trị mua ròng hoặc bán ròng của các nhà đầu tư nước ngoài (bao gồm quỹ ETF như Fubon, Diamond, Vaneck, và các quỹ chủ động như Dragon Capital, VinaCapital).
- **Room Ngoại (Foreign Ownership Limit):** Tỷ lệ % tối đa NĐT nước ngoài được phép sở hữu (thường là $49\%$, hoặc $30\%$ với ngành Ngân hàng). Khi cổ phiếu "kín room", khối ngoại chỉ có thể mua thỏa thuận với mức chênh lệch (Premium).

### Khối Tự Doanh (Proprietary Trading)
- Hoạt động mua bán cổ phiếu của chính các công ty chứng khoán (SSI, HSC, VNDirect, VPBS, TCBS...).
- Tự doanh thường nắm giữ danh mục cơ sở lớn để tạo lập chứng quyền (CW) và thực hiện phòng hộ (Hedging) bằng cách Short trên thị trường phái sinh VN30F1M.

### Bán Giải Chấp (Force Sell & Margin Call)
- Hiện tượng công ty chứng khoán chủ động bán giải chấp cổ phiếu trong tài khoản của nhà đầu tư khi tỷ lệ ký quỹ thực tế rơi xuống dưới mức xử lý (thường là $< 0.30$).
- Khi thị trường giảm đồng loạt, Force Sell chéo (bán lan sang cả các cổ phiếu cơ bản tốt để bù margin) tạo ra các vùng bán tháo hoảng loạn cùng cực (Capitulation), là thời điểm vàng để Quant săn lùng các món hời định giá.

---

## 3. Phái Sinh Chỉ Số & Arbitrage (Derivatives VN30F1M)

### Basis Phái Sinh
- Độ lệch điểm số: $\text{Basis} = \text{Điểm số VN30F1M} - \text{Chỉ số VN30 Index}$.
- **Contango (Basis > 0):** Giá phái sinh cao hơn cơ sở $\rightarrow$ Tâm lý hưng phấn, kỳ vọng thị trường đi lên.
- **Backwardation (Basis < 0):** Giá phái sinh thấp hơn cơ sở $\rightarrow$ Tâm lý thận trọng, phòng thủ. Khi Basis âm quá sâu ($-15$ đến $-25$ điểm), dễ kích hoạt hiện tượng "Short Squeeze" (kéo thốc các cổ phiếu trụ VN30 vào phiên ATC để ép đội Short phái sinh phải cắt lỗ).

### Arbitrage Phái Sinh - Cơ Sở (Cash and Carry)
- Khi Basis mở rộng bất thường ngoài biên độ chênh lệch chi phí vốn, các quỹ định chế kích hoạt thuật toán: Bán HĐTL VN30F1M và đồng thời Mua rổ 30 cổ phiếu VN30 để ăn chênh lệch Basis hội tụ khi đáo hạn.

---

## 4. Định Lượng Cơ Bản (Fundamental Quant)

### Piotroski F-Score (Thang điểm 0 - 9)
- Mô hình do Giáo sư Joseph Piotroski (Đại học Stanford) phát minh, đánh giá 9 tiêu chí sức khỏe tài chính: Khả năng sinh lời, Đòn bẩy tài chính & thanh khoản, Hiệu quả hoạt động.
- Điểm $\ge 7$: Doanh nghiệp tăng trưởng thực chất, bảng cân đối kế toán vững chắc.
- Điểm $\le 3$: Doanh nghiệp có dấu hiệu suy thoái tài chính nghiêm trọng.

### Tỷ Lệ Chất Lượng Lợi Nhuận (CFO / Net Income)
- So sánh giữa Dòng tiền thuần từ hoạt động kinh doanh ($CFO$) và Lợi nhuận sau thuế ($Net Income$).
- $CFO / Net Income > 1.0$: Lợi nhuận có tiền tươi thóc thật bảo trợ.
- $CFO / Net Income < 0.5$ hoặc âm: Lợi nhuận chỉ nằm trên giấy (phải thu khách hàng tăng vọt, nguy cơ trích lập dự phòng nợ xấu cao).

### P/E & P/B Historical Valuation Percentile Banding
- Đo lường mức độ đắt/rẻ của cổ phiếu so với chính lịch sử 3-5 năm của nó bằng phân vị thống kê ($0\% - 100\%$).
- Percentile $< 20\%$: Vùng chiết khấu sâu (Deep Value Discount).
- Percentile $> 80\%$: Vùng định giá quá nóng, dư địa tăng trưởng hẹp.

---

## 5. Luân Chuyển Ngành (Sector Rotation - RRG)

### Relative Rotation Graph (RRG)
- Biểu đồ xoay tua định lượng thể hiện tương quan sức mạnh giá ($RS\text{-Ratio}$) và gia tốc dòng tiền ($RS\text{-Momentum}$) của từng ngành so với chỉ số chung VN-Index.
- **Leading (Dẫn dắt):** Cả sức mạnh và gia tốc đều cao hơn thị trường.
- **Weakening (Suy yếu):** Sức mạnh còn cao nhưng gia tốc bắt đầu giảm.
- **Lagging (Tụt hậu):** Kém hơn thị trường toàn diện.
- **Improving (Cải thiện):** Bắt đầu có dòng tiền bắt đáy, chuẩn bị bứt phá vào chu kỳ dẫn dắt.
