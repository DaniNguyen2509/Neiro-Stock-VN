"""Unit tests cho Tab 2: Sổ Cái Vị Thế Khuyến Nghị & Theo Dõi Lãi/Lỗ PnL (T+ Tracker)."""

import pytest
from pathlib import Path
from src.collector.fialda_scanner import FialdaCandidate
from src.hud.terminal import generate_terminal_html
from src.risk_engine.signal_tracker import ActiveSignal


def test_active_positions_tracker_table_rendering(tmp_path):
    """Kiểm tra Tab 2 hiển thị danh sách vị thế đang nắm giữ, phân loại TP1/TP2 và ẩn mã hoàn tất."""
    out_html_path = tmp_path / "test_terminal.html"

    # Giả lập 3 vị thế với các trạng thái khác nhau:
    # 1. TCH: Đã đạt TP1, đang gồng lãi tới TP2 (phải xuất hiện trên bảng chính)
    # 2. BAF: Đang nắm giữ ACTIVE (phải xuất hiện trên bảng chính)
    # 3. HDC: Đã đạt TP2 toàn vòng (hoàn tất vòng đời -> biến mất khỏi bảng chính, nằm trong ngăn lịch sử)
    mock_signals = {
        "TCH": ActiveSignal(
            symbol="TCH",
            first_signal_date="2026-10-26 14:44:14",
            last_updated="2026-11-04 10:30:00",
            entry_original=11.90,
            current_price=12.55,
            pnl_pct=5.46,
            holding_days=9,
            trading_days=7,
            initial_stop_loss=11.50,
            current_stop_loss=11.90,
            tp1=12.44,
            tp2=12.80,
            status="TP1_REACHED",
            buy_permission="EXTENDED_NO_CHASING",
            advice_note="Chốt 50% tại TP1, nâng trailing stop lên giá vào 11.90",
            is_closed=False,
        ),
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
            advice_note="Đang theo dõi",
            is_closed=False,
        ),
        "HDC": ActiveSignal(
            symbol="HDC",
            first_signal_date="2026-10-28 10:00:00",
            last_updated="2026-10-31 14:30:00",
            entry_original=11.20,
            current_price=12.60,
            pnl_pct=12.50,
            holding_days=3,
            trading_days=3,
            initial_stop_loss=10.85,
            current_stop_loss=12.60,
            tp1=11.70,
            tp2=12.60,
            status="TP2_REACHED",
            buy_permission="EXTENDED_NO_CHASING",
            advice_note="Đạt mục tiêu TP2 toàn vòng",
            is_closed=True,
        ),
    }

    c_dummy = FialdaCandidate(
        symbol="HPG", price=22.00, signal_type="CHO_MUA_CHAN_SONG",
        entry_low=21.70, entry_high=22.30, stop_loss=20.80, target_1m=27.00,
        rs_1m=86, composite_rating=88, acc_diss_rating="A",
        rrg_r=103.0, rrg_m=102.0, foreign_net_value_billion=25.4, ranking_score=91.2,
        catalyst="Thép", adtv20_billion=380.0, liquidity_score=96.0,
        tp1=23.95, tp2=25.15, prev_rank=1, rank_change_delta=0,
        flow_regime="SIEU_SONG", flow_badge="🟢🟢 ĐỒNG THUẬN GOM",
    )

    generate_terminal_html(
        output_path=str(out_html_path),
        fialda_candidates=[c_dummy],
        top_n=1,
        active_signals=mock_signals,
    )

    html = out_html_path.read_text(encoding="utf-8")

    # 1. Bảng active-positions-table và nút Tab 2 hiện diện
    assert 'id="active-positions-table"' in html
    assert 'id="btn-tab-positions"' in html
    assert 'id="hud-tab-positions"' in html

    # 2. Vị thế TCH (đang chạy, đạt TP1) phải hiện trên bảng chính
    assert "TCH" in html
    assert 'data-sym="TCH"' in html
    assert "🎯 ĐÃ CHỐT 50% TP1 — GỒNG LÃI TỚI TP2 (CẤM MUA ĐUỔI)" in html
    assert "T+7 (Khả dụng 100%)" in html
    assert 'class="live-pnl" data-sym="TCH" data-entry="11.90"' in html

    # 3. Vị thế BAF (đang chạy, active) phải hiện trên bảng chính
    assert "BAF" in html
    assert 'data-sym="BAF"' in html
    assert "T+6 (Khả dụng 100%)" in html

    # 4. HDC đã đạt TP2 (+12.50%) hoàn tất vòng đời:
    # Phải nằm trong ngăn lịch sử chốt lời đóng vòng đời
    assert "🏆 ĐẠT TP2" in html
    assert "Đạt mục tiêu TP2 (12.60) • Hoàn tất chốt lời 100%" in html
    assert "Đã chốt lời toàn bộ TP2 &amp; rời bảng: <b style=\"color:#ffb300;\">1 mã</b>" in html


def test_empty_active_positions_graceful_display(tmp_path):
    """Kiểm tra giao diện khi không có vị thế nào đang mở."""
    out_html_path = tmp_path / "test_empty.html"
    generate_terminal_html(
        output_path=str(out_html_path),
        fialda_candidates=[],
        top_n=0,
        active_signals={},
    )
    html = out_html_path.read_text(encoding="utf-8")
    assert "Hiện không có vị thế nào đang nắm giữ" in html
