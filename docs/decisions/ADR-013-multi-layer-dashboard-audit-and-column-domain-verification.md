# ADR-013: Quy Trình Rà Soát Dashboard Đa Tầng & Audit Logic Từng Cột Dữ Liệu Thực Chiến

- **Trạng thái:** Accepted
- **Ngày quyết định:** 2026-10-27
- **Tác giả:** Neiro Quant Team
- **Liên kết:** [ADR-006](ADR-006-dynamic-trailing-stop-t25-and-ranking-history.md), [ADR-010](ADR-010-live-dynamic-price-polling-5min-cadence.md), [ADR-012](ADR-012-realtime-dashboard-synchronization-and-live-ticker.md)

---

## 1. Bối Cảnh (Context)

Trong quá trình phát triển và bảo trì Dashboard tài chính, AI coding agent thường xuyên gặp phải hiện tượng **"Hút tầm nhìn" (Tunnel Vision)**:
1. Khi người dùng yêu cầu "kiểm tra lại toàn bộ Dashboard", agent chỉ tập trung xử lý các lỗi bề nổi dễ thấy nhất (ví dụ: các thẻ thống kê KPI bị gán số cứng, bộ đếm thời gian countdown, căn chỉnh CSS layout).
2. Sau khi sửa xong các lỗi hiển thị này và thấy mã nguồn chạy không lỗi, agent vội vã kết luận đã hoàn thành nhiệm vụ.
3. Hậu quả là **bỏ sót hoàn toàn các lỗi logic nghiệp vụ sâu bên trong từng cột dữ liệu**:
   - Ví dụ thực tế: Cột `Kỳ Trước` trên bảng Top 20 tự động gán nhãn `🆕 MỚI` cho cổ phiếu vừa quay lại Top, chỉ vì ở phiên quét ngay trước đó cổ phiếu này tạm rớt khỏi danh sách. Trong khi trên thực tế, cổ phiếu này đã xuất hiện liên tục nhiều phiên trước đó và đã có điểm tích lũy/vị thế mua rõ ràng.
   - Điều này tạo ra tín hiệu sai lệch nghiêm trọng cho nhà đầu tư (tưởng là siêu cổ phiếu mới bứt phá lần đầu, dẫn đến quyết định mở mua đuổi sai nguyên tắc).

---

## 2. Quyết Định Kiến Trúc & Quy Chuẩn (Decision)

### 2.1. Đóng Gói Bộ Kỹ Năng Chuyên Sâu: `multi-layer-dashboard-audit`
Xây dựng tài liệu kỹ năng chuẩn hóa tại `.agents/skills/multi-layer-dashboard-audit/SKILL.md` áp dụng cho mọi tác vụ audit, rà soát, xây dựng Dashboard hoặc bảng số liệu tài chính.

### 2.2. Khung Kiểm Tra 3 Tầng Độc Lập (Three-Layer Audit Framework)
Mọi Dashboard và giao diện dữ liệu bắt buộc phải vượt qua kiểm định trên cả 3 tầng:

1. **Tầng 1 - Presentation & Stream (Trực quan & Thời gian thực):**
   - Loại bỏ 100% hardcode trên thẻ KPI/Header.
   - Cơ chế Live Ticker polling (30s) mượt mà, không giật lag.
   - Chuẩn màu sàn giao dịch (Tím trần, Xanh tăng, Vàng tham chiếu, Đỏ giảm, Xanh lơ sàn).
   - Thiết kế vừa vặn 100% màn hình, không cuộn ngang ngoài ý muốn.
2. **Tầng 2 - Data Pipeline & State Continuity (Nguồn & Tính liên tục):**
   - Session Debounce (ngăn chặn việc so sánh trùng lặp giữa các lần quét cách nhau vài phút).
   - Test Pollution Guard (cách ly hoàn toàn dữ liệu thật với test runner `pytest`).
   - Giới hạn Rolling Window (giữ kích thước tệp log lịch sử $< 50\text{ KB}$, đảm bảo chuẩn Zero-Waste $< 15\text{ MB}$).
3. **Tầng 3 - Column-by-Column Domain Logic (Audit Logic Từng Cột):**
   - **Bắt buộc rà soát từng cột từ trái qua phải:** Đối chiếu công thức tính toán và ý nghĩa nghiệp vụ của từng cột với hành vi dữ liệu thực tế.
   - **Cơ chế Fallback Lịch Sử:** Với các cột so sánh chuỗi thời gian (như `Kỳ Trước`), phải tra cứu toàn bộ lịch sử snapshot. Nếu mã tạm rớt khỏi Top ở phiên trước nhưng đã từng xuất hiện, phải so sánh với lần xuất hiện gần nhất thay vì gán nhãn `MỚI` sai lệch.
   - **Tính nhất quán của dấu:** Giá trị cải thiện phải mang dấu dương (`+` / `↗`), suy giảm mang dấu âm (`-` / `↘`).

### 2.3. Thử Nghiệm Góc Nhìn Nhà Đầu Tư Thực Chiến (Investor Persona Test)
Trước khi đóng bất kỳ tác vụ nào liên quan đến Dashboard, AI agent bắt buộc phải trả lời câu hỏi:
> *"Nếu một nhà đầu tư thực tế nhìn vào từng con số trên bảng này qua nhiều phiên giao dịch liên tiếp, có cột nào gây hiểu lầm hoặc đưa ra tín hiệu sai lệch hay không?"*

### 2.4. Nâng Cấp Thành Điều Luật Tối Cao (Supreme Rule)
Quy định này được tích hợp trực tiếp vào [AGENTS.md](file:///c:/Users/Daniel/Documents/My-Projects/Neiro-Stock-VN/AGENTS.md) (Mục 4) và [GEMINI.md](file:///c:/Users/Daniel/Documents/My-Projects/Neiro-Stock-VN/GEMINI.md) (Mục 3.4) với quyền lực bắt buộc tối cao: Mọi AI agent khi nhận nhiệm vụ review Dashboard đều **không được phép dừng lại ở tầng giao diện**, mà bắt buộc phải audit đến tận logic nghiệp vụ từng cột.

---

## 3. Hệ Quả & Lợi Ích (Consequences)

- **Triệt tiêu lỗi hiển thị sai lệch:** Dữ liệu trên bảng xếp hạng và các cột tín hiệu phản ánh trung thực, nhất quán với lịch sử giao dịch.
- **Tăng độ tin cậy của hệ thống:** Nhà đầu tư và mô hình ML downstream nhận được dữ liệu chuẩn xác, không bị nhiễu bởi các nhãn dán giả tạo.
- **Chuẩn hóa tác phong làm việc của AI Agent:** Ngăn chặn triệt để thói quen làm tắt, sửa lỗi bề nổi đối phó.
