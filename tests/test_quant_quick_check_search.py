"""Unit tests cho tính năng Quant Quick-Check Search: Tra cứu định lượng & đánh giá cổ phiếu tức thì (Tier 23 / ADR-021)."""

import json
from pathlib import Path
import pytest
from src.collector.fialda_scanner import FialdaCandidate
from src.hud.quant_search import (
    build_quant_search_snapshot,
    generate_quant_search_cockpit_html,
    load_historical_track_records,
)
from src.hud.terminal import generate_terminal_html
from src.risk_engine.signal_tracker import ActiveSignal


def test_load_historical_track_records_from_data():
    """Kiểm tra trích xuất track record quá khứ từ active_signals.jsonl và ml_signals_dataset.csv."""
    track_records = load_historical_track_records()
    assert isinstance(track_records, dict)
    assert len(track_records) > 0

    # Kiểm tra mã TCH có trong sổ cái
    if "TCH" in track_records:
        rec_tch = track_records["TCH"]
        assert rec_tch["total_signals"] >= 1
        assert rec_tch["wins"] >= 1
        assert rec_tch["win_rate_pct"] == 100.0
        assert rec_tch["avg_pnl_pct"] > 0
        assert rec_tch["last_status"] in ("TP1_REACHED", "TP2_REACHED", "STOPPED_OUT")

    # Kiểm tra mã VGC (đã dừng lỗ)
    if "VGC" in track_records:
        rec_vgc = track_records["VGC"]
        assert rec_vgc["total_signals"] >= 1
        assert rec_vgc["losses"] >= 1
        assert rec_vgc["avg_pnl_pct"] < 0
        assert rec_vgc["last_status"] == "STOPPED_OUT"


def test_build_quant_search_snapshot_metrics():
    """Kiểm tra cấu trúc và tính toán chỉ số Quantamental trong snapshot."""
    c_tch = FialdaCandidate(
        symbol="TCH",
        price=12.55,
        signal_type="CHO_MUA_CHAN_SONG",
        entry_low=11.80,
        entry_high=12.10,
        stop_loss=11.40,
        target_1m=14.50,
        rs_1m=88,
        composite_rating=85,
        acc_diss_rating="A",
        rrg_r=102.5,
        rrg_m=101.8,
        foreign_net_value_billion=12.5,
        ranking_score=92.0,
        catalyst="Bất động sản",
        adtv20_billion=115.0,
        liquidity_score=95.0,
        tp1=12.44,
        tp2=12.80,
        prev_rank=1,
        rank_change_delta=0,
        flow_regime="SIEU_SONG",
        flow_badge="🟢🟢 ĐỒNG THUẬN GOM",
    )

    mock_act = {
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
            advice_note="Chốt 50% tại TP1, nâng trailing stop lên 11.90",
            is_closed=False,
        )
    }

    snapshot = build_quant_search_snapshot(
        fialda_candidates=[c_tch],
        active_signals=mock_act,
        circuit_breaker_active=False,
    )

    assert "TCH" in snapshot
    tch_item = snapshot["TCH"]

    # 1. Kiểm tra bộ chỉ số Quantamental cốt lõi (Requirement 1b)
    assert tch_item["rs_1m"] == 88
    assert tch_item["ibd_score"] == 85
    assert tch_item["flow_grade"] == "A"
    assert tch_item["f_score"] >= 7
    assert "Leading" in tch_item["rrg_quadrant"]
    assert "ĐỒNG THUẬN GOM" in tch_item["dual_flow_badge"]

    # 2. Kiểm tra Cổng mua Tier 21 (Requirement 1a)
    # TCH đã tăng xa nền (EXTENDED_NO_CHASING)
    assert tch_item["buy_gate"] == "EXTENDED_NO_CHASING"
    assert "CẤM MUA ĐUỔI" in tch_item["buy_gate_label"]

    # 3. Kiểm tra Track Record quá khứ (Requirement 1c)
    assert "track_record" in tch_item
    assert tch_item["track_record"]["total_signals"] >= 1
    assert tch_item["track_record"]["win_rate_pct"] == 100.0


def test_circuit_breaker_overrides_all_buy_gates():
    """Kiểm tra khi Cầu chì vĩ mô kích hoạt, toàn bộ cổng mua đều chuyển sang MACRO_CIRCUIT_BREAKER."""
    c_hpg = FialdaCandidate(
        symbol="HPG",
        price=22.00,
        signal_type="CHO_MUA_CHAN_SONG",
        entry_low=21.70,
        entry_high=22.30,
        stop_loss=20.80,
        target_1m=27.00,
        rs_1m=86,
        composite_rating=88,
        acc_diss_rating="A",
        rrg_r=103.0,
        rrg_m=102.0,
        foreign_net_value_billion=25.4,
        ranking_score=91.2,
        catalyst="Thép",
        adtv20_billion=380.0,
        liquidity_score=96.0,
        tp1=23.95,
        tp2=25.15,
        prev_rank=1,
        rank_change_delta=0,
        flow_regime="SIEU_SONG",
        flow_badge="🟢🟢 ĐỒNG THUẬN GOM",
    )

    snapshot = build_quant_search_snapshot(
        fialda_candidates=[c_hpg],
        active_signals={},
        circuit_breaker_active=True,
    )

    assert "HPG" in snapshot
    assert snapshot["HPG"]["buy_gate"] == "MACRO_CIRCUIT_BREAKER"
    assert "CẦU CHÌ VĨ MÔ" in snapshot["HPG"]["buy_gate_label"]
    assert "rủi ro hệ thống" in snapshot["HPG"]["advice"]


def test_anti_junk_and_low_liquidity_flagging():
    """Kiểm tra cổ phiếu thanh khoản yếu (< 15 tỷ) hoặc F-Score thấp bị gán nhãn rác."""
    c_penny = FialdaCandidate(
        symbol="PEN",
        price=3.50,
        signal_type="CHO_MUA_CHAN_SONG",
        entry_low=3.40,
        entry_high=3.60,
        stop_loss=3.10,
        target_1m=4.50,
        rs_1m=45,
        composite_rating=50,
        acc_diss_rating="C",
        rrg_r=98.0,
        rrg_m=97.0,
        foreign_net_value_billion=0.1,
        ranking_score=55.0,
        catalyst="Penny",
        adtv20_billion=5.2,  # < 15 tỷ (thanh khoản siêu yếu)
        liquidity_score=30.0,
        tp1=3.80,
        tp2=4.10,
        prev_rank=50,
        rank_change_delta=0,
        flow_regime="NOI_CAN_HANG",
        flow_badge="⚪ TRUNG TÍNH",
    )

    snapshot = build_quant_search_snapshot(
        fialda_candidates=[c_penny],
        active_signals={},
        circuit_breaker_active=False,
    )

    assert "PEN" in snapshot
    assert snapshot["PEN"]["is_junk"] is True
    assert "Thanh khoản thấp" in snapshot["PEN"]["junk_warning"]
    assert snapshot["PEN"]["adtv20_billion"] == 5.2


def test_terminal_html_contains_quant_search_cockpit(tmp_path):
    """Kiểm tra Terminal HTML chứa đầy đủ giao diện tìm kiếm tức thì, snapshot JSON và mã Client JS."""
    out_path = tmp_path / "test_search_terminal.html"
    generate_terminal_html(
        output_path=str(out_path),
        fialda_candidates=[],
        top_n=0,
        active_signals={},
    )
    html = out_path.read_text(encoding="utf-8")

    # 1. Khối tìm kiếm định lượng hiện diện
    assert 'id="quant-search-section"' in html
    assert 'id="quant-search-input"' in html
    assert 'id="quant-search-result"' in html
    assert 'id="quant-db-count"' in html

    # 2. Dữ liệu Snapshot JSON và hàm Client JS hiện diện
    assert "const QUANT_SEARCH_DATA =" in html
    assert "handleQuantSearchInput" in html
    assert "selectQuickTicker" in html
    assert "renderQuantDiagnostic" in html
    assert "clearQuantSearch" in html

    # 3. Gợi ý 1-click pills cho các mã tiêu biểu
    for ticker in ["TCH", "SSI", "HPG", "FPT", "DBC", "BAF", "HDC", "VGC"]:
        assert f"selectQuickTicker('{ticker}')" in html

    # 4. Kiểm tra cảnh báo mã ngoài danh mục / hàng rác trong Client JS
    assert "NGOÀI DANH MỤC ĐỊNH LƯỢNG — KHÔNG KHUYẾN NGHỊ MUA" in html
    assert "Nguyên tắc bảo vệ vốn:" in html

