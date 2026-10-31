# Hướng Dẫn Tích Hợp Google Sheets, Looker Studio & Machine Learning

Tài liệu hướng dẫn thiết lập hệ thống **Nhật Ký Tín Hiệu Trực Tuyến Tự Động** qua Google Sheets, phân tích trực quan qua Google Looker Studio (Google Analysis), và sử dụng dữ liệu để huấn luyện Machine Learning (ML) trên Google Colab.

---

## 1. Thiết Lập Google Sheet & Google Apps Script Webhook (5 Phút)

### Bước 1: Tạo Bảng Tính Mới
1. Truy cập [Google Sheets](https://sheets.google.com) và tạo một bảng tính trống mới.
2. Đổi tên bảng tính thành: `Neiro_Stock_Signal_Ledger`.
3. Đổi tên Sheet đầu tiên từ `Trang tính1` (hoặc `Sheet1`) thành: `Signals`.

### Bước 2: Dán Mã Google Apps Script
1. Trên thanh menu Google Sheets, chọn **Tiện ích mở rộng (Extensions)** $\rightarrow$ **Apps Script**.
2. Xóa toàn bộ nội dung mặc định trong tệp `Code.gs` và dán đoạn mã sau vào:

```javascript
/**
 * Google Apps Script Webhook - Neiro-Stock-VN Signal Ledger & ML Dataset
 * Tự động ghi nhận và cập nhật tín hiệu từ GitHub Actions lên Google Sheets.
 */

function doPost(e) {
  try {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Signals");
    if (!sheet) {
      sheet = SpreadsheetApp.getActiveSpreadsheet().insertSheet("Signals");
    }

    var payload = JSON.parse(e.postData.contents);
    var records = payload.records || [];
    if (records.length === 0) {
      return ContentService.createTextOutput(JSON.stringify({ status: "empty" })).setMimeType(ContentService.MimeType.JSON);
    }

    // Danh sách các cột chuẩn hóa phục vụ phân tích & Machine Learning
    var headers = [
      "signal_id", "symbol", "first_signal_date", "last_updated",
      "entry_original", "current_price", "pnl_pct", "holding_days",
      "initial_stop_loss", "current_stop_loss", "tp1", "tp2",
      "status", "buy_permission", "advice_note",
      // ML Feature Vector tại T0
      "signal_type", "composite_rating", "rs_1m", "acc_diss_rating",
      "rrg_r", "rrg_m", "foreign_net_value_billion", "ranking_score",
      "catalyst", "adtv20_billion", "adv20_shares", "liquidity_score", "t25_exposure_level",
      // ML Ground Truth Labels
      "max_price_reached", "min_price_reached", "mfe_pct", "mae_pct",
      "pnl_t25_pct", "pnl_t5_pct", "pnl_t10_pct", "outcome_label", "target_win_binary",
      // ADR-019: v2 metadata, T0 features mo rong, co san sang ML
      "schema_version", "trading_days", "is_closed", "closed_at", "is_ml_ready",
      "has_actual_prop_flow_t0", "atr_pct_t0", "atr_dist_from_poc_t0", "poc_price_t0", "val_price_t0",
      "slippage_est_pct_t0", "market_breadth_pct_t0", "vn30_basis_t0",
      "pe_t0", "pb_t0", "eps_ttm_t0", "camel_score_t0"
    ];

    // Tạo dòng tiêu đề nếu trang tính còn trống
    if (sheet.getLastRow() === 0) {
      sheet.appendRow(headers);
      sheet.getRange(1, 1, 1, headers.length).setFontWeight("bold").setBackground("#1e293b").setFontColor("#ffffff");
      sheet.setFrozenRows(1);
    }

    // Đọc toàn bộ dữ liệu hiện có để tìm ID cập nhật
    var lastRow = sheet.getLastRow();
    var existingIds = {};
    if (lastRow > 1) {
      var idValues = sheet.getRange(2, 1, lastRow - 1, 1).getValues();
      for (var i = 0; i < idValues.length; i++) {
        existingIds[idValues[i][0]] = i + 2; // Lưu số dòng tương ứng
      }
    }

    // Ghi hoặc cập nhật từng bản ghi
    for (var r = 0; r < records.length; r++) {
      var rec = records[r];
      var rowData = headers.map(function(h) {
        return (rec[h] !== undefined && rec[h] !== null) ? rec[h] : "";
      });

      var sigId = rec["signal_id"];
      if (existingIds[sigId]) {
        // Cập nhật dòng đã tồn tại
        var rowNum = existingIds[sigId];
        sheet.getRange(rowNum, 1, 1, headers.length).setValues([rowData]);
      } else {
        // Thêm mới dòng vào cuối bảng
        sheet.appendRow(rowData);
        existingIds[sigId] = sheet.getLastRow();
      }
    }

    return ContentService.createTextOutput(JSON.stringify({ status: "success", count: records.length }))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ status: "error", message: err.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
```

### Bước 3: Triển Khai Dưới Dạng Web App
1. Bấm nút **Triển khai (Deploy)** ở góc trên bên phải $\rightarrow$ Chọn **Tùy chọn triển khai mới (New deployment)**.
2. Chọn loại: **Ứng dụng web (Web app)** (biểu tượng bánh răng).
3. Điền thông tin:
   - **Mô tả:** `Neiro Stock Ledger Webhook`.
   - **Thực thi dưới dạng (Execute as):** `Tôi (Me)`.
   - **Người có quyền truy cập (Who has access):** `Bất kỳ ai (Anyone)`. *(Bắt buộc chọn Anyone để GitHub Actions có thể gửi POST lên)*.
4. Bấm **Triển khai (Deploy)** và cấp quyền (Authorize Access).
5. Copy đường dẫn **URL ứng dụng web (Web App URL)** (dạng `https://script.google.com/macros/s/AKfycbx.../exec`).

### Bước 4: Lưu Vào GitHub Secrets
1. Vào repository GitHub của bạn: **Settings** $\rightarrow$ **Secrets and variables** $\rightarrow$ **Actions**.
2. Bấm **New repository secret**:
   - **Name:** `GOOGLE_SHEET_WEBHOOK_URL`
   - **Secret:** Dán đường link Web App URL đã copy ở Bước 3.
3. Bấm **Add secret**.

> Kể từ lúc này, mỗi khi GitHub Actions chạy quét định kỳ (mỗi 30 phút trong giờ giao dịch), hệ thống sẽ tự động cập nhật dữ liệu tín hiệu mới nhất lên Google Sheet của bạn!

---

## 2. Kết Nối Google Looker Studio (Google Analysis) Miễn Phí

Google Looker Studio (trước đây là Google Data Studio) cho phép tạo giao diện bảng điều khiển phân tích số liệu hoàn toàn miễn phí trên Web và Điện thoại:

1. Truy cập [Looker Studio](https://lookerstudio.google.com).
2. Bấm **Tạo (Create)** $\rightarrow$ **Báo cáo (Report)**.
3. Chọn nguồn dữ liệu: **Google Trang tính (Google Sheets)** $\rightarrow$ Chọn file `Neiro_Stock_Signal_Ledger` $\rightarrow$ Chọn sheet `Signals` $\rightarrow$ Bấm **Thêm (Add)**.
4. **Các biểu đồ phân tích gợi ý:**
   - **Thẻ điểm (Scorecard):** Tổng số tín hiệu, Tỷ lệ Thắng (`target_win_binary` trung bình), Lãi/Lỗ trung bình (`pnl_pct`).
   - **Biểu đồ cột (Column Chart):** Tỷ suất sinh lời `pnl_pct` phân bổ theo Ngành hoặc theo `composite_rating`.
   - **Biểu đồ tròn (Pie Chart):** Cơ cấu trạng thái `outcome_label` (`WIN_TP1`, `WIN_TP2`, `STOP_LOSS`, `ACTIVE`).
   - **Bảng dữ liệu (Table):** Hiển thị danh sách các cổ phiếu đang `BUY_OK`, mức giá khuyến nghị gốc, thị giá hiện tại và khuyến nghị hành động.
5. Chia sẻ link báo cáo hoặc lưu lại bookmark trên điện thoại để kiểm tra mọi lúc mọi nơi với **0 MB dung lượng máy tính**.

---

## 3. Huấn Luyện Machine Learning Trên Google Colab

Dữ liệu từ Google Sheets hoặc từ file `data/ml_signals_dataset.csv` đã được định dạng chuẩn ma trận $X$ và $y$. Bạn có thể mở một notebook trên [Google Colab](https://colab.research.google.com) và chạy thử nghiệm:

```python
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score

# 1. Đọc dữ liệu từ file CSV tự động của GitHub repo hoặc Google Sheets
url = "https://raw.githubusercontent.com/<YOUR_USER>/Neiro-Stock-VN/main/data/ml_signals_dataset.csv"
df = pd.read_csv(url)

# 2. Lọc các vị thế đã có kết quả (loại bỏ vị thế mới mở ACTIVE)
closed_df = df[(df["is_ml_ready"] == True) & (df["schema_version"] == "v2")].copy()

# 3. Chọn tập thuộc tính Feature Vector tại T0 (X)
feature_cols = [
    "composite_rating", "rs_1m", "rrg_r", "rrg_m",
    "foreign_net_value_billion", "ranking_score",
    "adtv20_billion", "liquidity_score",
    "atr_pct_t0", "atr_dist_from_poc_t0", "slippage_est_pct_t0",
    "market_breadth_pct_t0", "vn30_basis_t0", "pe_t0", "pb_t0"
]
X = closed_df[feature_cols]

# 4. Nhãn mục tiêu (y): 1 = Đột phá thành công (Lãi >= 5%), 0 = Vi phạm cắt lỗ
y = closed_df["target_win_binary"]

# 5. Phân chia Train/Test & Huấn luyện mô hình Random Forest
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)
clf = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
clf.fit(X_train, y_train)

# 6. Đánh giá hiệu suất dự báo
y_pred = clf.predict(X_test)
print(classification_report(y_test, y_pred))

# 7. Xem độ quan trọng của các yếu tố (Feature Importance)
importance_df = pd.DataFrame({
    "Feature": feature_cols,
    "Importance": clf.feature_importances_
}).sort_values(by="Importance", ascending=False)
print(importance_df)
```
