# ADR-009: Sổ Cái Tín Hiệu Ngầm & Rada Chống Mua Đuổi (Anti-FOMO Signal Ledger & Chasing Prevention)

- **Trạng thái:** ACCEPTED
- **Ngày quyết định:** 2026-10-26
- **Phạm vi tác động:** `src/risk_engine/signal_tracker.py`, `src/collector/fialda_scanner.py`, `.github/workflows/scanner_and_pages.yml`, `docs/spec.md`, `docs/architecture.md`, `README.md`

---

## 1. Bối Cảnh (Context)

Trên thị trường chứng khoán Việt Nam, rủi ro lớn nhất đối với nhà đầu tư cá nhân là tâm lý FOMO mua đuổi (chasing price) khi một cổ phiếu đã tăng mạnh 4–5 phiên liên tiếp kể từ điểm bùng nổ chân sóng. 
Với chu kỳ thanh toán $T+2.5$, hành vi mua đuổi cổ phiếu đã chạy xa nền hỗ trợ khiến nhà đầu tư rơi vào "vùng đóng băng vị thế":
- Không có đệm lãi an toàn như những người mua tại $T_0$.
- Phải chịu áp lực chốt lời ngắn hạn từ những nhà đầu tư $T+0$ và độ biến động rung lắc của thị trường.
- Bị kẹt hàng $2.5$ ngày, hoàn toàn bất lực khi giá quay đầu điều chỉnh giảm sâu mà không thể bấm nút bán cắt lỗ.

Người dùng yêu cầu hệ thống cần có một cơ chế **chạy ngầm trên GitHub** ghi nhớ giá khuyến nghị ban đầu ($T_0$), tự động theo dõi diễn biến giá sau 4-5 ngày, và đưa ra căn cứ đối chiếu vững chắc để cảnh báo "CẤM MUA ĐUỔI", **đồng thời không hiển thị lên giao diện Web Dashboard** để giữ giao diện luôn tinh gọn, trực quan.

---

## 2. Quyết Định Thiết Kế (Decisions)

### 2.1. Thiết Kế Sổ Cái Tín Hiệu Ngầm (`SignalTracker`)
- Tạo module [src/risk_engine/signal_tracker.py](file:///c:/Users/Daniel/Documents/My-Projects/Neiro-Stock-VN/src/risk_engine/signal_tracker.py) độc lập, hoạt động ngầm hoàn toàn và lưu trữ tại [data/active_signals.jsonl](file:///c:/Users/Daniel/Documents/My-Projects/Neiro-Stock-VN/data/active_signals.jsonl).
- **Mỏ neo giá ban đầu ($T_0$ Anchor Price):** Khi một mã cổ phiếu lần đầu tiên được hệ thống phát hiện lọt vào Top khuyến nghị, hệ thống ghi nhận mốc giá Entry gốc, Stop Loss ban đầu, TP1 và TP2.
- Khi các phiên quét sau diễn ra (mỗi 30 phút trên GitHub Actions), hệ thống cập nhật thị giá mới nhất, số ngày nắm giữ ($T+0, T+1, T+4...$), và tính toán tỷ lệ trượt giá lũy kế $\Delta\% = (\text{price} - \text{entry\_original}) / \text{entry\_original} \times 100\%$.

### 2.2. Bộ Quy Tắc Định Lượng Khóa Chiều Mua (Anti-FOMO Guard)
1. **$\Delta\% \le +3.0\%$:** `BUY_OK` (🟢 VÙNG MUA CHUẨN) — Cho phép mở vị thế chuẩn tại nền giá an toàn.
2. **$+3.1\% \le \Delta\% \le +5.0\%$:** `BUY_CAUTION` (🟡 VÙNG VỚI) — Chỉ giải ngân thăm dò tối đa $30\%$, không dùng margin.
3. **$\Delta\% > +5.0\%$ hoặc nắm giữ $\ge 3$ phiên:** `EXTENDED_NO_CHASING` (🔴 QUÁ ĐIỂM MUA - CẤM MUA ĐUỔI) — Tuyệt đối khóa chiều mua mới; chỉ ưu tiên người có hàng sẵn tiếp tục nắm giữ gồng lãi, người chưa có hàng kiên nhẫn đứng ngoài chờ nhịp tích lũy lại nền mới.
4. **Cơ chế nâng Stop Loss lên Hòa vốn:** Khi giá đạt hoặc vượt TP1, Stop Loss của vị thế tự động được nâng lên điểm hòa vốn (`entry_original`) để bảo vệ $100\%$ vốn gốc cho $50\%$ số cổ phiếu còn lại gồng lãi tới TP2.

### 2.3. Báo Cáo Đối Chiếu Ngầm & Tích Hợp GitHub Actions
- Xuất bản tệp báo cáo markdown ngầm [data/advisory_scorecard.md](file:///c:/Users/Daniel/Documents/My-Projects/Neiro-Stock-VN/data/advisory_scorecard.md) và tự động nối vào `GITHUB_STEP_SUMMARY` trong workflow `.github/workflows/scanner_and_pages.yml`.
- Cung cấp hàm tra cứu trực tiếp `SignalTracker().get_advisory(symbol)` hỗ trợ AI trả lời tư vấn định lượng tức thì với đầy đủ căn cứ lịch sử.
- **Giữ nguyên 100% giao diện Web Dashboard (`exports/index.html`):** Không chèn thêm bảng, bảo đảm trải nghiệm người dùng sạch sẽ, nhẹ nhàng.

---

## 3. Hệ Quả & Đánh Giá (Consequences)

- **Bảo Vệ Người Dùng:** Ngăn ngừa triệt để các quyết định mua cảm tính hoặc đu đỉnh ngắn hạn tại các nhịp FOMO của thị trường.
- **Tiêu Chuẩn Zero-Waste:** Kích thước `active_signals.jsonl` và `advisory_scorecard.md` tổng cộng chưa tới $5\text{ KB}$, toàn bộ repository duy trì ở mức $1.61\text{ MB} < 15\text{ MB}$.
- **Tương Thích Tuyệt Đối:** Toàn bộ 75/75 unit tests trong test suite đều pass 100%.
