# ADR-020: Tab 2 Sổ Cái Vị Thế Khuyến Nghị & Theo Dõi Lãi/Lỗ PnL (T+ Tracker) — Cơ Chế Rời Bảng Khi Đạt TP2 & Đồng Bộ Live PnL VPS

- **Trạng thái:** `ACCEPTED`
- **Ngày quyết định:** 2026-11-04
- **Phạm vi:** `src/hud/terminal.py`, `exports/index.html`, `tests/test_positions_tracker_tab.py`, `tests/test_retail_t25_blindspots.py`.

---

## 1. Bối Cảnh (Context)

Người dùng đặt vấn đề thực chiến:
Khi thị trường xuất hiện những cổ phiếu tăng mạnh hoặc tím trần trong phiên (điển hình như `TCH` ngày 2026-11-04 tăng trần lên `12.75`), nhà đầu tư nhìn vào Tab 1 (Top 20 Siêu cổ phiếu chân sóng) không thấy xuất hiện đề xuất mua mới và có thể thắc mắc hoặc băn khoăn:
1. *Tại sao cổ phiếu tím trần mà không được đề xuất mua mới?* (Thực tế là mã đã được khuyến nghị mua ở chân sóng ngày `2026-10-26` tại giá `11.90`, đã chạm `TP1 = 12.44` chốt lời 50%, dời trailing stop lên hòa vốn `11.90`, và hôm nay đang kéo chạm `TP2 = 12.80`, do đó bị khóa `EXTENDED_NO_CHASING` để bảo vệ tài khoản nhà đầu tư khỏi bẫy fomo đu đỉnh).
2. *Làm sao để nhà đầu tư biết mã này đã được mua từ trước và đang nắm giữ với lãi bao nhiêu %?*
3. *Quy tắc vòng đời:* Khi một vị thế đã chạm mục tiêu chốt lời toàn phần (`TP2`), sứ mệnh của nó đã hoàn thành ("coi như xong") và cần biến mất khỏi bảng theo dõi active để tránh rối mắt.
4. *Tối ưu Dashboard:* Tab 2 trước đây là Báo cáo kiểm định Walk-Forward lịch sử tĩnh (chạy tốn 10–12 giây CPU mỗi lần sinh báo cáo), người dùng yêu cầu thay thế Tab 2 bằng bảng theo dõi vị thế này.

---

## 2. Quyết Định Kiến Trúc (Architectural Decisions)

1. **Thay thế Tab 2 Walk-Forward bằng Tab 2 Sổ Cái Vị Thế Active Tracker:**
   - ID Tab: `#hud-tab-positions`, Nút chuyển Tab: `#btn-tab-positions`.
   - ID Bảng chính: `#active-positions-table`.
2. **Quy tắc phân loại và lọc vị thế:**
   - **Vị thế đang chạy (Active Running):** Gồm các mã có `status in ["ACTIVE", "TP1_REACHED"]` và `not is_closed` và `status != "TP2_REACHED"`.
   - **Quy tắc rời bảng khi đạt TP2:** Các mã đã đạt mục tiêu toàn vòng (`status == "TP2_REACHED"`, ví dụ `HDC +12.5%`) hoặc đã đóng bảo toàn vốn (`STOPPED_OUT`) sẽ tự động biến mất khỏi `#active-positions-table` và chuyển vào ngăn lưu trữ lịch sử collapsible (`<details>`).
   - Sắp xếp vị thế đang chạy theo thứ tự `% Lãi/Lỗ (PnL %)` giảm dần: mã sinh lời tốt nhất (như `TCH +5.5%` chân sóng) luôn đứng ở vị trí số 1 trên cùng.
3. **Cấu trúc 10 cột dữ liệu chuẩn xác:**
   - `STT`, `Mã CP`, `Ngày Mua (T0)`, `Chu Kỳ T+` (Huy hiệu T+0, T+1, T+2, T+k), `Giá Mua Gốc` (bất biến), `Thị Giá Live` (`.live-price`), `Lãi/Lỗ PnL %` (`.live-pnl`), `Cắt Lỗ (SL)` (hiện nhãn Hòa Vốn khi đạt TP1), `Chốt Lời (TP1 / TP2)` (gạch ngang TP1 khi đã chạm), `Trạng Thái & Quyết Nghị` (Huy hiệu rõ ràng: `🎯 ĐÃ CHỐT 50% TP1 — GỒNG LÃI TỚI TP2 (CẤM MUA ĐUỔI)`).
4. **Đồng bộ thời gian thực qua VPS Client-Side JS:**
   - Tự động kéo giá thị trường mỗi 30 giây từ `https://bgapidatafeed.vps.com.vn/getliststockdata/`.
   - Cập nhật tức thì `.live-pnl[data-sym]` theo công thức `((livePrice - entryOriginal) / entryOriginal) * 100`.
   - Tô màu chuẩn xác sàn chứng khoán: Tím `#ea39b8` (trần), Xanh lơ `#00e5ff` (sàn), Xanh lá `#00e676` (lãi), Đỏ `#ff5252` (lỗ).
   - Tự động cập nhật huy hiệu `.pos-badge` khi giá thị trường chạm mốc TP2 hoặc SL.
5. **Cắt giảm thời gian sinh mã HTML Terminal:**
   - Bỏ việc chạy lại `WalkForwardCoordinator().run_full_walk_forward()` trong mỗi chu kỳ xuất bản HTML, giảm thời gian sinh trang từ ~12 giây xuống ~0.5 giây.

---

## 3. Hệ Quả & Nghiệm Thu (Consequences & Verification)

- **Test Suite:** Toàn bộ 138/138 unit & integration tests vượt qua 100% (`tests/test_positions_tracker_tab.py`, `tests/test_retail_t25_blindspots.py`).
- **Trải nghiệm người dùng:** Khi mở Dashboard, nhà đầu tư có thể chuyển sang Tab 2 bất kỳ lúc nào để tra cứu danh mục đang nắm giữ, biết rõ cổ phiếu đã ở chu kỳ T mấy, lãi bao nhiêu %, không còn băn khoăn khi thấy cổ phiếu tím trần mà không được báo mua mới.
- **Tiêu chuẩn Zero-Waste:** Kích thước kho lưu trữ được giữ nguyên ở mức siêu nhẹ `1.96 MB < 15 MB`.
