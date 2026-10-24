# ADR-001: Khởi Tạo Nền Tảng Định Lượng Quantamental Cho Thị Trường Chứng Khoán Việt Nam

## 1. Trạng Thái (Status)
Đã duyệt (Approved) - Ngày: 2026-10-24

## 2. Bối Cảnh (Context)
Hệ thống **Neiro-Quant** ban đầu được xây dựng để chuyên sâu khai thác vi cấu trúc thị trường quyền chọn vàng (CME Gold Options Microstructure) với các công cụ Black-76 Greeks, Net GEX, Gamma Squeeze, Zero Gamma Flip $S^*$ và Delta Hedging.

Tuy nhiên, khi mở rộng chiến lược định lượng sang **Thị trường Chứng khoán Việt Nam (HOSE, HNX, UPCoM, VN30F1M)**, chúng ta đối mặt với môi trường giao dịch hoàn toàn khác biệt:
1. **Thiếu vắng Options đơn lẻ trên từng cổ phiếu:** Việt Nam chưa có thị trường Single Stock Options; do đó không thể sao chép trực tiếp công thức Net GEX/VEX của CME Options sang từng mã cổ phiếu như HPG, SSI, VCB.
2. **Cơ chế thanh toán trễ T+2.5 / T+1.5:** Rủi ro kẹp hàng qua đêm khiến các mô hình Stop-Loss T+0 của thị trường quốc tế trở nên vô hiệu.
3. **Biên độ trần/sàn cố định (HOSE $\pm 7\%$):** Khiến thanh khoản có thể bị triệt tiêu đột ngột ("trắng bên mua" hoặc "trắng bên bán").
4. **Cơ cấu nhà đầu tư cá nhân chiếm $85\%$:** Dẫn đến tính bầy đàn và biến động tâm lý cực lớn; các tổ chức (Khối ngoại, Tự doanh) dẫn dắt cuộc chơi thông qua gom hàng tại các vùng thanh khoản lớn và phòng hộ qua HĐTL VN30F1M.

Do đó, cần thành lập một workspace độc lập `Neiro-Stock-VN` kế thừa triết lý định lượng không dùng chỉ báo trễ, nhưng thay thế chuỗi Options CME bằng **Trục Hợp Lưu Quantamental: Định lượng Cơ bản (Fundamental Quant) + Cấu trúc Vi mô Sổ lệnh (Volume Profile & Order Flow) + Phái sinh VN30F1M + Luân chuyển ngành (RRG)**.

## 3. Quyết Định Kiến Trúc (Decision)
1. **Tách biệt Workspace:** Thành lập `Neiro-Stock-VN` độc lập tại `c:\Users\Daniel\Documents\My-Projects\Neiro-Stock-VN` cùng cấp với `Neiro-Quant`.
2. **Kế thừa bộ 24 AI Agent Skills:** Đảm bảo toàn bộ quy trình tiền trạm bắt buộc (Pre-Action Skill Discovery Gate), AGENTS.md, GEMINI.md và Zero-Waste Mandate được duy trì nghiêm ngặt.
3. **Thiết kế Kiến trúc 6 Tầng (6-Tier Engine):**
   - Tier 1: Fundamental Screening (Piotroski F-score $\ge 7$, CANSLIM, CFO/NI, P/E Banding).
   - Tier 2: Microstructure Engine (Volume Profile POC, VAH/VAL 70%, HVN/LVN, OFI).
   - Tier 3: Institutional Smart Money Tracking (Foreign, Prop Flow, Block Trades).
   - Tier 4: Derivatives VN30F1M Basis & Portfolio Beta Hedging.
   - Tier 5: Macro & Relative Rotation Graph (RRG Sector Momentum).
   - Tier 6: T+2.5 Execution Risk & Rolling Inventory Sizing.
4. **Phần cứng & Dung lượng:** Giữ toàn bộ dự án dưới **15MB**, không phụ thuộc server nặng, zero memory leak.

## 4. Hệ Quả (Consequences)
- **Tích cực:** Cung cấp hệ thống định lượng bài bản, thực chiến, phù hợp chính xác 100% với cấu trúc luật và thanh khoản của sàn chứng khoán Việt Nam.
- **Thách thức:** Cần tích hợp nguồn cấp dữ liệu chuẩn hóa của các công ty chứng khoán Việt Nam hoặc dữ liệu mở, đồng thời phải duy trì bộ mock data cho unit tests chạy offline.
