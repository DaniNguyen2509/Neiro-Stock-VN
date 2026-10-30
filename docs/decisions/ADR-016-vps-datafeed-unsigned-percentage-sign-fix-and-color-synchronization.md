# ADR-016: Khắc Phục Lệch Dấu Biến Động Giá VPS Datafeed & Đồng Bộ Màu Sắc Tuyệt Đối

- **Trạng thái:** Đã nghiệm thu (Accepted)
- **Ngày quyết định:** 30/10/2026
- **Phạm vi tác động:** `src/hud/terminal.py`, `exports/index.html`, `exports/vn_stock_terminal.html`, `exports/404.html`, `tests/test_terminal_hud.py`, `docs/architecture.md`, `docs/spec.md`

---

## 1. Bối cảnh & Hiện tượng (Context & Symptom)

Trên bảng điều khiển giao dịch tác chiến (Web Terminal Dashboard), khi theo dõi phiên giao dịch trực tiếp:
- Một số cổ phiếu giảm điểm (ví dụ: HPG giảm từ tham chiếu 21.20 xuống 20.95, giảm -1.2%), thị giá được hiển thị chuẩn màu đỏ (`#ff5252`).
- Tuy nhiên, phần trăm biến động ngay bên cạnh thị giá lại hiển thị nhầm thành `(+1.2%)` thay vì `(-1.2%)`.
- Tình trạng này xảy ra với toàn bộ các mã giảm điểm (VIX, NKG, TCH, SHI, ORS, CII, VSC, TPB, DIG, TCX, GEX...), gây hiểu lầm nghiêm trọng cho nhà đầu tư khi nhìn một con số màu đỏ nhưng mang dấu `+`.

---

## 2. Phân Tích Nguyên Nhân Gốc Rễ (Root Cause Analysis)

1. **Đặc thù của Public Datafeed VPS (`https://bgapidatafeed.vps.com.vn/getliststockdata/`):**
   - Trường dữ liệu `ot` (offset / độ lệch giá) và `changePc` (phần trăm biến động) do API VPS trả về **luôn là số dương (độ lớn tuyệt đối / unsigned magnitude)**, không hề mang dấu âm (`-`) ngay cả khi cổ phiếu giảm giá sâu:
     ```json
     {
       "sym": "HPG",
       "r": 21.2,
       "lastPrice": 20.95,
       "ot": "0.25",
       "changePc": "1.18"
     }
     ```
2. **Lỗi logic suy diễn dấu tại Client JavaScript:**
   - Trước đây mã client JS gán trực tiếp:
     ```javascript
     const chgPc = Number(item.changePc || 0);
     // ...
     const sign = info.changePct > 0 ? '+' : '';
     changeEl.innerText = '(' + sign + info.changePct.toFixed(1) + '%)';
     ```
   - Do `changePc` luôn là `"1.18"` (> 0), điều kiện `info.changePct > 0` luôn trả về `true`, dẫn đến việc tự động thêm tiền tố `+` thành `(+1.2%)`.

---

## 3. Giải Pháp Triệt Để (Architectural Fix)

Triển khai cơ chế **Khử lệch dấu hai tầng (Double-Guard Sign Synchronization)**:

1. **Tầng 1 - Chuẩn hóa dữ liệu nguồn tại Data Mapper:**
   - Khi bóc tách mảng `data` từ API VPS, so sánh trực tiếp giá khớp cuối cùng (`lastPrice` / `lp`) với giá tham chiếu (`r`):
     - Nếu $lp < r$: gán `chg = -Math.abs(chg)` và `chgPc = -Math.abs(chgPc)`. (Nếu `chgPc == 0`, tự động tính fallback `((lp - r) / r) * 100`).
     - Nếu $lp > r$: gán `chg = Math.abs(chg)` và `chgPc = Math.abs(chgPc)`.
     - Nếu $lp == r$ hoặc $lp == 0$: gán `chg = 0` và `chgPc = 0`.

2. **Tầng 2 - Khóa logic hiển thị DOM (Double-Guard Presentation Lock):**
   - Khi render ra thẻ `.live-change`, dấu hiển thị được khóa tuyệt đối theo so sánh giữa thị giá `p` và tham chiếu `info.ref`:
     ```javascript
     let pctStr = Math.abs(info.changePct).toFixed(1);
     if (pctStr === '0.0' || p === info.ref) {
         changeEl.innerText = '(0.0%)';
     } else if (p > info.ref) {
         changeEl.innerText = '(+' + pctStr + '%)';
     } else if (p < info.ref) {
         changeEl.innerText = '(-' + pctStr + '%)';
     } else {
         changeEl.innerText = '(' + (info.changePct > 0 ? '+' : '-') + pctStr + '%)';
     }
     changeEl.style.color = color;
     ```
   - Cơ chế này loại trừ 100% khả năng một cổ phiếu có giá thấp hơn tham chiếu lại có thể hiển thị dấu `+`.

---

## 4. Kiểm Thử & Nghiệm Thu (Quality Gate)

1. Bổ sung unit test `test_terminal_hud_live_change_negative_sign_and_sync` trong `tests/test_terminal_hud.py` nhằm xác thực logic khử lệch dấu và cấu trúc DOM rendering.
2. Kiểm thử toàn bộ hệ thống (`97/97 tests passed 100%`).
3. Đồng bộ toàn bộ các tệp đầu ra tĩnh trong `exports/` (`index.html`, `vn_stock_terminal.html`, `404.html`).
