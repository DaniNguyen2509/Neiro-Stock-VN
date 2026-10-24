# GEMINI.md - Quy tắc cốt lõi cho Google Gemini & Antigravity IDE tại Neiro-Stock-VN
> File này được nạp tự động vào ngữ cảnh của Google Gemini mỗi phiên làm việc tại Neiro-Stock-VN.

---

## 1. QUY TRÌNH BẮT BUỘC TRƯỚC MỌI HÀNH ĐỘNG (PRE-ACTION SKILL DISCOVERY)

> **BƯỚC 0: TRƯỚC KHI TRẢ LỜI, PHÂN TÍCH HAY CHỈNH SỬA CODE:**
> Gemini **BẮT BUỘC** phải gọi tool `view_file` để đọc nội dung file `SKILL.md` tương ứng trong thư mục `.agents/skills/`.
> Tuyệt đối không được bỏ qua bước này.

### 1.1. Bằng chứng bắt buộc trong mỗi câu trả lời (Mandatory Status Header)
Bắt đầu mỗi câu trả lời gửi đến người dùng, Gemini **PHẢI** xuất ra dòng trạng thái:
- Nếu áp dụng skill:
  `[Active Skill: <tên-skill> | Path: .agents/skills/<tên-skill>/SKILL.md]`
- Nếu là câu chào hỏi / xã giao thuần túy:
  `[Active Skill: None | Reason: <lý do ngắn gọn>]`

### 1.2. Chống lách luật (Anti-Rationalization Gate)
Nghiêm cấm Gemini tự đưa ra các lý do sau để bỏ qua việc mở skill:
- Yêu cầu này đơn giản tôi có thể giải quyết ngay -> **CẤM**
- Tôi đã có đủ kiến thức trong prompt -> **CẤM**
- Tôi sẽ trả lời trước rồi mới gọi skill sau -> **CẤM**

---

## 2. BẢNG ÁNH XẠ NHANH
*(Xem bảng đầy đủ tại [AGENTS.md](AGENTS.md))*

---

## 3. LUẬT BẤT DI BẤT DỊCH TẠI NEIRO-STOCK-VN

1. **Nguồn sự thật:** [docs/spec.md](docs/spec.md) & [docs/architecture.md](docs/architecture.md). Mã nguồn thực tế có quyền lực tối cao nếu có mâu thuẫn.
2. **Quy tắc Quantamental:** Kết hợp chặt chẽ chỉ tiêu cơ bản định lượng (Piotroski F-Score $\ge 7$, CFO/NI, EPS tăng trưởng) và cấu trúc vi mô sổ lệnh / khối lượng (Volume Profile POC/HVN, Order Flow Imbalance, Smart Money Inflow).
3. **Quy tắc T+2.5:** Quản trị rủi ro bắt buộc gắn liền với chu kỳ thanh toán T+2.5 tại TTCK Việt Nam.
4. **BẮT BUỘC ĐỒNG BỘ TÀI LIỆU (DOCUMENTATION-FIRST MANDATE):** Sau khi hoàn thành bất kỳ thay đổi, tối ưu tính năng, kiến trúc hoặc sửa lỗi nào trong repository, AI model **BẮT BUỘC PHẢI CẬP NHẬT LẠI TÀI LIỆU** tương ứng trước khi kết thúc phiên làm việc.
5. **DỌN RÁC & BẢO TỒN DUNG LƯỢNG MÁY TÍNH (ZERO-WASTE MANDATE):** Giữ toàn bộ dự án dưới 15MB, tự động dọn dẹp các tệp tạm, cache cào dữ liệu sau mỗi chu kỳ kiểm thử hoặc thực thi.
