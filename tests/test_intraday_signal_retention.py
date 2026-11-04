"""Unit tests cho ADR-023: Cơ Chế Duy Trì Vị Thế Khuyến Nghị Trong Ngày (Same-Day Intraday Signal Retention Policy)."""

import pytest
from datetime import datetime
from pathlib import Path
from src.collector.fialda_scanner import FialdaCandidate, FialdaScanner, retain_same_day_active_signals
from src.hud.terminal import generate_terminal_html
from src.risk_engine.signal_tracker import ActiveSignal, SignalTracker


def test_same_day_active_signal_retained_in_tab1():
    """Mã khuyến nghị hôm nay (T0) còn hiệu lực phải được giữ lại trên Tab 1 dù xếp hạng ngoài Top 20."""
    now_dt = datetime(2026, 11, 4, 14, 0, 0)
    today_str = "2026-11-04"

    # Giả lập 20 ứng viên khác chiếm trọn Top 20
    top_20 = [
        FialdaCandidate(
            symbol=f"SYM{i:02d}", price=30.0, signal_type="CHO_MUA_CHAN_SONG",
            entry_low=29.5, entry_high=30.5, stop_loss=28.5, target_1m=36.0,
            rs_1m=80, composite_rating=80, acc_diss_rating="A",
            rrg_r=101.0, rrg_m=101.0, foreign_net_value_billion=10.0, ranking_score=80.0 - i,
            catalyst="Test", adtv20_billion=50.0, liquidity_score=85.0,
        )
        for i in range(20)
    ]

    # VCK được khuyến nghị sáng nay lúc 10:12:03, điểm ranking tạm thời thấp hơn Top 20
    mock_signals = {
        "VCK": ActiveSignal(
            symbol="VCK",
            first_signal_date=f"{today_str} 10:12:03",
            last_updated=f"{today_str} 13:50:00",
            entry_original=28.10,
            current_price=28.60,
            pnl_pct=1.78,
            holding_days=0,
            trading_days=0,
            initial_stop_loss=26.84,
            current_stop_loss=26.84,
            tp1=30.10,
            tp2=31.36,
            status="ACTIVE",
            buy_permission="EXTENDED_NO_CHASING",
            advice_note="Đã chạy > 1.5% so với điểm bùng nổ T0",
            is_closed=False,
            ranking_score=42.5,
        ),
    }

    result = retain_same_day_active_signals(
        candidates=top_20,
        active_signals=mock_signals,
        now_dt=now_dt,
    )

    result_syms = [c.symbol for c in result]
    assert "VCK" in result_syms, "VCK phải được giữ lại trên bảng Tab 1 trong ngày T0"
    vck_cand = next(c for c in result if c.symbol == "VCK")
    assert vck_cand.price == 28.60
    assert vck_cand.t0_entry_original == 28.10
    assert vck_cand.buy_permission == "EXTENDED_NO_CHASING"


def test_previous_day_signal_not_retained_in_tab1():
    """Mã đã khuyến nghị từ các ngày trước (T+1 trở đi) không được tự động ghim vào Tab 1 mà chuyển sang Tab 2."""
    now_dt = datetime(2026, 11, 4, 14, 0, 0)

    top_20 = [
        FialdaCandidate(
            symbol=f"SYM{i:02d}", price=30.0, signal_type="CHO_MUA_CHAN_SONG",
            entry_low=29.5, entry_high=30.5, stop_loss=28.5, target_1m=36.0,
            rs_1m=80, composite_rating=80, acc_diss_rating="A",
            rrg_r=101.0, rrg_m=101.0, foreign_net_value_billion=10.0, ranking_score=80.0 - i,
            catalyst="Test", adtv20_billion=50.0, liquidity_score=85.0,
        )
        for i in range(20)
    ]

    # BAF mua ngày 2026-10-27 (T+6)
    mock_signals = {
        "BAF": ActiveSignal(
            symbol="BAF",
            first_signal_date="2026-10-27 09:15:00",
            last_updated="2026-11-04 10:30:00",
            entry_original=29.70,
            current_price=30.85,
            pnl_pct=3.87,
            holding_days=8,
            trading_days=6,
            initial_stop_loss=28.81,
            current_stop_loss=28.81,
            tp1=31.04,
            tp2=31.93,
            status="ACTIVE",
            buy_permission="STALE_SIGNAL",
            advice_note="Đang theo dõi T+6",
            is_closed=False,
        ),
    }

    result = retain_same_day_active_signals(
        candidates=top_20,
        active_signals=mock_signals,
        now_dt=now_dt,
    )

    result_syms = [c.symbol for c in result]
    assert "BAF" not in result_syms, "BAF đã qua ngày (T+6) nên không được tự động giữ trên Tab 1"


def test_same_day_stopped_out_signal_not_retained():
    """Mã khuyến nghị hôm nay nhưng vi phạm cắt lỗ (hết hiệu lực) thì không được giữ trên Tab 1."""
    now_dt = datetime(2026, 11, 4, 14, 0, 0)
    today_str = "2026-11-04"

    top_20 = [
        FialdaCandidate(
            symbol=f"SYM{i:02d}", price=30.0, signal_type="CHO_MUA_CHAN_SONG",
            entry_low=29.5, entry_high=30.5, stop_loss=28.5, target_1m=36.0,
            rs_1m=80, composite_rating=80, acc_diss_rating="A",
            rrg_r=101.0, rrg_m=101.0, foreign_net_value_billion=10.0, ranking_score=80.0 - i,
            catalyst="Test", adtv20_billion=50.0, liquidity_score=85.0,
        )
        for i in range(20)
    ]

    mock_signals = {
        "FAIL": ActiveSignal(
            symbol="FAIL",
            first_signal_date=f"{today_str} 09:30:00",
            last_updated=f"{today_str} 11:00:00",
            entry_original=10.0,
            current_price=9.2,
            pnl_pct=-8.0,
            holding_days=0,
            trading_days=0,
            initial_stop_loss=9.5,
            current_stop_loss=9.5,
            tp1=10.8,
            tp2=11.5,
            status="STOPPED_OUT",
            buy_permission="EXTENDED_NO_CHASING",
            advice_note="Chạm cắt lỗ trong ngày",
            is_closed=True,
        ),
    }

    result = retain_same_day_active_signals(
        candidates=top_20,
        active_signals=mock_signals,
        now_dt=now_dt,
    )

    result_syms = [c.symbol for c in result]
    assert "FAIL" not in result_syms, "Mã STOPPED_OUT không còn hiệu lực nên không được giữ trên Tab 1"


def test_terminal_renders_retained_same_day_signal(tmp_path):
    """Kiểm tra giao diện Terminal Tab 1 hiển thị mã khuyến nghị cùng ngày."""
    out_html_path = tmp_path / "test_retained_tab1.html"
    today_str = datetime.now().strftime("%Y-%m-%d")

    mock_signals = {
        "VCK": ActiveSignal(
            symbol="VCK",
            first_signal_date=f"{today_str} 10:12:03",
            last_updated=f"{today_str} 13:50:00",
            entry_original=28.10,
            current_price=28.60,
            pnl_pct=1.78,
            holding_days=0,
            trading_days=0,
            initial_stop_loss=26.84,
            current_stop_loss=26.84,
            tp1=30.10,
            tp2=31.36,
            status="ACTIVE",
            buy_permission="EXTENDED_NO_CHASING",
            advice_note="Vùng mua chuẩn",
            is_closed=False,
        ),
    }

    c_dummy = FialdaCandidate(
        symbol="HPG", price=22.00, signal_type="CHO_MUA_CHAN_SONG",
        entry_low=21.70, entry_high=22.30, stop_loss=20.80, target_1m=27.00,
        rs_1m=86, composite_rating=88, acc_diss_rating="A",
        rrg_r=103.0, rrg_m=102.0, foreign_net_value_billion=25.4, ranking_score=91.2,
        catalyst="Thép", adtv20_billion=380.0, liquidity_score=96.0,
    )

    generate_terminal_html(
        output_path=str(out_html_path),
        fialda_candidates=[c_dummy],
        top_n=1,
        active_signals=mock_signals,
    )

    html = out_html_path.read_text(encoding="utf-8")
    tab1_start = html.index('id="top-stocks-table"')
    tab1_end = html.index('</table>', tab1_start)
    tab1_html = html[tab1_start:tab1_end]

    assert "VCK" in tab1_html, "VCK phải xuất hiện trên bảng Tab 1 (khuyến nghị trong ngày)"

