"""Unit tests cho ADR-024: Kiểm Toán Chân Thực Vòng Đời Tín Hiệu (True Holding-Period Low Stop Loss & Time-Stop Capital Rotation)."""

import pytest
from datetime import datetime
from src.collector.fialda_scanner import FialdaCandidate
from src.risk_engine.signal_tracker import ActiveSignal, SignalTracker


def test_true_low_stop_loss_triggers_stopped_out_even_when_current_price_is_high():
    """Trường hợp VCI: Dù thị giá hiện tại đã hồi phục lên 20.20 (+5.5% TP1),
    nhưng đáy chu kỳ nắm giữ đã từng rơi về 18.05 (thủng SL 18.58) -> BẮT BUỘC STOPPED_OUT,
    chống triệt để lỗi Survivorship Bias / nhận vơ lợi nhuận ảo."""
    st = SignalTracker()

    # VCI: Mua 19.15, SL 18.58, TP1 20.00. Thị giá hiện tại 20.20.
    # Nhưng đáy trong chu kỳ nắm giữ là 18.05 <= 18.58
    status, buy_perm, advice, new_sl = st.evaluate_status_and_advice(
        entry_orig=19.15,
        cur_price=20.20,
        cur_stop=18.58,
        tp1=20.00,
        tp2=20.57,
        holding_days=9,
        trading_days=7,
        low_price=18.05,
        min_price_reached=18.05,
    )

    assert status == "STOPPED_OUT", f"VCI phải bị STOPPED_OUT vì đáy nến 18.05 <= 18.58, thực tế ra: {status}"
    assert "VI PHẠM CẮT LỖ" in advice
    assert buy_perm == "EXTENDED_NO_CHASING"


def test_time_stop_closes_stale_position_after_7_sessions(tmp_path):
    """Sau 7 phiên giao dịch thực tế mà cổ phiếu không bứt phá được TP1 (lãi < 3.0%),
    hệ thống cố vấn bắt buộc kích hoạt TIME_OUT để tất toán vị thế cơ cấu vốn, không để ngâm vốn vô hạn."""
    st = SignalTracker(signals_file=tmp_path / "active_signals.jsonl")

    # Giả lập mã BVS mua ngày 2026-10-26 (7 phiên trước), giá dậm chân tại chỗ PnL -0.5%
    status, buy_perm, advice, new_sl = st.evaluate_status_and_advice(
        entry_orig=27.30,
        cur_price=27.15,
        cur_stop=26.00,
        tp1=28.50,
        tp2=29.50,
        holding_days=9,
        trading_days=7,
        low_price=26.50,
        min_price_reached=26.50,
    )

    assert status == "TIME_OUT", f"Mã quá hạn 7 phiên không bứt phá phải chuyển TIME_OUT, thực tế: {status}"
    assert "TẤT TOÁN VỊ THẾ QUÁ HẠN" in advice
    assert buy_perm == "STALE_SIGNAL"


def test_t0_new_buy_does_not_use_pre_t0_low():
    """Vị thế mở mới hôm nay (T0, như VCK): Đáy xem xét chỉ là đáy của ngày hôm nay (lowPrice >= 27.05),
    tuyệt đối không bị ảnh hưởng bởi đáy của các ngày trước khi mua (ví dụ đáy 26.15 của 3 ngày trước)."""
    st = SignalTracker()

    status, buy_perm, advice, new_sl = st.evaluate_status_and_advice(
        entry_orig=28.10,
        cur_price=28.60,
        cur_stop=26.84,
        tp1=30.10,
        tp2=31.36,
        holding_days=0,
        trading_days=0,
        low_price=27.05,  # Đáy hôm nay an toàn trên Stop Loss 26.84
        min_price_reached=27.05,
    )

    assert status == "ACTIVE", f"VCK hôm nay an toàn trên Stop Loss phải là ACTIVE, thực tế: {status}"
    assert buy_perm in ("BUY_OK", "EXTENDED_NO_CHASING")


def test_signal_tracker_latches_stopped_out_permanently(tmp_path):
    """Khi một vị thế vi phạm cắt lỗ đáy nến, SignalTracker đóng vị thế vĩnh viễn (Terminal Latch)."""
    f_path = tmp_path / "test_active.jsonl"
    st = SignalTracker(signals_file=f_path)

    sig = ActiveSignal(
        symbol="VCI",
        first_signal_date="2026-10-26 14:45:13",
        last_updated="2026-10-29 14:30:00",
        entry_original=19.15,
        current_price=18.90,
        pnl_pct=-1.3,
        holding_days=3,
        trading_days=3,
        initial_stop_loss=18.58,
        current_stop_loss=18.58,
        tp1=20.00,
        tp2=20.57,
        status="ACTIVE",
        buy_permission="BUY_OK",
        advice_note="Đang theo dõi",
        is_closed=False,
    )
    st.save_active_signals({"VCI": sig})

    now_dt = datetime(2026, 11, 4, 14, 0, 0)
    # Cập nhật với giá hiện tại là 20.20 nhưng low là 18.05
    st.update_signals(
        current_candidates=[],
        current_time=now_dt,
        live_prices={"VCI": 20.20},
        live_lows={"VCI": 18.05},
    )

    loaded = st.load_active_signals()
    vci = loaded["VCI"]
    assert vci.status == "STOPPED_OUT", f"VCI phải là STOPPED_OUT, thực tế: {vci.status}"
    assert vci.is_closed is True
    assert vci.outcome_label == "STOP_LOSS"
