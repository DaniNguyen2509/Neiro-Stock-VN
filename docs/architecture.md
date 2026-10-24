# Architecture: Neiro-Stock-VN Architecture Overview

## 1. Toàn Cảnh Kiến Trúc Hệ Thống (System Architecture)

Neiro-Stock-VN được thiết kế theo mô hình kiến trúc phân lớp độc lập (Layered Decoupled Architecture), tối ưu hóa cho môi trường vận hành nhẹ (< 15MB), không yêu cầu hạ tầng server cồng kềnh, chạy mượt mà trên cả máy tính cá nhân lẫn môi trường CI/CD Cloud (GitHub Actions / Colab).

```mermaid
flowchart TD
    subgraph Data_Sources ["1. Data Ingestion Layer (Nguồn Dữ Liệu)"]
        D1["HOSE / HNX / UPCoM Price Feeds (OHLCV)"]
        D2["Financial Statements (BCTC Q/Y, IFRS/VAS)"]
        D3["Foreign & Prop Net Flow (Khối Ngoại & Tự Doanh)"]
        D4["HNX Derivatives VN30F1M (Sổ Lệnh & Basis)"]
        D5["Macro & SBV Policy (T-Bills, OMO, Lãi suất)"]
    end

    subgraph Quant_Engines ["2. Quantamental Core Processing"]
        FE["Fundamental Engine\n- Piotroski F-Score (0-9)\n- Core EPS & Sales Growth\n- CFO/NI Quality Ratio\n- Historical PE/PB Banding"]
        ME["Microstructure Engine\n- Volume Profile (POC, HVN, LVN)\n- Value Area (VAH, VAL 70%)\n- Order Flow Imbalance (OFI)\n- Large Block Tracker (>= 100k)"]
        SE["Sector & Macro Engine\n- Relative Rotation Graph (RRG)\n- RS-Ratio & RS-Momentum\n- Market Breadth (MA20/50/200)\n- Leading/Lagging Matrix"]
        DE["Derivatives Basis Engine\n- Basis = VN30F1M - VN30\n- Contango / Backwardation Tracker\n- T+2.5 Beta Hedge Calculator"]
    end

    subgraph Risk_Orchestrator ["3. Execution & Risk Engine"]
        RE["Risk Engine\n- Volatility-Adjusted ATR Sizing\n- Rolling Inventory Manager (T+0 Cushion)\n- Margin Call Buffer & Force Sell Radar"]
    end

    subgraph HUD_Presentation ["4. Tactical HUD Terminal Layer"]
        HUD["Plotly Interactive Dark Terminal\n- Multi-Panel Volume Profile\n- Screener Ranked Table\n- RRG Quadrant Radar\n- Basis Spread Gauge\n- Actionable Trade Cards"]
        OUT["HTML Web Exports & Alerts\n(exports/vn_stock_terminal.html)"]
    end

    D1 & D2 --> FE
    D1 & D3 & D4 --> ME
    D1 & D5 --> SE
    D1 & D4 --> DE

    FE & ME & SE & DE --> RE
    RE --> HUD
    HUD --> OUT
```

---

## 2. Chi Tiết Các Tầng Xử Lý (Layer Breakdown)

### 2.1. Tầng Thu Thập & Chuẩn Hóa Dữ Liệu (`src/collector/`)
- **`vn_market_client.py`:** Đầu mối tích hợp API chuẩn hóa dữ liệu từ các nền tảng tài chính Việt Nam (VNDirect, Vietstock, TCBS, SSI, FiinTrade hoặc thư viện mã nguồn mở `vnstock`). Hỗ trợ cơ chế failover dự phòng và mock benchmark data cho unit tests.
- **`data_loader.py`:** Làm sạch dữ liệu, xử lý các sự kiện chia tách cổ tức, tăng vốn, thưởng cổ phiếu; chuyển đổi cấu trúc BCTC chuẩn VAS về dataclasses định lượng nhất quán.
- **`fialda_scanner.py`:** Khai thác chuyên sâu hệ thống **Fialda VIP Expert & Swagger API** (529 endpoints):
  - Tự động xác thực JWT Token (`/api/TokenAuth/Authenticate`) với chu kỳ hiệu lực 24 giờ.
  - Thu thập tín hiệu AI Expert: Chờ Mua Chân Sóng (`GetTinHieuChoMuaNew`), Đột biến Giá trị giao dịch (`GetTinHieuDotBienGiaTri`).
  - Trích xuất bộ chỉ số định chế IBD O'Neil: Sức mạnh giá RS 1 tháng (`rS1M`), Điểm tổng hợp (`compositeRating`), Hệ số Tích lũy/Phân phối (`accDissRating`).
  - Nạp toàn bộ ma trận luân chuyển dòng tiền RRG 1,530 mã toàn thị trường (`GetRRGData`).
  - Lọc đa biến chọn lọc **Top 5 Siêu cổ phiếu bứt phá chân sóng** (khung 1 tháng, biên lợi nhuận kỳ vọng $+20\% - +35\%$, cắt lỗ chặt chẽ $-5.5\%$).

### 2.2. Tầng Định Lượng Cơ Bản (`src/fundamental_engine/`)
- **`screener.py`:** Bộ lọc đa biến lọc ra Top $10\% - 15\%$ doanh nghiệp chất lượng cao nhất toàn sàn:
  - Lọc sơ bộ vốn hóa: Market Cap $\ge 1,000$ tỷ VND, Khối lượng trung bình 20 phiên $\ge 200,000$ cp/phiên (loại bỏ cổ phiếu penny thanh khoản rác).
  - Điểm số tài chính Piotroski F-score $\ge 7/9$.
  - Chất lượng dòng tiền: $CFO / Net Income > 1.0$.
- **`valuation.py`:** Tính toán dải định giá phân vị lịch sử 3 năm (P/E Percentile Band, P/B Percentile Band), xác định vùng tích lũy rẻ định chế.

### 2.3. Tầng Cấu Trúc Vi Mô & Sổ Lệnh (`src/microstructure_engine/`)
- **`volume_profile.py`:** Thuật toán phân rã khối lượng giao dịch tích lũy theo từng bước giá (Price Bins):
  - Tính toán chính xác mức giá Point of Control (POC).
  - Vùng giá trị Value Area (VAH, VAL) chiếm $70\%$ khối lượng giao dịch.
  - Phân loại High Volume Nodes (HVN - Thành trì phòng ngự) và Low Volume Nodes (LVN / Air Pockets - Vùng chân không thanh khoản kích hoạt đà rơi/tăng tốc).
- **`order_flow.py`:** Đo lường tỷ lệ lệnh mua chủ động vs. bán chủ động ($OFI$), quét các lệnh khớp lô lớn $\ge 100,000$ cổ phiếu để xác định sự xuất hiện của Big Boys.
- **`basis_tracker.py`:** Theo dõi chênh lệch Basis giữa hợp đồng tương lai VN30F1M và chỉ số VN30 Index, nhận diện trạng thái Contango / Backwardation để dự báo điểm đảo chiều của thị trường cơ sở.

### 2.4. Tầng Luân Chuyển Ngành & Vĩ Mô (`src/sector_engine/`)
- **`rrg_rotation.py`:** Tính toán ma trận Relative Rotation Graph (RRG) cho 12 nhóm ngành chủ lực của nền kinh tế Việt Nam (Ngân hàng, Bất động sản, Thép, Chứng khoán, Bán lẻ, Hóa chất, Dầu khí, Đầu tư công, Điện nước, CNTT, Thủy sản, Dệt may).
  - Phân loại ngành vào 4 góc phần tư: Leading, Weakening, Lagging, Improving.
- **`market_breadth.py`:** Đo lường độ rộng thị trường (tỷ lệ cổ phiếu trên MA20, MA50, MA200, đường Advance-Decline Line) để phát hiện sớm các hiện tượng "kéo trụ xả danh mục" (Green Index - Red Market).

### 2.5. Tầng Quản Trị Rủi Ro & Vị Thế T+2.5 (`src/risk_engine/`)
- **`position_sizer.py`:** Tính toán quy mô giải ngân an toàn dựa trên rủi ro biến động $ATR(14)$ của cổ phiếu, khống chế mức lỗ tối đa cho mỗi vị thế không vượt quá $1.5\% - 2.0\%$ tổng NAV tài khoản.
- **`t25_manager.py`:** Quản trị vòng quay hàng sẵn có (Rolling Inventory), thiết lập cơ chế khóa lợi nhuận hoặc phòng hộ danh mục bằng HĐTL VN30F1M khi thị trường vi phạm các mốc thanh khoản trọng yếu.

### 2.6. Tầng Giao Diện Tác Chiến (`src/hud/`)
- **`terminal.py`:** Sinh mã nguồn HTML Plotly tương tác hoàn chỉnh, hỗ trợ chế độ Dark Mode hiện đại, giao diện trực quan theo tiêu chuẩn Bloomberg/TradingView, bao gồm:
  - Panel 1: Biểu đồ nến kết hợp Volume Profile ngang, đánh dấu rõ POC, VAH, VAL, HVN, LVN.
  - Panel 2: Biểu đồ RRG luân chuyển dòng tiền ngành 4 pha.
  - Panel 3: Bảng xếp hạng Quantamental Screener (Mã, F-Score, PE Percentile, OFI, Khối ngoại, Khuyến nghị).
  - Panel 4: Thanh trạng thái Basis VN30F1M và Khối ngoại / Tự doanh trong phiên.

---

## 3. Quản Lý Bộ Nhớ & Tiêu Chuẩn Zero-Waste

- **Zero Memory Leak:** Toàn bộ các cấu trúc dữ liệu chuỗi thời gian đều được ép kiểu `float32` hoặc `int32` trong Pandas/NumPy, tránh phát sinh overhead bộ nhớ.
- **Tự động dọn dẹp Cache:** Các tệp cache dữ liệu tạm thời trong `data/` được giới hạn kích thước và tự động dọn sạch sau khi hoàn tất pipeline kiểm thử.
- **Tổng dung lượng toàn bộ repository:** Đảm bảo duy trì dưới mức **15MB**, bảo vệ tối đa dung lượng ổ cứng của người dùng.
