# ADR-019: Cổng Mua Mới Chặt Chẽ (6 Gate) & Sổ Cái Tín Hiệu ML v2

- **Trạng thái:** ACCEPTED & IMPLEMENTED
- **Liên quan:** ADR-009, ADR-011, ADR-017

## Bối cảnh

Rà soát pipeline "MUA MỚI vs CẤM MUA MỚI" phát hiện 6 lỗ hổng thuật toán và 5 khiếm khuyết khiến `data/ml_signals_dataset.csv` chưa sẵn sàng huấn luyện ML.

## Quyết định

### A. Sáu cổng Mua Mới

| # | Lỗ hổng | Cách xử lý |
|---|---|---|
| 1 | Chỉ chặn cận trên POC (+2.5 ATR), không chặn gãy nền; vùng mua Fialda cũ có thể cao hơn TP1 | Loại mã có `atr_dist_from_poc < -2.0` hoặc giá `< VAL - 1.2 ATR`. Ép bất biến `SL < Entry_Low <= Entry_High < TP1 < TP2` |
| 2 | Sau T0 giá rơi dưới vùng gom vẫn báo "VÙNG MUA CHUẨN" | `pnl < -2.5%` → `EXTENDED_NO_CHASING` (CẤM BẮT DAO RƠI); `-2.5%..-1.5%` → `BUY_CAUTION`. JS client thêm nhãn `SUY YẾU` |
| 3 | Cầu chì vĩ mô không đồng bộ xuống Sổ cái / Scorecard | `update_signals(macro_pause_buying=...)`; mã mới xuất hiện lúc cầu chì bật hoặc Watchlist không được ghi T0 |
| 4 | Ngưỡng `HIGH` lệch (`breadth < 50`) và không hạ quyền mua | `HIGH` = `basis <= -6` hoặc `breadth < 45`; `HIGH` hạ `BUY_OK` → `BUY_CAUTION`; `MODERATE` gồm `breadth < 55` |
| 5 | `holding_days`/cooldown tính ngày lịch (T7, CN) | `count_vn_trading_days()` (loại T7, CN, lễ cố định 1/1, 30/4, 1/5, 2/9); `trading_days` điều khiển STALE, cooldown 3 phiên, nhãn PnL |
| 6 | API độ rộng lỗi (0,0) → Fail-Open 80% NAV; không có cổng cơ bản | `DATA_UNAVAILABLE_CAUTION` (trần 40% NAV). Loại `EPS TTM < 0`; Ngân hàng CAMEL < 50 chỉ qua nếu chân sóng + Acc/Diss A/B + IBD >= 75 |

### B. Sổ cái ML v2

1. `update_signals(live_prices=...)`: mã rớt khỏi Top 20 vẫn được cập nhật giá live (MFE/MAE, PnL, STOP_LOSS/WIN) → hết survivorship bias và nhãn đóng băng 0.0.
2. `signal_id` + `schema_version` (`v2`, bản cũ nạp là `v1_legacy`); trạng thái đóng (`STOPPED_OUT`, `TP2_REACHED`, `TIME_OUT` sau 20 phiên) bị khóa (`is_closed`, `closed_at`).
3. Sau khi hết cooldown 3 phiên, vòng sóng cũ được lưu vào `data/signal_history_ml.jsonl` (tối đa 2,000 mẫu) và mã được mở T0 mới; `export_ml_dataset()` hợp nhất archive + active theo `signal_id`.
4. Vector đặc trưng T0 mở rộng: `atr_pct_t0`, `atr_dist_from_poc_t0`, `poc_price_t0`, `val_price_t0`, `slippage_est_pct_t0`, `has_actual_prop_flow_t0`, `market_breadth_pct_t0`, `vn30_basis_t0`, `pe_t0`, `pb_t0`, `eps_ttm_t0`, `camel_score_t0`.
5. Nhãn: `pnl_t25/t5/t10_pct` chốt 1 lần theo phiên giao dịch thực; `target_win_binary` chốt cứng khi MFE >= +5% trước SL; `is_ml_ready = is_closed or trading_days >= 5`.

## Hệ quả

- Khi huấn luyện, lọc `is_ml_ready == True` và cân nhắc loại `schema_version == "v1_legacy"` (thiếu đặc trưng T0 mới).
- `MAX_HOLDING_DAYS` đổi từ 30 ngày lịch sang 20 phiên giao dịch.
- Workflow GitHub Actions commit thêm `data/signal_history_ml.jsonl`.
- Lễ âm lịch (Tết, Giỗ Tổ) chưa được mô hình hóa; chỉ T7, CN và lễ dương lịch cố định.
