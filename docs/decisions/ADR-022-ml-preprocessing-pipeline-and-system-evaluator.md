# ADR-022: Khung Chuẩn Hóa Tiền Xử Lý Dữ Liệu ML & Bộ Đánh Giá Toàn Diện Hệ Thống

- **Trạng thái:** ACCEPTED & IMPLEMENTED
- **Ngày quyết định:** 2026-11-04
- **Phạm vi tác động:** `src/ml/`, `scripts/evaluate_system_and_ml.py`, `reports/system_and_ml_evaluation.md`, `tests/test_ml_preprocessor_and_eval.py`, `docs/spec.md`, `docs/architecture.md`, `README.md`

---

## 1. Bối Cảnh (Context)

Người dùng yêu cầu kiểm toán và đánh giá xem hệ thống Neiro-Stock-VN đã có sẵn đủ dữ liệu để đánh giá hiệu suất hệ thống và huấn luyện mô hình Machine Learning (ML) hay chưa, đồng thời tiến hành chuẩn hóa nếu dữ liệu chưa đáp ứng.

Rà soát toàn diện kho dữ liệu phát hiện:
1. **Hệ thống Định lượng Quy tắc (Rule-based Quant): ĐÃ ĐỦ DỮ LIỆU.** Khung Walk-Forward Backtesting Engine đã có sẵn bộ dữ liệu chuẩn toán học 1,450 phiên giao dịch (2021 – 2026) tái lập đầy đủ 4 chu kỳ kinh tế lớn của TTCK Việt Nam và kiểm soát chặt chẽ quy định T+2.5.
2. **Dữ liệu Machine Learning (ML Dataset): CHƯA ĐỦ ĐIỀU KIỆN HUẤN LUYỆN THỰC CHIẾN.**
   - **Cỡ mẫu quá nhỏ:** Tập dữ liệu `data/ml_signals_dataset.csv` mới thu thập được 79 mẫu qua 7 phiên thực tế.
   - **Lệch pha phiên bản (Schema Drift):** 78/79 mẫu mang schema `v1_legacy` sinh ra trước ADR-019 nên khuyết các đặc trưng T0 nền tảng (`pe_t0`, `pb_t0`, `eps_ttm_t0`, `camel_score_t0`, `atr_pct_t0`, `vn30_basis_t0`).
   - **Mất cân bằng nhãn trầm trọng:** `target_win_binary` có 75 nhãn 0 và 4 nhãn 1 (tỷ lệ 95:5) do thị trường chung sụt giảm, dẫn tới nguy cơ bẫy Dummy Predictor nếu huấn luyện trực tiếp.
   - **Thiếu pipeline tiền xử lý đạt chuẩn Zero-Waste:** Không có `scikit-learn` trên máy cục bộ để giữ repo < 15MB.

---

## 2. Quyết Định Thiết Kế (Decisions)

### 2.1. Module Tiền Xử Lý ML Siêu Nhẹ Thuần Python/NumPy/Pandas (`src/ml/preprocessor.py`)
Xây dựng lớp `MLSignalPreprocessor` không phụ thuộc vào bất kỳ thư viện ngoài nào (dung lượng < 10KB):
1. `clean_and_filter_schema()`: Lọc bỏ các mẫu `v1_legacy` bị thiếu đặc trưng khi huấn luyện mô hình chất lượng cao, ép kiểu dữ liệu an toàn.
2. `winsorize_dataframe()`: Cắt xén ngoại lai phân vị (1% – 99%) cho các trường tài chính có đuôi nặng (fat tails) như PE, PB, ADTV, trượt giá.
3. `robust_scale_dataframe()`: Chuẩn hóa Robust Scaling theo Trung vị (Median) và khoảng biến thiên tứ phân vị (IQR), miễn nhiễm với hiện tượng kéo xả trần/sàn.
4. `calculate_class_weights()`: Tính toán trọng số lớp mẫu $w_j = \frac{N}{K \cdot n_j}$ để xử lý triệt để mất cân bằng nhãn 95:5.
5. `purged_train_test_split()`: Phân chia tập Train/Test theo chuỗi thời gian kèm khoảng đệm thanh toán T+2.5 (`purge_window_sessions = 3`) loại trừ rò rỉ dữ liệu (Lookahead Leakage) sang tập kiểm định.

### 2.2. Khung Kiểm Toán & Thẩm Định Dữ Liệu Tự Động (`src/ml/dataset_validator.py`)
Xây dựng lớp `MLDatasetValidator`:
- Đo lường độ thiếu hụt mẫu so với chuẩn thống kê ($N \ge 500$).
- Kiểm tra tỷ lệ Schema Drift và độ hoàn thiện đặc trưng V2.
- Tính toán tỷ lệ mất cân bằng nhãn và phát cảnh báo định lượng khi dữ liệu chưa đủ điều kiện.

### 2.3. Script Đánh Giá Toàn Diện 3 Tầng (`scripts/evaluate_system_and_ml.py`)
Cung cấp công cụ đánh giá 1-click tích hợp:
- **Tầng 1 (Rule-Based Backtesting):** Chạy `WalkForwardCoordinator` sinh bảng so sánh In-Sample vs Out-of-Sample.
- **Tầng 2 (Live Signals Track Record):** Phân tích 79 vị thế thực tế, tỷ lệ dừng lỗ, PnL trung bình, MFE/MAE.
- **Tầng 3 (ML Readiness):** Kiểm toán chất lượng dataset và xuất báo cáo tự động tại `reports/system_and_ml_evaluation.md`.

---

## 3. Hệ Quả & Kiểm Định (Consequences & Verification)

- **Tuân thủ Zero-Waste Mandate:** Toàn bộ giải pháp chỉ thêm ~15 KB mã nguồn, không kéo theo gói thư viện nặng.
- **Cloud-First:** Tập dữ liệu và pipeline tiền xử lý sẵn sàng xuất sang Google Colab để huấn luyện mô hình khi quy mô mẫu đạt chuẩn $\ge 500$.
- **Test suite:** Bổ sung 8 test case trong `tests/test_ml_preprocessor_and_eval.py`, pass 100%.
