# ADR-029: Hợp Nhất Sổ Cái Vị Thế & Đối Soát Chỉ Số T0 Thành Một Bảng Tổng Hợp Duy Nhất (Hybrid Unified Cockpit)

- **Trạng thái:** Accepted & Implemented
- **Ngày:** 2026-11-11
- **Tác giả:** Neiro-Stock-VN Architecture Team

## 1. Bối cảnh (Context)
Trước khi thực hiện ADR này, giao diện theo dõi vị thế khuyến nghị bị phân mảnh thành 2 Tab riêng biệt gây dư thừa dữ liệu và bất tiện trong trải nghiệm:
- **Tab 2:** Hiển thị 2 bảng riêng (Bảng 1: Vị thế đang nắm giữ 11 cột + Bảng 2: Lịch sử vị thế đã đóng 10 cột).
- **Tab 3:** Hiển thị 1 bảng chi tiết toàn bộ vị thế với **14 cột ngang rất rộng**, gây tràn màn hình trên các thiết bị laptop nhỏ và điện thoại, đồng thời lặp lại 100% dữ liệu của Tab 2.
Người dùng phải chuyển qua lại giữa 2 tab để vừa xem giá Live/PnL vừa soi chỉ số gốc tại thời điểm mua $T_0$.

## 2. Quyết định Kiến trúc (Decision)
Triển khai **Phương Án 5 (Hybrid Unified Cockpit)**: Hợp nhất toàn bộ Tab 2 và Tab 3 thành **1 BẢNG TỔNG HỢP DUY NHẤT** đặt tại Tab 2:
1. **Tinh Gọn Thanh Điều Hướng (Clean 2-Tab Navigation):**
   - Loại bỏ nút Tab 3 riêng lẻ, thanh điều hướng chỉ còn 2 Tab:
     - `📡 TAB 1: RADAR THỰC CHIẾN & BẢNG ĐỊNH LƯỢNG`
     - `📋 TAB 2: SỔ CÁI & ĐỐI SOÁT VỊ THẾ TOÀN VÒNG (T+ TRACKER • T0 → TP/SL)`
2. **Khối AI Tự Học Hậu Kiểm SL vs TP (Collapsible Widget):**
   - Đặt khối phân tích của anh Công Trần Tc ở đầu Tab 2 dưới dạng `<details id="hud-tab-t0-audit" open>`: Chứa 4 thẻ KPI và bảng 4 bài học trọng số rút ra từ tập lệnh bị SL để người dùng có thể mở ra nghiên cứu hoặc thu gọn lại để tập trung vào bảng.
3. **Thanh Lọc Nhanh 1-Click (Client-Side Filter Toolbar):**
   - 5 nút lọc phản hồi tức thì (<1ms): `Tất Cả`, `🟢 Đang Nắm Giữ`, `🎯 Đã Chốt Lời TP`, `🛑 Đã Cắt Lỗ SL`, `⏱️ Tất Toán T+7`.
4. **Bảng Tổng Hợp Duy Nhất (Single Unified Table — 8 Cột Đa Tầng Chống Tràn):**
   - Thay thế 3 bảng cũ bằng 1 bảng chuẩn hóa duy nhất (`#active-positions-table` / `unified-pos-row`):
     - Cột 1: `STT`
     - Cột 2: `Mã CP & Tín Hiệu` (Symbol to đậm + Badge Chân Sóng/Thể Chế)
     - Cột 3: `Trạng Thái & Chu Kỳ` (Badge Kết Quả + T+ và Thời gian `Ngày Vào T0 • Ngày Đóng`)
     - Cột 4: `Giá Vốn & Thoát/Live` (Giá vào $T_0$ → Giá Live/Đóng + Ngưỡng SL & TP1/TP2)
     - Cột 5: `Lãi/Lỗ PnL % & Biên Độ` (% PnL đổi màu + Đỉnh MFE / Đáy MAE)
     - Cột 6: `Bộ Chỉ Số T0` (AI Score, IBD/RS, Hạng Tích Lũy A-E, RRG Ratio/Mom)
     - Cột 7: `Dòng Tiền & Nền POC T0` (Khối ngoại & Tự doanh ròng, Giá POC & Độ lệch ATR, ADTV20)
     - Cột 8: `AI Chẩn Đoán & Quyết Nghị` (Chẩn đoán lý do TP / Bài học SL tại $T_0$ + Quyết nghị thực chiến)
5. **Khả Năng Tương Thích & Động Hóa Realtime:**
   - Bảo toàn 100% các class selector `.live-price[data-sym]`, `.live-pnl[data-sym]`, `.pos-badge` để JavaScript định kỳ kéo giá live từ VPS Datafeed và tự động cập nhật màu sắc/PnL.
   - Hỗ trợ hàm `filterUnifiedPositions(cat)` và alias `filterT0AuditRows(cat)`.

## 3. Hệ quả & Kiểm chứng (Consequences & Verification)
- **Triệt tiêu 100% dư thừa dữ liệu:** Không còn 2 bảng song song lặp lại mã.
- **Không tràn màn hình (Anti-Overflow):** Bảng 8 cột đa tầng co giãn hoàn hảo trên mọi kích thước màn hình mà vẫn cung cấp đầy đủ thông tin nhất quán.
- **Kiểm thử tự động:** Toàn bộ 166 tests pass 100% (`tests/test_positions_tracker_tab.py`, `tests/test_retail_t25_blindspots.py`, v.v.).

