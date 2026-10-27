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

# Quét tự động Top 5 Siêu cổ phiếu chân sóng (Fialda VIP Expert & Order Flow Harvester)
python -m src.collector.fialda_scanner

# Xuất bản Dashboard Bảng điều khiển Tác chiến VN-Stock (Plotly Dark Mode)
python -m src.hud.terminal --output exports/vn_stock_terminal.html
```

---

## 4. Project Structure

```
Neiro-Stock-VN/
├── .github/workflows/            # CI/CD & Tự động hóa tác chiến 24/7 trên Cloud
│   ├── ci.yml                    # Quality Gate tự động: Pytest & Zero-Waste Check
│   └── scanner_and_pages.yml     # Quét Top 20 & CAMEL tự động định kỳ 30 phút/lần & Deploy GitHub Pages
├── .agents/skills/               # 24 bộ kỹ năng chuẩn mực cho AI Agents
├── docs/
│   ├── spec.md                   # Bản đặc tả kỹ thuật hệ thống Quantamental VN
│   ├── architecture.md           # Kiến trúc dữ liệu và luồng thực thi tổng thể
│   ├── thuat_ngu_quant_vn.md     # Từ điển thuật ngữ Quantamental & Vi cấu trúc TTCK VN
│   ├── TRADER_PLAYBOOK_VN.md     # Cẩm nang tác chiến thực chiến cho Trader / Quỹ
│   ├── google_sheets_setup.md    # Hướng dẫn thiết lập Google Sheets, Looker Studio & ML
│   └── decisions/                # Architecture Decision Records (ADRs: ADR-001 -> ADR-011)
│       ├── ADR-001-quantamental-foundations-for-vn-equities.md
│       ├── ADR-002-fialda-vip-expert-automated-scanner.md
│       ├── ADR-003-liquidity-and-portfolio-capacity-sizer.md
│       ├── ADR-004-walk-forward-backtest-engine-t25.md
│       ├── ADR-005-resilient-realtime-pricing-and-public-fallback.md
│       ├── ADR-006-dynamic-trailing-stop-t25-and-ranking-history.md
│       ├── ADR-007-credential-sanitization-ci-hardening-and-scheduler-consolidation.md
│       ├── ADR-008-client-auto-reload-live-countdown-and-scheduling-mechanics.md
│       ├── ADR-009-background-anti-fomo-signal-ledger-and-chasing-prevention.md
│       ├── ADR-010-live-dynamic-price-polling-5min-cadence.md
│       └── ADR-011-online-signal-ledger-and-ml-dataset-pipeline.md
├── src/
│   ├── collector/                # Thu thập dữ liệu TTCK Việt Nam
│   │   ├── __init__.py
│   │   ├── data_loader.py        # Ingestion, cache & chuẩn hóa dữ liệu OHLCV / BCTC
│   │   ├── vn_market_client.py   # Client kết nối dữ liệu thị trường (Cơ sở, Phái sinh, Khối ngoại)
│   │   ├── fialda_scanner.py     # Harvester Fialda VIP Expert, AI signals, RRG & Top 5 Rockets
│   │   ├── ranking_history.py    # Lưu snapshot thứ hạng chuỗi thời gian, tính Delta Rank & Top Movers
│   │   └── google_sheets_client.py # Đồng bộ sổ cái trực tuyến qua Google Apps Script Webhook (ADR-011)
│   ├── fundamental_engine/       # Lõi lọc cơ bản định lượng
│   │   ├── __init__.py
│   │   ├── screener.py           # Bộ lọc CANSLIM, Piotroski F-score, CFO/NI
│   │   ├── banking_quant.py      # Mô hình CAMEL & Basel II/III (CAR, NPL, LLR, CIR, CASA, NIM, LDR)
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
│   │   ├── t25_manager.py        # Quản lý vòng quay hàng sẵn T+0 & Margin Buffer
│   │   ├── liquidity_sizer.py    # Bộ lọc ADTV20, Sức chứa danh mục & Trượt giá phi tuyến
│   │   ├── trailing_stop.py      # Initial SL, Chandelier Exit, Break-even 1.5R/2R & T+2.5 Exposure
│   │   └── signal_tracker.py     # Sổ cái tín hiệu ngầm, Neo mốc giá gốc T0, Chống mua đuổi & ML (ADR-009/011)
│   ├── backtesting/              # Module Kiểm định Quá khứ Walk-Forward T+2.5
│   │   ├── __init__.py
│   │   ├── models.py             # Data models: Exchange, PriceBand, Position, TradeRecord
│   │   ├── engine.py             # Lõi T25BacktestEngine: Queue T+2.5, Phí/Thuế, Trần/Sàn
│   │   ├── metrics.py            # Suite toán học: Sharpe, Sortino, MDD, CAGR, WinRate, PF
│   │   ├── point_in_time.py      # PIT Engine: Khắc phục triệt để Point-in-Time bias của BCTC
│   │   ├── historical_data.py    # Dataset chuẩn 2021-2026 cho VN30 & VNINDEX Benchmark
│   │   └── walk_forward.py       # Điều phối kiểm định In-Sample vs Out-of-Sample & tính WFE
│   └── hud/                      # Giao diện Tactical Terminal
│       ├── __init__.py
│       └── terminal.py           # Sinh Terminal tương tác đa tab, Widget Lịch sử Rank & Top 20
├── data/                         # Dữ liệu mẫu benchmark, ranking_history.jsonl, active_signals.jsonl, ml_signals_dataset.csv
├── exports/                      # File HTML Terminal và báo cáo định lượng xuất bản (GitHub Pages)
├── reports/                      # Báo cáo kết quả quét Top 5 mới nhất (latest_scan.md)
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

3. **Bộ Lọc Thanh Khoản & Sức Chứa Danh Mục (Liquidity & Capacity Sizer - Quy Chuẩn Quỹ):**
   - **Bộ lọc ADTV20 (Average Daily Trading Value 20 phiên):**
     $$\text{ADTV20} = \frac{1}{20} \sum_{t=1}^{20} (\text{Close}_t \times \text{Volume}_t)$$
     - $\text{ADTV20} \ge 30.0$ tỷ VNĐ/phiên: Đạt chuẩn Quỹ Định Chế (Institutional Grade).
     - $15.0 \le \text{ADTV20} < 30.0$ tỷ VNĐ/phiên: Đạt chuẩn Biên (Borderline Liquid).
     - $\text{ADTV20} < 15.0$ tỷ VNĐ/phiên: Loại bỏ hoàn toàn khỏi danh mục để triệt tiêu rủi ro mất thanh khoản khi thị trường sập.
   - **Mô Hình Sức Chứa Danh Mục (Portfolio Capacity Model):**
     Giới hạn tỷ trọng mua tối đa của 1 vị thế không vượt quá $10\% - 15\%$ khối lượng giao dịch trung bình ngày ($ADV20 = \text{ADTV20} / \text{Price}$), làm tròn lô 100 cổ phiếu:
     $$\text{Max Shares} = \left\lfloor \frac{ADV20 \times P_{\max}}{100} \right\rfloor \times 100$$
     Đảm bảo thời gian thanh lý an toàn trong chu kỳ T+2.5: $\text{Exit Days} \le 1.0$ phiên.
   - **Mô Hình Ước Lượng Trượt Giá Phi Tuyến (Nonlinear Slippage Model):**
     $$\text{Slippage} (\%) = \text{Spread}_{\text{bid-ask}} + k \cdot \left( \frac{\text{Order Shares}}{ADV20} \right)^\alpha$$
     với $k = 2.5$, $\alpha = 0.60$ (Square-Root Market Impact Law). Tự động kích hoạt cảnh báo `CRITICAL_OVER_CAPACITY` nếu tỷ lệ tham gia $> 15\%$, và cảnh báo `HIGH_SLIPPAGE` nếu trượt giá $\ge 1.50\%$.

---

### Tier 7: Fialda VIP Expert Harvester & Tactical Terminal Live (GitHub Pages)

1. **Kết Nối Trực Tiếp API Fialda VIP:**
   - **Bảng Giá & Khớp Lệnh Real-time:** `POST /api/services/app/Common/GetStockInfos` truy xuất dữ liệu giá khớp (`currentPrice`, `lastPrice`, `highPrice`, `lowPrice`) và giá trị giao dịch ròng Khối ngoại (`totalForeignNetValue`) theo thời gian thực (đơn vị: 1,000 VND).
   - **Chỉ Số Tài Chính Định Lượng Chuẩn:** `GET /api/services/app/TechnicalAnalysis/GetFinancialHighlights?symbol={symbol}` cung cấp dữ liệu báo cáo tài chính chuẩn hóa: Piotroski F-Score (0-9), P/E, P/B, EPS, dòng tiền $CFO / Net Income$.
   - **Tín Hiệu AI Chân Sóng & Đột Biến:** `GetTinHieuChoMuaNew` và `GetTinHieuDotBienGiaTri` lọc ra các mã nén giá nền tích lũy hoặc có dòng tiền cá mập đột biến giá trị.
   - **Ma Trận Luân Chuyển Ngành RRG:** `GetRRGData` tính toán tọa độ $RS\text{-Ratio}$ và $RS\text{-Momentum}$ chuẩn xác từ Fialda Expert.

2. **Chuẩn Hóa Giao Diện Tiếng Việt & Triển Khai GitHub Pages:**
   - **Bản Địa Hóa 100% Tiếng Việt:** Toàn bộ bảng điều khiển chiến thuật (`src/hud/terminal.py`) và báo cáo quét thị trường (`reports/latest_scan.md`) sử dụng tiếng Việt chuẩn mực, giữ nguyên các ký hiệu định lượng quốc tế chuẩn (Piotroski F-Score, P/E, P/B, RRG, Basis, Stop Loss, Target, NAV, T+2.5).
   - **Triển Khai Tự Động:** Nhánh `gh-pages` được tự động cập nhật qua GitHub Actions, cung cấp giao diện trực quan 24/7 xem được trên mọi thiết bị di động tại URL: `https://daninguyen2509.github.io/Neiro-Stock-VN/`.

3. **Thống Kê Tiến Trình Báo Cáo Tài Chính 1 Cổ Phiếu / 1 Dòng (Single-Row BCTC Progression):**
   - Bảng BCTC tổng hợp kết quả kinh doanh được định dạng tinh gọn chuẩn xác: mỗi cổ phiếu biểu diễn trên đúng 1 dòng duy nhất để người dùng nắm bắt trọn vẹn gia tốc tài chính không cần cuộn trang.
   - Trục ngang thể hiện tiến trình động lượng 3 quý liên tiếp theo chiều thời gian (Cũ ➔ Mới):
     - **Tiến trình Doanh thu thuần:** $Q_{-2} \rightarrow Q_{-1} \rightarrow Q_{\text{gần nhất}}$ (đơn vị: tỷ VNĐ).
     - **Tiến trình Lợi nhuận sau thuế (LNST):** $Q_{-2} \rightarrow Q_{-1} \rightarrow Q_{\text{gần nhất}}$ (đơn vị: tỷ VNĐ).
     - **Tăng trưởng LNST QoQ:** $\frac{LNST_0 - LNST_{-1}}{|LNST_{-1}|} \times 100\%$.
     - **Biên lãi gộp quý gần nhất:** $\frac{\text{Lợi Nhuận Gộp}_0}{\text{Doanh Thu}_0} \times 100\%$.
     - **Huy hiệu động lượng trực quan:** `🚀 TĂNG TỐC 3 QUÝ`, `🔥 BÙNG NỔ LNST`, `↗ TĂNG TRƯỞNG DƯƠNG`, `↘ CHẬM LẠI`, `⚠️ LỖ RÒNG`.

---

### Tier 8: Walk-Forward Backtesting Engine T+2.5 & Phòng Vệ Thiên Lệch Định Lượng

1. **Ràng Buộc Thực Thi Chu Kỳ Thanh Toán T+2.5:**
   - Mua phiên $T$ (bar index $i$) $\rightarrow$ Cổ phiếu được gán `settle_day_index = i + 2`. Cấm bán tuyệt đối tại $T+0$ và $T+1$.
   - Chiều ngày $T+2$ hoặc từ $T+3$ trở đi: Cổ phiếu khả dụng bán (`available_shares > 0`).
2. **Kiểm Soát Biên Độ Trần / Sàn Theo Sàn Niêm Yết:**
   - HOSE: $\pm 7\%$, HNX: $\pm 10\%$, UPCoM: $\pm 15\%$.
   - Lệnh mua bị từ chối nếu giá khớp vượt trần (trắng bên bán); lệnh bán bị từ chối nếu giá khớp dưới sàn (trắng bên mua / mất thanh khoản).
3. **Khấu Trừ Thuế & Phí Giao Dịch Thực Tế:**
   - Phí mua: $0.15\%$.
   - Phí bán: $0.15\%$ phí môi giới $+ 0.10\%$ thuế TNCN bán chứng khoán $= 0.25\%$.
   - Tổng ma sát vòng quay (Round-trip drag): $0.40\%$.
4. **Bộ Phòng Vệ 4 Thiên Lệch Định Lượng (Quantamental Bias Defense):**
   - **Look-ahead Bias:** Tín hiệu tính toán cuối ngày $t$ (ATC), khớp lệnh mở cửa ATO phiên $t+1$.
   - **Point-in-Time Bias:** BCTC chỉ được đưa vào tính Piotroski F-Score / CAMEL khi $filing\_date \le as\_of\_date$ (tối thiểu 30-45 ngày sau chốt quý).
   - **Overfitting & Curve Fitting:** Đóng băng và phân tách độc lập 2 tập dữ liệu: In-Sample (2021-2023: Bullrun + Đại suy thoái 2022) và Out-of-Sample (2024-2026: Dữ liệu mù Unseen Data). Đo lường $\text{WFE} = \text{Sharpe}_{\text{OOS}} / \text{Sharpe}_{\text{IS}}$.
5. **Thước Đo Hiệu Suất Chuẩn Mực & Phân Định Trách Nhiệm:**
   - CAGR, Annualized Sharpe ($R_f = 4.5\%$), Sortino Ratio, Max Drawdown (MDD), Profit Factor, Win Rate.
   - Kết quả thực nghiệm 2021-2026: MDD hệ thống chỉ **19.10%** (so với VN-Index sập tới **44.09%** trong khủng hoảng 2022), Sharpe OOS đạt **1.77**.
   - **Phân Định Trách Nhiệm:** Module Kiểm Định Lịch Sử (`src/backtesting/`) đóng vai trò động cơ kiểm chứng định lượng nội bộ (Internal Research Engine), độc lập phục vụ nghiên cứu và kiểm thử mô hình. Giao diện Web Dashboard (`exports/index.html`) duy trì cấu trúc tác chiến liên tục (Top 20 Siêu Cổ Phiếu Chân Sóng, Định Lượng Cơ Bản, CAMEL Ngân Hàng, BCTC & Tin Tức Spotlight) để nhà đầu tư hành động nhanh nhất.

---

### Tier 9: Quản Trị Rủi Ro Động, Điểm Thoát Lệnh T+2.5 & Theo Vết Lịch Sử Xếp Hạng

1. **Ngưỡng Cắt Lỗ Cứng Ban Đầu (Initial Stop Loss):**
   - Kết hợp giữa đáy nến gần nhất (Swing Low - hỗ trợ kỹ thuật) và độ biến động ATR(14):
     $$\text{Stop Loss} = \text{clamp}\Big(\max(\text{Swing Low}, \text{Entry} - 1.5 \times \text{ATR}_{14}),\ [0.93 \times \text{Entry},\ 0.97 \times \text{Entry}]\Big)$$
   - Khống chế mức rủi ro tối thiểu $3\%$ (tránh quét râu nhiễu) và tối đa $7\%$ (tương thích biên độ sàn HOSE).
   - Xác định đơn vị rủi ro chuẩn $1R = \text{Entry} - \text{Stop Loss}$.

2. **Cơ Chế Khóa Lợi Nhuận Tự Động (Chandelier Exit & Break-Even Ratchet):**
   - **Nâng lên Hòa Vốn (Break-Even):** Khi giá tăng đạt $\ge 1.5R$, Stop Loss tự động dời lên giá vốn ($\text{Entry}$) để bảo toàn 100% tài sản, xóa bỏ hoàn toàn rủi ro đảo chiều.
   - **Chandelier Trailing Stop:** Khi giá tiếp tục lập đỉnh mới ($\text{Highest High}$), Stop Loss bám sát:
     $$\text{Trailing Stop} = \max\Big(\text{Current Stop},\ \text{Highest High} - 2.0 \times \text{ATR}_{14}\Big)$$
   - **Tính chất bất biến (Ratchet Property):** Stop Loss chỉ đơn điệu tăng, tuyệt đối không bao giờ bị hạ xuống.

3. **Tỷ Lệ Vàng Risk/Reward ($R:R \ge 1:2.5$):**
   - **TP1 (Target 1.5R):** Khuyến nghị bán chốt lời $50\%$ số lượng cổ phiếu để hiện thực hóa lợi nhuận.
   - **TP2 (Target 2.5R đến 3.0R):** Gồng lãi $50\%$ còn lại theo Trailing Stop để tối đa hóa lợi nhuận toàn bộ con sóng.

4. **Quản Trị Rủi Ro "Vùng Đóng Băng T+0 đến T+2" Cho Nhà Đầu Tư Cổ Phiếu Cơ Sở:**
   - Dành riêng cho nhà đầu tư thuần mua bán Cổ phiếu Cơ sở (Spot Equities Long-Only): không short phái sinh.
   - Dùng độ lệch Basis VN30F1M và Độ rộng thị trường làm **Rada Cảnh Báo Sớm**:
     - 🟢 **SAFE:** Basis dương, thị trường giữ trend $\rightarrow$ Mở mua bình thường.
     - 🟡 **MODERATE:** Basis phân kỳ nhẹ $\rightarrow$ Chỉ giải ngân đợt 1 (50% vị thế tại nền).
     - 🔴 **HIGH / CRITICAL:** Phái sinh bán tháo mạnh (Basis âm sâu $< -10$ điểm) $\rightarrow$ Tạm dừng mở mua mới hàng đóng băng, bán hạ tỷ trọng trên các mã sẵn có để giữ tỷ trọng tiền mặt $\ge 50\% - 60\%$.

5. **Theo Vết & Lưu Trữ Lịch Sử Xếp Hạng (Ranking History Tracker):**
   - Tự động lưu trữ chuỗi thời gian các phiên quét vào `data/ranking_history.jsonl` (áp dụng Rolling Window giữ tối đa 500 records $\sim 35\text{ KB}$, bảo đảm tiêu chuẩn Zero-Waste $< 15\text{ MB}$).
   - **Cơ chế Chống Rung Nhiễu Phiên (Session Debounce 30 phút):** Tự động phát hiện các lần quét lặp lại trong vòng 30 phút, cập nhật batch của phiên hiện tại và giữ nguyên mốc so sánh là phiên giao dịch trước đó thực sự (không bị so sánh với lần bấm nút cách đó vài chục giây), bảo đảm cột Kỳ Trước luôn ổn định và nhất quán tuyệt đối.
   - **Khiên chắn cách ly kiểm thử (Test Pollution Guard):** Tự động chặn mọi thao tác ghi dữ liệu của `pytest` thông qua cờ `PYTEST_CURRENT_TEST` đối với file dữ liệu chính thức, triệt tiêu 100% rủi ro dữ liệu mock làm sai lệch thứ hạng thật.
   - **Tính toán Biến động Thứ hạng ($\Delta Rank$) với Fallback Lịch Sử:** So sánh với phiên liền trước để tính: $\Delta Rank = \text{Rank}_{\text{cũ}} - \text{Rank}_{\text{mới}}$ (`↗ +N` thăng hạng, `↘ -N` tụt hạng, `=` giữ hạng). Nếu mã tạm rớt khỏi Top 20 ở phiên liền trước nhưng đã từng xuất hiện trong lịch sử, tự động fallback so sánh với lần xuất hiện cuối cùng thay vì gán nhãn `🆕 MỚI` gây hiểu lầm. Chỉ hiển thị `🆕 MỚI` cho mã chưa bao giờ xuất hiện trong bất kỳ phiên quét nào trước đó.
   - **Bố cục 15 cột tinh gọn trên Dashboard & Báo cáo:** Hiển thị trực quan cột `Kỳ Trước` (`#cũ +N` / `MỚI`) ở cột cuối cùng trên bảng Top 20; phân tách mạch lạc các cột `Thanh Khoản (ADTV)`, `Chuẩn Quỹ (Lô Max/Trượt)`, `Điểm IBD Composite`, và `Tích Luỹ (A-E)` để hiển thị trực quan, vừa vặn 100% màn hình, không cần cuộn ngang.

---

### Tier 10: Chuẩn Hóa Chuỗi Xác Thực API, Khắc Phục CI Quality Gate & Tối Ưu Hóa Bộ Lập Lịch Tự Động (ADR-007)

1. **Chuẩn Hóa Bí Mật & Chống Nhiễu Chuỗi Môi Trường (Credential Sanitization):**
   - Loại bỏ tự động toàn bộ ký tự khoảng trắng thừa, dấu xuống dòng ẩn (`\r\n`), và dấu ngoặc kép bọc ngoài từ biến môi trường `FIALDA_USERNAME` và `FIALDA_PASSWORD`.
   - Ngăn chặn hoàn toàn lỗi xác thực giả `HTTP 500: Email hoặc mật khẩu không chính xác` do thao tác copy-paste trên giao diện đám mây GitHub Secrets.
   - Cơ chế chẩn đoán an toàn (Masked Diagnostics): Ghi nhận độ dài chuỗi và ký tự đầu/cuối của thông tin xác thực trên log console nhằm hỗ trợ gỡ lỗi tức thì mà không làm rò rỉ mật khẩu.

2. **Cơ Chế Đèn Báo Dữ Liệu & Fallback Dự Phòng Thông Minh:**
   - Khi kết nối Fialda VIP API thành công: Bật huy hiệu xanh `🟢 DỮ LIỆU: REAL-TIME FIALDA PRO API`.
   - Khi kết nối Fialda VIP gặp sự cố (mạng, hết hạn phiên hoặc sai thông tin xác thực): Hệ thống tự động in cảnh báo chi tiết, chuyển sang chế độ dự phòng an toàn `🟡 CHẾ ĐỘ DỰ PHÒNG: BẢNG GIÁ ENTRADE/DNSE PUBLIC` kèm thông báo trạng thái `⚠️ Fialda VIP gián đoạn - Đang tự động bảo vệ tín hiệu bằng nguồn dự phòng` để duy trì báo cáo và dashboard liên tục 24/7.

3. **Tương Thích Ngược & Đảm Bảo Chất Lượng CI Quality Gate:**
   - Chuẩn hóa khai báo Type Hinting cross-platform trên module Walk-Forward Backtesting (`src/backtesting/walk_forward.py`), giải quyết triệt để lỗi `NameError: name 'Any' is not defined` trên môi trường runtime Python 3.12 (Linux runner).
   - Duy trì tỷ lệ pass 100% cho 75 unit tests toán học định lượng và kiểm soát dung lượng repository dưới 15MB theo quy định Zero-Waste Mandate.

4. **Tối Ưu Hóa Bộ Lập Lịch Cron Chuẩn POSIX (`scanner_and_pages.yml`):**
   - Hợp nhất các mốc quét thành 5 biểu thức chuẩn POSIX (`15,45 2,3,4 * * 1-5`, `15,45 6,7 * * 1-5`, `5 8 * * 1-5`, `30 10 * * 1-5`, `0 12 * * 1-5`).
   - Tối ưu hóa chu kỳ quét tự động trong phiên giao dịch HOSE/HNX, bổ sung mốc 17:30 (bắt trọn Tự doanh sớm) và 19:00 (EOD Final Smart Money khóa băng toàn diện Tự doanh + Ngoại ròng + Phái sinh VSDC), loại bỏ hiện tượng nghẽn hàng đợi (queue starvation) của bộ điều phối GitHub Actions Scheduler.

---

### Tier 11: Tự Động Làm Mới Dashboard Trực Tuyến & Đồng Bộ Thời Gian Thực (Client Auto-Reload & Live Countdown Timer)

1. **Cơ Chế Tự Động Nạp Lại Trình Duyệt (Browser Client-Side Auto-Reload):**
   - Loại bỏ hoàn toàn sự phụ thuộc vào thao tác bấm phím F5 thủ công của người dùng khi theo dõi Dashboard trên máy tính hoặc điện thoại di động.
   - Tích hợp bộ đếm ngược thời gian thực (`Live Countdown Timer`) 60 giây hiển thị trực quan tại góc trên bên phải thanh Header (`🔄 Tự làm mới: 60s`).
   - Cung cấp nút thao tác tức thì `⚡ Tải lại ngay` cho phép người dùng chủ động nạp lại trang bất cứ lúc nào.
   - Cơ chế nạp lại chống lưu đệm trình duyệt (Cache-Busting Reload): Tự động gán tham số truy vấn thời gian thực `_t=Date.now()` khi tải lại, buộc trình duyệt luôn lấy phiên bản HTML mới nhất vừa được xuất bản từ CDN GitHub Pages.
   - Thẻ `<meta http-equiv="refresh" content="180">` đóng vai trò dự phòng an toàn (safe fallback) nếu trình duyệt chặn thực thi JavaScript.

2. **Hiển Thị Thời Gian Quét Thời Gian Thực (Scan Timestamping):**
   - Đóng dấu thời gian quét cụ thể theo múi giờ Việt Nam (UTC+7) trên thanh Header: `🕒 Cập nhật: HH:MM:SS • DD/MM/YYYY`.
   - Giúp nhà đầu tư định chế nhận diện tức thì độ tươi mới của dữ liệu vi cấu trúc và điểm mua bán trong phiên giao dịch.

---

### Tier 13: Cơ Chế Cập Nhật Giá Tự Động 5 Phút & Bảng Điện Tử Trực Tuyến (Live Dynamic Price Polling - ADR-010)

1. **Cập Nhật Giá Tự Động Phía Trình Duyệt (Browser Dynamic Live Ticker):**
   - Tận dụng Public Datafeed mở có hỗ trợ `Access-Control-Allow-Origin: *` từ Bảng giá VPS (`https://bgapidatafeed.vps.com.vn/getliststockdata/SYM1,SYM2,...`).
   - Cứ mỗi 5 phút (300 giây) hoặc ngay khi mở trang, mã JavaScript siêu nhẹ (~40 dòng) tự động truy vấn giá khớp mới nhất của toàn bộ cổ phiếu trên bảng.
   - Tự động điền giá vào các ô `class="live-price"` và đổi màu sắc đúng chuẩn Sở Giao dịch (Xanh lá / Đỏ / Tím trần / Xanh lam sàn / Vàng tham chiếu).
   - Hiển thị nhãn trạng thái trực tiếp: `🟢 Live 5m (HH:MM:SS)` phản ánh thời điểm kéo dữ liệu mới nhất.
   - Bộ đếm ngược tự động nạp lại trang định kỳ 5 phút (`🔄 Tự làm mới: 300s`) cùng thẻ dự phòng `<meta http-equiv="refresh" content="300">`.

2. **Chế Độ Local Watcher Daemon Cho Máy Trạm:**
   - Hỗ trợ tham số dòng lệnh `--watch` và `--interval 300` trong `src/hud/terminal.py`:
     ```bash
     python -m src.hud.terminal --watch --interval 300
     ```
   - Chạy vòng lặp ngầm trên máy trạm của người dùng để liên tục cập nhật và sinh lại file HTML mỗi 5 phút.

---

### Tier 14: Sổ Nhật Ký Đề Xuất Tự Động, Ma Trận Dòng Tiền Kép & Xuất Bản ML Dataset (ADR-011)

1. **Ma Trận Dòng Tiền Kép (Dual Flow Matrix: Ngoại vs Quỹ Nội Gom):**
   - Phân loại rõ nét 4 trạng thái dòng tiền định chế nhằm giải quyết triệt để đặc thù khối ngoại bán ròng tại TTCK Việt Nam:
     - `SIEU_SONG` (🟢🟢 ĐỒNG THUẬN): Ngoại gom + Nội gom (Tích lũy hạng A/B, RRG Leading).
     - `NOI_CAN_HANG` (🟢 NỘI CÂN HÀNG): Khối ngoại bán ròng hoặc trung tính nhưng Dòng tiền Nội (Quỹ nội Dragon Capital, SSIAM, Tự doanh, Cá mập nội) hấp thụ sạch cung bán giá thấp ở chân sóng.
     - `NGOAI_DO_GIA` (🔵 NGOẠI ĐỠ GIÁ): Ngoại gom đỡ chỉ số khi dòng tiền nội chưa sẵn sàng.
     - `RUI_RO_XA` (🔴 RỦI RO PHÂN PHỐI): Cả hai bên cùng thoái vốn (Phân phối hạng D/E, RRG Lagging).
   - Tích hợp nhãn nhận diện trên Terminal HUD và tập dữ liệu phân tích.

2. **Sổ Nhật Ký Tín Hiệu Online & Google Sheets Sync:**
   - Tự động ghi chép và theo dõi toàn diện vòng đời tín hiệu (P&L, MFE, MAE, trạng thái $T+2.5$, Take Profit, Trailing Stop).
   - Tự động đồng bộ hai chiều lên Google Sheets qua Apps Script Webhook siêu nhẹ, kết nối trực tiếp với Google Looker Studio để trực quan hóa hiệu suất hoàn toàn miễn phí.

3. **Xuất Bản Tự Động Tập Dữ Liệu ML `data/ml_signals_dataset.csv`:**
   - Lưu trữ Vector đặc trưng $T_0$ bất biến cùng biến mục tiêu $y$ (`outcome_label`, `target_win_binary`) phục vụ huấn luyện các mô hình Machine Learning / Deep Learning trên Google Colab.

---

### Tier 15: Đồng Bộ Hóa Toàn Diện Dashboard & Live Ticker 30 Giây (ADR-012)

1. **Xóa Bỏ Hardcode & Tính Toán Động 4 Thẻ Chỉ Số Header:**
   - **Dòng Tiền Cá Mập (Smart Money):** Tính tổng mua/bán ròng thực tế của khối ngoại và tự doanh từ danh mục Top cổ phiếu; phản ánh chính xác trạng thái ngoại xả nội gom thay vì số liệu cứng.
   - **Độ Rộng Danh Mục (Momentum Breadth):** Tính tỷ lệ cổ phiếu giữ xung lực dẫn dắt (RS/Composite $\ge 70$).
   - **Ngành Dẫn Dắt (Leading Sector):** Gom nhóm ngành tự động dựa trên tọa độ RRG thực tế và số lượng ứng viên dẫn đầu.
   - **Gán ID Semantic:** Cung cấp ID cho tất cả thẻ chỉ số để JavaScript cập nhật thời gian thực.

2. **Vòng Lặp Polling 30 Giây Phía Trình Duyệt (Real-Time Live Ticker):**
   - Lặp lại `fetchLivePrices()` định kỳ mỗi 30 giây (`setInterval(fetchLivePrices, 30000)`), liên tục kéo giá từ VPS Datafeed.
   - Đồng bộ cột giá khớp kèm `% Biến động` đổi màu chuẩn Sở Giao dịch.
   - Tự động đánh giá lại Vùng Mua và Cắt Lỗ thời gian thực: Cảnh báo `MUA ĐUỔI ⚠️` nếu giá vượt quá $3\%$ điểm bùng nổ, `CHẠM SL 🔴` khi thủng stop loss, `ĐẠT TP1 🎯` khi chạm chốt lời 1.
   - Cập nhật nhãn thời gian phân định rõ ràng giữa chu kỳ quét AI toàn diện và dòng giá khớp lệnh trực tuyến.
