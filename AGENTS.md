# AGENTS.md - Quy tắc cốt lõi cho mọi AI Coding Agent tại Neiro-Stock-VN
> Áp dụng bắt buộc cho: **Gemini, DeepSeek, Claude, Cursor, Copilot, OpenCode, Windsurf** và mọi mô hình AI khi hoạt động trong repository Neiro-Stock-VN.

---

## 1. QUY TRÌNH TIỀN TRẠM BẮT BUỘC: GỌI SKILL TRƯỚC MỌI PHẢN HỒI

> **BƯỚC 0: TRƯỚC KHI SUY NGHĨ GIẢI PHÁP, TRẢ LỜI HOẶC SỬA BẤT KỲ DÒNG CODE NÀO:**
> Mọi model AI **BẮT BUỘC** phải truy cập vào thư mục `.agents/skills/` và dùng tool đọc file (`view_file` / `read_file`) để nạp file `SKILL.md` phù hợp nhất với yêu cầu hiện tại của người dùng.

### 1.1. Header xác nhận bắt buộc (Bằng chứng gọi Skill)
Ở đầu mỗi lượt phản hồi cho người dùng, AI **bắt buộc** phải ghi dòng trạng thái sau:
- Khi áp dụng skill:
  `[Active Skill: <ten-skill> | Path: .agents/skills/<ten-skill>/SKILL.md]`
- Ngoại lệ duy nhất (câu chào hỏi, hội thoại thông thường không liên quan kỹ thuật/code):
  `[Active Skill: None | Reason: <lý do ngắn gọn>]`

### 1.2. Quy tắc chống lách luật (Anti-Rationalization Gate)
Các model **TUYỆT ĐỐI KHÔNG ĐƯỢC** tự biện hộ để bỏ qua việc gọi skill:
- "Yêu cầu này đơn giản tôi có thể giải quyết ngay" -> **CẤM**
- "Tôi đã nắm rõ nghiệp vụ chứng khoán VN" -> **CẤM**
- "Tôi sẽ trả lời trước rồi mới gọi skill sau" -> **CẤM**

---

## 2. BẢNG ÁNH XẠ NHANH: Ý ĐỊNH (INTENT) -> SKILL BẮT BUỘC GỌI

| Giai đoạn / Ý định của User | Tên Skill | Đường dẫn SKILL.md |
| :--- | :--- | :--- |
| **Chưa rõ làm gì / Cần định hướng** | using-agent-skills | `.agents/skills/using-agent-skills/SKILL.md` |
| **Làm rõ yêu cầu / Phỏng vấn lấy spec** | interview-me | `.agents/skills/interview-me/SKILL.md` |
| **Phát triển ý tưởng / So sánh phương án** | idea-refine | `.agents/skills/idea-refine/SKILL.md` |
| **Tính năng mới / Thay đổi kiến trúc** | spec-driven-development | `.agents/skills/spec-driven-development/SKILL.md` |
| **Lập kế hoạch / Chia nhỏ task** | planning-and-task-breakdown | `.agents/skills/planning-and-task-breakdown/SKILL.md` |
| **Viết code / Sửa code / Triển khai** | incremental-implementation | `.agents/skills/incremental-implementation/SKILL.md` |
| **Code phức tạp, rủi ro cao** | doubt-driven-development | `.agents/skills/doubt-driven-development/SKILL.md` |
| **Đối chiếu tài liệu chuẩn / Verify API** | source-driven-development | `.agents/skills/source-driven-development/SKILL.md` |
| **Giao diện / Frontend / Component UI** | frontend-ui-engineering | `.agents/skills/frontend-ui-engineering/SKILL.md` |
| **Audit Dashboard / Rà soát bảng số liệu** | multi-layer-dashboard-audit | `.agents/skills/multi-layer-dashboard-audit/SKILL.md` |
| **Thiết kế API / Struct / Interface** | api-and-interface-design | `.agents/skills/api-and-interface-design/SKILL.md` |
| **Thu thập context / Nạp tài liệu repo** | context-engineering | `.agents/skills/context-engineering/SKILL.md` |
| **Viết test / TDD / Kiểm thử logic** | test-driven-development | `.agents/skills/test-driven-development/SKILL.md` |
| **Sửa lỗi / Debug / Bug** | debugging-and-error-recovery | `.agents/skills/debugging-and-error-recovery/SKILL.md` |
| **Review code / Đánh giá chất lượng** | code-review-and-quality | `.agents/skills/code-review-and-quality/SKILL.md` |
| **Tối ưu code / Đơn giản hóa** | code-simplification | `.agents/skills/code-simplification/SKILL.md` |
| **Bảo mật / Rà soát lỗ hổng** | security-and-hardening | `.agents/skills/security-and-hardening/SKILL.md` |
| **Hiệu năng / Tối ưu tốc độ** | performance-optimization | `.agents/skills/performance-optimization/SKILL.md` |
| **Git / Commit / Branch** | git-workflow-and-versioning | `.agents/skills/git-workflow-and-versioning/SKILL.md` |
| **Viết tài liệu / ADR / Kiến trúc** | documentation-and-adrs | `.agents/skills/documentation-and-adrs/SKILL.md` |
| **Ship / Release / Đóng gói** | shipping-and-launch | `.agents/skills/shipping-and-launch/SKILL.md` |

*(Nếu không biết chọn skill nào, mặc định nạp `.agents/skills/using-agent-skills/SKILL.md`)*

---

## 3. CÁC QUY TẮC BẤT DI BẤT DỊCH TẠI NEIRO-STOCK-VN

1. **Nguồn sự thật:** `docs/spec.md` (đặc tả hệ thống) và `docs/architecture.md`. Mã nguồn thực tế có quyền lực tối cao nếu có mâu thuẫn.
2. **Triết lý Quantamental chuẩn xác:**
   - Hợp lưu giữa **Cơ bản định lượng (Fundamental Quant)**: Piotroski F-score, tăng trưởng doanh thu/LNST cốt lõi, CFO/Net Income > 1, định giá theo phân vị P/E - P/B 3 năm.
   - Và **Cấu trúc vi mô dòng tiền (Market Microstructure & Order Flow)**: Volume Profile (HVN/LVN/POC), Order Flow Imbalance (OFI), Lệnh lớn cá mập $\ge 100k$, Dòng tiền Khối ngoại & Tự doanh, Chênh lệch Basis VN30F1M.
   - **Tuyệt đối KHÔNG sử dụng các chỉ báo trễ thông thường đơn lẻ (RSI, MACD, Stochastic...)** để đoán đỉnh đáy.
3. **Quy tắc bất biến chu kỳ thanh toán T+2.5:**
   - Mọi mô hình Position Sizing và Quản trị rủi ro bắt buộc phải tính đến độ trễ về cổ phiếu T+2.5. Tuyệt đối không mô hình hóa giả định thị trường có thể cắt lỗ T+0 trên cổ phiếu mới mở hoàn toàn nếu không có lượng hàng sẵn có làm đệm (Rolling Inventory) hoặc phòng hộ bằng Short VN30F1M.
4. **Bắt buộc đồng bộ tài liệu (DOCUMENTATION-FIRST MANDATE):**
   - Sau khi hoàn thành bất kỳ tính năng, chỉnh sửa kiến trúc hoặc sửa lỗi nào, AI **bắt buộc phải cập nhật lại tài liệu** tương ứng (`docs/spec.md`, `docs/architecture.md`, `README.md`, hoặc tạo ADR trong `docs/decisions/`) trước khi kết thúc phiên làm việc.
5. **Định dạng ngôn ngữ & Trình bày:**
   - Code Python: snake_case cho hàm/biến, PascalCase cho class, type hints bắt buộc cho public interface. Comment giải thích logic nghiệp vụ bằng tiếng Việt có dấu.
   - Markdown: Tiếng Việt có dấu, trình bày khoa học, trực quan, chuyên nghiệp.

---

## 🛡️ 4. QUY ĐỊNH BẮT BUỘC TỐI CAO: AUDIT DASHBOARD ĐA TẦNG & TỪNG CỘT DỮ LIỆU (MULTI-LAYER DASHBOARD MANDATE)

> [!CRITICAL]
> **LUẬT TỐI CAO CHO DASHBOARD & GIAO DIỆN BÁO CÁO TÀI CHÍNH:**
> 1. **Tuyệt đối cấm lỗi "Hút tầm nhìn" (Anti-Tunnel-Vision Gate):** Nghiêm cấm việc chỉ sửa các lỗi bề nổi dễ thấy (như hardcode số trên thẻ Header KPI, bộ đếm ngược JS, layout CSS) rồi vội vã kết luận đã hoàn thành, trong khi bỏ sót logic nghiệp vụ cốt lõi của các cột trong bảng dữ liệu.
> 2. **Bắt buộc kiểm tra đủ 3 tầng độc lập:**
>    - **Tầng 1 (Presentation & Stream):** Bố cục trực quan, responsive không cuộn ngang bất hợp lý, Client JS kéo giá live và auto-reload mượt mà, đúng chuẩn màu sàn giao dịch.
>    - **Tầng 2 (Data Pipeline & Continuity):** Kiểm tra tính liên tục của dữ liệu qua nhiều phiên quét (Session Debounce, Test Pollution Guard, Rolling Window bảo tồn bộ nhớ).
>    - **Tầng 3 (Column-by-Column Domain Logic):** **Audit từng cột một trong bảng dữ liệu**. Phải hiểu rõ bản chất nghiệp vụ của từng con số/nhãn dán: Có cơ chế fallback lịch sử khi cổ phiếu tạm thời biến mất rồi quay lại không? Có bị gán nhãn `MỚI` sai lệch gây hiểu lầm cho trader không? Dấu âm/dương của thứ hạng và biến động có phản ánh đúng chiều tốt/xấu không?
> 3. **Thử nghiệm góc nhìn Nhà đầu tư thực chiến (Investor Persona Test):** Trước khi kết thúc task, AI bắt buộc phải tự đặt câu hỏi: *"Nếu một nhà đầu tư thực tế nhìn vào từng con số trên bảng này qua nhiều phiên giao dịch liên tiếp, có cột nào gây hiểu lầm hoặc đưa ra tín hiệu sai lệch hay không?"*

---

## 🧹 5. QUY ĐỊNH BẮT BUỘC: DỌN RÁC & BẢO TỒN DUNG LƯỢNG MÁY TÍNH (ZERO-WASTE MANDATE)

> [!CRITICAL]
> **TIÊU CHUẨN DUNG LƯỢNG TỐI THIỂU CHO MÁY TÍNH CỦA NGƯỜI DÙNG:**
> Toàn bộ dự án phải luôn được giữ ở mức siêu nhẹ (< 15MB). Mọi AI model khi thực thi đều phải tuân thủ nghiêm ngặt:
> 1. **Tự động dọn rác ngay lập tức:** Mọi file cào thử nghiệm (HTML/JSON tạm), script test scratch, file log tạm thời sinh ra trong quá trình nghiên cứu bắt buộc phải bị XÓA SẠCH SẼ ngay sau khi tác vụ hoàn thành.
> 2. **Không xả rác vào thư mục gốc:** Không tạo các file rác, file backup đuôi .bak, .tmp bừa bãi.
> 3. **Tận dụng đám mây (Cloud-First):** Ưu tiên chạy tính toán trên Google Colab / Codespaces, không cài đặt các gói dữ liệu nặng vào ổ cứng laptop của người dùng nếu không có yêu cầu rõ ràng.

---

## 🚀 6. QUY TRÌNH KẾT THÚC BẮT BUỘC: 4 BƯỚC FINAL TỰ ĐỘNG (ZERO-PROMPT FINALIZATION MANDATE)

> [!CRITICAL]
> **LUẬT TỐI CAO - KHÔNG CẦN CHỜ NGƯỜI DÙNG NHẮC LẠI:**
> Sau khi hoàn thành bất kỳ nhiệm vụ lập trình, sửa đổi mã nguồn, tối ưu tính năng hoặc cấu hình hệ thống nào, AI model **TUYỆT ĐỐI KHÔNG ĐƯỢC DỪNG LẠI** khi chưa hoàn tất chuỗi **4 BƯỚC FINAL TỰ ĐỘNG** sau:
> 
> 1. **Đồng Bộ Tài Liệu & Kiến Trúc (Documentation Sync):**
>    - Bắt buộc cập nhật ngay các tệp tài liệu tương ứng: [README.md](README.md), [docs/spec.md](docs/spec.md), [docs/architecture.md](docs/architecture.md) (và lập ADR trong `docs/decisions/` nếu có thay đổi kiến trúc/nghiệp vụ).
> 2. **Kiểm Thử Quality Gate:**
>    - Chạy toàn bộ test suite (`python -m pytest`) đảm bảo tỷ lệ pass 100%, không để lọt bất kỳ lỗi hồi quy (regression) nào.
> 3. **Dọn Rác & Kiểm Soát Zero-Waste:**
>    - Xóa sạch các tệp tạm, cache cào dữ liệu, log scratch phát sinh trong phiên làm việc; kiểm tra dung lượng repository luôn `< 15MB`.
> 4. **Commit & Push Lên Git (Automated Git Push):**
>    - Tự động `git add`, `git commit` với thông điệp chuẩn Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`, `ci:`) và thực thi `git push origin <branch>`.
>    - Báo cáo rõ ràng commit hash và trạng thái đẩy code thành công trong câu trả lời kết thúc phiên.
