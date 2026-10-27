from datetime import datetime, timezone, timedelta
from pathlib import Path
from dataclasses import dataclass
from src.risk_engine.signal_tracker import SignalTracker, ActiveSignal


@dataclass
class MockCandidate:
    symbol: str
    price: float
    stop_loss: float
    tp1: float
    tp2: float


def test_signal_tracker_lifecycle_and_chasing_prevention(tmp_path: Path):
    """Kiem thu toan bo vong doi tin hieu, tinh ty le lai lo sau 4-5 ngay va khoa chieu mua duoi."""
    signals_file = tmp_path / "data" / "test_active_signals.jsonl"
    scorecard_file = tmp_path / "data" / "test_scorecard.md"
    tracker = SignalTracker(signals_file=signals_file, scorecard_file=scorecard_file)

    tz_vn = timezone(timedelta(hours=7))
    t0 = datetime(2026, 10, 20, 9, 30, 0, tzinfo=tz_vn)

    # 1. Ngay T0: Phat hien sieu co phieu CTS tai gia 20.0
    c_t0 = [
        MockCandidate(symbol="CTS", price=20.0, stop_loss=19.0, tp1=22.0, tp2=24.0)
    ]
    signals = tracker.update_signals(c_t0, current_time=t0)

    assert "CTS" in signals
    cts_t0 = signals["CTS"]
    assert cts_t0.entry_original == 20.0
    assert cts_t0.current_price == 20.0
    assert cts_t0.pnl_pct == 0.0
    assert cts_t0.holding_days == 0
    assert cts_t0.buy_permission == "BUY_OK"
    assert cts_t0.status == "ACTIVE"

    # 2. Ngay T+1 (21/10): Gia tang nhe len 20.8 (+4.0% -> Vung voi BUY_CAUTION)
    t1 = datetime(2026, 10, 21, 14, 0, 0, tzinfo=tz_vn)
    c_t1 = [
        MockCandidate(symbol="CTS", price=20.8, stop_loss=19.0, tp1=22.0, tp2=24.0)
    ]
    signals = tracker.update_signals(c_t1, current_time=t1)
    cts_t1 = signals["CTS"]
    assert cts_t1.entry_original == 20.0
    assert cts_t1.current_price == 20.8
    assert cts_t1.pnl_pct == 4.0
    assert cts_t1.holding_days == 1
    assert cts_t1.buy_permission == "BUY_CAUTION"

    # 3. Sau 4 ngay T+4 (24/10): Gia but pha manh len 22.2 (+11.0%)
    # - Da vuot qua nguong +5%
    # - Da vuot moc TP1 (22.0) -> Dat TP1, Stop Loss tu nang len gia hoa von (20.0)
    # - KHOA TUYET DOI CHIEU MUA: EXTENDED_NO_CHASING
    t4 = datetime(2026, 10, 24, 14, 30, 0, tzinfo=tz_vn)
    c_t4 = [
        MockCandidate(symbol="CTS", price=22.2, stop_loss=19.0, tp1=22.0, tp2=24.0)
    ]
    signals = tracker.update_signals(c_t4, current_time=t4)
    cts_t4 = signals["CTS"]

    assert cts_t4.entry_original == 20.0
    assert cts_t4.current_price == 22.2
    assert cts_t4.pnl_pct == 11.0
    assert cts_t4.holding_days == 4
    assert cts_t4.status == "TP1_REACHED"
    assert cts_t4.buy_permission == "EXTENDED_NO_CHASING"
    assert cts_t4.current_stop_loss == 20.0  # Da nang len diem hoa von

    # 4. Kiem tra ham tra cuu tu van get_advisory()
    advisory_text = tracker.get_advisory("CTS")
    assert "CẤM MUA ĐUỔI" in advisory_text
    assert "20.00" in advisory_text
    assert "+11.0%" in advisory_text
    assert "4 phiên" in advisory_text

    # Tra cuu ma khong ton tai
    unknown_text = tracker.get_advisory("XYZ")
    assert "chưa có trong Sổ Cái" in unknown_text

    # 5. Kiem tra bao cao Scorecard markdown
    assert scorecard_file.exists()
    scorecard_content = scorecard_file.read_text(encoding="utf-8")
    assert "CTS" in scorecard_content
    assert "+11.0%" in scorecard_content
    assert "CẤM MUA ĐUỔI" in scorecard_content


def test_signal_tracker_stop_loss_trigger(tmp_path: Path):
    """Kiem thu khi co phieu giam xuyen qua Stop Loss thi trang thai la STOPPED_OUT."""
    signals_file = tmp_path / "data" / "test_signals_sl.jsonl"
    scorecard_file = tmp_path / "data" / "test_scorecard_sl.md"
    tracker = SignalTracker(signals_file=signals_file, scorecard_file=scorecard_file)

    tz_vn = timezone(timedelta(hours=7))
    t0 = datetime(2026, 10, 20, 10, 0, 0, tzinfo=tz_vn)
    c_t0 = [MockCandidate(symbol="VIX", price=12.0, stop_loss=11.4, tp1=13.0, tp2=14.5)]
    tracker.update_signals(c_t0, current_time=t0)

    # Gia roi xuyen nguong 11.4 xuong 11.2
    t1 = datetime(2026, 10, 22, 10, 0, 0, tzinfo=tz_vn)
    c_t1 = [MockCandidate(symbol="VIX", price=11.2, stop_loss=11.4, tp1=13.0, tp2=14.5)]
    signals = tracker.update_signals(c_t1, current_time=t1)

    vix = signals["VIX"]
    assert vix.status == "STOPPED_OUT"
    assert vix.buy_permission == "EXTENDED_NO_CHASING"
    assert "VI PHẠM CẮT LỖ" in vix.advice_note


def test_signal_tracker_ml_features_and_dataset_export(tmp_path: Path):
    """Kiem thu tinh toan day du cac truong ML Features, Labels va xuat CSV."""
    signals_file = tmp_path / "data" / "test_signals_ml.jsonl"
    scorecard_file = tmp_path / "data" / "test_scorecard_ml.md"
    ml_csv_file = tmp_path / "data" / "test_ml_dataset.csv"

    tracker = SignalTracker(
        signals_file=signals_file,
        scorecard_file=scorecard_file,
        ml_dataset_file=ml_csv_file,
    )

    tz_vn = timezone(timedelta(hours=7))
    t0 = datetime(2026, 10, 20, 9, 30, 0, tzinfo=tz_vn)

    c0 = [
        MockCandidate(
            symbol="HPG",
            price=20.0,
            stop_loss=19.0,
            tp1=21.6,
            tp2=23.0,
        )
    ]
    # Bổ sung thuộc tính động
    c0[0].composite_rating = 92
    c0[0].rs_1m = 88
    c0[0].catalyst = "Khai trương lò cao mới"

    signals = tracker.update_signals(c0, current_time=t0)
    hpg_t0 = signals["HPG"]
    assert hpg_t0.composite_rating == 92
    assert hpg_t0.rs_1m == 88
    assert hpg_t0.catalyst == "Khai trương lò cao mới"
    assert hpg_t0.mfe_pct == 0.0
    assert hpg_t0.mae_pct == 0.0
    assert hpg_t0.target_win_binary == 0
    assert hpg_t0.outcome_label == "ACTIVE"

    # Sau 2 ngay (T+2): gia tang len 21.5 (+7.5% > 5%)
    t2 = datetime(2026, 10, 22, 14, 0, 0, tzinfo=tz_vn)
    c2 = [
        MockCandidate(
            symbol="HPG",
            price=21.5,
            stop_loss=19.0,
            tp1=21.6,
            tp2=23.0,
        )
    ]
    signals = tracker.update_signals(c2, current_time=t2)
    hpg_t2 = signals["HPG"]

    assert hpg_t2.max_price_reached == 21.5
    assert hpg_t2.mfe_pct == 7.5
    assert hpg_t2.pnl_t25_pct == 7.5
    assert hpg_t2.target_win_binary == 1

    # Kiem tra file CSV da duoc xuat ra dung
    assert ml_csv_file.exists()
    import pandas as pd
    df = pd.read_csv(ml_csv_file)
    assert len(df) == 1
    assert df.iloc[0]["symbol"] == "HPG"
    assert df.iloc[0]["target_win_binary"] == 1
    assert df.iloc[0]["composite_rating"] == 92
