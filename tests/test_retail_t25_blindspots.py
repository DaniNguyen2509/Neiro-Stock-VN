"""Bộ kiểm thử chuyên biệt khắc phục 8 Điểm mù Rủi ro T+2.5 cho Nhà đầu tư Cá nhân Nhỏ lẻ.

Đối chiếu trực tiếp với hợp đồng đặc tả tại:
docs/plans/RETAIL_T25_BLINDSPOT_REMEDIATION_PLAN.md (ADR-017)
"""

from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import pytest

from src.collector.fialda_scanner import (
    FialdaScanner,
    classify_dual_flow,
)


VN_TZ = timezone(timedelta(hours=7))


class TestPhase1DataIntegrityAndAntiClimax:
    """Giai đoạn 1: Thanh lọc dữ liệu thật & Chặn đu đỉnh Pre-T0 (BM-02, BM-03, BM-04)."""

    def test_bm03_dual_flow_never_fabricates_domestic_buying_on_foreign_dump(self):
        """Khối ngoại xả -241.7 tỷ kèm Acc/Diss=E (như VIC 30/10/2026) phải báo RUI_RO_XA và không bịa +362.5 tỷ."""
        regime, badge, prop_val = classify_dual_flow(
            foreign_net_val=-241.7,
            acc_diss="E",
            signal_type="DOT_BIEN_GIA_TRI",
            rrg_r=101.6,
            rrg_m=101.7,
            ibd_composite=39,
        )
        assert regime == "RUI_RO_XA"
        assert "XẢ" in badge or "PHÂN PHỐI" in badge
        # Không có dữ liệu Tự doanh thực tế -> tuyệt đối không bịa số dương +362.5 tỷ
        assert prop_val == 0.0

    def test_bm03_dual_flow_accepts_verified_prop_or_grade_ab_absorption(self):
        """Chỉ cấp nhãn NOI_CAN_HANG khi có dữ liệu Tự doanh mua thật hoặc tích lũy hạng A/B giữ nền chặt."""
        # Trường hợp 1: Có số liệu Tự doanh thực chứng hấp thụ cung ngoại
        reg_verified, _, prop_verified = classify_dual_flow(
            foreign_net_val=-15.0,
            acc_diss="C",
            signal_type="CHO_MUA_CHAN_SONG",
            rrg_r=102.0,
            rrg_m=101.5,
            prop_net_actual_billion=24.5,
            ibd_composite=78,
        )
        assert reg_verified == "NOI_CAN_HANG"
        assert prop_verified == 24.5

        # Trường hợp 2: Chưa có số Tự doanh EOD nhưng cổ phiếu tích lũy hạng A + IBD cao + đóng cửa cao nhất phiên
        reg_ab, _, prop_ab = classify_dual_flow(
            foreign_net_val=-3.2,
            acc_diss="A",
            signal_type="CHO_MUA_CHAN_SONG",
            rrg_r=103.0,
            rrg_m=101.8,
            prop_net_actual_billion=None,
            ibd_composite=82,
            close_position_in_range=0.85,
        )
        assert reg_ab == "NOI_CAN_HANG"
        assert prop_ab == 0.0

    def test_bm04_adtv20_filter_rejects_illiquid_and_one_day_penny_spike(self):
        """Bộ lọc ADTV20 phải tính đúng trung bình 20 phiên thật, không kẹp sàn max(..., 20.0)."""
        scanner = FialdaScanner(username="u", password="p")
        scanner.token = "tok"

        mock_cho_mua = {
            "LIQ": {"item1": True, "item2": 20.0, "item3": 20.6},
            "ILL": {"item1": True, "item2": 10.0, "item3": 10.3},
            "SPK": {"item1": True, "item2": 12.0, "item3": 12.4},
        }
        mock_top = [
            {"symbol": "LIQ", "currentPrice": 20.4, "totalValue": 60e9, "totalForeignerNetBuyValue": 5e9},
            {"symbol": "ILL", "currentPrice": 10.1, "totalValue": 6.5e9, "totalForeignerNetBuyValue": 1e9},
            # SPK nổ thanh khoản 1 phiên 35 tỷ nhưng 19 phiên trước chỉ 2.4 tỷ/phiên -> ADTV20 < 5 tỷ
            {"symbol": "SPK", "currentPrice": 12.2, "totalValue": 35e9, "totalForeignerNetBuyValue": 0.5e9},
        ]
        mock_stock_infos = {
            "LIQ": {"PriceInfo": {"currentPrice": 20.4, "totalVal": 60e9}, "ForeignTrade": {"totalForeignNetValue": 5e9}},
            "ILL": {"PriceInfo": {"currentPrice": 10.1, "totalVal": 6.5e9}, "ForeignTrade": {"totalForeignNetValue": 1e9}},
            "SPK": {"PriceInfo": {"currentPrice": 12.2, "totalVal": 35e9}, "ForeignTrade": {"totalForeignNetValue": 0.5e9}},
        }
        mock_ohlcv_map = {
            "LIQ": {
                "o": [20.0] * 20,
                "h": [20.6] * 20,
                "l": [19.8] * 20,
                "c": [20.3] * 20,
                "v": [3_000_000] * 20,  # ~60.9 tỷ/phiên
            },
            "ILL": {
                "o": [10.0] * 20,
                "h": [10.3] * 20,
                "l": [9.8] * 20,
                "c": [10.1] * 20,
                "v": [600_000] * 20,  # ~6.06 tỷ/phiên (< 15 tỷ -> loại)
            },
            "SPK": {
                "o": [12.0] * 20,
                "h": [12.3] * 20,
                "l": [11.8] * 20,
                "c": [12.0] * 19 + [12.2],
                "v": [200_000] * 19 + [2_870_000],  # 19 phiên 2.4 tỷ + 1 phiên 35 tỷ -> ADTV20 ~ 4.03 tỷ (< 15 tỷ -> loại)
            },
        }

        with patch.object(scanner, "get_expert_buy_signals", return_value=mock_cho_mua), \
             patch.object(scanner, "get_expert_value_surge", return_value=[]), \
             patch.object(scanner, "get_rrg_data", return_value={s: {"r": 102.0, "m": 101.5} for s in mock_cho_mua}), \
             patch.object(scanner, "get_market_top_symbols", side_effect=[mock_top, []]), \
             patch.object(scanner, "get_stock_infos", return_value=mock_stock_infos), \
             patch.object(scanner, "get_expert_rating", return_value={"rS1M": 82, "compositeRating": 85, "accDissRating": "A"}), \
             patch.object(scanner, "get_recent_ohlcv_batch", return_value=mock_ohlcv_map, create=True):

            results = scanner.scan_top_rockets(top_n=10, record_history=False)
            symbols = [c.symbol for c in results]
            assert "LIQ" in symbols
            assert "ILL" not in symbols
            assert "SPK" not in symbols

    def test_bm02_pre_t0_altitude_and_climax_distribution_gate(self):
        """Chặn cổ phiếu phân phối nặng Acc/Diss=E (như VIC) và cổ phiếu đã chạy nóng > 2.5*ATR xa POC."""
        scanner = FialdaScanner(username="u", password="p")
        scanner.token = "tok"

        mock_dot_bien = ["BAS", "VIC", "HOT"]
        mock_stock_infos = {
            "BAS": {"PriceInfo": {"currentPrice": 21.0, "totalVal": 120e9}, "ForeignTrade": {"totalForeignNetValue": 15e9}},
            "VIC": {"PriceInfo": {"currentPrice": 239.7, "totalVal": 829.5e9}, "ForeignTrade": {"totalForeignNetValue": -241.7e9}},
            "HOT": {"PriceInfo": {"currentPrice": 34.0, "totalVal": 95e9}, "ForeignTrade": {"totalForeignNetValue": 2e9}},
        }
        ratings = {
            "BAS": {"rS1M": 82, "compositeRating": 84, "accDissRating": "A"},
            "VIC": {"rS1M": 6, "compositeRating": 39, "accDissRating": "E"},
            "HOT": {"rS1M": 92, "compositeRating": 80, "accDissRating": "B"},
        }
        # BAS: Tích lũy chặt quanh POC ~ 20.6, ATR ~ 0.6 -> cur_price=21.0 chỉ cách POC ~ 0.67 ATR (Hợp lệ!)
        # HOT: Tích lũy 15 phiên ở 24.0 (volume lớn ở 24.0 -> POC ~ 24.5), sau đó kéo dựng đứng lên 34.0 (> 6 ATR xa POC -> Cấm mua đuổi!)
        mock_ohlcv_map = {
            "BAS": {
                "o": [20.5] * 20,
                "h": [21.0] * 20,
                "l": [20.3] * 20,
                "c": [20.6] * 19 + [21.0],
                "v": [5_000_000] * 20,
            },
            "VIC": {
                "o": [235.0] * 20,
                "h": [244.0] * 20,
                "l": [232.0] * 20,
                "c": [238.0] * 19 + [239.7],
                "v": [3_500_000] * 20,
            },
            "HOT": {
                "o": [24.0] * 15 + [26.0, 28.0, 30.0, 32.0, 33.5],
                "h": [24.6] * 15 + [27.5, 29.5, 31.5, 33.5, 34.2],
                "l": [23.8] * 15 + [25.8, 27.8, 29.8, 31.8, 33.0],
                "c": [24.2] * 15 + [27.2, 29.2, 31.2, 33.2, 34.0],
                "v": [6_000_000] * 15 + [2_000_000] * 5,
            },
        }

        with patch.object(scanner, "get_expert_buy_signals", return_value={}), \
             patch.object(scanner, "get_expert_value_surge", return_value=mock_dot_bien), \
             patch.object(scanner, "get_rrg_data", return_value={s: {"r": 102.0, "m": 101.5} for s in mock_dot_bien}), \
             patch.object(scanner, "get_market_top_symbols", return_value=[]), \
             patch.object(scanner, "get_stock_infos", return_value=mock_stock_infos), \
             patch.object(scanner, "get_expert_rating", side_effect=lambda s: ratings[s]), \
             patch.object(scanner, "get_recent_ohlcv_batch", return_value=mock_ohlcv_map, create=True):

            results = scanner.scan_top_rockets(top_n=10, record_history=False)
            symbols = [c.symbol for c in results]
            assert "BAS" in symbols
            # VIC bị loại vì phân phối nặng Acc/Diss=E + ngoại xả -241.7 tỷ
            assert "VIC" not in symbols
            # HOT bị loại vì giá đã kéo quá xa POC (> 2.5 * ATR(14)) trước T0
            assert "HOT" not in symbols

    def test_bm02_morning_session_adds_intraday_bull_trap_caution(self):
        """Quét trong khung sáng (09:15 - 11:15) phải gắn cảnh báo thăm dò <= 30% chờ chiều T+2.5."""
        scanner = FialdaScanner(username="u", password="p")
        scanner.token = "tok"

        morning_time = datetime(2026, 10, 30, 9, 45, 0, tzinfo=VN_TZ)
        mock_dot_bien = ["HPG"]
        mock_stock_infos = {
            "HPG": {"PriceInfo": {"currentPrice": 21.0, "totalVal": 300e9}, "ForeignTrade": {"totalForeignNetValue": 25e9}},
        }
        mock_ohlcv = {
            "HPG": {
                "o": [20.6] * 20,
                "h": [21.1] * 20,
                "l": [20.4] * 20,
                "c": [20.8] * 19 + [21.0],
                "v": [14_000_000] * 20,
            }
        }

        with patch.object(scanner, "get_expert_buy_signals", return_value={}), \
             patch.object(scanner, "get_expert_value_surge", return_value=mock_dot_bien), \
             patch.object(scanner, "get_rrg_data", return_value={"HPG": {"r": 102.0, "m": 101.0}}), \
             patch.object(scanner, "get_market_top_symbols", return_value=[]), \
             patch.object(scanner, "get_stock_infos", return_value=mock_stock_infos), \
             patch.object(scanner, "get_expert_rating", return_value={"rS1M": 80, "compositeRating": 85, "accDissRating": "B"}), \
             patch.object(scanner, "get_recent_ohlcv_batch", return_value=mock_ohlcv, create=True):

            results = scanner.scan_top_rockets(top_n=5, record_history=False, scan_time=morning_time)
            assert len(results) == 1
            assert "13:45" in results[0].catalyst or "30%" in results[0].catalyst


class TestPhase2T25RealisticStopLossAndMacroBreaker:
    """Giai đoạn 2: Cắt lỗ cấu trúc T+2.5, Độ rộng thị trường & Radar Basis sống (BM-05, BM-06)."""

    def test_bm05_individualized_t25_stop_loss_not_clamped_to_3pct_and_net_rr_after_fees(self):
        """SL không được đóng khung đồng loạt -3.0%; phải co giãn theo ATR(14) (-4.5%..-7.5%) và bù 0.40% phí thuế."""
        from src.collector.fialda_scanner import FialdaCandidate, enrich_candidates_with_trailing_stop_and_history

        c_low_vol = FialdaCandidate(
            symbol="VCB", price=60.0, signal_type="CHO_MUA_CHAN_SONG",
            entry_low=59.2, entry_high=60.5, stop_loss=57.0, target_1m=72.0,
            rs_1m=78, composite_rating=84, acc_diss_rating="A",
            rrg_r=101.0, rrg_m=100.8, foreign_net_value_billion=25.0, ranking_score=82.0,
            catalyst="Bank leader", atr_14=1.10, val_price=58.0, swing_low_10d=57.8,
        )
        c_mid_vol = FialdaCandidate(
            symbol="HPG", price=21.20, signal_type="DOT_BIEN_GIA_TRI",
            entry_low=20.8, entry_high=21.4, stop_loss=20.0, target_1m=26.5,
            rs_1m=80, composite_rating=85, acc_diss_rating="B",
            rrg_r=102.0, rrg_m=101.2, foreign_net_value_billion=29.4, ranking_score=84.0,
            catalyst="Steel leader", atr_14=0.75, val_price=20.1, swing_low_10d=20.0,
        )
        c_high_vol = FialdaCandidate(
            symbol="SSI", price=20.0, signal_type="DOT_BIEN_GIA_TRI",
            entry_low=19.6, entry_high=20.2, stop_loss=18.6, target_1m=25.0,
            rs_1m=85, composite_rating=82, acc_diss_rating="B",
            rrg_r=103.0, rrg_m=102.0, foreign_net_value_billion=12.0, ranking_score=83.0,
            catalyst="Brokerage beta", atr_14=0.92, val_price=18.7, swing_low_10d=18.6,
        )

        enriched = enrich_candidates_with_trailing_stop_and_history(
            [c_low_vol, c_mid_vol, c_high_vol],
            record_history=False,
        )
        sl_pcts = [round((c.price - c.stop_loss) / c.price * 100.0, 2) for c in enriched]

        # 1. Không còn mã nào bị kẹp cứng ở -3.0%; tất cả nằm trong vùng chịu nhiệt T+2.5 [4.4%, 7.6%]
        for pct in sl_pcts:
            assert 4.4 <= pct <= 7.6, f"SL {pct}% nằm ngoài vùng chịu nhiệt T+2.5 [4.5%, 7.5%]"

        # 2. Mức SL cá thể hóa theo ATR thực tế (cổ phiếu beta cao có biên SL rộng hơn cổ phiếu trụ)
        assert sl_pcts[0] < sl_pcts[1] < sl_pcts[2]

        # 3. TP1 sau khi trừ 0.40% phí + thuế vẫn đảm bảo >= 1.5R thực nhận
        for c in enriched:
            r_unit = c.price - c.stop_loss
            net_tp1_profit = (c.tp1 - c.price) - (c.price * 0.004)
            assert net_tp1_profit >= 1.5 * r_unit - 0.02

    def test_bm06_market_breadth_collapse_25pct_triggers_t25_circuit_breaker(self):
        """Phiên Tăng 83 / Giảm 248 (25.1%) phải kích hoạt cầu chì CRITICAL & NGỪNG MUA MỚI cho 100% mã."""
        from src.sector_engine.market_breadth import analyze_market_breadth
        from src.collector.fialda_scanner import FialdaCandidate, enrich_candidates_with_trailing_stop_and_history

        snap = analyze_market_breadth(advances=83, declines=248, total_value_billion=11241.0)
        assert snap.regime == "DISTRIBUTION_DANGER"
        assert snap.pause_new_buying is True
        assert 25.0 <= snap.breadth_pct <= 25.2

        cand = FialdaCandidate(
            symbol="HPG", price=21.20, signal_type="CHO_MUA_CHAN_SONG",
            entry_low=20.8, entry_high=21.4, stop_loss=20.0, target_1m=26.5,
            rs_1m=80, composite_rating=85, acc_diss_rating="A",
            rrg_r=102.0, rrg_m=101.2, foreign_net_value_billion=29.4, ranking_score=84.0,
            catalyst="Steel",
        )
        enriched = enrich_candidates_with_trailing_stop_and_history(
            [cand],
            basis_points=0.0,
            market_breadth_pct=snap.breadth_pct,
            record_history=False,
        )
        assert enriched[0].t25_exposure_level == "CRITICAL"
        assert "SAFE" not in enriched[0].t25_status_badge
        assert "NGỪNG MUA" in enriched[0].t25_status_badge or "CRITICAL" in enriched[0].t25_status_badge

    def test_bm06_terminal_eliminates_hardcoded_basis_and_renders_circuit_breaker_banner(self, tmp_path):
        """terminal.py không được hardcode 1312.20/1315.50 và phải hiện Banner Cầu Chì T+2.5 khi độ rộng < 35%."""
        from pathlib import Path
        from src.hud.terminal import generate_terminal_html
        from src.collector.fialda_scanner import FialdaCandidate

        terminal_src = Path("src/hud/terminal.py").read_text(encoding="utf-8")
        assert "1312.20" not in terminal_src
        assert "1315.50" not in terminal_src

        out = tmp_path / "terminal_p2.html"
        cand = FialdaCandidate(
            symbol="HPG", price=21.20, signal_type="CHO_MUA_CHAN_SONG",
            entry_low=20.8, entry_high=21.4, stop_loss=20.0, target_1m=26.5,
            rs_1m=80, composite_rating=85, acc_diss_rating="A",
            rrg_r=102.0, rrg_m=101.2, foreign_net_value_billion=29.4, ranking_score=84.0,
            catalyst="Steel", tp1=23.0, tp2=24.5,
        )
        generate_terminal_html(
            output_path=str(out),
            fialda_candidates=[cand],
            top_n=1,
            spot_deriv_override={"VN30_INDEX": 1340.00, "VN30F1M": 1330.50, "VNINDEX": 1260.00},
            market_breadth={"advances": 83, "declines": 248, "totalValue": 11241e9},
        )
        html = out.read_text(encoding="utf-8")
        assert "-9.50" in html
        assert "CẦU CHÌ T+2.5" in html
        assert "NGỪNG MUA MỚI" in html or "TẠM NGỪNG" in html


class TestPhase3UnifiedAntiFomoAndRetailSizer:
    """Giai đoạn 3: Hợp nhất Sổ cái Anti-FOMO ra Dashboard & Position Sizer Nhỏ lẻ (BM-01, BM-07)."""

    def test_bm01_bull_trap_lock_and_stale_negative_pnl_wording(self, tmp_path):
        """Mã từng tăng >+5% (MFE=+8%) rồi rơi lại +1% phải khóa BULL_TRAP_REJECT; mã T+4 âm -2.9% không được báo 'Đã tăng -2.9%'."""
        from dataclasses import dataclass
        from src.risk_engine.signal_tracker import SignalTracker

        @dataclass
        class StubCand:
            symbol: str
            price: float
            stop_loss: float
            tp1: float
            tp2: float

        tracker = SignalTracker(
            signals_file=tmp_path / "signals_p3.jsonl",
            scorecard_file=tmp_path / "scorecard_p3.md",
            ml_dataset_file=tmp_path / "ml_p3.csv",
        )
        t0 = datetime(2026, 10, 26, 9, 30, tzinfo=VN_TZ)
        t1 = datetime(2026, 10, 27, 14, 0, tzinfo=VN_TZ)
        t2 = datetime(2026, 10, 28, 14, 0, tzinfo=VN_TZ)
        t4 = datetime(2026, 10, 30, 14, 0, tzinfo=VN_TZ)

        # 1. Bull-Trap: DXS T0=10.0 -> T1 kéo lên 10.8 (+8.0%, dưới TP1=11.5) -> T2 xả về 10.1 (+1.0%)
        tracker.update_signals([StubCand("DXS", 10.0, 9.3, 11.5, 12.5)], current_time=t0)
        tracker.update_signals([StubCand("DXS", 10.8, 9.3, 11.5, 12.5)], current_time=t1)
        sigs_t2 = tracker.update_signals([StubCand("DXS", 10.1, 9.3, 11.5, 12.5)], current_time=t2)
        dxs = sigs_t2["DXS"]
        assert dxs.buy_permission == "BULL_TRAP_REJECT"
        assert dxs.buy_permission != "BUY_OK"
        assert "BẪY" in dxs.advice_note

        # 2. Stale Signal: HPG T0=21.85 -> T4 giảm về 21.21 (-2.93%, trên SL=20.40)
        tracker.update_signals([StubCand("HPG", 21.85, 20.40, 24.0, 26.0)], current_time=t0)
        sigs_t4 = tracker.update_signals([StubCand("HPG", 21.21, 20.40, 24.0, 26.0)], current_time=t4)
        hpg = sigs_t4["HPG"]
        assert hpg.buy_permission == "STALE_SIGNAL"
        assert "Đã tăng -" not in hpg.advice_note
        assert "QUÁ HẠN" in hpg.advice_note

    def test_bm01_scanner_anchors_t0_entry_filters_stopped_out_and_surfaces_anti_fomo_on_ui(self, tmp_path):
        """Mã đã STOPPED_OUT bị loại khỏi Top mới; mã đã chạy +11.5% từ T0 phải khóa vùng mua gốc T0 và hiện CẤM MUA ĐUỔI trên HTML & Markdown."""
        from src.risk_engine.signal_tracker import SignalTracker
        from src.collector.fialda_scanner import (
            FialdaCandidate,
            enrich_candidates_with_trailing_stop_and_history,
            format_top_5_markdown,
        )
        from src.hud.terminal import generate_terminal_html

        tracker = SignalTracker(
            signals_file=tmp_path / "signals_ui.jsonl",
            scorecard_file=tmp_path / "scorecard_ui.md",
            ml_dataset_file=tmp_path / "ml_ui.csv",
        )
        t0 = datetime(2026, 10, 27, 10, 0, tzinfo=VN_TZ)
        t1 = datetime(2026, 10, 29, 14, 0, tzinfo=VN_TZ)
        t2 = datetime(2026, 10, 30, 14, 0, tzinfo=VN_TZ)

        # T0: EIB mua 17.85 (SL 16.80), DXS mua 10.00 (SL 9.40, TP1 11.00, TP2 12.00)
        c_eib_t0 = FialdaCandidate(
            symbol="EIB", price=17.85, signal_type="CHO_MUA_CHAN_SONG",
            entry_low=17.60, entry_high=18.00, stop_loss=16.80, target_1m=22.0,
            rs_1m=78, composite_rating=76, acc_diss_rating="B",
            rrg_r=101.4, rrg_m=100.5, foreign_net_value_billion=10.0, ranking_score=83.0,
            catalyst="Bank", tp1=19.50, tp2=21.50,
        )
        c_dxs_t0 = FialdaCandidate(
            symbol="DXS", price=10.00, signal_type="DOT_BIEN_GIA_TRI",
            entry_low=9.85, entry_high=10.15, stop_loss=9.40, target_1m=12.5,
            rs_1m=85, composite_rating=82, acc_diss_rating="A",
            rrg_r=103.0, rrg_m=102.0, foreign_net_value_billion=5.0, ranking_score=86.0,
            catalyst="Property", tp1=11.00, tp2=12.00,
        )
        tracker.update_signals([c_eib_t0, c_dxs_t0], current_time=t0)

        # T1 (29/10): EIB thủng SL về 16.50 -> STOPPED_OUT
        c_eib_sl = FialdaCandidate(
            symbol="EIB", price=16.50, signal_type="CHO_MUA_CHAN_SONG",
            entry_low=16.20, entry_high=16.65, stop_loss=15.60, target_1m=20.5,
            rs_1m=70, composite_rating=72, acc_diss_rating="C",
            rrg_r=100.2, rrg_m=99.8, foreign_net_value_billion=-4.0, ranking_score=78.0,
            catalyst="Bank", tp1=18.00, tp2=19.50,
        )
        tracker.update_signals([c_eib_sl], current_time=t1)

        # T2 (30/10): Scanner quét thấy EIB (nảy nhẹ 16.90), DXS (đã chạy +11.5% lên 11.15, vùng mua trượt 10.93-11.26), và mã mới HPG (21.20)
        c_eib_rebound = FialdaCandidate(
            symbol="EIB", price=16.90, signal_type="CHO_MUA_CHAN_SONG",
            entry_low=16.60, entry_high=17.05, stop_loss=15.95, target_1m=21.0,
            rs_1m=72, composite_rating=74, acc_diss_rating="B",
            rrg_r=100.5, rrg_m=100.2, foreign_net_value_billion=1.0, ranking_score=80.0,
            catalyst="Bank rebound",
        )
        c_dxs_chased = FialdaCandidate(
            symbol="DXS", price=11.15, signal_type="DOT_BIEN_GIA_TRI",
            entry_low=10.93, entry_high=11.26, stop_loss=10.50, target_1m=13.9,
            rs_1m=91, composite_rating=86, acc_diss_rating="A",
            rrg_r=104.0, rrg_m=103.0, foreign_net_value_billion=8.0, ranking_score=89.0,
            catalyst="Property surge",
        )
        c_hpg_fresh = FialdaCandidate(
            symbol="HPG", price=21.20, signal_type="CHO_MUA_CHAN_SONG",
            entry_low=20.90, entry_high=21.35, stop_loss=20.00, target_1m=26.5,
            rs_1m=80, composite_rating=85, acc_diss_rating="A",
            rrg_r=102.0, rrg_m=101.2, foreign_net_value_billion=25.0, ranking_score=85.0,
            catalyst="Steel base",
        )

        enriched = enrich_candidates_with_trailing_stop_and_history(
            [c_dxs_chased, c_eib_rebound, c_hpg_fresh],
            record_history=False,
            signal_tracker=tracker,
            current_time=t2,
        )
        syms = [c.symbol for c in enriched]
        # 1. EIB vừa STOPPED_OUT trong vòng 3 ngày cooldown -> bị loại khỏi danh sách khuyến nghị mua mới!
        assert "EIB" not in syms
        assert "DXS" in syms and "HPG" in syms

        # 2. DXS bị khóa vùng mua neo quanh T0=10.00 (entry_high <= 10.20, không trượt lên 11.26) & gắn CẤM MUA ĐUỔI
        dxs_out = next(c for c in enriched if c.symbol == "DXS")
        assert dxs_out.entry_high <= 10.25
        assert dxs_out.buy_permission == "EXTENDED_NO_CHASING"
        assert "CẤM MUA ĐUỔI" in dxs_out.anti_fomo_badge

        # 3. Cả báo cáo Markdown lẫn Web Terminal HTML đều hiển thị trực diện nhãn CẤM MUA ĐUỔI
        md_text = format_top_5_markdown(enriched)
        assert "CẤM MUA ĐUỔI" in md_text

        html_out = tmp_path / "anti_fomo_terminal.html"
        generate_terminal_html(
            output_path=str(html_out),
            fialda_candidates=enriched,
            top_n=5,
            spot_deriv_override={"VN30_INDEX": 1320.0, "VN30F1M": 1321.0, "VNINDEX": 1270.0},
        )
        html_text = html_out.read_text(encoding="utf-8")
        assert "CẤM MUA ĐUỔI" in html_text

    def test_bm07_retail_cold_start_20pct_cap_and_lot100_feasibility(self):
        """Vốn nhỏ lẻ 100tr cold-start (0% T+0) giới hạn <= 20% NAV/mã, cảnh báo lô 100 cp cho VIC (239.7) & FRT (147.7), bỏ lời khuyên sáo rỗng."""
        from src.risk_engine.position_sizer import calculate_retail_t25_position_size
        from src.collector.fialda_scanner import FialdaCandidate, format_top_5_markdown

        # 1. HPG thị giá 21.20 (21,200đ), SL 19.84 -> Mua được >= 600 cp nhưng tối đa <= 20,000,000đ (<= 900 cp), chia 50/50 TP1/TP2 tốt
        plan_hpg = calculate_retail_t25_position_size(
            equity_vnd=100_000_000.0,
            current_price_vnd=21.20,
            stop_loss_price_vnd=19.84,
            available_t0_ratio=0.0,
            symbol="HPG",
        )
        assert plan_hpg.total_outlay_vnd <= 20_000_000.0
        assert plan_hpg.target_shares % 100 == 0
        assert plan_hpg.target_shares >= 200
        assert plan_hpg.is_lot100_feasible is True
        assert plan_hpg.can_split_tp1_tp2 is True
        assert plan_hpg.allow_margin is False

        # 2. VIC thị giá 239.70 (239,700đ) -> 1 lô 100 cp tốn 23.97 triệu > 20% NAV (20 triệu) -> Bất khả thi cho vốn 100tr!
        plan_vic = calculate_retail_t25_position_size(
            equity_vnd=100_000_000.0,
            current_price_vnd=239.70,
            stop_loss_price_vnd=225.00,
            available_t0_ratio=0.0,
            symbol="VIC",
        )
        assert plan_vic.target_shares == 0
        assert plan_vic.is_lot100_feasible is False
        assert plan_vic.can_split_tp1_tp2 is False

        # 3. FRT thị giá 147.70 (147,700đ) -> Chỉ mua được đúng 100 cp (14.77 triệu) -> Không thể chia 50/50 TP1/TP2 lô chẵn HOSE!
        plan_frt = calculate_retail_t25_position_size(
            equity_vnd=100_000_000.0,
            current_price_vnd=147.70,
            stop_loss_price_vnd=139.00,
            available_t0_ratio=0.0,
            symbol="FRT",
        )
        assert plan_frt.target_shares == 100
        assert plan_frt.is_lot100_feasible is True
        assert plan_frt.can_split_tp1_tp2 is False

        # 4. Markdown report không còn khuyên câu sáo rỗng "luôn duy trì đệm hàng T+0 >= 35% tài khoản" cho mua mới
        cand = FialdaCandidate(
            symbol="FRT", price=147.70, signal_type="CHO_MUA_CHAN_SONG",
            entry_low=145.0, entry_high=148.5, stop_loss=139.0, target_1m=180.0,
            rs_1m=82, composite_rating=84, acc_diss_rating="A",
            rrg_r=102.0, rrg_m=101.2, foreign_net_value_billion=12.0, ranking_score=84.0,
            catalyst="Retail pharmacy", tp1=160.0, tp2=172.0,
        )
        md = format_top_5_markdown([cand])
        assert "luôn duy trì đệm hàng T+0 >= 35%" not in md
        assert "20% NAV" in md and "0% Margin" in md


class TestPhase4HonestFloorLockBacktest:
    """Giai đoạn 4: Kiểm định Backtest Kẹt Sàn T+2.5 Trung Thực & Đồng Bộ Live/Backtest (BM-08)."""

    def test_bm08_floor_lock_blocks_sell_at_exact_floor_price_and_rolls_to_t3_gap_down(self):
        """Khi hàng về chiều T+2 nhưng cổ phiếu nằm sàn cứng (-7.0% trắng bên mua), lệnh bán bị từ chối và trượt sang T+3 khớp giá mở cửa thấp hơn."""
        from src.backtesting.models import BacktestConfig, Exchange, MarketBar, PriceBand
        from src.backtesting.engine import T25BacktestEngine

        cfg = BacktestConfig(initial_capital=100_000_000.0, min_holding_bars=2)
        engine = T25BacktestEngine(cfg)

        # Ngày T0 (day_idx=0): Mua tại 20.00 (20% NAV = 20tr)
        batch = engine.execute_buy(
            symbol="DIG",
            price=20.00,
            date="2026-10-26",
            day_idx=0,
            exchange=Exchange.HOSE,
            allocated_capital=20_000_000.0,
            reference_price=19.80,
        )
        assert batch is not None

        # Ngày T+1 (day_idx=1): Giảm sàn từ ref=20.00 xuống 18.60 -> Hàng chưa về, không bán được
        band_t1 = PriceBand.calculate(20.00, Exchange.HOSE)
        bar_t1 = MarketBar(
            symbol="DIG", date="2026-10-27",
            open=19.20, high=19.30, low=band_t1.floor_price, close=band_t1.floor_price,
            volume=500_000, reference_price=20.00, exchange=Exchange.HOSE,
        )
        assert engine.check_and_execute_stop_loss("DIG", bar_t1, day_idx=1, stop_loss_price=18.90) is None

        # Ngày T+2 (day_idx=2, chiều hàng về): Cổ phiếu tiếp tục chất sàn cứng đúng bằng floor_price (ref=18.60 -> floor=17.30)
        band_t2 = PriceBand.calculate(18.60, Exchange.HOSE)
        assert band_t2.floor_price == 17.30
        # Dù hàng đã đủ T+2.5, khớp lệnh tại đúng giá sàn trắng bên mua (17.30) PHẢI BỊ TỪ CHỐI!
        sell_at_locked_floor = engine.execute_sell(
            symbol="DIG",
            price=band_t2.floor_price,
            date="2026-10-28",
            day_idx=2,
            exchange=Exchange.HOSE,
            reference_price=18.60,
            reason="STOP_LOSS",
        )
        assert sell_at_locked_floor is None
        assert "DIG" in engine.positions

        # Ngày T+3 (day_idx=3): Mở cửa gap-down tại 16.40 (trên giá sàn mới 16.09, có cầu hấp thụ giải cứu) -> Thoát lệnh tại 16.40 (-18% thực tế)
        band_t3 = PriceBand.calculate(17.30, Exchange.HOSE)
        assert 16.40 > band_t3.floor_price
        bar_t3 = MarketBar(
            symbol="DIG", date="2026-10-29",
            open=16.40, high=17.10, low=16.20, close=16.95,
            volume=15_000_000, reference_price=17.30, exchange=Exchange.HOSE,
        )
        trade_t3 = engine.check_and_execute_stop_loss("DIG", bar_t3, day_idx=3, stop_loss_price=18.90)
        assert trade_t3 is not None
        # Khớp tại min(open=16.40, stop=18.90) = 16.40, KHÔNG được khớp ảo ở close=16.95 hay stop=18.90!
        assert trade_t3.exit_price == 16.40
        assert trade_t3.return_pct < -17.5
        assert trade_t3.holding_days == 3

    def test_bm08_walk_forward_rejects_overextended_entries_and_caps_20pct_nav(self):
        """WalkForwardCoordinator không mua đuổi cổ phiếu đã kéo > 2.5*ATR xa MA20 và tuân thủ trần 20% NAV/mã."""
        from src.backtesting.models import BacktestConfig, Exchange, MarketBar
        from src.backtesting.point_in_time import PITFinancialSnapshot, PointInTimeDatabase
        from src.backtesting.walk_forward import WalkForwardCoordinator

        pit = PointInTimeDatabase()
        pit.add_snapshot(PITFinancialSnapshot(
            symbol="HOT", year=2024, quarter=1,
            period_end_date="2024-03-31", filing_date="2024-04-15",
            f_score=8, cfo_ni_ratio=1.4,
        ))

        dates = [f"2024-05-{d:02d}" for d in range(1, 26)]
        hot_bars = []
        vni_bars = []
        for idx, d in enumerate(dates):
            vni_bars.append(MarketBar("VNINDEX", d, 1250.0, 1258.0, 1245.0, 1255.0, 600e6, 1250.0, ofi=0.2))
            if idx < 20:
                # 20 phiên đi ngang chặt quanh 20.0 (ATR rất nhỏ ~ 0.4)
                hot_bars.append(MarketBar("HOT", d, 20.0, 20.2, 19.8, 20.0, 1_000_000, 20.0, ofi=0.05, exchange=Exchange.HOSE))
            elif idx == 20:
                # Phiên 20 nhảy vọt phi mã lên 24.5 (> 6 ATR xa MA20 ~ 20.2) với OFI dương & Vol đột biến -> Phải CHẶN không mua đuổi!
                hot_bars.append(MarketBar("HOT", d, 23.5, 24.6, 23.4, 24.5, 4_000_000, 23.0, ofi=0.65, exchange=Exchange.HOSE))
            else:
                hot_bars.append(MarketBar("HOT", d, 24.0, 24.3, 23.5, 23.8, 1_200_000, 24.2, ofi=0.0, exchange=Exchange.HOSE))

        cfg = BacktestConfig(initial_capital=100_000_000.0, position_allocation_pct=0.35)
        wf = WalkForwardCoordinator(
            config=cfg,
            stock_bars_dict={"HOT": hot_bars},
            vnindex_bars=vni_bars,
            pit_db=pit,
        )
        res = wf.run_simulation(0, len(dates), period_label="ANTI_CHASE_TEST")
        # Bị chặn bởi cổng Anti-Chasing > 2.5*ATR xa nền cân bằng -> 0 cổ phiếu nào được mua đuổi (stock_value == 0 suốt kỳ)!
        assert all(d.stock_value == 0.0 for d in res.equity_curve)
        assert res.final_equity == 100_000_000.0

        # Ngược lại, cổ phiếu BAS bứt phá vừa phải sát nền (< 1.5*ATR) được mua nhưng khóa trần <= 20% NAV (<= 20tr dù config 35%)
        pit.add_snapshot(PITFinancialSnapshot(
            symbol="BAS", year=2024, quarter=1,
            period_end_date="2024-03-31", filing_date="2024-04-15",
            f_score=8, cfo_ni_ratio=1.4,
        ))
        bas_bars = []
        for idx, d in enumerate(dates):
            if idx < 20:
                bas_bars.append(MarketBar("BAS", d, 20.0, 20.5, 19.6, 20.0, 1_000_000, 20.0, ofi=0.05, exchange=Exchange.HOSE))
            elif idx == 20:
                bas_bars.append(MarketBar("BAS", d, 20.2, 20.8, 20.1, 20.6, 2_000_000, 20.0, ofi=0.35, exchange=Exchange.HOSE))
            else:
                bas_bars.append(MarketBar("BAS", d, 20.6, 21.0, 20.4, 20.8, 1_200_000, 20.6, ofi=0.10, exchange=Exchange.HOSE))

        wf_bas = WalkForwardCoordinator(
            config=cfg,
            stock_bars_dict={"BAS": bas_bars},
            vnindex_bars=vni_bars,
            pit_db=pit,
        )
        res_bas = wf_bas.run_simulation(0, len(dates), period_label="COLD_START_CAP_TEST")
        max_stock_val = max(d.stock_value for d in res_bas.equity_curve)
        assert 0.0 < max_stock_val <= 20_500_000.0


class TestPhase5MultiLayerDashboardAudit:
    """Giai đoạn 5: Kiểm định 3 Tầng Dashboard, 15 Cột Dữ Liệu, Ba Trạng Thái Thời Gian & Investor Persona Test."""

    def test_stopped_out_gate_blocks_all_7_baseline_sl_violators(self, tmp_path):
        """BM-01a Scorecard: Cả 7 mã đã STOPPED_OUT (VIX, ORS, VSC, DIG, GEX, TCX, PNJ) bị chặn 100% khỏi Top 20."""
        from src.risk_engine.signal_tracker import SignalTracker
        from src.collector.fialda_scanner import FialdaCandidate, enrich_candidates_with_trailing_stop_and_history

        tracker = SignalTracker(
            signals_file=tmp_path / "sl7.jsonl",
            scorecard_file=tmp_path / "sl7.md",
            ml_dataset_file=tmp_path / "sl7.csv",
        )
        t0 = datetime(2026, 10, 28, 10, 0, tzinfo=VN_TZ)
        t1 = datetime(2026, 10, 29, 14, 0, tzinfo=VN_TZ)
        t2 = datetime(2026, 10, 30, 14, 45, tzinfo=VN_TZ)

        sl_violators = ["VIX", "ORS", "VSC", "DIG", "GEX", "TCX", "PNJ"]
        t0_cands = [
            FialdaCandidate(
                symbol=s, price=20.0, signal_type="CHO_MUA_CHAN_SONG",
                entry_low=19.7, entry_high=20.3, stop_loss=19.0, target_1m=24.0,
                rs_1m=80, composite_rating=78, acc_diss_rating="B",
                rrg_r=101.0, rrg_m=101.0, foreign_net_value_billion=2.0, ranking_score=82.0,
                catalyst="T0", tp1=21.6, tp2=23.2,
            )
            for s in sl_violators
        ]
        tracker.update_signals(t0_cands, current_time=t0)

        # T1: Cả 7 mã đều gãy SL về 18.2 (<= 19.0) -> STOPPED_OUT
        t1_cands = [
            FialdaCandidate(
                symbol=s, price=18.2, signal_type="CHO_MUA_CHAN_SONG",
                entry_low=18.0, entry_high=18.4, stop_loss=17.3, target_1m=22.0,
                rs_1m=70, composite_rating=70, acc_diss_rating="C",
                rrg_r=99.0, rrg_m=99.0, foreign_net_value_billion=-3.0, ranking_score=75.0,
                catalyst="SL hit", tp1=19.8, tp2=21.2,
            )
            for s in sl_violators
        ]
        tracker.update_signals(t1_cands, current_time=t1)

        # T2: Quét lại 7 mã đã STOPPED_OUT cùng 2 mã khỏe mới (HPG, MBB)
        scan_batch = t1_cands + [
            FialdaCandidate(
                symbol=good, price=22.0, signal_type="CHO_MUA_CHAN_SONG",
                entry_low=21.7, entry_high=22.3, stop_loss=20.9, target_1m=26.5,
                rs_1m=86, composite_rating=85, acc_diss_rating="A",
                rrg_r=103.0, rrg_m=102.0, foreign_net_value_billion=15.0, ranking_score=89.0,
                catalyst="Clean",
            )
            for good in ("HPG", "MBB")
        ]
        enriched = enrich_candidates_with_trailing_stop_and_history(
            scan_batch,
            market_breadth_pct=60.0,
            record_history=False,
            signal_tracker=tracker,
            current_time=t2,
        )
        out_syms = {c.symbol for c in enriched}
        assert out_syms == {"HPG", "MBB"}
        assert out_syms.isdisjoint(set(sl_violators))

    def test_immutable_t0_zone_anchors_entry_across_multiple_30m_scans(self, tmp_path):
        """BM-01b Scorecard: Qua 3 chu kỳ quét 30 phút (20.0 -> 20.7 -> 21.4), Vùng mua vẫn khóa cứng ở T0 (19.70 - 20.30)."""
        from src.risk_engine.signal_tracker import SignalTracker
        from src.collector.fialda_scanner import FialdaCandidate, enrich_candidates_with_trailing_stop_and_history

        tracker = SignalTracker(
            signals_file=tmp_path / "imm.jsonl",
            scorecard_file=tmp_path / "imm.md",
            ml_dataset_file=tmp_path / "imm.csv",
        )
        base_dt = datetime(2026, 10, 30, 9, 30, tzinfo=VN_TZ)

        def make_cand(p: float) -> FialdaCandidate:
            return FialdaCandidate(
                symbol="CTS", price=p, signal_type="CHO_MUA_CHAN_SONG",
                entry_low=round(p * 0.98, 2), entry_high=round(p * 1.01, 2),
                stop_loss=round(p * 0.945, 2), target_1m=round(p * 1.25, 2),
                rs_1m=88, composite_rating=85, acc_diss_rating="A",
                rrg_r=103.0, rrg_m=102.0, foreign_net_value_billion=8.0, ranking_score=88.0,
                catalyst="Anchor check",
            )

        # Scan 1 (09:30): Giá gốc T0 = 20.00 -> Ghi vào sổ cái
        s1 = enrich_candidates_with_trailing_stop_and_history(
            [make_cand(20.00)], record_history=False, signal_tracker=tracker, current_time=base_dt
        )[0]
        tracker.update_signals([s1], current_time=base_dt)

        # Scan 2 (10:00): Giá kéo lên 20.70 (+3.5% -> BUY_CAUTION)
        s2 = enrich_candidates_with_trailing_stop_and_history(
            [make_cand(20.70)], record_history=False, signal_tracker=tracker,
            current_time=base_dt + timedelta(minutes=30),
        )[0]
        assert (s2.entry_low, s2.entry_high) == (19.70, 20.30)
        assert s2.buy_permission == "BUY_CAUTION"

        # Scan 3 (10:30): Giá kéo rướn lên 21.40 (+7.0% -> EXTENDED_NO_CHASING)
        s3 = enrich_candidates_with_trailing_stop_and_history(
            [make_cand(21.40)], record_history=False, signal_tracker=tracker,
            current_time=base_dt + timedelta(minutes=60),
        )[0]
        assert (s3.entry_low, s3.entry_high) == (19.70, 20.30)
        assert s3.buy_permission == "EXTENDED_NO_CHASING"
        assert "CẤM MUA ĐUỔI" in s3.anti_fomo_badge

    def test_layer2_and_layer3_temporal_states_abc_ranking_continuity(self, tmp_path):
        """Kiểm định 3 trạng thái thời gian (A: Mới lần đầu, B: Duy trì liên tiếp, C: Vắng mặt 1 phiên rồi quay lại không bị gán MỚI sai)."""
        from src.collector.ranking_history import RankingHistoryTracker

        tracker = RankingHistoryTracker(history_file=tmp_path / "rank_abc.jsonl")
        mk = lambda sym, r_sc: type("C", (), {"symbol": sym, "price": 20.0, "ranking_score": r_sc})()

        # Scan 1 (09:00): HPG (#1), SSI (#2), CTS (#3)
        t1 = datetime(2026, 10, 29, 9, 0, tzinfo=VN_TZ)
        tracker.record_snapshot([mk("HPG", 92), mk("SSI", 89), mk("CTS", 85)], timestamp="2026-10-29 09:00:00")

        # Scan 2 (10:00): HPG (#1), SSI (#2), MBB (#3 - State A mới), CTS tạm vắng mặt
        tracker.record_snapshot([mk("HPG", 93), mk("SSI", 88), mk("MBB", 86)], timestamp="2026-10-29 10:00:00")

        # Scan 3 (11:00): CTS quay lại ở #1 (State C), HPG xuống #2 (State B), VCB lần đầu xuất hiện ở #3 (State A)
        t3 = datetime(2026, 10, 29, 11, 0, tzinfo=VN_TZ)
        changes = tracker.calculate_rank_changes([mk("CTS", 95), mk("HPG", 92), mk("VCB", 87)], current_time=t3)

        # State C: CTS từng ở #3 tại 09:00 -> Nay lên #1 => Delta = 3 - 1 = +2 (TUYỆT ĐỐI KHÔNG BỊ GÁN '🆕 MỚI')
        assert changes["CTS"]["prev_rank"] == 3
        assert changes["CTS"]["delta_rank"] == 2
        assert "MỚI" not in changes["CTS"]["badge"]

        # State B: HPG từ #1 xuống #2 => Delta = 1 - 2 = -1
        assert changes["HPG"]["prev_rank"] == 1
        assert changes["HPG"]["delta_rank"] == -1

        # State A: VCB chưa từng xuất hiện => '🆕 MỚI'
        assert changes["VCB"]["prev_rank"] is None
        assert "MỚI" in changes["VCB"]["badge"]

    def test_layer1_and_layer3_all_15_columns_and_tab2_walk_forward_investor_persona(self, tmp_path):
        """Audit toàn diện 15 cột #top-stocks-table, cảnh báo lô 100 cp, Tab 2 Walk-Forward Floor-Lock và chế độ Cầu chì Vĩ mô."""
        import re
        from src.collector.fialda_scanner import FialdaCandidate
        from src.hud.terminal import generate_terminal_html

        c_normal = FialdaCandidate(
            symbol="HPG", price=22.00, signal_type="CHO_MUA_CHAN_SONG",
            entry_low=21.70, entry_high=22.30, stop_loss=20.80, target_1m=27.00,
            rs_1m=86, composite_rating=88, acc_diss_rating="A",
            rrg_r=103.0, rrg_m=102.0, foreign_net_value_billion=25.4, ranking_score=91.2,
            catalyst="Thép HRC", adtv20_billion=380.0, liquidity_score=96.0,
            tp1=23.95, tp2=25.15, prev_rank=3, rank_change_delta=2,
            flow_regime="SIEU_SONG", flow_badge="🟢🟢 ĐỒNG THUẬN GOM",
        )
        c_high_price = FialdaCandidate(
            symbol="FPT", price=215.00, signal_type="CHO_MUA_CHAN_SONG",
            entry_low=212.00, entry_high=217.00, stop_loss=203.00, target_1m=255.00,
            rs_1m=84, composite_rating=90, acc_diss_rating="B",
            rrg_r=102.0, rrg_m=101.0, foreign_net_value_billion=12.0, ranking_score=88.5,
            catalyst="AI Cloud", adtv20_billion=420.0, liquidity_score=98.0,
            tp1=234.00, tp2=246.00, prev_rank=None, rank_change_delta=None,
            flow_regime="SIEU_SONG", flow_badge="🟢🟢 ĐỒNG THUẬN GOM",
        )

        # 1. Trạng thái thị trường khỏe (Breadth 62%, Basis +1.50)
        out_ok = tmp_path / "hud_ok.html"
        generate_terminal_html(
            output_path=str(out_ok),
            fialda_candidates=[c_normal, c_high_price],
            top_n=2,
            spot_deriv_override={"VN30_INDEX": 1320.0, "VN30F1M": 1321.5, "VNINDEX": 1270.0},
            market_breadth={"advances": 248, "declines": 152, "totalValue": 21000e9},
        )
        html_ok = out_ok.read_text(encoding="utf-8")

        # Kiểm tra đủ đúng 15 cột chuẩn trên #top-stocks-table (không phát sinh cột 16 gây tràn ngang)
        table_match = re.search(r'<table id="top-stocks-table">.*?<thead>(.*?)</thead>', html_ok, re.S)
        assert table_match is not None
        th_headers = re.findall(r"<th[^>]*>(.*?)</th>", table_match.group(1))
        assert len(th_headers) == 15
        assert th_headers == [
            "STT", "Mã CP", "Tín Hiệu AI", "Giá Khớp", "Vùng Mua", "Cắt Lỗ",
            "Chốt Lời (TP1 / TP2)", "Thanh Khoản", "Chuẩn Quỹ", "RRG",
            "Điểm IBD", "Tích Luỹ", "Khối Ngoại", "Điểm AI", "Kỳ Trước",
        ]

        # FPT giá 215.00 (1 lô = 21.5 triệu > trần 20 triệu của TK 100tr) -> Hiện cảnh báo LÔ 100CP CAO
        assert "LÔ 100CP CAO" in html_ok
        # Tab 2 Walk-Forward T+2.5 hiện diện đầy đủ với Floor-Lock, 0.40% phí thuế & <= 20% NAV
        assert 'id="walk-forward-table"' in html_ok
        assert "0.40%" in html_ok
        assert "20% NAV" in html_ok
        assert "lần sàn" in html_ok

        # 2. Trạng thái sập độ rộng (Breadth 25.1%: 83 Tăng / 248 Giảm) -> Toàn bộ cột Tín Hiệu AI chuyển sang NGỪNG MUA MỚI
        out_cb = tmp_path / "hud_cb.html"
        generate_terminal_html(
            output_path=str(out_cb),
            fialda_candidates=[c_normal],
            top_n=1,
            spot_deriv_override={"VN30_INDEX": 1320.0, "VN30F1M": 1318.0, "VNINDEX": 1250.0},
            market_breadth={"advances": 83, "declines": 248, "totalValue": 11241e9},
        )
        html_cb = out_cb.read_text(encoding="utf-8")
        assert "NGỪNG MUA MỚI — QUAN SÁT" in html_cb
        assert 'data-buy-perm="EXTENDED_NO_CHASING"' in html_cb





