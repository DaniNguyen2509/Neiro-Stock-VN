# Neiro-Stock-VN: Quantitative & Fundamental Trading System (Quantamental)
> Hệ thống định lượng dòng tiền kết hợp phân tích cơ bản chuyên sâu (Quantamental Architecture) dành riêng cho **Thị trường Chứng khoán Việt Nam (HOSE, HNX, UPCoM & Phái sinh VN30F1M)**.

---

## 1. Giới Thiệu & Triết Lý Cốt Lõi

**Neiro-Stock-VN** được kế thừa các nguyên lý định lượng tinh hoa từ hệ thống giao dịch vi cấu trúc vàng **Neiro-Quant**, nhưng được thiết kế lại toàn diện để thích ứng hoàn hảo với các đặc thù vi mô của thị trường chứng khoán Việt Nam:

| Trục So Sánh | Thị Trường Vàng Quốc Tế (Neiro-Quant) | TTCK Việt Nam (Neiro-Stock-VN) |
|---|---|---|
| **Sản phẩm trọng tâm** | Gold Futures (`GCZ26`), CME Options (`OGX26`), XAUUSD Spot | Cổ phiếu cơ sở (HOSE, HNX, UPCoM), HĐTL Chỉ số (`VN30F1M`) |
| **Công cụ phái sinh** | Chuỗi quyền chọn CME cực sâu (Greeks, Net GEX, DEX, VEX) | HĐTL VN30F1M, Chứng quyền có bảo đảm (Covered Warrants) |
| **Chu kỳ thanh toán** | T+0 tức thì (mua bán khớp và tất toán ngay) | **T+2.5 / T+1.5** (rủi ro kẹt hàng qua đêm, không thể cắt lỗ ngay) |
| **Biên độ giá** | Không biên độ trần/sàn (biến động liên tục 24/5) | **HOSE $\pm 7\%$, HNX $\pm 10\%$, UPCoM $\pm 15\%$, VN30F1M $\pm 7\%$** |
| **Cấu trúc phiên** | Giao dịch điện tử liên tục 23h/ngày | ATO (09:00-09:15), Khớp lệnh liên tục, **ATC (14:30-14:45)** |
| **Lực lượng dẫn dắt** | Dealer / Market Makers toàn cầu, Quỹ CTA, Ngân hàng TW | Cá nhân nhỏ lẻ ($80-85\%$), **Khối ngoại, Tự doanh CTCK** |
| **Động lực giá** | Lãi suất thực TIPS, DXY, Địa chính trị, Gold Flow ETF | **Tăng trưởng EPS/Doanh thu, Chu kỳ ngành, Lãi suất NHNN, Margin** |

### Triết Lý Quantamental (Quant + Fundamental)
- **Không đoán mò đỉnh đáy, loại bỏ chỉ báo kỹ thuật trễ:** Tuyệt đối không dùng các chỉ báo kỹ thuật đơn lẻ (RSI, MACD, Bollinger Bands) để dự báo.
- **Hợp lưu 2 trụ cột:**
  1. **Chất lượng cơ bản định lượng (Fundamental Quant):** Lọc doanh nghiệp bằng thang điểm **Piotroski F-Score (0-9)**, tốc độ tăng trưởng doanh thu/lợi nhuận cốt lõi (Core EBIT, EPS), kiểm tra chất lượng dòng tiền kinh doanh ($CFO / Net Income > 1.0$), và định giá phân vị lịch sử 3-5 năm (P/E, P/B Historical Bands).
  2. **Cấu trúc vi mô sổ lệnh & dòng tiền (Microstructure & Order Flow):** Phân tích bản đồ thanh khoản **Volume Profile (POC, HVN, LVN / Air Pockets)**, áp lực mua/bán chủ động ($OFI$), quét lệnh lô lớn của Cá mập ($\ge 100k$), theo dõi dòng tiền mua bán ròng của Khối ngoại & Tự doanh, và đo độ lệch Basis HĐTL VN30F1M.
- **Quản trị rủi ro chu kỳ T+2.5:** Áp dụng chiến lược **Rolling Inventory (Đệm hàng sẵn có T+0)** và công cụ phòng hộ danh mục bằng Short VN30F1M khi thị trường gãy hỗ trợ quan trọng.

---

## 2. Kiến Trúc Định Lượng Toàn Diện (System Engines & Tiers)

1. **Tier 1 - Quantitative Fundamental Screening:** Bộ lọc tự động CANSLIM, Piotroski F-Score $\ge 7$, CFO/NI $> 1.0$, và P/E Percentile Banding.
2. **Tier 2 - Market Microstructure & Order Flow:** Volume Profile tại từng mức giá (Point of Control POC, Value Area VAH/VAL 70%, High Volume Nodes HVN, Low Volume Nodes / Air Pockets LVN) và Order Flow Imbalance (OFI).
3. **Tier 3 - Institutional Smart Money Tracking:** Giám sát dòng tiền Khối ngoại ($\Delta Foreign$), Tự doanh CTCK ($\Delta Prop$), Lệnh thỏa thuận và Chỉ số phân kỳ dòng tiền Cá mập (SMDI).
4. **Tier 4 - Derivatives VN30F1M Basis & Hedging:** Đo lường chênh lệch Basis ($VN30F1M - VN30$), phát hiện bẫy đáo hạn phái sinh và tính toán tỷ lệ Short phòng hộ cho danh mục cơ sở.
5. **Tier 5 - Macro & Sector Rotation (RRG):** Mô hình Relative Rotation Graph định lượng sức mạnh giá ($RS\text{-Ratio}$) và gia tốc ($RS\text{-Momentum}$) của 12 nhóm ngành trên sàn.
6. **Tier 6 - T+2.5 Risk & Position Sizing:** Định lượng quy mô giải ngân an toàn theo $ATR(14)$, kiểm soát tỷ lệ Margin và cảnh báo sớm nguy cơ Force Sell chéo.
7. **Tier 7 - Dynamic Trailing Stop & Ranking History (ADR-006):** Initial SL, Break-Even Ratchet tại $1.5R$, Chandelier Exit đỉnh $2.0 \times \text{ATR}$, và theo vết $\Delta Rank$ chuỗi thời gian.
8. **Tier 8 - Resilient Fallback & Credential Sanitization (ADR-007):** Khử nhiễu khoảng trắng/ký tự ẩn secrets, đèn báo dữ liệu, và fallback bảng giá công khai Entrade/DNSE.
9. **Tier 9 - Client-Side Auto-Reload & Live Countdown Timer (ADR-008):** Đếm ngược thời gian thực, nút nạp lại tức thì `⚡ Tải lại ngay`, và đóng dấu múi giờ VN (UTC+7).
10. **Tier 10 - Background Anti-FOMO Signal Ledger & Chasing Prevention (ADR-009):** Sổ cái tín hiệu ngầm 100% trên GitHub Actions, đo trượt giá sau 4-5 ngày, cấm mua đuổi $> +5.0\%$ (`EXTENDED_NO_CHASING`), xuất bản `advisory_scorecard.md`.
11. **Tier 11 - 5-Minute Live Dynamic Price Polling & Local Watcher (ADR-010):** Kéo trực tiếp giá khớp lệnh thời gian thực 5 phút/lần từ Public Datafeed VPS (CORS `*`), tự động đổi màu chuẩn sàn (Tím/Xanh/Đỏ/Vàng), đếm lùi 300s và hỗ trợ cờ `--watch` chạy ngầm cục bộ.

---

## 3. Cấu Trúc Dự Án

```
Neiro-Stock-VN/
├── .agents/skills/               # 25 bộ kỹ năng chuẩn cho AI Coding Agents
├── docs/
│   ├── spec.md                   # Bản đặc tả kỹ thuật chi tiết hệ thống
│   ├── architecture.md           # Kiến trúc hệ thống và luồng dữ liệu toàn cảnh
│   ├── thuat_ngu_quant_vn.md     # Từ điển thuật ngữ Quantamental & Vi cấu trúc TTCK VN
│   ├── TRADER_PLAYBOOK_VN.md     # Cẩm nang tác chiến thực chiến cho Trader / Quỹ
│   ├── google_sheets_setup.md    # Hướng dẫn thiết lập Google Sheets, Looker Studio & ML
│   └── decisions/                # Architecture Decision Records (ADRs: ADR-001 -> ADR-014)
├── src/
│   ├── collector/                # Thu thập & chuẩn hóa dữ liệu TTCK VN, Google Sheets Client (ADR-011)
│   ├── fundamental_engine/       # Bộ lọc Piotroski F-score, EPS, PE/PB Banding
│   ├── microstructure_engine/    # Volume Profile (POC/HVN/LVN), OFI, Basis VN30F1M
│   ├── sector_engine/            # Mô hình luân chuyển ngành RRG & Độ rộng thị trường
│   ├── risk_engine/              # Quản trị T+2.5, Rolling Position, ATR Sizing, Signal Tracker & ML (ADR-009/011)
│   ├── backtesting/              # Walk-Forward Backtesting T+2.5 (Look-ahead & PIT Defense)
│   └── hud/                      # Giao diện Tactical Terminal Web Đa Tab (Auto-Reload, Dark Mode)
├── data/                         # Dữ liệu mẫu benchmark, ranking_history.jsonl, active_signals.jsonl, ml_signals_dataset.csv
├── exports/                      # Tệp HTML Terminal xuất bản (GitHub Pages)
├── tests/                        # Kiểm thử tự động Unit & Math verification (91/91 passed 100%)
├── AGENTS.md / GEMINI.md         # Quy tắc bắt buộc gọi Skill & Zero-Waste Mandate
├── requirements.txt              # Thư viện Python phụ thuộc
├── pyproject.toml                # Cấu hình ruff & pytest
└── README.md                     # Hướng dẫn tổng quan & Bắt đầu nhanh
```

---

## 4. Hướng Dẫn Bắt Đầu Nhanh (Quick Start)

### 4.1. Cài đặt môi trường
```bash
# Clone repository từ GitHub
git clone https://github.com/DaniNguyen2509/Neiro-Stock-VN.git
cd Neiro-Stock-VN

# Khởi tạo môi trường ảo Python
python -m venv .venv
.venv\Scripts\activate

# Cài đặt thư viện phụ thuộc
pip install -r requirements.txt
```

### 4.2. Chạy kiểm thử tự động
```bash
# Chạy 100% Unit Tests xác minh tính toán toán học & T+2.5 Backtest (91/91 passed 100%)
python -m pytest tests/ -v --tb=short

# Kiểm tra quy chuẩn mã nguồn (Ruff)
python -m ruff check src/ tests/
```

### 4.3. Chạy các module định lượng
```bash
# 1. Chạy bộ lọc Quantamental Cổ phiếu (F-score, P/E Banding)
python -m src.fundamental_engine.screener --top 20

# 2. Phân tích Volume Profile và vùng thanh khoản cho cổ phiếu (ví dụ HPG)
python -m src.microstructure_engine.volume_profile --symbol HPG

# 3. Phân tích luân chuyển dòng tiền ngành (RRG Rotation)
python -m src.sector_engine.rrg_rotation

# 4. Quét tự động Top 20 Siêu cổ phiếu chân sóng, BCTC 4 quý & Tin tức (Fialda VIP Expert Scanner)
python -m src.collector.fialda_scanner --top 20 --save-report reports/latest_scan.md --generate-terminal

# 5. Chạy Kiểm Định Quá Khứ Walk-Forward T+2.5 & Xuất Bản Dashboard Web Đa Tab
python -m src.hud.terminal --output exports/index.html

# 6. Chạy chế độ Watcher ngầm trên máy cá nhân (Tự động cập nhật 5 phút/lần)
python -m src.hud.terminal --watch --interval 300
```

### 4.4. Cấu hình Tài khoản VIP Fialda (Tùy chọn cục bộ)
Tạo file `.env` từ file mẫu `.env.example`:
```bash
cp .env.example .env
```
Điền thông tin tài khoản VIP:
```env
FIALDA_USERNAME=your_vip_email@example.com
FIALDA_PASSWORD=your_password
```
*Lưu ý:* File `.env` được bảo vệ nghiêm ngặt trong `.gitignore` và không bao giờ được commit lên Git. Hệ thống tự động fallback sang bộ dữ liệu mẫu benchmark nếu không có tài khoản.

### 4.5. Tự Động 100% Trên GitHub (Xem Mọi Lúc Mọi Nơi 24/7)
Hệ thống được trang bị workflow **GitHub Actions CI/CD** tự động hoàn toàn:
- **Lịch trình quét tự động 30 phút/lần chuẩn POSIX (Giờ Việt Nam - Thứ 2 đến Thứ 6):**
  - **Phiên sáng:** `09:15`, `09:45`, `10:15`, `10:45`, `11:15`, `11:45` (Quét từ mở cửa ATO đến hết phiên sáng).
  - **Phiên chiều:** `13:15`, `13:45`, `14:15`, `14:45` (Quét hấp thụ tin tức trưa, hàng T+2.5 về tài khoản và đón sóng ATC).
  - **Chốt phiên:** `15:05` (Chốt dữ liệu đóng cửa phiên chính thức toàn thị trường).
  - **Chốt Tự doanh & Khối ngoại chiều:** `17:30` (Cập nhật sớm dòng tiền Tự doanh CTCK & Thỏa thuận cá mập).
  - **Chốt sổ toàn diện buổi tối (EOD Final Smart Money):** `19:00` (Khóa băng toàn diện 100% dòng tiền Tự doanh, Khối ngoại, Phái sinh VSDC để review chiến lược tối).
- **Kích hoạt thủ công bất kỳ lúc nào:** Vào tab **Actions** trên GitHub (trên máy tính hoặc ứng dụng di động GitHub Mobile) -> Chọn workflow **Fialda VIP Expert Scanner & GitHub Pages Deploy** -> Bấm **Run workflow**.
- **Địa chỉ truy cập Dashboard trực tiếp trên Mobile/Web:**
  - **GitHub Pages:** `https://daninguyen2509.github.io/Neiro-Stock-VN/` (Giao diện Dark Mode tương tác mượt mà trên iPhone/Android với Top 20 cổ phiếu, BCTC 4 quý, Tin tức & Sự kiện; tích hợp **Bộ đếm ngược Live Countdown 300s, Tự động kéo giá Live 5 phút/lần từ VPS Datafeed & Auto-Reload** không cần bấm F5).
  - **GitHub Mobile App:** Mở lượt chạy Action bất kỳ, bảng xếp hạng Top 20 và **Báo Cáo Đối Chiếu Sổ Cái Tín Hiệu & Radar Chống Mua Đuổi (Advisory Scorecard)** hiển thị tức thì ngay trong tab **Summary**.
- **Cấu hình GitHub Secrets:**
  Vào repository: **Settings** -> **Secrets and variables** -> **Actions** -> Thêm 2 Secrets:
  - `FIALDA_USERNAME`: Email tài khoản Fialda VIP.
  - `FIALDA_PASSWORD`: Mật khẩu tài khoản Fialda VIP.
- **Kích hoạt GitHub Pages:**
  Vào **Settings** -> **Pages** -> Tại mục **Build and deployment**, chọn **Source: Deploy from a branch** với Branch là **gh-pages / (root)** để xem trực tiếp ngay lập tức tại:
  `https://daninguyen2509.github.io/Neiro-Stock-VN/`

### 4.6. Sổ Nhật Ký Tín Hiệu Online, Ma Trận Dòng Tiền Kép & Machine Learning Dataset (ADR-011)
- **Ma Trận Dòng Tiền Kép (Dual Flow Matrix):** Phân định 4 trạng thái dòng tiền định chế (`🟢🟢 SIEU_SONG` Đồng thuận Ngoại + Nội gom, `🟢 NOI_CAN_HANG` Sóng Quỹ nội gom cân sạch cung xả giá thấp, `🔵 NGOAI_DO_GIA`, `🔴 RUI_RO_XA`). Giúp phân biệt rõ bản chất "Ngoại bán nhưng Quỹ nội gom thì cổ phiếu vẫn vào siêu sóng".
- **Sổ Nhật Ký Tự Động & Google Sheets Webhook:** Tự động đồng bộ các khuyến nghị lên Google Sheets qua Apps Script Webhook siêu nhẹ, kết nối trực tiếp với **Google Looker Studio** hiển thị Dashboard phân tích trực quan 100% miễn phí.
- **Tập Dữ Liệu Huấn Luyện AI/ML (`data/ml_signals_dataset.csv`):** Tự động xuất bản và duy trì cấu trúc dữ liệu phẳng không rò rỉ tương lai ($T_0$ features vs $T+2.5/T+5$ outcomes) cho phép tải trực tiếp vào Google Colab (`pd.read_csv(...)`) để train mô hình Machine Learning.

### 4.7. Đồng Bộ Hóa Toàn Diện Dashboard, Live Ticker 30 Giây & Fallback Biến Động Thứ Hạng (ADR-012)
- **Xóa Bỏ Hoàn Toàn Hardcode:** 4 Thẻ chỉ số Header (Chênh lệch Basis, Dòng tiền Cá mập Ngoại/Nội, Độ rộng danh mục, Ngành dẫn dắt RRG) được tính toán động 100% từ dữ liệu thực tế, giải quyết triệt để tình trạng số liệu thẻ mâu thuẫn với bảng Top 20 bên dưới.
- **Vòng Lặp Kéo Giá Live 30 Giây (Live Ticker Stream):** JavaScript trình duyệt tự động cập nhật giá khớp lệnh và `% Biến động` mỗi 30 giây trực tiếp từ VPS Datafeed, đồng thời đánh giá lại Vùng Mua (`MUA ĐUỔI ⚠️`), Cắt Lỗ (`CHẠM SL 🔴`) và Chốt Lời (`ĐẠT TP1 🎯`) theo thời gian thực.
- **Cơ Chế Fallback Lịch Sử Cột Kỳ Trước:** Tự động tra cứu toàn bộ lịch sử quét để so sánh rank với lần xuất hiện gần nhất của cổ phiếu. Nếu mã chỉ tạm rớt khỏi Top 20 một phiên quét rồi quay lại, hệ thống sẽ tính toán $\Delta Rank$ chính xác dựa trên rank cũ thay vì gán nhãn `🆕 MỚI` gây nhiễu.

### 4.8. Quy Chuẩn Audit Dashboard Đa Tầng & Audit Từng Cột Dữ Liệu Thực Chiến (ADR-013)
- **Bộ Kỹ Năng Độc Quyền `multi-layer-dashboard-audit`:** Định hình quy trình kiểm định 3 tầng độc lập (Tầng 1: Presentation & Stream, Tầng 2: Data Pipeline & Continuity, Tầng 3: Column-by-Column Domain Logic) chống lại hội chứng "Hút tầm nhìn" (Tunnel Vision).
- **Điều Luật Bắt Buộc Tối Cao (AGENTS.md & GEMINI.md):** Bắt buộc mọi AI model khi review giao diện phải audit chi tiết từng cột số liệu, đặt mình vào vị thế nhà đầu tư thực tế (Investor Persona Test), tuyệt đối không dừng lại ở việc sửa lỗi hiển thị bề nổi.

### 4.9. Chẩn Đoán Bảng Dashboard Bị Đứng, Khử Nghẽn Scheduler và Phòng Vệ Client Live Stream (ADR-015)
- **Khử Nghẽn Hàng Đợi GitHub Actions (Scheduler Decollision):** Chuyển dịch toàn bộ các mốc cron sang phút lệch (`:18`, `:48`, `:08`, `:35`) thay vì các mốc tròn phổ biến (`:00`, `:15`, `:30`, `:45`) nhằm tránh tình trạng bị GitHub Scheduler drop hoặc delay hàng tiếng đồng hồ do quá tải bot toàn cầu.
- **Phòng Vệ Client Live Stream (WAF HTML Guard):** Tăng cường hàm JavaScript `fetchLivePrices()` tại Dashboard để kiểm tra dữ liệu trước khi parse JSON, ngăn chặn triệt để tình trạng máy chủ ngoài trả về mã HTML lỗi (WAF / Rate limit) khiến client bị rơi vào trạng thái `Offline` đóng băng.
- **Đồng Bộ Hoàn Toàn Nhánh Main:** Bổ sung `exports/index.html` và `exports/404.html` vào quy trình commit tự động của GitHub Actions, đảm bảo nhánh `main` và nhánh `gh-pages` luôn luôn đồng nhất số liệu quét mới nhất.
---

## 5. Quy Chuẩn Vận Hành AI Agent (Zero-Waste & Skill Protocol)

- **Bắt buộc gọi Skill trước mọi hành động:** Mỗi lượt phản hồi của AI model đều phải kiểm tra và áp dụng skill từ `.agents/skills/` tương ứng với công việc (xem chi tiết tại `AGENTS.md` và `GEMINI.md`).
- **Tiêu chuẩn Zero-Waste:** Toàn bộ dự án luôn được giữ siêu nhẹ (< 15MB), tự động thu hồi RAM, xóa cache tạm thời sau khi xử lý dữ liệu.
- **Đồng bộ tài liệu (Documentation-First):** Bất kỳ nâng cấp tính năng hoặc thay đổi logic nào đều phải được cập nhật ngay vào `docs/spec.md` và `docs/architecture.md`.
