# Spec: Neiro-Stock-VN - Quantitative & Fundamental Trading System (Quantamental)

## 1. Objective & Vision

Xây dựng hệ thống định lượng dòng tiền (Order Flow & Microstructure), sức khỏe tài chính doanh nghiệp (Fundamental Screening) và vĩ mô luân chuyển ngành (Sector Rotation) dành riêng cho **Thị trường Chứng khoán Việt Nam (HOSE, HNX, UPCoM & Phái sinh VN30F1M)**:

1. **Bản chất khác biệt giữa Gold (Neiro-Quant) và TTCK Việt Nam (Neiro-Stock-VN):**
   - **Thị trường Vàng (XAUUSD / CME GC Futures):** Thị trường tài chính toàn cầu 24/5, thanh khoản hàng nghìn tỷ USD, chuỗi quyền chọn CME cực sâu (Options Greeks, Gamma Squeeze, Zero Gamma Flip $S^*$, Delta Hedging của Dealer). T+0 tức thì, đòn bẩy cao, hai chiều Long/Short tự do, không có biên độ trần/sàn.
   - **Thị trường Chứng khoán Việt Nam:**
     - **Chưa có Options đơn lẻ cho từng cổ phiếu**, chỉ có HĐTL VN30 (VN30F1M) và Chứng quyền có bảo đảm (Covered Warrants do CTCK phát hành).
     - **Biên độ dao động cố định:** HOSE $\pm 7\%$, HNX $\pm 10\%$, UPCoM $\pm 15\%$, VN30F1M $\pm 7\%$.
     - **Chu kỳ thanh toán T+2.5 / T+1.5:** Mua T+0 thì chiều T+1.5 hoặc T+2 cổ phiếu mới về tài khoản để bán được. Do đó, rủi ro "kẹp hàng" không thể cắt lỗ ngay trong phiên là yếu tố sống còn.
     - **Cấu trúc phiên đặc thù:** Phiên mở cửa ATO (09:00 - 09:15), Khớp lệnh liên tục, Phiên đóng cửa ATC (14:30 - 14:45). Phiên ATC là nơi các Quỹ và Market Makers tạo đột biến thanh khoản và giá đóng cửa phiên.
     - **Cơ cấu nhà đầu tư:** Cá nhân nhỏ lẻ (Retail) chiếm $80\% - 85\%$ thanh khoản toàn thị trường $\rightarrow$ Dễ xuất hiện tâm lý FOMO cực độ hoặc hoảng loạn bán tháo diện rộng; Khối ngoại (Foreign) và Tự doanh (Proprietary Trading) giữ vai trò dẫn dắt xu hướng định chế.

2. **Mục tiêu Quantamental của Neiro-Stock-VN:**
   - **Định lượng Cơ bản (Fundamental Quant):** Loại bỏ việc đọc báo cáo tài chính thủ công bằng mô hình chấm điểm tự động Piotroski F-Score (0-9), tăng trưởng lợi nhuận cốt lõi (Core EBIT, EPS), kiểm tra chất lượng dòng tiền hoạt động kinh doanh ($CFO / Net Income > 1.0$), và định giá phân vị lịch sử 3-5 năm (P/E & P/B Historical Percentile Bands).
   - **Cấu trúc Vi mô & Dòng tiền (Microstructure & Order Flow):** Tái tạo bản đồ thanh khoản Volume Profile (POC, HVN, LVN / Air Pockets) cho từng mã cổ phiếu và VN-Index; đo lường áp lực khớp lệnh chủ động (Order Flow Imbalance - OFI) và theo dõi sát dấu chân Cá mập (lệnh thỏa thuận, lệnh khớp lô lớn $\ge 100,000$ cp, mua/bán ròng của Khối ngoại & Tự doanh).
   - **Định lượng Phái sinh & Phòng hộ (Derivatives Basis & Hedging):** Giám sát độ lệch Basis ($VN30F1M - VN30 Index$), nhận diện thời điểm ép trụ đáo hạn phái sinh và kích hoạt công cụ Short VN30F1M để phòng hộ danh mục cơ sở trước các cú sập bất ngờ trong chu kỳ T+2.5.
   - **Luân chuyển ngành (Sector Rotation - RRG):** Phân tích tương quan sức mạnh giá ($RS\text{-Ratio}$) và gia tốc ($RS\text{-Momentum}$) của 12 nhóm ngành chính (Ngân hàng, Bất động sản, Thép, Chứng khoán, Bán lẻ, Hóa chất, Dầu khí, Đầu tư công...) để nhận diện ngành dẫn dắt (Leading Sector).
   - **Bảng điều khiển tác chiến trực quan (Tactical HUD Terminal):** Xuất bản báo cáo tương tác định lượng trên giao diện Web Plotly Dark Mode, hỗ trợ nhà đầu tư ra quyết định chính xác trong 30 giây.

---

## 2. Tech Stack

| Layer | Công nghệ | Vai trò & Trách nhiệm |
|---|---|---|
| **Quant Core** | Python 3.12+ | Lõi tính toán phân vị, F-Score, Volume Profile, RRG, Risk Sizing |
| **Data Ingestion** | Requests / HTTPX / Playwright | Thu thập dữ liệu BCTC, Sổ lệnh L2, Khối ngoại, Tự doanh, VN30F1M |
| **Data Processing** | Pandas / NumPy / SciPy | Xử lý chuỗi thời gian OHLCV, tính phân vị và ma trận xoay ngành |
| **Tactical Dashboard** | Plotly HTML (Dark Mode) | Giao diện Web tương tác hiển thị Volume Profile, Screener, RRG |
| **Testing & Quality** | Pytest / Ruff | Kiểm thử unit test toán học và chuẩn hóa mã nguồn tự động |

---

## 3. Commands

```bash
# Cài đặt môi trường ảo và thư viện
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Chạy toàn bộ bộ kiểm thử Unit & Integration Tests
python -m pytest tests/ -v --tb=short

# Kiểm tra cú pháp và định dạng mã nguồn (Lint & Format)
python -m ruff check src/ tests/
python -m ruff format src/ tests/

# Chạy bộ lọc Quantamental Cổ phiếu (Fundamental Screener)
python -m src.fundamental_engine.screener --top 20

# Tính toán Volume Profile & Vùng thanh khoản cho mã cổ phiếu (ví dụ HPG, SSI, VCB)
python -m src.microstructure_engine.volume_profile --symbol HPG --bins 50

# Chạy phân tích Luân chuyển dòng tiền ngành (RRG Rotation)
python -m src.sector_engine.rrg_rotation --benchmark VNINDEX

# Xuất bản Dashboard Bảng điều khiển Tác chiến VN-Stock (Plotly Dark Mode)
python -m src.hud.terminal --output exports/vn_stock_terminal.html
```

---

## 4. Project Structure

```
Neiro-Stock-VN/
├── .agents/skills/               # 24 bộ kỹ năng chuẩn mực cho AI Agents
├── docs/
│   ├── spec.md                   # Bản đặc tả kỹ thuật hệ thống Quantamental VN
│   ├── architecture.md           # Kiến trúc dữ liệu và luồng thực thi tổng thể
│   ├── thuat_ngu_quant_vn.md     # Từ điển thuật ngữ Quantamental & Vi cấu trúc TTCK VN
│   ├── TRADER_PLAYBOOK_VN.md     # Cẩm nang tác chiến thực chiến cho Trader / Quỹ
│   └── decisions/                # Architecture Decision Records (ADRs)
│       └── ADR-001-quantamental-foundations-for-vn-equities.md
├── src/
│   ├── collector/                # Thu thập dữ liệu TTCK Việt Nam
│   │   ├── __init__.py
│   │   ├── data_loader.py        # Ingestion, cache & chuẩn hóa dữ liệu OHLCV / BCTC
│   │   └── vn_market_client.py   # Client kết nối dữ liệu thị trường (Cơ sở, Phái sinh, Khối ngoại)
│   ├── fundamental_engine/       # Lõi lọc cơ bản định lượng
│   │   ├── __init__.py
│   │   ├── screener.py           # Bộ lọc CANSLIM, Piotroski F-score, CFO/NI
│   │   └── valuation.py          # Định giá phân vị lịch sử PE/PB Banding
│   ├── microstructure_engine/    # Cấu trúc vi mô sổ lệnh & Khối lượng
│   │   ├── __init__.py
│   │   ├── volume_profile.py     # Volume Profile (POC, HVN, LVN / Air Pockets)
│   │   ├── order_flow.py         # Order Flow Imbalance (OFI), Lệnh lớn cá mập
│   │   └── basis_tracker.py      # Giám sát chênh lệch Basis VN30F1M vs VN30
│   ├── sector_engine/            # Vĩ mô & Luân chuyển dòng tiền ngành
│   │   ├── __init__.py
│   │   ├── rrg_rotation.py       # Relative Rotation Graph (RS-Ratio, RS-Momentum)
│   │   └── market_breadth.py     # Độ rộng thị trường (% trên MA, Advance-Decline)
│   ├── risk_engine/              # Quản trị rủi ro & Vị thế T+2.5
│   │   ├── __init__.py
│   │   ├── position_sizer.py     # Tính toán tỷ trọng theo Volatility ATR(14)
│   │   └── t25_manager.py        # Quản lý vòng quay hàng sẵn T+0 & Margin Buffer
│   └── hud/                      # Giao diện Tactical Terminal
│       ├── __init__.py
│       └── terminal.py           # Sinh Plotly Dashboard tương tác đa chiều
├── data/                         # Dữ liệu chuẩn hóa mẫu (benchmark data)
├── exports/                      # File HTML Terminal và báo cáo định lượng xuất bản
├── tests/                        # 100% Automated Unit Tests cho từng công thức toán
├── AGENTS.md / GEMINI.md         # Quy tắc kích hoạt Skill & Luật bất di bất dịch
├── requirements.txt              # Danh sách thư viện Python phụ thuộc
├── pyproject.toml                # Cấu hình dự án & công cụ kiểm tra Ruff
└── README.md                     # Hướng dẫn tổng quan & Bắt đầu nhanh
```

---

## 5. Code Style & Standards

- **Quy chuẩn đặt tên:** `snake_case` cho hàm và biến, `PascalCase` cho Classes và DataModels.
- **Type Annotations:** Bắt buộc type hints trên mọi hàm public (dùng `typing` hoặc Python 3.12+ native union `|`).
- **Tài liệu hàm (Docstrings):** Chuẩn Google Style, giải thích rõ `Args:`, `Returns:`, và ý nghĩa kinh tế định lượng.
- **Zero-Warning Tolerance:** Mã nguồn phải vượt qua `ruff check` và `ruff format` không có cảnh báo nào.

---

## 6. Testing Strategy

- **Toán học bất biến (Math Invariants):** Mọi công thức (Piotroski F-Score, Volume Profile POC, Basis Spread, RRG Vectors, ATR Sizing) đều phải có Unit Test độc lập kiểm tra giá trị biên.
- **Dữ liệu giả lập kiểm chuẩn (Mock Benchmark Data):** Mọi test đều chạy trên mock data chuẩn trong bộ nhớ, không phụ thuộc vào kết nối mạng bên ngoài, đảm bảo test chạy dưới 5 giây.

---

## 7. Boundaries (Giới hạn hoạt động)

- **Luôn luôn làm (Always):** Chạy `pytest` trước khi commit; kiểm tra tính toán T+2.5 trong mọi logic mua bán; dọn dẹp bộ nhớ RAM và tệp tạm thời.
- **Hỏi ý kiến trước (Ask First):** Thêm thư viện nặng bên thứ 3; thay đổi công thức tính F-Score hoặc các ngưỡng phân loại HVN/LVN.
- **Tuyệt đối cấm (Never):** Dùng các chỉ báo trễ đơn lẻ (RSI/MACD) để dự đoán đỉnh đáy; bỏ qua chu kỳ thanh toán T+2.5; xả file rác vượt quá dung lượng 15MB của dự án.

---

## 8. Kiến trúc Lý thuyết & Công thức Toán học (6-Tier Quantamental Engine)

### Tier 1: Quantitative Fundamental Screening (Chất Lượng Doanh Nghiệp)

#### 1. Mô hình Piotroski F-Score (Thang điểm 0 - 9)
Đánh giá sức khỏe tài chính tổng thể của doanh nghiệp qua 3 nhóm tiêu chí:
1. **Khả năng sinh lời (Profitability):**
   - $F_1 = 1$ nếu $ROA_t > 0$, ngược lại $0$.
   - $F_2 = 1$ nếu Dòng tiền hoạt động kinh doanh $CFO_t > 0$, ngược lại $0$.
   - $F_3 = 1$ nếu $\Delta ROA = ROA_t - ROA_{t-1} > 0$, ngược lại $0$.
   - $F_4 = 1$ nếu Chất lượng lợi nhuận $CFO_t > Net Income_t$ (Accrual âm: tiền thật cao hơn lãi trên sổ sách), ngược lại $0$.
2. **Đòn bẩy tài chính & Thanh khoản (Leverage & Liquidity):**
   - $F_5 = 1$ nếu Nợ vay dài hạn giảm $\Delta Leverage = LongTermDebt_t - LongTermDebt_{t-1} < 0$, ngược lại $0$.
   - $F_6 = 1$ nếu Tỷ số thanh toán hiện hành tăng $\Delta CurrentRatio = CR_t - CR_{t-1} > 0$, ngược lại $0$.
   - $F_7 = 1$ nếu Số lượng cổ phiếu lưu hành không bị pha loãng $\Delta Shares \le 0$, ngược lại $0$.
3. **Hiệu quả hoạt động (Operating Efficiency):**
   - $F_8 = 1$ nếu Biên lợi nhuận gộp tăng $\Delta GrossMargin = GM_t - GM_{t-1} > 0$, ngược lại $0$.
   - $F_9 = 1$ nếu Vòng quay tài sản tăng $\Delta AssetTurnover = ATO_t - ATO_{t-1} > 0$, ngược lại $0$.

$$\text{F-Score} = \sum_{i=1}^9 F_i$$
- **F-Score $\ge 7$:** Cổ phiếu đạt tiêu chuẩn tài chính định chế xuất sắc.
- **F-Score $\le 3$:** Rủi ro cao về thao túng BCTC hoặc suy kiệt thanh khoản $\rightarrow$ Loại khỏi danh mục.

#### 2. Định giá Phân Vị Lịch Sử (Historical Valuation Percentile Banding)
Thay vì dùng P/E hoặc P/B cố định, tính phân vị tích lũy của P/E hiện tại so với dữ liệu 3 năm (750 phiên giao dịch):
$$\text{Percentile}(P/E) = \frac{\text{Số phiên có } (P/E)_i \le (P/E)_{\text{hiện tại}}}{N} \times 100\%$$
- **Percentile $< 20\%$:** Vùng định giá rẻ hiếm có (Undervalued Value Zone).
- **Percentile $> 80\%$:** Vùng định giá quá nóng (Overheated Valuation Bubble).

---

### Tier 2: Market Microstructure & Order Flow (Cấu Trúc Vi Mô Sổ Lệnh)

#### 1. Volume Profile tại từng mức giá (Volume at Price - VAP)
Chia dải giá của cổ phiếu thành $N$ Price Bins:
- **Point of Control (POC):** Mức giá có khối lượng giao dịch tích lũy lớn nhất:
  $$POC = \arg\max_k (\text{Volume}_k)$$
- **Value Area (VA):** Vùng giá tập trung $70\%$ tổng khối lượng giao dịch trong chu kỳ:
  $$\sum_{k \in VA} \text{Volume}_k \ge 0.70 \times \text{Total Volume}$$
  Xác định $VAH$ (Value Area High) và $VAL$ (Value Area Low).
- **High Volume Nodes (HVN - Thành trì phòng thủ):** Các mức giá có Volume đột biến $\ge 1.5 \times \text{MA(Volume Bins)}$, nơi diễn ra sự hấp thụ (Absorption) và tích lũy của Big Boys.
- **Low Volume Nodes / Air Pockets (LVN - Vùng chân không thanh khoản):** Các mức giá có Volume $< 0.4 \times \text{MA(Volume Bins)}$, nơi giá sẽ trôi cực nhanh (Slicing Runner / Gap) mà không gặp lực cản.

#### 2. Order Flow Imbalance (OFI - Áp lực Khớp Lệnh Chủ Động)
Đo lường mức độ chênh lệch giữa lệnh Mua chủ động (ăn thẳng vào dư bán) và Bán chủ động (xả thẳng vào dư mua):
$$OFI = \frac{\text{Volume}_{\text{Mua chủ động}} - \text{Volume}_{\text{Bán chủ động}}}{\text{Volume}_{\text{Mua chủ động}} + \text{Volume}_{\text{Bán chủ động}}}$$
- $OFI > +0.30$: Áp lực gom hàng chủ động quyết liệt của dòng tiền lớn (Aggressive Buying).
- $OFI < -0.30$: Áp lực bán tháo xả hàng chủ động (Aggressive Selling).

---

### Tier 3: Institutional Smart Money Tracking (Dòng Tiền Cá Mập)

Theo dõi sự dịch chuyển vị thế của 3 khối nhà đầu tư lớn tại TTCK Việt Nam:
1. **Khối ngoại (Foreign Net Flow):**
   $$\Delta \text{Foreign}_t = \text{BuyValue}_{\text{Foreign}} - \text{SellValue}_{\text{Foreign}}$$
2. **Khối Tự Doanh CTCK (Proprietary Trading Flow):**
   $$\Delta \text{Prop}_t = \text{BuyValue}_{\text{Prop}} - \text{SellValue}_{\text{Prop}}$$
3. **Chỉ số Phân kỳ Dòng tiền (Smart Money Divergence Index - SMDI):**
   Đo lường sự bất tương xứng giữa Biến động Giá và Dòng tiền Cá mập:
   $$\text{SMDI} = \text{Sign}(\Delta \text{Price}) \times \text{Sign}(\Delta \text{Foreign} + \Delta \text{Prop})$$
   - Khi $\Delta \text{Price} < 0$ nhưng $(\Delta \text{Foreign} + \Delta \text{Prop}) > 0$ $\rightarrow$ **Smart Money Gom Hàng Trong Hoảng Loạn** (Tín hiệu tích lũy đảo chiều đáy).
   - Khi $\Delta \text{Price} > 0$ nhưng $(\Delta \text{Foreign} + \Delta \text{Prop}) < 0$ $\rightarrow$ **Kéo Giá Xả Hàng Cho Nhỏ Lẻ (Bull Trap)**.

---

### Tier 4: Derivatives VN30F1M Basis & Hedging Engine

1. **Chênh lệch Basis phái sinh:**
   $$\text{Basis} = \text{Price}_{\text{VN30F1M}} - \text{Index}_{\text{VN30}}$$
   - **Contango ($\text{Basis} > +5.0$ điểm):** Thị trường kỳ vọng tăng giá, kích thích dòng tiền Long phái sinh hoặc mở ra cơ hội Arbitrage Bán Phái Sinh - Mua Cổ phiếu Cơ sở VN30.
   - **Backwardation ($\text{Basis} < -8.0$ điểm):** Tâm lý phòng thủ, các tổ chức đang Short phái sinh mạnh để khóa danh mục cổ phiếu cơ sở; khi Basis âm quá sâu ($-15$ đến $-20$ điểm), thường xảy ra cú kéo Short Squeeze quét điểm.

2. **Hệ số Phòng Hộ Danh Mục (T+2.5 Beta Hedge Ratio):**
   Khi thị trường gãy ngưỡng hỗ trợ POC quan trọng nhưng danh mục cổ phiếu cơ sở đang bị kẹt chu kỳ T+2.5 chưa bán được, hệ thống kích hoạt lệnh Short VN30F1M phòng hộ:
   $$N_{\text{HĐ Short}} = \text{Round}\left( \frac{\text{Giá trị Danh mục} \times \beta_{\text{Danh mục}}}{\text{Price}_{\text{VN30F1M}} \times 100,000 \text{ VND}} \right)$$

---

### Tier 5: Macro & Sector Rotation Engine (Mô Hình RRG)

Sử dụng thuật toán Relative Rotation Graph (RRG) của JdK để định lượng dòng tiền luân chuyển giữa các ngành:
1. **Sức mạnh giá tương đối (RS-Ratio):**
   $$RS(i, t) = \frac{P_{\text{Ngành } i, t}}{P_{\text{VNINDEX}, t}}$$
   $$RS\text{-Ratio}(i, t) = 100 + 10 \times \left( \frac{RS(i, t) - \text{SMA}_{n}(RS)}{\sigma_{n}(RS)} \right)$$
2. **Gia tốc biến động dòng tiền (RS-Momentum):**
   $$RS\text{-Momentum}(i, t) = 100 + 10 \times \left( \frac{\Delta RS\text{-Ratio}(i, t) - \text{SMA}_{m}(\Delta RS\text{-Ratio})}{\sigma_{m}(\Delta RS\text{-Ratio})} \right)$$
3. **4 Pha Luân Chuyển Ngành:**
   - **Leading ($RS\text{-Ratio} > 100, RS\text{-Mom} > 100$):** Ngành Dẫn dắt $\rightarrow$ Tập trung $60\%$ vốn.
   - **Weakening ($RS\text{-Ratio} > 100, RS\text{-Mom} < 100$):** Ngành Suy yếu $\rightarrow$ Chốt lời từng phần.
   - **Lagging ($RS\text{-Ratio} < 100, RS\text{-Mom} < 100$):** Ngành Tụt hậu $\rightarrow$ Tuyệt đối không tham gia.
   - **Improving ($RS\text{-Ratio} < 100, RS\text{-Mom} > 100$):** Ngành Đang hồi phục $\rightarrow$ Canh giải ngân thăm dò.

---

### Tier 6: Quản Trị Rủi Ro & Vị Thế Chu Kỳ T+2.5

1. **Định lượng Tỷ trọng theo Biến động (Volatility-Targeted Sizing):**
   Áp dụng biến động biên độ thực tế 14 phiên $ATR(14)$ để xác định số lượng cổ phiếu giải ngân tối đa cho một giao dịch:
   $$\text{Max Risk VND} = \text{Tổng Vốn} \times \text{Risk\%} \quad (\text{Mặc định } 1.5\% - 2.0\%)$$
   $$\text{Khối Lượng Mua} = \text{RoundDown}\left( \frac{\text{Max Risk VND}}{k \times ATR(14)} \right)$$
   (với $k = 1.5 - 2.0$ lần ATR, tương ứng mức Stop Loss kỹ thuật).

2. **Quy tắc Rolling Inventory (Đệm Hàng Sẵn Có T+0):**
   - Chỉ giải ngân vị thế tỷ trọng lớn $\ge 20\%$ tài khoản khi tài khoản **đã có sẵn ít nhất $50\%$ khối lượng mã đó ở trạng thái T+0** (hàng đã khả dụng bán).
   - Nếu thị trường bất ngờ có biến cố Black Swan trong phiên, nhà đầu tư có thể xả ngay lượng hàng T+0 sẵn có để khóa rủi ro, vô hiệu hóa hoàn toàn bẫy kẹt hàng T+2.5.
