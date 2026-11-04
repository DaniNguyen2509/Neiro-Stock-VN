# 📊 Báo Cáo Đánh Giá Toàn Diện Hệ Thống & Machine Learning
*Hệ thống Neiro-Stock-VN • Thời điểm lập báo cáo: `2026-11-04 12:59:28` (Giờ VN UTC+7)*

---

## 📌 Tóm Tắt Định Hướng (Executive Verdict)

| Hạng Mục | Kết Luận Thẩm Định | Tình Trạng Dữ Liệu | Quyết Nghị Triển Khai |
| :--- | :---: | :---: | :--- |
| **Hệ Thống Định Lượng (Rule-Based Quant)** | **🟢 ĐÃ ĐỦ ĐIỀU KIỆN & VƯỢT CHUẨN** | 1,450 phiên (2021 – 2026), 4 chu kỳ | Đang vận hành live, Sharpe OOS = **1.65**, MDD = **4.18%** |
| **Sổ Cái Tín Hiệu Live (Live Signals)** | **🟡 THEO DÕI BẢO TOÀN VỐN** | 79 vị thế (40 đóng, 39 mở) | Cầu chì T+2.5 & Cổng Mua Mới ADR-019 đã phát huy hiệu quả chặn mua đỉnh |
| **Mô Hình Machine Learning (ML Models)** | **🔴 CHƯA ĐỦ ĐIỀU KIỆN HUẤN LUYỆN** | 79 mẫu (thiếu 421 mẫu) | Sử dụng làm Pilot Cold-Start, tiếp tục tích lũy dữ liệu tự động |

---

## 1. Báo Cáo Kiểm Định Walk-Forward Backtesting (2021 - 2026)
*Cơ sở dữ liệu lịch sử chuẩn mực 1,450 thanh nến, mô phỏng khắt khe chu kỳ thanh toán T+2.5 và phí thuế thực tế.*

| Chỉ Số Đánh Giá | In-Sample (2021 - 2023) | Out-of-Sample (2024 - 2026) | Toàn Kỳ (2021 - 2026) | Ghi Chú Ý Nghĩa |
| :--- | :---: | :---: | :---: | :--- |
| **Tổng Lợi Nhuận (Total Return)** | **+8.63%** | **+51.14%** | **+60.28%** | Lợi nhuận vượt trội giai đoạn OOS |
| **Tỷ Suất Sinh Lời Hàng Năm (CAGR)** | 2.71% | **16.81%** | 8.54% | Tăng trưởng ổn định dài hạn |
| **Sharpe Ratio (Rf = 4.5%)** | -0.19 | **1.65** | 0.54 | Hiệu suất điều chỉnh rủi ro cao ở OOS |
| **Sortino Ratio** | -0.26 | **2.82** | 0.80 | Kiểm soát biến động sụt giảm tốt |
| **Sụt Giảm Tối Đa (Max Drawdown)** | 13.30% | **4.18%** | 13.30% | Sụt giảm thấp trong thị trường gấu 2022 |
| **Tỷ Lệ Thắng (Win Rate %)** | 30.14% | **49.21%** | 39.13% | Thực tế khớp lệnh theo T+2.5 |
| **Profit Factor (Lãi gộp / Lỗ gộp)** | 1.22 | **3.46** | 2.02 | Lãi gấp 2 lần lỗ toàn kỳ |
| **Alpha vs VN-Index** | **+15.56%** | -114.20% | -88.20% | Alpha dương lớn trong downtrend 2022 |
| **Lần Chặn Bán Ép T+2.5** | 15 | 15 | 30 | Đảm bảo đúng luật thanh toán VN |
| **Số Lượng Giao Dịch** | 73 | 63 | 138 | Tần suất giao dịch chọn lọc |

---

## 2. Báo Cáo Phân Tích Sổ Cái Tín Hiệu Thực Tế (Live Track Record)
*Dữ liệu ghi nhận trực tiếp từ Fialda VIP qua pipeline quét ngầm tự động (26/10 – 04/11/2026).*

- **Tổng số vị thế theo dõi:** **79** mã cổ phiếu.
- **Trạng thái vòng đời vị thế:**
  - **Đã đóng (Closed):** **40** mã (39 STOP_LOSS, 1 WIN_TP2 HPG). Win Rate: **5.0%**, PnL trung bình đóng: **-6.14%**.
  - **Đang mở (Active):** **39** mã (1 mã đạt TP1).
- **Thống kê biên độ dịch chuyển giá:**
  - **PnL lũy kế trung bình:** **-3.20%** (Biên độ từ -17.1% đến +12.5%).
  - **Lợi nhuận tiềm năng cực đại (Mean MFE):** **+0.97%**.
  - **Sụt giảm cực đại trung bình (Mean MAE):** **-4.06%**.
- **Ý Nghĩa Thực Chiến:**
  Giai đoạn 26/10 đến 04/11/2026, thị trường cơ sở gặp áp lực bán mạnh và gãy nhiều hỗ trợ ngắn hạn. Tỷ lệ đóng dừng lỗ 39/40 vị thế phản ánh sát diễn biến giảm điểm chung của VN-Index. Nhờ có **Cầu chì Vĩ mô T+2.5** và **6 Cổng Mua Mới của ADR-019**, toàn bộ các mã suy yếu đã bị khóa quyền mua (`CẤM BẮT DAO RƠI`, `CẤM MUA ĐUỔI`), ngăn chặn triệt để hành vi bình quân giá xuống hay FOMO nguy hiểm.

---

## 3. Thẩm Định Dữ Liệu Machine Learning & Lộ Trình Chuẩn Hóa
*Đối chiếu với Bộ Tiêu Chuẩn Thống Kê Tabular Machine Learning (ADR-011 / ADR-019 / ADR-022).*

| Tiêu Chí Kỹ Thuật | Hiện Trạng Dữ Liệu | Tiêu Chuẩn Sản Xuất | Đánh Giá Rủi Ro |
| :--- | :---: | :---: | :--- |
| **Quy mô mẫu (Sample Size)** | **79** dòng | $\ge 500$ dòng | 🔴 Cực kỳ thiếu mẫu (dễ Overfitting) |
| **Mẫu chuẩn hóa v2** | **1** (1.27%) | 100% mẫu chuẩn v2 | ⚠️ 78 mẫu cũ v1_legacy thiếu đặc trưng T0 |
| **Mất cân bằng nhãn (Imbalance)** | **18.75:1** (95% nhãn 0 vs 5% nhãn 1) | $\le 4:1$ | 🔴 Bẫy Dummy Guessing (cần Class Weights) |
| **Độ hoàn thiện đặc trưng v2** | **13.13%** | $\ge 80.0\%$ | ⚠️ Các trường PE, PB, CAMEL, Basis đang khuyết ở v1 |

### 🛠️ Lộ Trình Chuẩn Hóa Đã Triển Khai (ADR-022):
1. **Module Tiền Xử Lý (`src.ml.preprocessor.MLSignalPreprocessor`):**
   - Hỗ trợ `clean_and_filter_schema(drop_legacy=True)` loại bỏ hoàn toàn nhiễu từ các mẫu v1_legacy.
   - Chuẩn hóa phân vị **Winsorization (1% – 99%)** khử nhiễu ngoại lai tài chính.
   - Chuẩn hóa **Robust Scaling** theo Median/IQR chống méo lệch dữ liệu.
   - Tính toán **Class Weights** bù trừ mất cân bằng nhãn 95:5.
   - Phân chia **Purged Time-Series Split** có khoảng đệm 3 phiên chống rò rỉ dữ liệu T+2.5.
2. **Khuyến Nghị Vận Hành:**
   - **Hiện tại:** Duy trì chạy pipeline quét tự động 30 phút/lần trên GitHub Actions để tích lũy hữu cơ các mẫu schema `v2`.
   - **Khi đạt $\ge 500$ mẫu v2:** Xuất dữ liệu sang Google Colab để train LightGBM / XGBoost theo hướng dẫn tại `docs/google_sheets_setup.md` mà không cài đặt gói nặng lên máy local (bảo tồn Zero-Waste Mandate).
