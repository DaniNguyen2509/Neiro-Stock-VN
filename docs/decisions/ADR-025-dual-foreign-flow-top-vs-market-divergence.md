# ADR-025: Chuẩn Hóa Chỉ Số Phân Kỳ Dòng Tiền Khối Ngoại — So Sánh Song Hành Rổ Top vs. Toàn Sàn (Flow Divergence Delta)

- **Trạng thái:** Accepted & Implemented
- **Ngày ban hành:** 2026-11-06
- **Tác giả:** Neiro Quant Team
- **Liên kết:** [ADR-011](ADR-011-online-signal-ledger-and-ml-dataset-pipeline.md), [ADR-012](ADR-012-realtime-dashboard-synchronization-and-live-ticker.md), [ADR-018](ADR-018-api-crawling-resilience-and-schema-alignment.md)

---

## 1. Bối Cảnh (Context)

Người dùng ghi nhận tình trạng thắc mắc và nhầm lẫn về số liệu khối ngoại trên Bảng điều khiển Web HUD:
- Thẻ số 2 trước đây ghi chung chung: `Dòng Tiền Cá Mập Định Chế` với giá trị `+153.2 Tỷ VND`.
- Khi đối chiếu với các bảng giá toàn thị trường như FireAnt, TCBS, SSI, người dùng thấy toàn sàn chỉ ghi nhận khối ngoại mua ròng `+50.0 Tỷ VND`, dẫn đến nghi ngờ về nguồn gốc và tính trung thực của dữ liệu.

Qua phân tích vi cấu trúc dòng tiền (Market Microstructure), sự chênh lệch này hoàn toàn hợp lý về mặt bản chất nghiệp vụ:
1. **Khối ngoại Toàn thị trường ($\text{Net}_{\text{Market}}$):** Đo lường áp lực dòng vốn vĩ mô (Macro Sentiment) và cơ cấu danh mục quỹ ETF thụ động trên toàn bộ ~1.600 mã. Số liệu này bị nhiễu rất mạnh bởi các giao dịch thỏa thuận và xả hàng ở các mã trụ cũ.
2. **Khối ngoại Rổ Top Radar ($\text{Net}_{\text{Top}}$):** Đo lường dòng tiền thông minh chọn lọc cổ phiếu tăng trưởng (Active Alpha Stock Picking). Khối ngoại có thể bán ròng toàn sàn nhưng lại dồn vốn gom mạnh ở các mã dẫn dắt.

Tuy nhiên, việc chỉ hiển thị một con số đơn lẻ mà không có bối cảnh toàn thị trường khiến nhà đầu tư dễ rơi vào bẫy hiểu lầm hoặc mất phương hướng.

---

## 2. Quyết Định Kiến Trúc (Decision)

### 2.1. Chuẩn Hóa Công Thức Phân Kỳ Dòng Tiền (Flow Divergence Delta)
Hệ thống định lượng hóa sự tương quan giữa hai dòng tiền theo công thức:
$$\Delta \text{Flow} = \text{Net Foreign}_{\text{Top}} - \text{Net Foreign}_{\text{Market}}$$

Hệ thống tự động phân loại thị trường thành **Ma trận 4 Trạng Thái Định Lượng (Quant Divergence Matrix)**:
1. **`SIEU_SONG` (🟢🟢 SIÊU SÓNG ĐỒNG THUẬN):** Khi $\text{Net}_{\text{Top}} > 0$ và $\text{Net}_{\text{Market}} > 0$. Vĩ mô và cổ phiếu chọn lọc cùng hút tiền, xác suất thắng T+2.5 cực cao.
2. **`DAI_CAT_TIM_VANG` (🟢 ĐÃI CÁT TÌM VÀNG):** Khi $\text{Net}_{\text{Top}} > 0$ và $\text{Net}_{\text{Market}} \le 0$ (hoặc $\Delta \text{Flow} \ge +30\text{ tỷ}$). Khối ngoại xả mã yếu ngoài sàn nhưng dồn lực gom siêu cổ phiếu Top.
3. **`KEO_TRU_PHAN_HOA` (🟡 KÉO TRỤ PHÂN HÓA):** Khi $\text{Net}_{\text{Top}} \le 0$ và $\text{Net}_{\text{Market}} > 0$. Kéo chỉ số chung nhưng rút ròng ở danh mục tăng trưởng (cảnh báo Bull-trap).
4. **`AP_LUC_XA_DIEN_RONG` (🔴 ÁP LỰC XẢ DIỆN RỘNG):** Khi cả $\text{Net}_{\text{Top}} \le 0$ và $\text{Net}_{\text{Market}} \le 0$. Khối ngoại tháo chạy diện rộng, kích hoạt phòng vệ.

### 2.2. Hiển Thị Song Hành Hai Tầng Trên Web Terminal HUD
Trong [src/hud/terminal.py](file:///c:/Users/Daniel/Documents/My-Projects/Neiro-Stock-VN/src/hud/terminal.py):
1. **Đổi tên thẻ trực quan:** `Khối Ngoại Ròng: Rổ Top vs. Toàn Sàn`.
2. **Hiển thị song hành:** `Top: +X.Xt | Sàn: +Y.Yt` kèm thuộc tính ngữ nghĩa `data-market-net`.
3. **Đồng bộ thời gian thực qua Client JS (30s Polling):** Tự động tính toán lại $\Delta \text{Flow}$ và cập nhật huy hiệu trạng thái mỗi chu kỳ 30 giây trực tiếp trên DOM mà không cần reload trang.

---

## 3. Hệ Quả & Kiểm Chứng Chất Lượng (Consequences)

- **Trực quan & Minh bạch 100%:** Nhà đầu tư lập tức hiểu rõ tại sao Rổ Top có thể đạt `+153 tỷ` trong khi toàn sàn FireAnt chỉ có `+50 tỷ` nhờ chỉ số so sánh $\Delta \text{Flow} = +103\text{ tỷ}$.
- **Hỗ trợ ra quyết định sắc bén:** Giúp trader nhận biết sớm pha "Đãi cát tìm vàng" của dòng tiền thông minh để tự tin nắm giữ cổ phiếu mạnh.
- **Kiểm thử tự động:** Bổ sung kịch bản `test_terminal_hud_dual_foreign_flow_top_vs_market` đảm bảo tỷ lệ pass 100%.
