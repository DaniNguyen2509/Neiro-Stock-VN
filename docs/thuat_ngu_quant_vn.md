# Sổ Tay Thuật Ngữ & Công Thức Học Thuật Quantamental TTCK Việt Nam
> **Academic Quantamental Handbook & Market Microstructure Compendium**  
> Dành riêng cho hệ thống phân tích định lượng **Neiro-Stock-VN** (HOSE, HNX, UPCoM & Phái sinh VN30F1M).

---

## MỤC LỤC TỔNG QUAN

1. [Cấu Trúc Vi Mô Sổ Lệnh & Dòng Tiền (Order Flow & Microstructure)](#1-cấu-trúc-vi-mô-sổ-lệnh--dòng-tiền-order-flow--microstructure)
   - [Order Flow Imbalance (OFI) & Market Imbalance](#order-flow-imbalance-ofi--market-imbalance)
   - [Order Block (Khối Lệnh Thể Chế)](#order-block-khối-lệnh-thể-chế)
   - [Point of Control (POC) & Value Area (VA 70%)](#point-of-control-poc--value-area-va-70)
   - [High Volume Nodes (HVN) & Low Volume Nodes (LVN)](#high-volume-nodes-hvn--low-volume-nodes-lvn)
   - [Hiệu Ứng Dẫn Dắt - Trễ (Lead-Lag Effect)](#hiệu-ứng-dẫn-dắt---trễ-lead-lag-effect)
   - [Bất Đối Xứng Thông Tin & Chỉ Số PIN (Asymmetric Information)](#bất-đối-xứng-thông-tin--chỉ-số-pin-asymmetric-information)
2. [Mô Hình Đa Nhân Tố & Luân Chuyển Ngành (Multi-Factor & Macro Dynamics)](#2-mô-hình-đa-nhân-tố--luân-chuyển-ngành-multi-factor--macro-dynamics)
   - [Mô Hình Phân Rã Giá: Market + Sector + Company](#mô-hình-phân-rã-giá-market--sector--company)
   - [Động Lượng Chéo & Động Lượng Chuỗi Thời Gian (Momentum)](#động-lượng-chéo--động-lượng-chuỗi-thời-gian-momentum)
   - [Kinh Doanh Chênh Lệch Thống Kê & Cặp Đôi (Statistical Arbitrage & Pairs Trading)](#kinh-doanh-chênh-lệch-thống-kê--cặp-đôi-statistical-arbitrage--pairs-trading)
   - [Đặc Trưng Định Lượng (Quant Features in ML/Algo)](#đặc-trưng-định-lượng-quant-features-in-mlalgo)
   - [Chiến Lược Mua Bán & Sáp Nhập (M&A Arbitrage)](#chiến-lược-mua-bán--sáp-nhập-ma-arbitrage)
3. [Định Lượng Cơ Bản & Thuyết Giá Trị (Fundamental Quant & Valuation Models)](#3-định-lượng-cơ-bản--thuyết-giá-trị-fundamental-quant--valuation-models)
   - [Chiến Lược Net-Net của Benjamin Graham (NCAV)](#chiến-lược-net-net-của-benjamin-graham-ncav)
   - [Mô Hình Chiết Khấu Dòng Tiền (Discounted Cash Flow - DCF)](#mô-hình-chiết-khấu-dòng-tiền-discounted-cash-flow---dcf)
   - [Tỷ Số Tăng Trưởng Lợi Nhuận PEG (Peter Lynch PEG Ratio)](#tỷ-số-tăng-trưởng-lợi-nhuận-peg-peter-lynch-peg-ratio)
   - [Mô Hình Điểm Số Tài Chính Piotroski F-Score (Thang Điểm 0 - 9)](#mô-hình-điểm-số-tài-chính-piotroski-f-score-thang-điểm-0---9)
   - [Định Luật Benford & Kiểm Toán Gian Lận BCTC (Benford's Law)](#định-luật-benford--kiểm-toán-gian-lận-bctc-benfords-law)
   - [Chất Lượng Dòng Tiền & Dải Phân Vị PE/PB (Accrual & Percentile Banding)](#chất-lượng-dòng-tiền--dải-phân-vị-pepb-accrual--percentile-banding)
4. [Phái Sinh, Phòng Hộ & Cơ Chế Thanh Toán T+2.5](#4-phái-sinh-phòng-hộ--cơ-chế-thanh-toán-t25)
   - [Basis Phái Sinh & Hiện Tượng Ép Trụ Đáo Hạn](#basis-phái-sinh--hiện-tượng-ép-trụ-đáo-hạn)
   - [Quản Trị Rủi Ro Đệm Hàng Sẵn Có (Rolling Inventory T+0)](#quản-trị-rủi-ro-đệm-hàng-sẵn-có-rolling-inventory-t0)

---

## 1. CẤU TRÚC VI MÔ SỔ LỆNH & DÒNG TIỀN (ORDER FLOW & MICROSTRUCTURE)

### Order Flow Imbalance (OFI) & Market Imbalance
- **Bản chất học thuật:** Sự mất cân bằng giữa luồng lệnh mua chủ động (Aggressive Buy / Market Orders) và bán chủ động (Aggressive Sell) tác động trực tiếp lên độ trượt giá (Price Impact).
- **Công thức chuẩn mực Cartea & Jaimungal (2014):**
  $$OFI_t = I_{\{P_{b,t} \ge P_{b,t-1}\}} \cdot q_{b,t} - I_{\{P_{b,t} \le P_{b,t-1}\}} \cdot q_{b,t-1} - \left(I_{\{P_{a,t} \le P_{a,t-1}\}} \cdot q_{a,t} - I_{\{P_{a,t} \ge P_{a,t-1}\}} \cdot q_{a,t-1}\right)$$
- **Công thức khớp lệnh chủ động thực chiến tại sàn HOSE/HNX:**
  $$OFI_{\text{trade}} = \frac{V_{\text{buy\_active}} - V_{\text{sell\_active}}}{V_{\text{buy\_active}} + V_{\text{sell\_active}}}$$
  * $OFI > +0.30$: Áp lực gom lệnh chủ động vượt trội $\rightarrow$ Đà tăng tiếp diễn.
  * $OFI < -0.30$: Áp lực bán tháo chủ động xả thẳng vào dư mua $\rightarrow$ Nguy cơ thủng nền giá.

### Order Block (Khối Lệnh Thể Chế)
- **Định nghĩa:** Vùng giá mà các tổ chức tài chính lớn (Market Makers, Quỹ đầu tư) tích lũy một lượng lệnh chờ khớp (Limit Orders) khổng lồ trước khi đẩy giá bứt phá.
- **Phân loại:**
  * **Bullish Order Block:** Cụm nến giảm giá cuối cùng trước một nhịp tăng dốc phá vỡ cấu trúc (Break of Structure - BOS), để lại khoảng trống thanh khoản (Fair Value Gap - FVG).
  * **Bearish Order Block:** Cụm nến tăng giá cuối cùng trước một nhịp rơi mạnh phá vỡ hỗ trợ.
- **Liên hệ với Volume Profile:** Order Block trên biểu đồ thời gian chính là vùng hình thành **High Volume Node (HVN)** và **Point of Control (POC)** trên biểu đồ phân phối khối lượng. Khi giá kiểm định lại (Retest) Order Block, xác suất phản ứng bật nảy đảo chiều là cao nhất.

### Point of Control (POC) & Value Area (VA 70%)
- **Point of Control (POC):** Mức giá có tổng khối lượng khớp lệnh tích lũy cao nhất trong phiên hoặc khung thời gian nghiên cứu. Đại diện cho "Giá trị đồng thuận công bằng" (Fair Value).
- **Value Area (VA):** Vùng giá tập trung đúng $70\%$ tổng khối lượng giao dịch:
  * $VAH$ (Value Area High): Cận trên vùng giá trị.
  * $VAL$ (Value Area Low): Cận dưới vùng giá trị.
- **Chiến lược hành động:** Giá nằm trong VA biểu thị thị trường đang cân bằng (Market Balance / Consolidation). Khi giá bứt phá thoát ra ngoài VAH/VAL kèm OFI tăng vọt, thị trường kích hoạt xu hướng mất cân bằng (Imbalance Trend).

### High Volume Nodes (HVN) & Low Volume Nodes (LVN)
- **HVN (Thành trì thanh khoán):** Vùng đỉnh khối lượng nhô cao. Là nơi dòng tiền lớn hấp thụ và tích lũy. Giá di chuyển chậm lại khi tiến vào HVN.
- **LVN / Air Pockets (Vùng chân không thanh khoản):** Vùng thung lũng khối lượng trũng sâu. Khi giá xâm nhập vào LVN, do thiếu vắng lệnh đối ứng cản đường, giá sẽ xảy ra hiện tượng **Slicing (trượt giá cực nhanh)**, hình thành các cây nến thân dài hoặc khoảng trống giá (Gap).

### Hiệu Ứng Dẫn Dắt - Trễ (Lead-Lag Effect)
- **Khái niệm:** Hiện tượng một tài sản hoặc chỉ số (Leader) phản ánh thông tin mới và di chuyển trước, kéo theo tài sản khác (Laggard) di chuyển theo sau với một độ trễ thời gian $\tau$.
- **Mô hình Tương quan chéo (Cross-Correlation Function - CCF):**
  $$\rho_{XY}(\tau) = \frac{\mathbb{E}\left[(X_t - \mu_X)(Y_{t+\tau} - \mu_Y)\right]}{\sigma_X \sigma_Y}$$
  Nếu $\rho_{XY}(\tau)$ đạt giá trị cực đại tại $\tau > 0$, chuỗi $X$ dẫn dắt chuỗi $Y$ với độ trễ $\tau$ chu kỳ.
- **Ứng dụng thực chiến tại TTCK Việt Nam:**
  1. **Phái sinh dẫn dắt cơ sở:** Giá hợp đồng tương lai VN30F1M thường biến động khám phá giá (Price Discovery) trước chỉ số VN30 Index và VN-Index từ $15$ giây đến $2$ phút.
  2. **Cổ phiếu đầu ngành dẫn dắt (Sector Leader):** Cổ phiếu vốn hóa lớn đầu ngành (ví dụ VCB nhóm Ngân hàng, HPG nhóm Thép, SSI nhóm Chứng khoán, FPT nhóm Công nghệ) thường phát tín hiệu bứt phá hoặc gãy nền trước các cổ phiếu Mid-Cap cùng ngành từ $0.5$ đến $1$ phiên.

### Bất Đối Xứng Thông Tin & Chỉ Số PIN (Asymmetric Information)
- **Bản chất:** Thị trường tài chính luôn tồn tại sự phân hóa thông tin giữa các nhóm tham gia (Mô hình Kyle 1985 & Glosten-Milgrom 1985):
  * **Informed Traders (Nhà đầu tư có thông tin):** Nắm bắt trước số liệu kinh doanh, thương vụ M&A, chính sách tín dụng nội bộ.
  * **Uninformed / Noise Traders (Nhà đầu tư cá nhân nhỏ lẻ):** Giao dịch dựa trên tin tức đại chúng đã trễ hoặc cảm xúc FOMO/hoảng loạn.
  * **Market Makers (Nhà tạo lập):** Cung cấp thanh khoản và liên tục điều chỉnh chênh lệch giá Bid-Ask để phòng ngừa rủi ro bị "ăn thịt" bởi Informed Traders.
- **Xác suất Giao dịch có Thông tin (Probability of Informed Trading - PIN):**
  $$PIN = \frac{\alpha \mu}{\alpha \mu + 2\epsilon}$$
  * $\alpha$: Xác suất xảy ra sự kiện thông tin bất đối xứng.
  * $\mu$: Tần suất đặt lệnh của nhóm có thông tin (Informed).
  * $\epsilon$: Tần suất đặt lệnh ngẫu nhiên của nhóm không có thông tin (Noise).
- **Ứng dụng Quant:** Khi $PIN$ tăng vọt hoặc chênh lệch Bid-Ask Spread giãn rộng bất thường, cổ phiếu chuẩn bị đón nhận thông tin biến động cực lớn.

---

## 2. MÔ HÌNH ĐA NHÂN TỐ & LUÂN CHUYỂN NGÀNH (MULTI-FACTOR & MACRO DYNAMICS)

### Mô Hình Phân Rã Giá: Market + Sector + Company
- **Bản chất:** Giá và lợi suất của một cổ phiếu niêm yết không biến động ngẫu nhiên đơn lẻ mà được phân rã trực giao thành 3 tầng nhân tố cốt lõi:
  $$\text{Stock Return} = \text{Market Component} + \text{Sector Component} + \text{Company Idiosyncratic Component}$$
- **Phương trình Hồi quy Đa nhân tố (Multi-Factor Linear Regression):**
  $$R_{i,t} = \alpha_i + \beta_{i,m} R_{m,t} + \beta_{i,s} R_{s,t} + \epsilon_{i,t}$$
  Trong đó:
  * $R_{i,t}$: Lợi suất của cổ phiếu $i$ tại ngày $t$.
  * $R_{m,t}$: Lợi suất của thị trường chung (VN-Index) $\rightarrow$ Đo lường tác động vĩ mô, lãi suất, tỷ giá.
  * $\beta_{i,m}$: Hệ số nhạy cảm của cổ phiếu với thị trường chung (Market Beta).
  * $R_{s,t}$: Lợi suất rổ ngành $s$ tương ứng (đã loại bỏ tương quan thị trường) $\rightarrow$ Đo lường sóng ngành.
  * $\beta_{i,s}$: Hệ số nhạy cảm với ngành (Sector Beta).
  * $\alpha_i$: Lợi suất vượt trội do chất lượng nội tại doanh nghiệp (Alpha đặc thù).
  * $\epsilon_{i,t}$: Phần dư biến động ngẫu nhiên riêng lẻ (Idiosyncratic Residual Risk, $\mathbb{E}[\epsilon] = 0$).
- **Phân rã Rủi ro Phương sai:**
  $$\sigma_i^2 = \beta_{i,m}^2 \sigma_m^2 + \beta_{i,s}^2 \sigma_s^2 + \sigma_{\epsilon_i}^2$$
  * Trên TTCK Việt Nam: Biến động thị trường chung ($\beta_m$) chiếm khoảng $45-50\%$, sóng ngành ($\beta_s$) chiếm $25-30\%$, và yếu tố nội tại ($\alpha, \epsilon$) chiếm $20-25\%$.

### Động Lượng Chéo & Động Lượng Chuỗi Thời Gian (Momentum)
- **Cross-Sectional Momentum (Jegadeesh & Titman 1993):**
  * Lựa chọn top các cổ phiếu có hiệu suất vượt trội so với toàn sàn trong chu kỳ quá khứ (thường dùng $MOM(12, 1)$ - tính 12 tháng trước bỏ qua tháng gần nhất để tránh hiệu ứng đảo chiều ngắn hạn):
    $$MOM_{i,t}(12, 1) = \frac{P_{i, t-1}}{P_{i, t-12}} - 1$$
- **Time-Series Momentum (Trend Following):**
  $$TSMOM_{i,t} = \text{sign}\left(R_{i, t-k \to t}\right) \times \frac{R_{i,t}}{\sigma_i}$$
- **Relative Rotation Graph (RRG Momentum):**
  * $RS\text{-Ratio}$: Đo lường sức mạnh tương đối của ngành so với VN-Index.
  * $RS\text{-Momentum}$: Đo gia tốc thay đổi của $RS\text{-Ratio}$.
  * Chu kỳ dịch chuyển: $\text{Improving} \rightarrow \text{Leading} \rightarrow \text{Weakening} \rightarrow \text{Lagging}$.

### Kinh Doanh Chênh Lệch Thống Kê & Cặp Đôi (Statistical Arbitrage & Pairs Trading)
- **Bản chất:** Khai thác tính chất đồng tích hợp (Cointegration) của hai cổ phiếu cùng ngành có tương quan cao (ví dụ: SSI vs VND, HPG vs HSG).
- **Mô hình Hồi quy Cặp đôi (Engle-Granger Two-Step):**
  $$Y_t = \alpha + \beta X_t + \epsilon_t$$
  Spread phần dư: $S_t = Y_t - \beta X_t$. Nếu kiểm định ADF (Augmented Dickey-Fuller) chứng minh $S_t$ là chuỗi dừng (Stationary), quá trình hồi quy về trung bình (Mean Reversion) được xác nhận.
- **Tính toán Điểm chuẩn hóa Z-Score:**
  $$Z_t = \frac{S_t - \mu_S}{\sigma_S}$$
- **Nguyên tắc giao dịch:**
  * Khi $Z_t > +2.0$: Cổ phiếu $Y$ đang quá đắt so với $X$ $\rightarrow$ Bán/Giảm tỷ trọng $Y$, Mua/Tăng tỷ trọng $X$.
  * Khi $Z_t < -2.0$: Cổ phiếu $Y$ đang quá rẻ so với $X$ $\rightarrow$ Mua $Y$, Giảm $X$.
  * Khi $Z_t \to 0$: Đóng toàn bộ vị thế khi spread co về giá trị trung bình.

### Đặc Trưng Định Lượng (Quant Features in ML/Algo)
- **Định nghĩa:** Các biến số đầu vào (Predictive Signals) được tiền xử lý và chuẩn hóa từ dữ liệu thị trường để cấp cho các mô hình định lượng và thuật toán xếp hạng cổ phiếu:
  1. **Price & Liquidity Features:** Lợi suất logarit, ATR(14) chuẩn hóa tỷ lệ %, Khối lượng tương đối $V_t / SMA_{20}(V)$, Chỉ số thanh khoản Amihud Illiquidity.
  2. **Microstructure Features:** Giá trị $OFI$, Tỷ lệ chênh lệch giá so với POC $(P - POC)/POC$, Tỷ lệ khối lượng trong Value Area, Tỷ lệ lệnh cá mập $\ge 100k$.
  3. **Fundamental Features:** Piotroski F-Score, CFO/NI, ROE, Tốc độ tăng trưởng Doanh thu/LNST cốt lõi, Phân vị PE/PB 3 năm.
  4. **Derivatives & Macro Features:** Điểm Basis $VN30F1M - VN30$, Giá trị mua ròng khối ngoại, Tỷ lệ đòn bẩy Margin thị trường.

### Chiến Lược Mua Bán & Sáp Nhập (M&A Arbitrage)
- **Merger Arbitrage (Kinh doanh chênh lệch M&A):**
  * Khi một doanh nghiệp công bố mua lại hoặc chào mua công khai cổ phiếu của công ty mục tiêu tại mức giá chào mua ấn định $P_{\text{offer}}$, thị giá trên sàn $P_{\text{market}}$ thường giao dịch thấp hơn $P_{\text{offer}}$ một khoảng chiết khấu (M&A Spread):
    $$\text{M\&A Spread} = \frac{P_{\text{offer}} - P_{\text{market}}}{P_{\text{market}}}$$
  * Khoảng bù spread phản ánh rủi ro thương vụ không hoàn tất (rủi ro pháp lý, cổ đông phủ quyết, hủy deal).
- **Tín hiệu định lượng nhận diện gom hàng M&A:**
  * Lệnh khớp thỏa thuận lô lớn liên tục tăng đột biến ở mức giá cố định.
  * Tỷ lệ sở hữu cô đặc nhanh chóng, thanh khoản trôi nổi tự do (Free-float) giảm mạnh.

---

## 3. ĐỊNH LƯỢNG CƠ BẢN & THUYẾT GIÁ TRỊ (FUNDAMENTAL QUANT & VALUATION MODELS)

### Chiến Lược Net-Net của Benjamin Graham (NCAV)
- **Bản chất triết lý:** Chiến lược siêu bảo thủ được Benjamin Graham đề xướng trong tác phẩm *Security Analysis (1934)*. Mua các doanh nghiệp có thị giá rẻ hơn cả giá trị thanh lý tài sản lưu động ngắn hạn sau khi đã thanh toán sạch toàn bộ nghĩa vụ nợ.
- **Công thức chuẩn mực học thuật:**
  $$\text{NCAV (Net Current Asset Value)} = \text{Tài sản ngắn hạn (Current Assets)} - \text{Tổng nợ phải trả (Total Liabilities)} - \text{Cổ phiếu ưu đãi}$$
  $$\text{NCAV per share} = \frac{\text{Current Assets} - \text{Total Liabilities}}{\text{Tổng số cổ phiếu đang lưu hành (Shares Outstanding)}}$$
- **Quy tắc Giải Ngân An Toàn của Graham (Margin of Safety 33.3%):**
  $$\text{Giá Thị Trường (Market Price)} < \frac{2}{3} \times \text{NCAV per share} = \frac{2}{3} \times \frac{\text{Current Assets} - \text{Total Liabilities}}{\text{Shares Outstanding}}$$
  > **Lưu ý đính chính công thức:** Trong công thức toán học tài chính, dấu giữa Tài sản ngắn hạn và Nợ phải là **DẤU TRỪ** (vì nợ là nghĩa vụ phải hoàn trả cho chủ nợ khi thanh lý, cổ đông chỉ được hưởng phần thặng dư dôi dư còn lại).

### Mô Hình Chiết Khấu Dòng Tiền (Discounted Cash Flow - DCF)
- **Bản chất:** Xác định Giá trị nội tại (Intrinsic Value) của doanh nghiệp bằng tổng giá trị hiện tại của toàn bộ dòng tiền thuần tự do sinh ra trong tương lai chiết khấu về thời điểm hiện tại.
- **Dòng tiền tự do cho Doanh nghiệp (FCFF - Free Cash Flow to Firm):**
  $$FCFF_t = EBIT_t \times (1 - t_c) + D\&A_t - CapEx_t - \Delta NWC_t$$
  * $EBIT(1 - t_c)$: Lợi nhuận trước lãi vay sau thuế (NOPAT).
  * $D\&A$: Khấu hao tài sản cố định và chi phí phân bổ (chi phí phi tiền mặt cộng lại).
  * $CapEx$: Chi phí đầu tư tài sản cố định (mua sắm nhà xưởng, máy móc).
  * $\Delta NWC$: Biến động vốn lưu động ròng ($\Delta \text{Tài sản ngắn hạn} - \Delta \text{Nợ ngắn hạn không chịu lãi}$).
- **Giá Trị Doanh Nghiệp (Enterprise Value - EV):**
  $$EV = \sum_{t=1}^{N} \frac{FCFF_t}{(1 + WACC)^t} + \frac{Terminal Value_N}{(1 + WACC)^N}$$
  Với Giá trị vĩnh viễn (Terminal Value) theo mô hình Gordon Growth:
  $$Terminal Value_N = \frac{FCFF_N \times (1 + g)}{WACC - g}$$
  ($WACC$: Chi phí sử dụng vốn bình quân, $g$: Tốc độ tăng trưởng dài hạn vĩnh viễn).
- **Giá Trị Cổ Phiếu Nội Tại (Intrinsic Price Per Share):**
  $$\text{Equity Value} = EV + \text{Tiền \& Đầu tư tài chính ngắn hạn} - \text{Tổng nợ vay (Debt)}$$
  $$\text{Giá trị nội tại 1 cổ phiếu} = \frac{\text{Equity Value}}{\text{Tổng số cổ phiếu lưu hành}}$$
- **Nguyên tắc đầu tư:** Chỉ mua khi:
  $$\text{Giá cổ phiếu thị trường} \le \text{Giá trị nội tại 1 cổ phiếu} \times (1 - \text{Margin of Safety})$$

### Tỷ Số Tăng Trưởng Lợi Nhuận PEG (Peter Lynch PEG Ratio)
- **Bản chất:** Hoàn thiện chỉ số P/E đơn thuần bằng cách đặt trong tương quan với tốc độ tăng trưởng lợi nhuận EPS của doanh nghiệp (Peter Lynch - *One Up On Wall Street*).
- **Công thức:**
  $$PEG = \frac{P/E}{G}$$
  Trong đó:
  * $P/E$: Hệ số Giá trên Lợi nhuận một cổ phiếu.
  * $G$: Tốc độ tăng trưởng EPS kép kỳ vọng hàng năm (được biểu thị bằng số nguyên %, ví dụ tăng trưởng $20\%$/năm thì $G = 20$).
- **Thang đo định giá của Peter Lynch:**
  * $PEG < 0.5$: Cổ phiếu bị định giá siêu rẻ so với tiềm năng tăng trưởng (Món hời kim cương).
  * $0.5 \le PEG \le 1.0$: Định giá hấp dẫn, an toàn để giải ngân.
  * $PEG = 1.0$: Định giá công bằng (Fair Value - tăng trưởng $20\%$ thì $P/E = 20$).
  * $PEG > 1.5 - 2.0$: Cổ phiếu bị thị trường định giá quá nóng, rủi ro điều chỉnh mạnh nếu tăng trưởng chững lại.
- **Công thức Giá trị Hợp lý Tương đối (Fair Price Target):**
  $$\text{Fair Price} = G \times EPS = \text{EPS Growth (\%)} \times EPS$$

### Mô Hình Điểm Số Tài Chính Piotroski F-Score (Thang Điểm 0 - 9)
Được phát triển bởi Giáo sư Joseph Piotroski (Stanford University, 2000). Đánh giá toàn diện 9 tiêu chí nhị phân ($1$ điểm nếu đạt, $0$ điểm nếu không đạt):

#### Nhóm 1: Khả năng Sinh Lời (Profitability - Tối đa 4 điểm)
1. **$F_1$ (ROA dương):** $ROA_t > 0 \rightarrow 1$, ngược lại $0$.
2. **$F_2$ (Dòng tiền kinh doanh dương):** $CFO_t > 0 \rightarrow 1$, ngược lại $0$.
3. **$F_3$ (Tăng trưởng ROA):** $ROA_t - ROA_{t-1} > 0 \rightarrow 1$, ngược lại $0$.
4. **$F_4$ (Chất lượng lợi nhuận - Accrual âm):** $CFO_t > NetIncome_t \rightarrow 1$ (tiền mặt thu về lớn hơn lợi nhuận ghi nhận trên sổ sách).

#### Nhóm 2: Đòn Bẩy & Thanh Khoản (Leverage & Liquidity - Tối đa 3 điểm)
5. **$F_5$ (Giảm đòn bẩy nợ dài hạn):** $Leverage_t < Leverage_{t-1} \rightarrow 1$ (với $Leverage = \text{Nợ dài hạn} / \text{Tổng tài sản}$).
6. **$F_6$ (Cải thiện thanh toán hiện hành):** $CurrentRatio_t > CurrentRatio_{t-1} \rightarrow 1$.
7. **$F_7$ (Không pha loãng cổ phiếu):** $Shares_t \le Shares_{t-1} \rightarrow 1$ (doanh nghiệp không in giấy phát hành thêm).

#### Nhóm 3: Hiệu Quả Hoạt Động (Operating Efficiency - Tối đa 2 điểm)
8. **$F_8$ (Mở rộng biên lợi nhuận gộp):** $GrossMargin_t > GrossMargin_{t-1} \rightarrow 1$.
9. **$F_9$ (Tăng vòng quay tài sản):** $AssetTurnover_t > AssetTurnover_{t-1} \rightarrow 1$ (sử dụng tài sản để tạo doanh thu hiệu quả hơn).

**Tổng điểm Piotroski:**
$$F\text{-Score} = \sum_{k=1}^{9} F_k \quad (0 \le F\text{-Score} \le 9)$$
* **$F \ge 7$ (Institutional Grade):** Doanh nghiệp có nền tảng cơ bản xuất sắc, sức khỏe tài chính lành mạnh.
* **$4 \le F \le 6$ (Neutral):** Doanh nghiệp trung bình, cần kết hợp thêm bộ lọc dòng tiền.
* **$F \le 3$ (Distressed / Junk):** Doanh nghiệp suy thoái tài chính nghiêm trọng, loại bỏ khỏi danh mục Quantamental.

### Định Luật Benford & Kiểm Toán Gian Lận BCTC (Benford's Law)
- **Định luật xác suất:** Trong các tập dữ liệu số tự nhiên (kế toán, dân số, độ dài dòng sông...), tần suất xuất hiện của chữ số đầu tiên (First Digit) $d \in \{1, 2, \dots, 9\}$ tuân theo quy luật logarit tự nhiên:
  $$P(d) = \log_{10}\left(1 + \frac{1}{d}\right)$$
- **Bảng phân phối xác suất chuẩn mực:**
  * Chữ số 1: $30.1\%$
  * Chữ số 2: $17.6\%$
  * Chữ số 3: $12.5\%$
  * Chữ số 4: $9.7\%$
  * Chữ số 5: $7.9\%$
  * Chữ số 6: $6.7\%$
  * Chữ số 7: $5.8\%$
  * Chữ số 8: $5.1\%$
  * Chữ số 9: $4.6\%$
- **Ứng dụng trong Kế toán Điều tra (Forensic Accounting) tại TTCK VN:**
  * Khi doanh nghiệp xào nấu số liệu, tạo hóa đơn doanh thu ảo hoặc điều chỉnh chi phí nhân tạo, phân phối chữ số đầu tiên trên các tài khoản kế toán sẽ vi phạm phân phối Benford.
  * Sử dụng kiểm định Chi-Square ($\chi^2$) để đo độ sai lệch:
    $$\chi^2 = \sum_{d=1}^{9} \frac{(O_d - E_d)^2}{E_d}$$
    ($O_d$: tần suất thực tế quan sát được, $E_d$: tần suất kỳ vọng theo Benford). Nếu $\chi^2 > \chi^2_{\text{critical}}$ ($p < 0.05$), gắn cờ đỏ cảnh báo gian lận BCTC.

### Chất Lượng Dòng Tiền & Dải Phân Vị PE/PB (Accrual & Percentile Banding)
- **Tỷ số Chất lượng Dòng tiền Kinh doanh:**
  $$\text{Earnings Quality Ratio} = \frac{CFO}{\text{Net Income}}$$
  * $> 1.0$: Dòng tiền kinh doanh thật dồi dào, lợi nhuận bền vững.
  * $< 0.5$ hoặc âm: Lợi nhuận ảo nằm ở khoản phải thu và hàng tồn kho ứ đọng.
- **Dải Phân Vị Định Giá Lịch Sử 3-5 Năm (Percentile Banding):**
  $$\text{Valuation Percentile} = \frac{\text{Số phiên có } P/E_{\text{history}} < P/E_{\text{current}}}{\text{Tổng số phiên quan sát (750 phiên)}} \times 100\%$$
  * Percentile $< 20\%$: Vùng định giá rẻ hiếm có trong lịch sử chu kỳ (Deep Value).
  * Percentile $> 80\%$: Vùng định giá đắt, phản ánh quá nhiều kỳ vọng tích cực.

---

## 4. PHÁI SINH, PHÒNG HỘ & CƠ CHẾ THANH TOÁN T+2.5

### Basis Phái Sinh & Hiện Tượng Ép Trụ Đáo Hạn
- **Độ lệch Basis:**
  $$\text{Basis} = \text{Điểm số HĐTL VN30F1M} - \text{Chỉ số VN30 Index}$$
  * **Contango ($\text{Basis} > 0$):** Tâm lý hưng phấn. Khi Basis dương lớn ($> +8$ điểm), rủi ro đảo chiều giảm phiên kế tiếp cao.
  * **Backwardation ($\text{Basis} < 0$):** Tâm lý thận trọng. Khi Basis âm sâu ($< -15$ đến $-25$ điểm), dễ kích hoạt hiện tượng "Short Squeeze" (kéo thốc chỉ số VN30 phiên ATC để ép đội Short phái sinh cắt lỗ).

### Quản Trị Rủi Ro Đệm Hàng Sẵn Có (Rolling Inventory T+0)
- **Ràng buộc T+2.5 tại Việt Nam:** Mua cổ phiếu ngày $T+0$ thì đến chiều $T+2$ hoặc sáng $T+2.5$ cổ phiếu mới có thể bán. Không thể dùng lệnh Stop-Loss T+0 quốc tế.
- **Giải pháp Đệm hàng sẵn có (Rolling Inventory):**
  * Luôn duy trì tỷ trọng $30-50\%$ cổ phiếu mục tiêu đã khả dụng trong tài khoản (đã qua chu kỳ T+2.5).
  * Khi phát hiện cơ hội lướt sóng hoặc thị trường biến động:
    * Mua thêm $X$ cổ phiếu giá thấp lúc hoảng loạn.
    * Khi giá bật tăng trong phiên, bán ngay $X$ cổ phiếu có sẵn ra để chốt lời ngay trong ngày ($T+0$), giữ nguyên quy mô danh mục cốt lõi và hạ giá vốn an toàn.
- **Công thức Phòng Hộ Danh Mục bằng HĐTL VN30F1M (Beta Hedging):**
  $$N_{\text{contracts}} = \frac{\text{NAV Danh Mục Cơ Sở} \times \beta_{\text{portfolio}}}{\text{Điểm số VN30F1M} \times 100,000 \text{ VND}}$$
  Khi thị trường gãy hỗ trợ quan trọng, mở vị thế **Short đúng $N_{\text{contracts}}$** để bảo vệ 100% giá trị danh mục cơ sở đang bị kẹt T+2.5.

---
*Tài liệu được cập nhật và kiểm chuẩn tự động theo tiêu chuẩn học thuật của dự án Neiro-Stock-VN.*
