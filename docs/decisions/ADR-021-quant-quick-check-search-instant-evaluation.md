# ADR-021: Tìm Kiếm Định Lượng & Đánh Giá Cổ Phiếu Tức Thì (Quant Quick-Check Search)

## Bối Cảnh (Context)
Trên Web Terminal Dashboard (`exports/index.html`), nhà đầu tư theo dõi bảng Radar Top Cổ Phiếu (Tab 1) và Sổ Cái Vị Thế Đang Nắm Giữ (Tab 2). Tuy nhiên, khi muốn tra cứu nhanh một mã cổ phiếu cụ thể ngoài Top 20 (hoặc kiểm tra lại mã mình đang quan tâm như TCH, SSI, HPG, FPT, VHM, DIG, DBC, BAF...), nhà đầu tư chưa có công cụ tìm kiếm và đánh giá định lượng tức thì ngay trên giao diện.

Các giải pháp truyền thống thường dùng **Dynamic Server-side Search** (mỗi lần gõ ký tự lại gửi request cào lại sàn hoặc gọi backend server). Trong mô hình Serverless / GitHub Pages tĩnh 24/7 của Neiro-Stock-VN, giải pháp này mang lại nhiều rủi ro:
1. Gây nghẽn mạng, chậm trễ (latency > 1 - 2 giây), dễ dính rate-limit của nhà cung cấp dữ liệu Fialda/VPS.
2. Tiêu tốn CPU và tài nguyên mạng không cần thiết, vi phạm Zero-Waste Mandate.
3. Nếu mạng chập chờn hoặc server bận, giao diện dashboard sẽ bị treo đơ (freeze).

## Quyết Định Kiến Trúc (Architectural Decisions)

### 1. Kiến Trúc Pre-Computed Snapshot Search (Client-Side JS)
- Trong mỗi chu kỳ quét định kỳ (`generate_terminal_html`), hệ thống Python tự động tổng hợp một snapshot dữ liệu siêu nhẹ (`QUANT_SEARCH_SNAPSHOT`) nhúng trực tiếp vào mã nguồn HTML.
- Snapshot bao gồm danh mục >310 mã cổ phiếu được chấm điểm sẵn theo các trục Quantamental (RS 1M, F-Score, Điểm IBD, Tích lũy Order Flow A-E, Động lượng RRG, Dòng tiền Cá mập Dual Flow) và phân loại Cổng mua Tier 21.
- Client-Side JavaScript tìm kiếm trực tiếp trên RAM trình duyệt với độ trễ `< 1ms`, 0% tải server, hoạt động mượt mà ngay cả khi offline hoặc khi VPS API bận.

### 2. Trích Xuất Thống Kê Quá Khứ (Bot Track Record)
- Tự động quét và tổng hợp lịch sử khuyến nghị từ `data/active_signals.jsonl`, `data/signal_history_ml.jsonl`, và `data/ml_signals_dataset.csv`.
- Với mỗi mã cổ phiếu, trích xuất chính xác:
  - Tổng số lần bot đã khuyến nghị trong lịch sử.
  - Tỷ lệ Thắng/Thua (Wins / Losses).
  - Tỷ lệ Thắng (Win Rate %).
  - Lợi nhuận trung bình (% Avg PnL).

### 3. Cổng Mua Tier 21 & Cảnh Báo Bảo Vệ Vốn (Anti-Junk Guard)
- Phân loại rõ ràng 5 trạng thái hành động theo Tier 21:
  - `VÙNG MUA CHUẨN 🟢` (`BUY_OK`): Đạt chuẩn định lượng, nằm trong biên độ an toàn `-1.5% .. +3.0%` quanh T0 hoặc POC.
  - `THĂM DÒ <=30% 🟡` (`BUY_CAUTION`): Đạt chuẩn nhưng rủi ro vị thế vừa phải, chỉ giải ngân thăm dò $\le 30\%$ vị thế.
  - `CẤM MUA ĐUỔI ⛔` (`EXTENDED_NO_CHASING`): Giá đã tăng xa nền tích lũy (`> +5.0%` hoặc đã chạy sóng), cấm FOMO mua đuổi.
  - `SUY YẾU/CHỜ TẠO ĐÁY 🛑` (`WEAK_OR_BOTTOMING`): Gãy nền, phân phối hoặc vi phạm cắt lỗ.
  - `CẦU CHÌ VĨ MÔ 🛑` (`MACRO_CIRCUIT_BREAKER`): Thị trường chung sập độ rộng (< 30%) hoặc basis âm sâu (< -8.0).
- **Anti-Junk & Low Liquidity Guard:** Nếu mã có thanh khoản thấp (ADTV20 < 15 tỷ) hoặc cơ bản yếu (Piotroski F-Score < 4/9), hiển thị cảnh báo đỏ nổi bật giải thích rõ lý do để bảo vệ vốn nhà đầu tư.

### 4. Giao Diện Cockpit Tương Tác Hiện Đại
- Bố trí ô tìm kiếm (`#quant-search-input`) ngay tại vị trí trung tâm, phía trên các Tab chiến thuật.
- Bổ sung các nút bấm gợi ý nhanh (Quick Suggestion Pills: TCH, SSI, HPG, FPT, DBC, BAF, VGC, HDC, MWG, VHM) giúp tra cứu 1-click.
- Khung kết quả hiển thị 4 khối phân tích chuyên sâu (Quyết nghị Cổng Mua, Chỉ số Quantamental, Track Record quá khứ, Cảnh báo an toàn vốn).

## Hệ Quả (Consequences)
- **Tích cực:** Nhà đầu tư tra cứu tức thì bất kỳ mã cổ phiếu nào với độ trễ `< 1ms`. Không phát sinh request cào Fialda, bảo đảm tính ổn định tuyệt đối của hệ thống.
- **Tiêu chuẩn kiểm thử:** Unit test chuyên biệt `tests/test_quant_quick_check_search.py` đảm bảo kiểm định logic snapshot và UI rendering.
- **Zero-Waste:** Toàn bộ dữ liệu snapshot bổ sung chỉ nặng ~40-60 KB, bảo đảm repository luôn duy trì kích thước `< 15 MB`.

