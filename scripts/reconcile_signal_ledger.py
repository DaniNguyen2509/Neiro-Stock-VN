"""Script đối soát và làm sạch dữ liệu Sổ Cái Tín Hiệu theo chuẩn ADR-024.

- Quét toàn bộ đáy nến thực tế (PriceInfo.lowPrice, RealtimeStatistic.adjLow5DCandle)
- Kích hoạt STOPPED_OUT vĩnh viễn cho các mã đã đâm thủng Stop Loss (đặc biệt là VCI đáy 18.05 <= 18.58)
- Kích hoạt TIME_OUT cho các mã quá hạn T+7 phiên không đạt TP1 để giải phóng danh mục
- Tinh gọn bảng Active Running về các mã thực sự đang chạy và an toàn
"""

import json
from datetime import datetime
from src.collector.fialda_scanner import FialdaScanner
from src.risk_engine.signal_tracker import ActiveSignal, SignalTracker, count_vn_trading_days


def reconcile_ledger() -> None:
    scanner = FialdaScanner()
    scanner.login()
    tracker = SignalTracker()
    now_vn = tracker.current_vn_time()
    now_str = tracker.format_time(now_vn)

    signals_dict = tracker.load_active_signals()
    if not signals_dict:
        print("Không có tín hiệu nào trong sổ cái.")
        return

    syms = list(signals_dict.keys())
    print(f"Bắt đầu đối soát {len(syms)} mã tín hiệu trong sổ cái...")
    stock_infos = scanner.get_stock_infos(syms)

    stopped_count = 0
    timeout_count = 0
    active_count = 0

    for sym, sig in signals_dict.items():
        entry = float(sig.entry_original or 0.0)
        sl = float(sig.current_stop_loss or sig.initial_stop_loss or 0.0)
        tp1 = float(sig.tp1 or 0.0)
        tp2 = float(sig.tp2 or 0.0)

        first_dt = tracker.parse_time(sig.first_signal_date) or now_vn
        t_days = count_vn_trading_days(first_dt.date(), now_vn.date())
        h_days = max(0, (now_vn.date() - first_dt.date()).days)

        info = stock_infos.get(sym, {})
        pi = info.get("PriceInfo", {}) if isinstance(info, dict) else {}
        rs = info.get("RealtimeStatistic", {}) if isinstance(info, dict) else {}

        cur_p = float(pi.get("currentPrice") or pi.get("lastPrice") or sig.current_price or 0.0)
        low_p = float(pi.get("lowPrice") or cur_p)
        low_5d = float(rs.get("adjLow5DCandle") or low_p)

        # Phân biệt T0 (chỉ xét nến hôm nay) vs T>=1 (xét toàn bộ nến chu kỳ)
        if t_days == 0:
            eff_low = low_p
        else:
            eff_low = min(v for v in [low_p, low_5d] if v > 0) if (low_p > 0 or low_5d > 0) else cur_p

        pnl = round(((cur_p - entry) / entry) * 100.0, 2) if entry > 0 else 0.0
        cur_min = min(sig.min_price_reached or entry, eff_low)
        cur_max = max(sig.max_price_reached or entry, cur_p)
        mfe = max(sig.mfe_pct, round(((cur_max - entry) / entry) * 100.0, 2)) if entry > 0 else 0.0
        mae = min(sig.mae_pct, round(((cur_min - entry) / entry) * 100.0, 2)) if entry > 0 else 0.0

        sig.holding_days = h_days
        sig.trading_days = t_days
        sig.current_price = cur_p
        sig.min_price_reached = cur_min
        sig.max_price_reached = cur_max
        sig.mfe_pct = mfe
        sig.mae_pct = mae
        sig.pnl_pct = pnl
        sig.last_updated = now_str

        # Nếu đã đóng trước đó và không phải case VCI bị nhầm thành TP1:
        if sig.is_closed and sig.status in ("STOPPED_OUT", "TP2_REACHED"):
            continue

        # Kiểm tra điều kiện Stop Loss chân thực (đặc biệt xử lý case VCI)
        if eff_low <= sl or cur_min <= sl:
            sig.status = "STOPPED_OUT"
            sig.buy_permission = "EXTENDED_NO_CHASING"
            sig.outcome_label = "STOP_LOSS"
            sig.is_closed = True
            sig.closed_at = sig.closed_at or now_str
            sig.advice_note = (
                f"❌ VI PHẠM CẮT LỖ (Đáy chu kỳ {eff_low:.2f} <= Stop {sl:.2f}). "
                "Bán dứt khoát thoát vị thế, bảo toàn vốn tối đa."
            )
            stopped_count += 1
            print(f"🛑 [STOPPED_OUT] {sym}: Đáy chu kỳ {eff_low:.2f} <= Stop {sl:.2f} (Entry {entry:.2f}, Cur {cur_p:.2f})")
        elif tp2 > 0 and cur_p >= tp2:
            sig.status = "TP2_REACHED"
            sig.buy_permission = "EXTENDED_NO_CHASING"
            sig.outcome_label = "WIN_TP2"
            sig.is_closed = True
            sig.closed_at = sig.closed_at or now_str
            sig.advice_note = f"🎯 ĐẠT MỤC TIÊU LỚN TP2 ({tp2:.2f}, Lãi {pnl:+.1f}%). Hoàn tất chốt lời 100%."
            print(f"🏆 [TP2_REACHED] {sym}: Đạt mục tiêu TP2 ({cur_p:.2f} >= {tp2:.2f}, Lãi {pnl:+.1f}%)")
        elif t_days >= 7 and pnl < 3.0:
            sig.status = "TIME_OUT"
            sig.buy_permission = "STALE_SIGNAL"
            sig.outcome_label = "WIN_TP1" if mfe >= 5.0 else "TIME_OUT"
            sig.is_closed = True
            sig.closed_at = sig.closed_at or now_str
            sig.advice_note = (
                f"⏱️ TẤT TOÁN VỊ THẾ QUÁ HẠN T+{t_days} (Biến động {pnl:+.1f}% sau {t_days} phiên): "
                "Động lượng dòng tiền suy kiệt, tất toán cơ cấu danh mục thu hồi vốn."
            )
            timeout_count += 1
            print(f"⏱️ [TIME_OUT] {sym}: Quá hạn T+{t_days} không bứt phá (PnL {pnl:+.1f}%) -> Tất toán cơ cấu vốn")
        elif tp1 > 0 and cur_p >= tp1:
            sig.status = "TP1_REACHED"
            sig.buy_permission = "EXTENDED_NO_CHASING"
            sig.outcome_label = "WIN_TP1"
            sig.target_win_binary = 1
            sig.current_stop_loss = max(sig.current_stop_loss, entry)
            sig.advice_note = f"🚀 ĐẠT MỤC TIÊU 1 TP1 ({tp1:.2f}, Lãi {pnl:+.1f}%). Chốt 50%, dời SL hòa vốn {entry:.2f}."
            active_count += 1
            print(f"🎯 [TP1_REACHED] {sym}: Đạt TP1 ({cur_p:.2f} >= {tp1:.2f}, Lãi {pnl:+.1f}%) -> Tiếp tục gồng")
        else:
            sig.status = "ACTIVE"
            active_count += 1
            print(f"🟢 [ACTIVE] {sym}: Đang nắm giữ T+{t_days} (Entry {entry:.2f}, Cur {cur_p:.2f}, PnL {pnl:+.1f}%)")

        sig.is_ml_ready = bool(sig.is_closed or t_days >= 5)

    tracker.save_active_signals(signals_dict)
    tracker.generate_scorecard_markdown(signals_dict, now_str)
    tracker.export_ml_dataset(signals_dict)

    print("\n=== HOÀN TẤT ĐỐI SOÁT SỔ CÁI ===")
    print(f"- Tổng số mã: {len(signals_dict)}")
    print(f"- Số mã vi phạm cắt lỗ (Stop Loss): {stopped_count}")
    print(f"- Số mã quá hạn cơ cấu vốn (Time-Out): {timeout_count}")
    print(f"- Số mã đang nắm giữ thực tế (Active Focus Portfolio): {active_count}")


if __name__ == "__main__":
    reconcile_ledger()

