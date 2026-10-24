# Cẩm Nang Tác Chiến Định Lượng TTCK Việt Nam (Trader Playbook)
> Dành cho Nhà Giao Dịch Chuyên Nghiệp & Quản Lý Quỹ tại Thị Trường Chứng Khoán Việt Nam.

---

## 1. Setup 1: Gom Hàng Tại Point of Control (POC Accumulation & Absorption)

### Bối cảnh thị trường
- Cổ phiếu cơ bản tốt (Piotroski F-Score $\ge 7$, tăng trưởng EPS cốt lõi $\ge 15\%$, định giá P/E Percentile $< 35\%$).
- Cổ phiếu đang tích lũy trong vùng High Volume Node (HVN) với mức giá Point of Control (POC) rõ ràng trên Volume Profile 20-40 phiên.

### Điều kiện kích hoạt vào lệnh (Entry Checklist)
1. **Kiểm tra hấp thụ:** Giá kiểm định lại POC và rút chân với Volume cạn kiệt, không bị thủng Value Area Low (VAL).
2. **Dòng tiền chủ động:** $OFI > +0.20$ (lệnh mua chủ động bắt đầu chiếm ưu thế).
3. **Smart Money Confluence:** Khối ngoại hoặc Tự doanh liên tục mua ròng tại vùng giá này ít nhất 3 phiên liên tiếp.
4. **Vị thế T+2.5:** Đảm bảo giải ngân theo từng đợt (Thăm dò $30\%$ vốn, gia tăng $70\%$ khi có xác nhận bứt phá).

### Quản trị vị thế
- **Stop Loss:** Đặt ngay dưới biên dưới $VAL - 1.5\times ATR$ (thường khoảng $-3.5\% \text{ đến } -5.0\%$).
- **Target 1:** Value Area High (VAH).
- **Target 2:** Vùng High Volume Node của chu kỳ phân phối trước đó.

---

## 2. Setup 2: Pocket Pivot Bứt Phá Vùng Chân Không Thanh Khoản (LVN Vacuum Runner)

### Bối cảnh thị trường
- Cổ phiếu bứt phá ra khỏi nền tích lũy hoặc mẫu hình VCP (Volatility Contraction Pattern).
- Phía trên mức giá hiện tại là một khoảng Low Volume Node (LVN / Air Pocket) rộng lớn, nơi khối lượng giao dịch tích lũy trước đó rất mỏng.

### Điều kiện kích hoạt vào lệnh
1. **Khối lượng bùng nổ:** Khối lượng phiên sáng (đến 11:30) đã đạt $\ge 80\%$ khối lượng trung bình 20 phiên.
2. **Lệnh lớn cá mập:** Xuất hiện chuỗi lệnh khớp lô lớn $\ge 100,000$ cp ăn thẳng vào các bước giá dư bán.
3. **Slicing Runner Trigger:** Giá vượt qua cạnh trên của HVN và bắt đầu tiến vào LVN.

### Chiến thuật hành động
- **CẤM ĐẶT LỆNH BÁN GIỚI HẠN SỚM:** Vì trong vùng LVN, giá sẽ trôi cực nhanh (chạy trần cứng hoặc tăng $5-7\%$ rất dứt khoát do không có lượng cung kẹp hàng đối ứng).
- Nắm giữ vị thế để dòng tiền đẩy hết biên độ của Air Pocket tới ngưỡng kháng cự HVN tiếp theo mới cân nhắc chốt lời từng phần.

---

## 3. Setup 3: Bẫy Kéo Trụ Đạp Midcap & Phân Kỳ Dòng Tiền (Breadth Trap)

### Bối cảnh thị trường
- Chỉ số VN-Index hoặc VN30 xanh điểm nhẹ ($+3$ đến $+6$ điểm) nhưng số mã giảm giá áp đảo hoàn toàn số mã tăng giá (Độ rộng thị trường Advance/Decline $< 0.40$).
- Dòng tiền chỉ tập trung kéo cục bộ 1-2 cổ phiếu vốn hóa lớn (ví dụ VCB, VIC, VHM, BID) để neo chỉ số, trong khi các dòng cổ phiếu thị trường (Bất động sản, Thép, Chứng khoán) bị bán tháo ngầm.

### Dấu hiệu định lượng
- $Basis VN30F1M$ âm sâu ($< -7.0$ điểm) cho thấy phe tay to đang Short phòng thủ mạnh trên phái sinh.
- Chỉ số phân kỳ dòng tiền cá mập $SMDI < 0$.

### Hành động tác chiến
- **CẤM BẮT ĐÁY:** Tuyệt đối không giải ngân mua mới cổ phiếu Midcap/Smallcap vì nguy cơ sau phiên kéo trụ sẽ là phiên xả lũ đồng loạt.
- **Hạ tỷ trọng Margin về 0:** Đưa tài khoản về trạng thái an toàn tiền mặt $\ge 50-70\%$.

---

## 4. Setup 4: Chiến Thuật Lướt T+0 Hạ Giá Vốn Trên Danh Mục Sẵn Có (Rolling Inventory)

### Điều kiện tiên quyết
- Nhà đầu tư **bắt buộc đã có sẵn một lượng cổ phiếu T+0** trong tài khoản (ví dụ có sẵn 10,000 cp HPG).

### Kịch bản thực thi
1. **Buổi sáng (ATO hoặc đầu phiên sáng):** Thị trường gặp tin tức xấu hoảng loạn mở Gap giảm mạnh về ngay ngưỡng hỗ trợ cứng POC hoặc đáy hoảng loạn trước đó.
2. **Mua bổ sung:** Giải ngân mua thêm $3,000 - 5,000$ cp tại vùng hoảng loạn khi $OFI$ bắt đầu có tín hiệu rút chân đảo chiều.
3. **Bán trả hàng trong phiên (T+0):** Đến đầu phiên chiều hoặc ATC, khi thị trường hồi phục theo quán tính bật tăng $+2.5\% \text{ đến } +4\%$, lập tức bán ngay đúng $3,000 - 5,000$ cp sẵn có trong danh mục.
4. **Kết quả:** Tổng số lượng cổ phiếu nắm giữ dài hạn không đổi, nhưng hạ được giá vốn danh mục từ $1.5\% - 3.0\%$ ngay trong ngày mà không bị rủi ro giam vốn T+2.5.

---

## 5. Setup 5: Phòng Hộ Bằng Phái Sinh VN30F1M Khi VN-Index Gãy Cản

### Bối cảnh
- Nhà đầu tư đang nắm giữ danh mục cổ phiếu cơ sở giá trị 1 tỷ VND nhưng toàn bộ hoặc một phần vừa mới mua ở T+0, T+1 (chưa đủ điều kiện bán theo quy chế T+2.5).
- Thị trường bất ngờ có biến cố địa chính trị hoặc vĩ mô, VN-Index gãy thủng ngưỡng hỗ trợ MA20 và POC lớn của thị trường chung.

### Công thức tính lệnh Short phòng hộ
$$N_{\text{HĐ Short}} = \text{Round}\left( \frac{\text{Giá trị Danh mục} \times \beta_{\text{Danh mục}}}{\text{Điểm số VN30F1M} \times 100,000 \text{ VND}} \right)$$
- Ví dụ: Danh mục 1 tỷ VND, $\beta = 1.2$, VN30F1M ở mức 1,300 điểm:
  $$N_{\text{HĐ Short}} = \frac{1,000,000,000 \times 1.2}{1,300 \times 100,000} = \frac{1,200,000,000}{130,000,000} \approx 9 \text{ Hợp Đồng VN30F1M}$$
- Mở ngay vị thế **Short 9 HĐ VN30F1M**. Lợi nhuận từ vị thế Short phái sinh sẽ bù đắp toàn bộ mức sụt giảm của danh mục cơ sở trong thời gian chờ cổ phiếu về tài khoản ở chu kỳ T+2.5!
