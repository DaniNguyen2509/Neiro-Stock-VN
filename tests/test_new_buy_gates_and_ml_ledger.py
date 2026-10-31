"""Kiểm thử TDD toàn diện 6 Cổng Mua Mới Chặt Chẽ (New-Buy Gates) & Sổ Cái ML v2 (ADR-019)."""

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
import pandas as pd
import pytest

from src.collector.fialda_scanner import (
    FialdaCandidate,
    FialdaScanner,
    enrich_candidates_with_trailing_stop_and_history,
)
from src.hud.terminal import generate_terminal_html
from src.risk_engine.signal_tracker import SignalTracker, format_public_anti_fomo_badge
from src.risk_engine.trailing_stop import evaluate_t25_exposure
from src.sector_engine.market_breadth import analyze_market_breadth

VN_TZ = timezone(timedelta(hours=7))


class TestNewBuyAlgorithmicGates:
    """Kiểm thử triệt để 6 lỗ hổng thuật toán Mua Mới vs Cấm Mua Mới."""

    def test_loophole1_lower_bound_broken_base_rejected_and_price_zone_invariant_enforced(self):
        """Mã gãy nền sâu (< -2.0 ATR dưới POC như FPT -3.6 ATR, PVT -2.8 ATR) bị loại; bất biến SL < Entry_Low <= Entry_High < TP1 < TP2 luôn đúng."""
        scanner = FialdaScanner(username="u", password="p")
        scanner.token = "mock_tok"

        # FPT rơi sâu xuống 52.70 trong khi POC=57.80 (-3.6 ATR) và vùng cho_mua cũ bị treo ở 56.41-56.97
        # HPG tích lũy chuẩn quanh POC=22.00 (+0.3 ATR)
        mock_cho_mua = {
            "FPT": {"item1": True, "item2": 56.41, "item3": 56.97},
            "HPG": {"item1": True, "item2": 21.85, "item3": 22.30},
        }
        mock_rrg = {
            "FPT": {"r": 99.8, "m": 99.6},
            "HPG": {"r": 102.5, "m": 101.8},
        }
        mock_infos = {
            "FPT": {
                "PriceInfo": {"currentPrice": 52.70, "totalVal": 350e9},
                "ForeignTrade": {"totalForeignNetValue": -15.0e9},
                "BasicInfo": {"eps_TTM": 5200.0, "pe": 14.5, "pb": 3.8},
            },
            "HPG": {
                "PriceInfo": {"currentPrice": 22.15, "totalVal": 420e9},
                "ForeignTrade": {"totalForeignNetValue": 35.0e9},
                "BasicInfo": {"eps_TTM": 2100.0, "pe": 10.5, "pb": 1.3},
            },
        }
        mock_ohlcv = {
            "FPT": {
                "c": [57.8] * 18 + [55.0, 52.7],
                "h": [58.4] * 18 + [55.8, 53.5],
                "l": [57.2] * 18 + [54.2, 52.4],
                "v": [3_000_000] * 20,
            },
            "HPG": {
                "c": [21.9] * 18 + [22.0, 22.15],
                "h": [22.3] * 18 + [22.4, 22.45],
                "l": [21.5] * 18 + [21.7, 21.85],
                "v": [18_000_000] * 20,
            },
        }
        ratings = {
            "FPT": {"rS1M": 45, "compositeRating": 72, "accDissRating": "C"},
            "HPG": {"rS1M": 86, "compositeRating": 88, "accDissRating": "A"},
        }

        with patch.object(scanner, "get_expert_buy_signals", return_value=mock_cho_mua), \
             patch.object(scanner, "get_expert_value_surge", return_value=[]), \
             patch.object(scanner, "get_rrg_data", return_value=mock_rrg), \
             patch.object(scanner, "get_market_top_symbols", return_value=[]), \
             patch.object(scanner, "get_stock_infos", return_value=mock_infos), \
             patch.object(scanner, "get_recent_ohlcv_batch", return_value=mock_ohlcv), \
             patch.object(scanner, "get_market_breadth", return_value={"advances": 210, "declines": 120, "totalValue": 18000e9}), \
             patch.object(scanner, "get_live_basis_points", return_value=1.0), \
             patch.object(scanner, "get_expert_rating", side_effect=lambda s: ratings[s]):
            res = scanner.scan_top_rockets(top_n=10, record_history=False)

        syms = {c.symbol for c in res}
        assert "FPT" not in syms, "Cổ phiếu gãy nền -3.6 ATR dưới POC không được lọt vào Top Mua Mới"
        assert "HPG" in syms

        # Kiểm tra bất biến toán học SL < Entry_Low <= Entry_High < TP1 < TP2 ngay cả khi đầu vào cho_mua bị treo cao hơn thị giá
        stale_zone_cand = FialdaCandidate(
            symbol="PVT",
            price=21.25,
            signal_type="CHO_MUA_CHAN_SONG",
            entry_low=23.28,   # Stale zone cao hơn cả TP1 (23.27)!
            entry_high=23.51,
            stop_loss=20.0,
            target_1m=26.5,
            rs_1m=75,
            composite_rating=78,
            acc_diss_rating="B",
            rrg_r=101.0,
            rrg_m=100.5,
            foreign_net_value_billion=5.0,
            ranking_score=80.0,
            catalyst="Tanker",
            atr_14=0.75,
        )
        enriched = enrich_candidates_with_trailing_stop_and_history(
            [stale_zone_cand],
            basis_points=1.0,
            market_breadth_pct=65.0,
            record_history=False,
        )
        pvt = enriched[0]
        assert pvt.stop_loss < pvt.entry_low <= pvt.entry_high < pvt.tp1 < pvt.tp2

    def test_loophole2_post_t0_downside_breakdown_blocks_falling_knife_buy_and_js_badge(self, tmp_path: Path):
        """Mã sau T0 giảm -4.0% (vẫn trên SL -6.0%) phải chặn mua mới (CẤM BẮT DAO RƠI), không được báo VÙNG MUA CHUẨN."""
        tracker = SignalTracker(
            signals_file=tmp_path / "downside.jsonl",
            scorecard_file=tmp_path / "downside.md",
            ml_dataset_file=tmp_path / "downside.csv",
        )
        t0 = datetime(2026, 10, 27, 9, 30, tzinfo=VN_TZ)
        t1 = datetime(2026, 10, 28, 10, 30, tzinfo=VN_TZ)

        c0 = FialdaCandidate(
            symbol="CTG", price=20.00, signal_type="CHO_MUA_CHAN_SONG",
            entry_low=19.70, entry_high=20.30, stop_loss=18.80, target_1m=25.0,
            rs_1m=82, composite_rating=84, acc_diss_rating="A",
            rrg_r=102.0, rrg_m=101.0, foreign_net_value_billion=12.0, ranking_score=86.0,
            catalyst="Bank", tp1=21.88, tp2=23.08,
        )
        tracker.update_signals([c0], current_time=t0)

        # T+1: Giá rơi về 19.20 (-4.0% dưới T0, xuyên thủng vùng mua 19.70 nhưng vẫn trên SL 18.80)
        c1_weak = FialdaCandidate(
            symbol="CTG", price=19.20, signal_type="CHO_MUA_CHAN_SONG",
            entry_low=18.90, entry_high=19.40, stop_loss=18.80, target_1m=24.0,
            rs_1m=76, composite_rating=80, acc_diss_rating="B",
            rrg_r=100.5, rrg_m=99.8, foreign_net_value_billion=-2.0, ranking_score=80.0,
            catalyst="Bank pullback", tp1=21.88, tp2=23.08,
        )
        sigs = tracker.update_signals([c1_weak], current_time=t1)
        ctg = sigs["CTG"]
        assert ctg.status == "ACTIVE"  # Người đang có hàng vẫn giữ theo kỷ luật SL 18.80
        assert ctg.buy_permission == "EXTENDED_NO_CHASING"
        badge = format_public_anti_fomo_badge(ctg.buy_permission, ctg.pnl_pct, ctg.holding_days)
        assert "ĐÃ SUY YẾU" in badge or "CẤM BẮT DAO RƠI" in badge

        # Rung lắc vừa phải -2.0% (19.60) -> BUY_CAUTION (thăm dò thận trọng, không xanh mượt mù quáng)
        status_caut, perm_caut, _, _ = tracker.evaluate_status_and_advice(
            entry_orig=20.00, cur_price=19.60, cur_stop=18.80, tp1=21.88, tp2=23.08, holding_days=1
        )
        assert status_caut == "ACTIVE"
        assert perm_caut == "BUY_CAUTION"

        # Kiểm tra Client JS trong terminal.py có nhánh cảnh báo suy yếu dưới vùng mua
        html_out = tmp_path / "hud_downside.html"
        generate_terminal_html(output_path=str(html_out), fialda_candidates=[c0], top_n=1)
        html_text = html_out.read_text(encoding="utf-8")
        assert "SUY YẾU" in html_text

    def test_loophole3_macro_circuit_breaker_synchronizes_signal_tracker_and_blocks_new_t0_pollution(self, tmp_path: Path):
        """Khi Cầu chì Vĩ mô bật: Mã cũ trong sổ cái chuyển sang NGỪNG MUA trên Scorecard; mã mới trên Watchlist không được ghi khống thành T0 mới."""
        tracker = SignalTracker(
            signals_file=tmp_path / "macro_sync.jsonl",
            scorecard_file=tmp_path / "macro_sync.md",
            ml_dataset_file=tmp_path / "macro_sync.csv",
        )
        t0_good_day = datetime(2026, 10, 29, 10, 0, tzinfo=VN_TZ)
        t1_crash_day = datetime(2026, 10, 30, 14, 0, tzinfo=VN_TZ)

        c_ctg = FialdaCandidate(
            symbol="CTG", price=35.00, signal_type="CHO_MUA_CHAN_SONG",
            entry_low=34.50, entry_high=35.50, stop_loss=33.20, target_1m=42.0,
            rs_1m=84, composite_rating=85, acc_diss_rating="A",
            rrg_r=102.0, rrg_m=101.5, foreign_net_value_billion=18.0, ranking_score=88.0,
            catalyst="Bank leader", tp1=37.85, tp2=39.65,
        )
        tracker.update_signals([c_ctg], current_time=t0_good_day, macro_pause_buying=False)
        assert "CTG" in tracker.load_active_signals()

        # Ngày T+1: Độ rộng sập 27.9% -> macro_pause_buying=True; Watchlist xuất hiện thêm STB (CRITICAL / NGỪNG MUA)
        c_ctg_t1 = FialdaCandidate(
            symbol="CTG", price=35.20, signal_type="CHO_MUA_CHAN_SONG",
            entry_low=34.50, entry_high=35.50, stop_loss=33.20, target_1m=42.0,
            rs_1m=84, composite_rating=85, acc_diss_rating="A",
            rrg_r=102.0, rrg_m=101.5, foreign_net_value_billion=5.0, ranking_score=87.0,
            catalyst="Bank leader", tp1=37.85, tp2=39.65,
            t25_exposure_level="CRITICAL",
            buy_permission="EXTENDED_NO_CHASING",
        )
        c_stb_watchlist = FialdaCandidate(
            symbol="STB", price=55.00, signal_type="DOT_BIEN_GIA_TRI",
            entry_low=54.20, entry_high=55.80, stop_loss=52.00, target_1m=68.0,
            rs_1m=80, composite_rating=70, acc_diss_rating="E",
            rrg_r=101.0, rrg_m=100.2, foreign_net_value_billion=-4.0, ranking_score=65.0,
            catalyst="Watchlist only", tp1=59.50, tp2=62.50,
            t25_exposure_level="CRITICAL",
            buy_permission="EXTENDED_NO_CHASING",
        )
        sigs_t1 = tracker.update_signals(
            [c_ctg_t1, c_stb_watchlist],
            current_time=t1_crash_day,
            macro_pause_buying=True,
        )
        # 1. STB là mã mới xuất hiện đúng lúc thị trường CẤM MUA -> Tuyệt đối không được ghi khống vào sổ cái T0 & ML Dataset!
        assert "STB" not in sigs_t1
        # 2. CTG đã có từ trước -> Được cập nhật giá 35.20 nhưng khóa quyền mua mới đồng bộ với Dashboard!
        assert sigs_t1["CTG"].current_price == 35.20
        assert sigs_t1["CTG"].buy_permission == "EXTENDED_NO_CHASING"
        scorecard_md = (tmp_path / "macro_sync.md").read_text(encoding="utf-8")
        assert "VÙNG MUA CHUẨN" not in scorecard_md
        assert "CẦU CHÌ" in scorecard_md or "NGỪNG MUA" in scorecard_md

    def test_loophole4_high_exposure_downgrades_buy_ok_to_buy_caution_and_breadth_alignment(self):
        """Chế độ HIGH T+2.5 (Basis <= -6 hoặc Breadth < 45%) phải hạ quyền mua xuống BUY_CAUTION thay vì để lọt BUY_OK."""
        exp_high = evaluate_t25_exposure(
            symbol="SSI", shares=20_000, t_stage="T+0", basis_points=-7.5, market_breadth_pct=52.0
        )
        assert exp_high.exposure_level == "HIGH"
        assert exp_high.pause_new_buying is True

        cand = FialdaCandidate(
            symbol="SSI", price=26.00, signal_type="CHO_MUA_CHAN_SONG",
            entry_low=25.60, entry_high=26.30, stop_loss=24.60, target_1m=32.0,
            rs_1m=85, composite_rating=86, acc_diss_rating="A",
            rrg_r=103.0, rrg_m=102.0, foreign_net_value_billion=20.0, ranking_score=90.0,
            catalyst="Brokerage",
        )
        enriched = enrich_candidates_with_trailing_stop_and_history(
            [cand],
            basis_points=-7.5,
            market_breadth_pct=52.0,
            record_history=False,
        )
        assert enriched[0].t25_exposure_level == "HIGH"
        assert enriched[0].buy_permission == "BUY_CAUTION"
        assert "VÙNG MUA CHUẨN" not in enriched[0].anti_fomo_badge

    def test_loophole5_vn_trading_days_prevents_friday_to_monday_false_stale_and_short_cooldown(self, tmp_path: Path):
        """Tín hiệu T0 chiều Thứ Sáu sang sáng Thứ Hai mới qua 1 phiên giao dịch (không bị gán STALE_SIGNAL T+3 sai); Cooldown SL tính đủ 3 phiên thực."""
        from src.risk_engine.signal_tracker import count_vn_trading_days

        # Thứ Sáu 23/10/2026 -> Thứ Hai 26/10/2026 chỉ là 1 phiên giao dịch
        assert count_vn_trading_days(date(2026, 10, 23), date(2026, 10, 26)) == 1
        # Nghỉ lễ 30/04 - 01/05 (Thứ Năm 30/04/2026 & Thứ Sáu 01/05/2026 là ngày lễ -> Thứ Tư 29/04 sang Thứ Hai 04/05 chỉ có 1 phiên!)
        assert count_vn_trading_days(date(2026, 4, 29), date(2026, 5, 4)) == 1

        tracker = SignalTracker(
            signals_file=tmp_path / "trading_cal.jsonl",
            scorecard_file=tmp_path / "trading_cal.md",
            ml_dataset_file=tmp_path / "trading_cal.csv",
        )
        fri_t0 = datetime(2026, 10, 23, 14, 15, tzinfo=VN_TZ)  # Thứ Sáu
        mon_t1 = datetime(2026, 10, 26, 9, 45, tzinfo=VN_TZ)   # Thứ Hai (mới T+1 phiên thực!)
        tue_t2 = datetime(2026, 10, 27, 10, 0, tzinfo=VN_TZ)   # Thứ Ba (mới T+2 phiên thực!)

        c_good = FialdaCandidate(
            symbol="MBB", price=25.00, signal_type="CHO_MUA_CHAN_SONG",
            entry_low=24.65, entry_high=25.35, stop_loss=23.75, target_1m=31.0,
            rs_1m=85, composite_rating=88, acc_diss_rating="A",
            rrg_r=102.5, rrg_m=101.5, foreign_net_value_billion=22.0, ranking_score=89.0,
            catalyst="Military Bank", tp1=27.00, tp2=28.30,
        )
        c_sl = FialdaCandidate(
            symbol="DIG", price=15.00, signal_type="DOT_BIEN_GIA_TRI",
            entry_low=14.80, entry_high=15.20, stop_loss=14.20, target_1m=19.0,
            rs_1m=78, composite_rating=75, acc_diss_rating="B",
            rrg_r=101.0, rrg_m=100.5, foreign_net_value_billion=2.0, ranking_score=80.0,
            catalyst="Property", tp1=16.25, tp2=17.05,
        )
        tracker.update_signals([c_good, c_sl], current_time=fri_t0)

        # Chiều Thứ Sáu DIG gãy luôn SL xuống 14.00 -> STOPPED_OUT
        c_sl_hit = FialdaCandidate(
            symbol="DIG", price=14.00, signal_type="DOT_BIEN_GIA_TRI",
            entry_low=13.80, entry_high=14.20, stop_loss=13.30, target_1m=18.0,
            rs_1m=70, composite_rating=70, acc_diss_rating="C",
            rrg_r=99.5, rrg_m=99.0, foreign_net_value_billion=-5.0, ranking_score=74.0,
            catalyst="SL", tp1=16.25, tp2=17.05,
        )
        tracker.update_signals([c_sl_hit], current_time=fri_t0 + timedelta(minutes=25))

        # Sáng Thứ Hai: MBB ở giá 25.15 (+0.6%) mới qua 1 phiên thực -> Phải giữ BUY_OK, KHÔNG bị hết hạn STALE_SIGNAL!
        c_good_mon = FialdaCandidate(
            symbol="MBB", price=25.15, signal_type="CHO_MUA_CHAN_SONG",
            entry_low=24.65, entry_high=25.35, stop_loss=23.75, target_1m=31.0,
            rs_1m=85, composite_rating=88, acc_diss_rating="A",
            rrg_r=102.5, rrg_m=101.5, foreign_net_value_billion=22.0, ranking_score=89.0,
            catalyst="Military Bank", tp1=27.00, tp2=28.30,
        )
        sigs_mon = tracker.update_signals([c_good_mon], current_time=mon_t1)
        assert sigs_mon["MBB"].trading_days == 1
        assert sigs_mon["MBB"].buy_permission == "BUY_OK"

        # Thứ Ba (4 ngày lịch nhưng mới 2 phiên giao dịch thực sau chiều Thứ Sáu): DIG vẫn phải bị chặn bởi cooldown 3 phiên thực!
        dig_sig = tracker.load_active_signals()["DIG"]
        assert tracker.is_in_stopout_cooldown(dig_sig, now_dt=tue_t2, cooldown_days=3) is True

    def test_loophole6_fundamental_loss_making_and_weak_camel_bank_guard_plus_macro_fail_caution(self):
        """API độ rộng lỗi (0,0) hạ trần NAV <= 40% (Fail-Caution); Scanner chặn doanh nghiệp lỗ (EPS TTM < 0) & Bank CAMEL < 50 yếu."""
        # 1. Fail-Caution khi mất dữ liệu độ rộng
        snap_missing = analyze_market_breadth(advances=0, declines=0)
        assert snap_missing.pause_new_buying is False
        assert snap_missing.max_total_nav_exposure_pct <= 40.0
        assert snap_missing.regime != "BULLISH_EXPANSION"

        # 2. Scanner chặn công ty thua lỗ (EPS TTM < 0) và Bank hạng C yếu (EIB CAMEL=39 < 50 với DOT_BIEN_GIA_TRI + Acc/Diss=C)
        scanner = FialdaScanner(username="u", password="p")
        scanner.token = "mock_tok"

        mock_cho_mua = {"VCB": {"item1": True, "item2": 56.2, "item3": 57.1}}
        mock_dot_bien = ["LOS", "EIB"]
        mock_rrg = {
            "VCB": {"r": 102.5, "m": 101.5},
            "LOS": {"r": 104.0, "m": 103.0},
            "EIB": {"r": 101.2, "m": 100.5},
        }
        mock_infos = {
            "VCB": {
                "PriceInfo": {"currentPrice": 56.8, "totalVal": 220e9},
                "ForeignTrade": {"totalForeignNetValue": 35e9},
                "BasicInfo": {"eps_TTM": 4850.0, "pe": 13.2, "pb": 2.4},
            },
            "LOS": {
                "PriceInfo": {"currentPrice": 18.5, "totalVal": 95e9},
                "ForeignTrade": {"totalForeignNetValue": 5e9},
                "BasicInfo": {"eps_TTM": -620.0, "pe": -29.8, "pb": 1.9},
            },
            "EIB": {
                "PriceInfo": {"currentPrice": 17.8, "totalVal": 110e9},
                "ForeignTrade": {"totalForeignNetValue": -2e9},
                "BasicInfo": {"eps_TTM": 1200.0, "pe": 14.5, "pb": 1.2},
            },
        }
        mock_ohlcv = {
            s: {"c": [p] * 20, "h": [p * 1.015] * 20, "l": [p * 0.985] * 20, "v": [4_000_000] * 20}
            for s, p in [("VCB", 56.8), ("LOS", 18.5), ("EIB", 17.8)]
        }
        ratings = {
            "VCB": {"rS1M": 84, "compositeRating": 88, "accDissRating": "A"},
            "LOS": {"rS1M": 90, "compositeRating": 82, "accDissRating": "A"},
            "EIB": {"rS1M": 76, "compositeRating": 68, "accDissRating": "C"},
        }

        with patch.object(scanner, "get_expert_buy_signals", return_value=mock_cho_mua), \
             patch.object(scanner, "get_expert_value_surge", return_value=mock_dot_bien), \
             patch.object(scanner, "get_rrg_data", return_value=mock_rrg), \
             patch.object(scanner, "get_market_top_symbols", return_value=[]), \
             patch.object(scanner, "get_stock_infos", return_value=mock_infos), \
             patch.object(scanner, "get_recent_ohlcv_batch", return_value=mock_ohlcv), \
             patch.object(scanner, "get_market_breadth", return_value={"advances": 220, "declines": 110, "totalValue": 19000e9}), \
             patch.object(scanner, "get_live_basis_points", return_value=2.0), \
             patch.object(scanner, "get_expert_rating", side_effect=lambda s: ratings[s]):
            res = scanner.scan_top_rockets(top_n=10, record_history=False)

        res_map = {c.symbol: c for c in res}
        assert "LOS" not in res_map, "Công ty lỗ ròng (EPS TTM < 0) phải bị chặn khỏi khuyến nghị Mua Mới"
        assert "EIB" not in res_map, "Ngân hàng tái cơ cấu CAMEL < 50 thiếu tích lũy A/B chân sóng phải bị lọc"
        assert "VCB" in res_map
        assert res_map["VCB"].camel_score_t0 >= 80.0
        assert res_map["VCB"].eps_ttm_t0 == 4850.0


class TestMLSignalLedgerV2:
    """Kiểm thử Sổ cái Đề xuất Giao dịch & Pipeline ML Dataset v2 chuẩn định chế."""

    def test_ml_ledger_v2_dropped_out_live_price_refresh_eliminates_frozen_labels(self, tmp_path: Path):
        """Mã rớt khỏi Top 20 sau T0 vẫn được cập nhật giá live, MFE/MAE, PnL T+2.5/T+5 và đóng vị thế STOP_LOSS chính xác."""
        tracker = SignalTracker(
            signals_file=tmp_path / "ml_refresh.jsonl",
            scorecard_file=tmp_path / "ml_refresh.md",
            ml_dataset_file=tmp_path / "ml_refresh.csv",
        )
        t0 = datetime(2026, 10, 19, 9, 30, tzinfo=VN_TZ)   # Thứ Hai
        t2 = datetime(2026, 10, 21, 14, 15, tzinfo=VN_TZ)  # Thứ Tư (T+2 phiên)
        t5 = datetime(2026, 10, 26, 14, 45, tzinfo=VN_TZ)  # Thứ Hai tuần sau (T+5 phiên)

        c_hpg = FialdaCandidate(
            symbol="HPG", price=20.00, signal_type="CHO_MUA_CHAN_SONG",
            entry_low=19.70, entry_high=20.30, stop_loss=19.00, target_1m=25.0,
            rs_1m=86, composite_rating=88, acc_diss_rating="A",
            rrg_r=103.0, rrg_m=102.0, foreign_net_value_billion=30.0, ranking_score=91.0,
            catalyst="Steel", tp1=21.60, tp2=23.10,
        )
        c_ssi = FialdaCandidate(
            symbol="SSI", price=25.00, signal_type="DOT_BIEN_GIA_TRI",
            entry_low=24.65, entry_high=25.35, stop_loss=23.75, target_1m=31.0,
            rs_1m=84, composite_rating=85, acc_diss_rating="B",
            rrg_r=102.0, rrg_m=101.0, foreign_net_value_billion=12.0, ranking_score=87.0,
            catalyst="Brokerage", tp1=27.00, tp2=28.30,
        )
        tracker.update_signals([c_hpg, c_ssi], current_time=t0)

        # T+2: SSI rớt khỏi Top 20 (chỉ còn HPG trong candidates), nhưng live_prices báo SSI=24.25 (-3.0%)
        c_hpg_t2 = FialdaCandidate(
            symbol="HPG", price=21.20, signal_type="CHO_MUA_CHAN_SONG",
            entry_low=19.70, entry_high=20.30, stop_loss=19.00, target_1m=25.0,
            rs_1m=88, composite_rating=89, acc_diss_rating="A",
            rrg_r=103.5, rrg_m=102.5, foreign_net_value_billion=40.0, ranking_score=92.0,
            catalyst="Steel", tp1=21.60, tp2=23.10,
        )
        sigs_t2 = tracker.update_signals([c_hpg_t2], current_time=t2, live_prices={"SSI": 24.25})
        assert sigs_t2["SSI"].current_price == 24.25
        assert sigs_t2["SSI"].pnl_t25_pct == -3.0
        assert sigs_t2["SSI"].mae_pct == -3.0

        # T+5: SSI tiếp tục vắng mặt khỏi Top 20 và thủng SL về 23.25 (<= 23.75); HPG chạm TP2 23.20 (+16%)
        c_hpg_t5 = FialdaCandidate(
            symbol="HPG", price=23.20, signal_type="CHO_MUA_CHAN_SONG",
            entry_low=19.70, entry_high=20.30, stop_loss=20.00, target_1m=26.0,
            rs_1m=92, composite_rating=92, acc_diss_rating="A",
            rrg_r=105.0, rrg_m=104.0, foreign_net_value_billion=55.0, ranking_score=95.0,
            catalyst="Steel", tp1=21.60, tp2=23.10,
        )
        sigs_t5 = tracker.update_signals([c_hpg_t5], current_time=t5, live_prices={"SSI": 23.25})
        assert sigs_t5["SSI"].status == "STOPPED_OUT"
        assert sigs_t5["SSI"].outcome_label == "STOP_LOSS"
        assert sigs_t5["SSI"].pnl_t5_pct == -7.0
        assert sigs_t5["SSI"].is_closed is True
        assert sigs_t5["SSI"].is_ml_ready is True
        assert sigs_t5["HPG"].status == "TP2_REACHED"
        assert sigs_t5["HPG"].outcome_label == "WIN_TP2"
        assert sigs_t5["HPG"].is_ml_ready is True

    def test_ml_ledger_v2_terminal_latch_win_latch_archive_rollover_and_enriched_features(self, tmp_path: Path):
        """Chốt cứng trạng thái đóng (Terminal Latch), chốt nhãn thắng +5% MFE, lưu trữ vòng sóng cũ vào archive không mất mẫu ML."""
        tracker = SignalTracker(
            signals_file=tmp_path / "ml_v2.jsonl",
            scorecard_file=tmp_path / "ml_v2.md",
            ml_dataset_file=tmp_path / "ml_v2.csv",
        )
        t0 = datetime(2026, 10, 19, 9, 30, tzinfo=VN_TZ)   # Thứ Hai
        t1 = datetime(2026, 10, 20, 14, 0, tzinfo=VN_TZ)   # Thứ Ba
        t2 = datetime(2026, 10, 21, 14, 0, tzinfo=VN_TZ)   # Thứ Tư
        t7 = datetime(2026, 10, 28, 10, 0, tzinfo=VN_TZ)   # Thứ Tư tuần sau (đã qua > 3 phiên cooldown sau T1!)

        c_vix_w1 = FialdaCandidate(
            symbol="VIX", price=12.00, signal_type="CHO_MUA_CHAN_SONG",
            entry_low=11.82, entry_high=12.18, stop_loss=11.40, target_1m=15.0,
            rs_1m=85, composite_rating=84, acc_diss_rating="A",
            rrg_r=102.5, rrg_m=101.8, foreign_net_value_billion=14.0, ranking_score=88.0,
            catalyst="Wave 1", tp1=12.95, tp2=13.60,
            atr_14=0.42, poc_price=11.90, val_price=11.60, atr_dist_from_poc=0.24,
            slippage_est_pct=0.35, has_actual_prop_flow=True, prop_net_value_billion=6.5,
            market_breadth_pct_t0=64.5, vn30_basis_t0=2.5, pe_t0=11.2, pb_t0=1.4, eps_ttm_t0=1070.0,
        )
        c_cts = FialdaCandidate(
            symbol="CTS", price=20.00, signal_type="CHO_MUA_CHAN_SONG",
            entry_low=19.70, entry_high=20.30, stop_loss=19.00, target_1m=25.0,
            rs_1m=88, composite_rating=86, acc_diss_rating="A",
            rrg_r=103.0, rrg_m=102.0, foreign_net_value_billion=8.0, ranking_score=89.0,
            catalyst="Brokerage", tp1=21.60, tp2=23.10,
        )
        sigs0 = tracker.update_signals([c_vix_w1, c_cts], current_time=t0)
        assert sigs0["VIX"].is_ml_ready is False  # T0 mới mở chưa thể dùng làm nhãn y huấn luyện có giám sát!
        assert sigs0["VIX"].schema_version == "v2"
        assert sigs0["VIX"].market_breadth_pct_t0 == 64.5
        assert sigs0["VIX"].pe_t0 == 11.2

        # T+1: VIX thủng SL xuống 11.20 -> STOPPED_OUT (đóng vị thế); CTS tăng vọt lên 21.30 (+6.5% >= +5.0% -> target_win_binary = 1)
        tracker.update_signals([], current_time=t1, live_prices={"VIX": 11.20, "CTS": 21.30})

        # T+2: VIX hồi kỹ thuật lên 12.80, CTS rung lắc lùi về 20.50 (+2.5%)
        # - VIX ĐÃ ĐÓNG (STOPPED_OUT) ở T+1 -> Tuyệt đối không được xóa nhãn STOP_LOSS hay đổi target_win_binary thành 1!
        # - CTS đã từng đạt +6.5% (>= +5.0%) trước khi chạm SL -> target_win_binary phải giữ chốt = 1!
        sigs2 = tracker.update_signals([], current_time=t2, live_prices={"VIX": 12.80, "CTS": 20.50})
        assert sigs2["VIX"].status == "STOPPED_OUT"
        assert sigs2["VIX"].outcome_label == "STOP_LOSS"
        assert sigs2["VIX"].target_win_binary == 0
        assert sigs2["CTS"].target_win_binary == 1

        # T+7 (5 phiên giao dịch thực sau khi VIX đóng ở T+1 -> hết cooldown 3 phiên): VIX xuất hiện sóng mới hợp lệ tại 13.00
        c_vix_w2 = FialdaCandidate(
            symbol="VIX", price=13.00, signal_type="CHO_MUA_CHAN_SONG",
            entry_low=12.80, entry_high=13.20, stop_loss=12.30, target_1m=16.5,
            rs_1m=89, composite_rating=87, acc_diss_rating="A",
            rrg_r=103.5, rrg_m=102.5, foreign_net_value_billion=20.0, ranking_score=90.0,
            catalyst="Wave 2", tp1=14.10, tp2=14.85,
        )
        sigs7 = tracker.update_signals([c_vix_w2], current_time=t7)
        assert sigs7["VIX"].entry_original == 13.00
        assert sigs7["VIX"].status == "ACTIVE"

        # Kiểm tra ML CSV Dataset bảo toàn CẢ sóng 1 đã đóng (STOP_LOSS) LẪN sóng 2 mới của VIX + CTS (tổng 3 dòng, signal_id duy nhất)
        df = pd.read_csv(tmp_path / "ml_v2.csv")
        assert len(df) == 3
        assert df["signal_id"].nunique() == 3
        vix_rows = df[df["symbol"] == "VIX"].sort_values("first_signal_date")
        assert len(vix_rows) == 2
        assert vix_rows.iloc[0]["outcome_label"] == "STOP_LOSS"
        assert bool(vix_rows.iloc[0]["is_ml_ready"]) is True
        assert vix_rows.iloc[1]["entry_original"] == 13.00

