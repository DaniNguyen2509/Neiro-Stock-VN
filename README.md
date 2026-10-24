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

## 2. Kiến Trúc 6 Tầng Định Lượng (6-Tier Engine)

1. **Tier 1 - Quantitative Fundamental Screening:** Bộ lọc tự động CANSLIM, Piotroski F-Score $\ge 7$, CFO/NI $> 1.0$, và P/E Percentile Banding.
2. **Tier 2 - Market Microstructure & Order Flow:** Volume Profile tại từng mức giá (Point of Control POC, Value Area VAH/VAL 70%, High Volume Nodes HVN, Low Volume Nodes / Air Pockets LVN) và Order Flow Imbalance (OFI).
3. **Tier 3 - Institutional Smart Money Tracking:** Giám sát dòng tiền Khối ngoại ($\Delta Foreign$), Tự doanh CTCK ($\Delta Prop$), Lệnh thỏa thuận và Chỉ số phân kỳ dòng tiền Cá mập (SMDI).
4. **Tier 4 - Derivatives VN30F1M Basis & Hedging:** Đo lường chênh lệch Basis ($VN30F1M - VN30$), phát hiện bẫy đáo hạn phái sinh và tính toán tỷ lệ Short phòng hộ cho danh mục cơ sở.
5. **Tier 5 - Macro & Sector Rotation (RRG):** Mô hình Relative Rotation Graph định lượng sức mạnh giá ($RS\text{-Ratio}$) và gia tốc ($RS\text{-Momentum}$) của 12 nhóm ngành trên sàn.
6. **Tier 6 - T+2.5 Risk & Position Sizing:** Định lượng quy mô giải ngân an toàn theo $ATR(14)$, kiểm soát tỷ lệ Margin và cảnh báo sớm nguy cơ Force Sell chéo.

---

## 3. Cấu Trúc Dự Án

```
Neiro-Stock-VN/
├── .agents/skills/               # 24 bộ kỹ năng chuẩn cho AI Coding Agents
├── docs/
│   ├── spec.md                   # Bản đặc tả kỹ thuật chi tiết hệ thống
│   ├── architecture.md           # Kiến trúc hệ thống và luồng dữ liệu toàn cảnh
│   ├── thuat_ngu_quant_vn.md     # Từ điển thuật ngữ Quantamental & Vi cấu trúc TTCK VN
│   ├── TRADER_PLAYBOOK_VN.md     # Cẩm nang tác chiến thực chiến cho Trader / Quỹ
│   └── decisions/                # Architecture Decision Records (ADRs)
│       └── ADR-001-quantamental-foundations-for-vn-equities.md
├── src/
│   ├── collector/                # Thu thập & chuẩn hóa dữ liệu TTCK VN
│   ├── fundamental_engine/       # Bộ lọc Piotroski F-score, EPS, PE/PB Banding
│   ├── microstructure_engine/    # Volume Profile (POC/HVN/LVN), OFI, Basis VN30F1M
│   ├── sector_engine/            # Mô hình luân chuyển ngành RRG & Độ rộng thị trường
│   ├── risk_engine/              # Quản trị T+2.5, Rolling Position, ATR Sizing
│   └── hud/                      # Giao diện Tactical Terminal Web Plotly (Dark Mode)
├── data/                         # Dữ liệu mẫu benchmark phục vụ kiểm thử
├── exports/                      # Tệp HTML Terminal xuất bản
├── tests/                        # Kiểm thử tự động Unit & Math verification
├── AGENTS.md / GEMINI.md         # Quy tắc bắt buộc gọi Skill & Zero-Waste Mandate
├── requirements.txt              # Thư viện Python phụ thuộc
├── pyproject.toml                # Cấu hình ruff & pytest
└── README.md                     # Tài liệu giới thiệu dự án
```

---

## 4. Hướng Dẫn Bắt Đầu Nhanh (Quick Start)

### 4.1. Cài đặt môi trường
```bash
# Khởi tạo môi trường ảo Python
python -m venv .venv
.venv\Scripts\activate

# Cài đặt thư viện phụ thuộc
pip install -r requirements.txt
```

### 4.2. Chạy kiểm thử tự động
```bash
# Chạy 100% Unit Tests xác minh tính toán toán học
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

# 4. Xuất bản Tactical Terminal Web (Dark Theme)
python -m src.hud.terminal --output exports/vn_stock_terminal.html
```

---

## 5. Quy Chuẩn Vận Hành AI Agent (Zero-Waste & Skill Protocol)

- **Bắt buộc gọi Skill trước mọi hành động:** Mỗi lượt phản hồi của AI model đều phải kiểm tra và áp dụng skill từ `.agents/skills/` tương ứng với công việc (xem chi tiết tại `AGENTS.md` và `GEMINI.md`).
- **Tiêu chuẩn Zero-Waste:** Toàn bộ dự án luôn được giữ siêu nhẹ (< 15MB), tự động thu hồi RAM, xóa cache tạm thời sau khi xử lý dữ liệu.
- **Đồng bộ tài liệu (Documentation-First):** Bất kỳ nâng cấp tính năng hoặc thay đổi logic nào đều phải được cập nhật ngay vào `docs/spec.md` và `docs/architecture.md`.
