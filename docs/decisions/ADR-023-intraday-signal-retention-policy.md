# ADR-023: Cơ Chế Duy Trì Vị Thế Khuyến Nghị Trong Ngày (Same-Day Intraday Signal Retention Policy) & Chuyển Giao Tab 2 Khi Qua Ngày (T+1)

## 1. Trạng thái
- **Trạng thái:** `ACCEPTED & IMPLEMENTED`
- **Ngày quyết định:** 2026-11-04
- **Người đề xuất:** Owner / Chief Quant Architect
- **Phạm vi áp dụng:** `src/collector/fialda_scanner.py`, `src/hud/terminal.py`, `src/risk_engine/signal_tracker.py`, `docs/spec.md`, `docs/architecture.md`.

---

## 2. Bối cảnh & Vấn đề (Context & Problem Statement)

1. **Hiện tượng biến mất tín hiệu trong phiên (Intraday Signal Disappearance):**
   - Trong phiên giao dịch buổi sáng (ví dụ lúc 10:12:03 ngày $T_0$), hệ thống phát hiện dòng tiền đột biến và khuyến nghị giải ngân cổ phiếu `VCK` tại giá `28.10`. Nhà đầu tư mở Tab 1 (*Top 20 Siêu Cổ Phiếu Chân Sóng*) và nhận khuyến nghị này.
   - Trong các chu kỳ quét định kỳ tiếp theo vào buổi chiều (11:30, 13:30, 14:00), thị giá và thanh khoản toàn thị trường biến động liên tục khiến bảng xếp hạng `ranking_score` của 300+ mã thay đổi. Điểm xếp hạng tức thời của `VCK` có thể tạm thời lùi về hạng 21 - 25.
   - Do scanner trước đây áp dụng lát cắt cứng `top_final = enriched_all[:top_n]`, `VCK` bị rơi khỏi Top 20 của Tab 1.
2. **Nghịch lý trải nghiệm người dùng (Trader Persona UX Friction):**
   - Nhà đầu tư cá nhân vừa nhận khuyến nghị mua cổ phiếu buổi sáng, buổi chiều vào lại kiểm tra thì mã đột nhiên "biến mất" khỏi bảng khuyến nghị chính (Tab 1), gây ra tâm lý hoang mang, nghi ngờ về độ tin cậy của hệ thống (*"Hồi sáng vừa gợi ý VCK, giờ nó đi đâu mất rồi?"*).
   - Mặc dù mã vẫn nằm trong Sổ Cái Tab 2, nhưng nhà đầu tư theo dõi thị trường thường nhìn vào Tab 1 đầu tiên để quan sát các cơ hội mua trong ngày.

---

## 3. Quyết định Kiến trúc (Architectural Decisions)

Owner đã trực tiếp chỉ đạo quy tắc vận hành bất biến:
> *"Các mã em đã khuyến nghị mà vẫn hiệu lực trong ngày thì em cứ để ở đó đi, không cần remove đâu, qua ngày hãy remove."*

Hệ thống thiết lập 3 nguyên tắc cốt lõi:

### 3.1. Nguyên tắc 1: Duy Trì Vị Thế Trong Ngày (Same-Day Retention on Tab 1)
- **Điều kiện duy trì:**
  - Ngày bùng nổ tín hiệu gốc `first_signal_date` thuộc cùng ngày dương lịch với ngày quét hiện tại (`first_signal_date[:10] == now_vn[:10]`, tức chu kỳ $T_0$).
  - Tín hiệu **vẫn còn hiệu lực:** chưa đóng (`is_closed == False`) và chưa vi phạm cắt lỗ (`status != "STOPPED_OUT"`).
- **Hành vi:**
  - Bắt buộc được **giữ lại (retained / pinned)** trên danh sách Top Khuyến Nghị của Tab 1 trong suốt phiên giao dịch, bất kể biến động thứ hạng tức thời của phiên quét buổi chiều.
  - Được cập nhật liên tục thị giá thực tế (`current_price`), giá vào gốc $T_0$ (`entry_original`), ngưỡng dừng lỗ (`stop_loss`), mục tiêu (`tp1`, `tp2`), và huy hiệu chống FOMO (`anti_fomo_badge`).

### 3.2. Nguyên tắc 2: Phân Biệt Huy Hiệu Trực Quan Theo Thị Giá Live
- Nếu thị giá cổ phiếu vẫn nằm trong biên độ an toàn $\le +1.5\%$ so với giá kích hoạt $T_0$:
  - Gán nhãn `🟢 VÙNG MUA CHUẨN` (cho phép giải ngân).
- Nếu thị giá đã tăng mạnh vượt $+1.5\%$ (ví dụ `VCK` tăng từ 28.10 lên 28.60, tức +1.8%):
  - Khóa quyền mua đuổi và hiển thị huy hiệu đỏ cảnh báo: `⛔ ĐÃ CHẠY > 1.5% — CẤM MUA ĐUỔI (T0)`.
  - Giúp nhà đầu tư mới vào phiên chiều biết rõ: *Mã này hệ thống đã báo sáng nay và đã sinh lãi, cấm mua đuổi.*

### 3.3. Nguyên tắc 3: Chuyển Giao Khi Bước Sang Ngày Giao Dịch Mới ($T+1$)
- Khi bước sang ngày tiếp theo (`now_vn.date() > first_signal_date.date()`, tức $T \ge 1$):
  - Mã này đã hoàn thành vai trò phát tín hiệu mở vị thế mới của ngày $T_0$.
  - Hệ thống **tự động loại bỏ (remove)** việc ghim mã này trên Tab 1 để bảng khuyến nghị luôn tươi mới và không làm người xem ngộ nhận là điểm mua mới của ngày hôm sau.
  - Quyền theo dõi mã được chuyển giao toàn phần sang **Tab 2: Sổ Cái Vị Thế Đang Nắm Giữ & Theo Dõi Lãi/Lỗ PnL (T+ Tracker)** cho đến hết vòng đời (TP2 hoặc Stop Loss).

### 3.4. Ngoại lệ ngắt tín hiệu trong ngày (Stop Loss Exception)
- Nếu trong phiên ngày $T_0$, cổ phiếu đảo chiều bất ngờ và vi phạm ngưỡng cắt lỗ bảo toàn vốn (`status == "STOPPED_OUT"`):
  - Tín hiệu bị coi là **hết hiệu lực**.
  - Mã ngay lập tức bị loại khỏi Tab 1 để chấm dứt khuyến nghị mua, chuyển thẳng sang ngăn lưu trữ đóng vị thế của Tab 2.

---

## 4. Triển khai Kỹ thuật (Implementation Details)

1. **Tại `src/collector/fialda_scanner.py` (`scan_top_rockets`):**
   - Quét danh sách `active_ledger = SignalTracker().load_active_signals()`.
   - Lọc các mã cùng ngày: `same_day_symbols = [sym for sym, sig in active_ledger.items() if not sig.is_closed and sig.status != 'STOPPED_OUT' and sig.first_signal_date[:10] == today_str]`.
   - Nếu có mã trong `same_day_symbols` chưa lọt vào `top_final[:top_n]`, tự động tìm trong `enriched_all` hoặc tái tạo ứng viên `FialdaCandidate` chuẩn qua hàm `candidate_from_active_signal(sig)` và bổ sung vào `top_final`.
2. **Tại `src/hud/terminal.py` (`generate_terminal_html`):**
   - Bổ sung cơ chế bảo vệ kép (Defense-in-Depth): Đảm bảo danh sách `fialda_candidates` hiển thị trên Tab 1 không bao giờ thiếu bất kỳ mã khuyến nghị nào của ngày hôm nay.

---

## 5. Kết quả & Lợi ích (Consequences & Benefits)

- **Trực quan & Nhất quán:** Nhà đầu tư tìm thấy đầy đủ các mã khuyến nghị trong ngày trên Bảng Radar Tab 1, không còn hiện tượng "biến mất khó hiểu".
- **Kỷ luật chống FOMO:** Cổ phiếu đã chạy lãi buổi chiều vẫn hiện diện trên Tab 1 nhưng gắn nhãn đỏ `CẤM MUA ĐUỔI`, bảo vệ nhà đầu tư khỏi bẫy giá cao.
- **Rõ ràng theo chu kỳ T+:** Qua ngày $T+1$, mã rời Tab 1 và nằm ngăn nắp ở Tab 2, phân định rạch ròi giữa *Khuyến nghị mở mới ($T_0$)* và *Quản lý danh mục đang nắm giữ ($T+1$ đến $T+20$)*.

