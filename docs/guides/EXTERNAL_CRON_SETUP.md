# Hướng Dẫn Kích Hoạt Quét Tự Động Neiro-Stock-VN Qua External Cron Webhook

Tài liệu này hướng dẫn cách kết nối dịch vụ Cron bên ngoài (**cron-job.org** hoặc **Cloudflare Workers**) để kích hoạt bot quét định lượng Neiro-Stock-VN chạy tự động trên GitHub Actions, khắc phục 100% tình trạng bị trễ (delay) hoặc bị bỏ qua (drop queue) của hạ tầng GitHub Actions native scheduler.

---

## 🔑 BƯỚC 1: TẠO GITHUB PERSONAL ACCESS TOKEN (PAT)

Để dịch vụ bên ngoài có quyền kích hoạt bot trên GitHub, bạn cần tạo một mã Token có quyền tối thiểu (Fine-grained Token):

1. Truy cập: [GitHub Settings > Personal Access Tokens > Fine-grained tokens](https://github.com/settings/tokens?type=beta)
2. Nhấn nút **"Generate new token"**.
3. Điền thông tin:
   - **Token name:** `Neiro-Stock-External-Cron`
   - **Expiration:** Chọn `90 days` hoặc `No expiration` (tùy nhu cầu).
   - **Repository access:** Chọn **"Only select repositories"** -> Chọn `DaniNguyen2509/Neiro-Stock-VN`.
4. Mục **Permissions > Repository permissions**:
   - Tìm **"Actions"**: Chọn **Access: Read and write** (cần quyền này để trigger workflow).
   - Tìm **"Contents"**: Chọn **Access: Read-only**.
   - Tìm **"Metadata"**: Tự động chọn **Read-only**.
5. Nhấn **"Generate token"** ở cuối trang và copy mã token (bắt đầu bằng `github_pat_...`).

---

## 🌐 BƯỚC 2: CẤU HÌNH CRON-JOB.ORG (KHUYÊN DÙNG - 2 PHÚT LÀ XONG)

`cron-job.org` là dịch vụ lập lịch cron trên nền web hoàn toàn miễn phí, độ trễ 0 giây và không yêu cầu cài đặt code.

### 1. Đăng ký & Tạo Job Mới
- Truy cập [cron-job.org](https://cron-job.org/) -> Đăng ký tài khoản miễn phí.
- Vào mục **"Cronjobs"** -> Nhấn **"CREATE CRONJOB"**.

### 2. Điền thông số Request
- **Title:** `Neiro Stock VN - Trading Scan`
- **URL:** 
  ```text
  https://api.github.com/repos/DaniNguyen2509/Neiro-Stock-VN/dispatches
  ```
- **Request Method:** Chọn **`POST`**.
- **Headers (Nhấn Add Header):**
  | Key | Value |
  | :--- | :--- |
  | `Accept` | `application/vnd.github+json` |
  | `Authorization` | `Bearer github_pat_YOUR_TOKEN_HERE` |
  | `User-Agent` | `Neiro-CronJob-Org` |
  | `X-GitHub-Api-Version` | `2022-11-28` |

- **Request Body (dán vào ô Body):**
  ```json
  {"event_type": "external_scan"}
  ```

### 3. Cấu hình Lịch Quét (Schedule)
- **Timezone:** Chọn `Asia/Bangkok` hoặc `Asia/Ho_Chi_Minh` (GMT+7).
- **Execution Schedule:** Chọn **User-defined (Cron syntax)** hoặc chọn các mốc giờ:
  
  **Khung giờ quét chuẩn trong ngày giao dịch (Thứ 2 đến Thứ 6):**
  - **Phiên sáng:** `09:18, 09:48, 10:18, 10:48, 11:18, 11:48`
  - **Phiên chiều:** `13:18, 13:48, 14:18, 14:48`
  - **Chốt phiên ATC:** `15:08`
  - **Chốt Tự doanh & Khối ngoại chiều:** `17:35`
  - **Chốt sổ tối toàn diện:** `19:08`

*(Bạn có thể tạo 1 cronjob chạy mỗi 30 phút trong khoảng 09:15-11:45 và 13:15-15:15 Thứ 2 - Thứ 6, hoặc tạo các job riêng lẻ tùy thích).*

- Nhấn **"CREATE"**.
- Nhấn nút **"Test Run"** để kiểm tra ngay lập tức. Nếu GitHub trả về mã `204 No Content` là hoàn tất thành công 100%!

---

## ⚡ BƯỚC 3 (TÙY CHỌN): CẤU HÌNH CLOUDFLARE WORKERS (SERVERLESS)

Nếu bạn muốn quản lý tập trung bằng code JavaScript serverless miễn phí:

1. Vào [Cloudflare Dashboard](https://dash.cloudflare.com/) -> **Workers & Pages** -> **Create Application** -> **Create Worker**.
2. Đặt tên worker: `neiro-stock-scanner-cron`.
3. Nhấn **Deploy** rồi vào mục **Edit code**.
4. Dán toàn bộ nội dung file [`scripts/cloudflare_worker_cron.js`](file:///c:/Users/Daniel/Documents/My-Projects/Neiro-Stock-VN/scripts/cloudflare_worker_cron.js) vào trình soạn thảo và nhấn **Save and deploy**.
5. Vào tab **Settings**:
   - **Variables and Secrets**:
     + Nhấn Add -> Variable name: `GITHUB_PAT`, gán giá trị token của bạn, nhấn **Encrypt**.
     + Variable name: `GITHUB_REPO` = `DaniNguyen2509/Neiro-Stock-VN`.
   - **Triggers > Cron Triggers**:
     + Nhấn **Add Cron Trigger** và điền các biểu thức POSIX cron (giờ UTC):
       - `18,48 2,3,4 * * 1-5` (Phiên sáng)
       - `18,48 6,7 * * 1-5` (Phiên chiều)
       - `8 8 * * 1-5` (Chốt ATC)
       - `35 10 * * 1-5` (Chốt Tự doanh & Ngoại)
       - `8 12 * * 1-5` (Chốt sổ tối)

---

## 🖥️ BƯỚC 4: KÍCH HOẠT THỦ CÔNG QUA TERMINAL / SCRIPT

Mã nguồn dự án đã tích hợp sẵn script Python [`scripts/trigger_scan.py`](file:///c:/Users/Daniel/Documents/My-Projects/Neiro-Stock-VN/scripts/trigger_scan.py) để bạn có thể kích hoạt quét từ bất kỳ máy tính nào:

```powershell
# Cách 1: Truyền trực tiếp token
python scripts/trigger_scan.py --token "github_pat_..."

# Cách 2: Đặt biến môi trường và gọi nhanh
$env:GITHUB_TOKEN="github_pat_..."
python scripts/trigger_scan.py
```

Hoặc dùng lệnh cURL:
```bash
curl -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer <YOUR_GITHUB_PAT>" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  https://api.github.com/repos/DaniNguyen2509/Neiro-Stock-VN/dispatches \
  -d '{"event_type": "external_scan"}'
```
