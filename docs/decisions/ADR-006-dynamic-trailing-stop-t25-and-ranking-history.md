# ADR-006: Quản Trị Rủi Ro Động, Thoát Lệnh T+2.5 & Lưu Lịch Sử Xếp Hạng

- **Trạng thái:** Accepted (Đã chấp thuận & Triển khai vào Core)
- **Ngày quyết định:** 24/10/2026
- **Tác giả:** Neiro-Stock-VN Quantitative Team
- **Tệp liên quan:**
  - `src/risk_engine/trailing_stop.py`
  - `src/collector/ranking_history.py`
  - `src/collector/fialda_scanner.py`
  - `src/hud/terminal.py`
  - `tests/test_trailing_stop.py`
  - `tests/test_ranking_history.py`
  - `data/ranking_history.jsonl`

---

## 1. Bối cảnh & Thách thức (Context & Problem Statement)

Tại Thị trường Chứng khoán Việt Nam, nhà đầu tư cổ phiếu cơ sở (Spot Equities Long-Only) đối mặt với 2 rào cản chí mạng:
1. **Độ trễ thanh toán T+2.5 (Vùng Đóng Băng T+0 đến T+2):** Mua cổ phiếu ngày $T+0$, chỉ có thể bán từ chiều $T+2$. Trong thời gian này, nhà đầu tư hoàn toàn bị "khóa tay" không thể cắt lỗ trực tiếp trên mã vừa mua. Hơn nữa, nhà đầu tư cá nhân không giao dịch phái sinh và không thể short cổ phiếu cơ sở.
2. **Thiếu kỷ luật khóa lợi nhuận (Profit Lock):** Đa số nhà đầu tư thường để lãi thành lỗ khi cổ phiếu đảo chiều sau khi tăng $10\% - 20\%$. Cần một cơ chế cơ học nâng Stop Loss lên hòa vốn (Break-even) và bám sát đỉnh (Chandelier Exit) bảo toàn tỷ lệ Risk/Reward $R:R \ge 1:2.5$.
3. **Mất dấu vết dòng tiền (Ranking Amnesia):** Trước đây mỗi chu kỳ quét định kỳ 30 phút/lần ghi đè file snapshot mới nhất, không lưu lại chuỗi thời gian xếp hạng khiến người dùng không biết cổ phiếu nào đang thăng hạng liên tục ($\Delta Rank$) hoặc cổ phiếu nào mới bứt phá vào Top (`NEW`).

---

## 2. Quyết định Kiến trúc (Architectural Decisions)

### 2.1. Module Trailing Stop & Thoát Lệnh Động (`src/risk_engine/trailing_stop.py`)
- **Initial Stop Loss:** Khởi tạo an toàn kết hợp Swing Low gần nhất và `entry_price - 1.5 * ATR(14)`, khống chế mức rủi ro trong dải $[3\%, 7\%]$ phù hợp biên độ trần/sàn HOSE. Đơn vị rủi ro chuẩn: $1R = \text{Entry} - \text{Stop Loss}$.
- **Break-Even Ratchet:** Khi giá tăng đạt $\ge 1.5R$ (hoặc $2.0R$), hệ thống tự động nâng Stop Loss lên giá vốn ($\text{Entry}$).
- **Chandelier Trailing Exit:** Khi giá tiếp tục lập đỉnh mới, $\text{Stop Loss} = \max(\text{Current Stop}, \text{Highest Price} - 2.0 \times \text{ATR}_{14})$.
- **Ratchet Invariant:** Stop Loss là hàm đơn điệu không giảm ($\text{Stop}_{t+1} \ge \text{Stop}_t$), tuyệt đối không bị hạ xuống khi giá điều chỉnh.
- **Tỷ lệ Vàng Risk/Reward:** $\text{TP1} = \text{Entry} + 1.5R$ (chốt 50%), $\text{TP2} = \text{Entry} + 2.5R$ (gồng 50% còn lại với $R:R \ge 1:2.5$).

### 2.2. Rada Cảnh Báo Phơi Nhiễm T+2.5 Dành Cho Cổ Phiếu Cơ Sở
- Không yêu cầu Short phái sinh đối với tài khoản cơ sở.
- Dùng Basis VN30F1M và Độ rộng thị trường làm đèn tín hiệu giao thông:
  - 🟢 **SAFE:** Basis dương $\rightarrow$ Mở mua bình thường.
  - 🟡 **MODERATE:** Basis phân kỳ nhẹ $\rightarrow$ Chỉ giải ngân đợt 1 (50% vị thế tại nền).
  - 🔴 **CRITICAL:** Basis âm sâu $< -10$ điểm hoặc phái sinh bán tháo $\rightarrow$ Tạm dừng mở mua mới, kích hoạt lệnh bán hạ tỷ trọng trên các mã hàng sẵn có để nâng tiền mặt $\ge 50\% - 60\%$.

### 2.3. Lưu Trữ Lịch Sử Xếp Hạng Siêu Nhẹ (`src/collector/ranking_history.py`)
- Lưu trữ chuỗi snapshot vào `data/ranking_history.jsonl`.
- Áp dụng cơ chế **Rolling Window** tự động cắt tỉa chỉ duy trì tối đa 500 bản ghi ($\sim 35\text{ KB}$), bảo đảm tuyệt đối tôn trọng **Zero-Waste Mandate (< 15MB)**.
- Tự động so sánh phiên hiện tại với phiên liền kề để tính toán:
  - `↗ +N`: Thăng hạng
  - `↘ -N`: Tụt hạng
  - `=`: Giữ hạng
  - `🆕 MỚI`: Cổ phiếu mới lọt Top 20

---

## 3. Hệ quả & Đánh giá (Consequences & Verification)

- **Kiểm thử toán học:** Đạt 100% pass với 72 unit tests tự động (`tests/test_trailing_stop.py`, `tests/test_ranking_history.py`).
- **Giao diện Web Terminal:** Bảng Top 20 hiển thị đầy đủ: STT kèm Huy hiệu $\Delta Rank$, Cắt lỗ (SL), Chốt lời 1 (TP1), Chốt lời 2 (TP2), Tỷ lệ R:R ($1:2.5$), Vùng T+2.5, và Widget lịch sử phiên quét.
- **Dung lượng Repository:** Duy trì ở mức siêu nhẹ **1.69 MB** (tiêu chuẩn $< 15\text{ MB}$).
