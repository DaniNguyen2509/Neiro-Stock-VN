"""Unit tests kiểm thử logic toán học Module Quản Trị Rủi Ro Động & Thoát Lệnh T+2.5."""

import pytest
from src.risk_engine.trailing_stop import (
    TrailingStopState,
    T25ExposureReport,
    calculate_initial_stop_loss,
    calculate_take_profit_levels,
    initialize_trailing_stop,
    update_trailing_stop,
    evaluate_t25_exposure,
)


class TestInitialStopLoss:
    """Kiểm thử tính toán Initial Stop Loss."""

    def test_initial_stop_loss_with_swing_low(self):
        # Entry 50.0, swing low 47.5, ATR 1.5 -> atr_stop = 50 - 1.5*1.5 = 47.75
        # chosen_stop = max(47.5, 47.75) = 47.75 (lo 4.5%, nam trong bien 3%-7%)
        sl = calculate_initial_stop_loss(
            entry_price=50.0,
            swing_low=47.5,
            atr_14=1.5,
            atr_multiplier=1.5,
        )
        assert sl == 47.75
        assert 50.0 * 0.93 <= sl <= 50.0 * 0.97

    def test_initial_stop_loss_clamped_to_min_risk(self):
        # Neu swing low qua sat gia vao (vi du 49.5 -> chi lo 1%), phai bi clamp boi min_risk_pct = 3%
        sl = calculate_initial_stop_loss(
            entry_price=50.0,
            swing_low=49.5,
            atr_14=0.2,
            atr_multiplier=1.0,
            min_risk_pct=0.03,
            max_risk_pct=0.07,
        )
        # 50 * (1 - 0.03) = 48.5
        assert sl == 48.5

    def test_initial_stop_loss_clamped_to_max_risk(self):
        # Neu swing low qua xa (vi du 42.0 -> lo 16%), phai bi clamp boi max_risk_pct = 7%
        sl = calculate_initial_stop_loss(
            entry_price=50.0,
            swing_low=42.0,
            atr_14=3.0,
            atr_multiplier=2.0,
            min_risk_pct=0.03,
            max_risk_pct=0.07,
        )
        # 50 * (1 - 0.07) = 46.5
        assert sl == 46.5

    def test_invalid_entry_price_raises_error(self):
        with pytest.raises(ValueError):
            calculate_initial_stop_loss(entry_price=0.0)


class TestTakeProfitLevels:
    """Kiểm thử tính toán Take Profit & Risk/Reward Ratio."""

    def test_tp_levels_and_rr_ratio(self):
        entry = 100.0
        sl = 95.0  # R = 5.0
        tp1, tp2, rr = calculate_take_profit_levels(
            entry_price=entry,
            stop_loss=sl,
            tp1_r_multiple=1.5,
            tp2_r_multiple=2.5,
        )
        # TP1 = 100 + 1.5 * 5 = 107.5
        assert tp1 == 107.5
        # TP2 = 100 + 2.5 * 5 = 112.5
        assert tp2 == 112.5
        # R:R = (112.5 - 100) / 5 = 2.5
        assert rr == 2.5
        assert rr >= 2.5

    def test_invalid_sl_raises_error(self):
        with pytest.raises(ValueError):
            calculate_take_profit_levels(entry_price=100.0, stop_loss=105.0)


class TestTrailingStopEngine:
    """Kiểm thử Chandelier Exit, Break-even & Ratchet Invariant."""

    def test_breakeven_trigger_at_1_5r(self):
        # Entry 100, SL 95 -> R = 5, TP1 = 107.5, TP2 = 112.5
        state = initialize_trailing_stop(
            symbol="HPG",
            entry_price=100.0,
            swing_low=95.0,
            atr_14=3.33,  # R = 5
        )
        assert state.current_stop == 95.0
        assert not state.is_breakeven_activated

        # Gia tang nhe len 103 (+0.6R) -> chua kich hoat break-even
        s1 = update_trailing_stop(state, current_price=103.0)
        assert s1.current_stop == 95.0
        assert not s1.is_breakeven_activated
        assert s1.status == "ACTIVE"

        # Gia tang vuot 107.5 (+1.5R) -> Tu dong nang len Hoa Von (100.0)
        s2 = update_trailing_stop(s1, current_price=108.0)
        assert s2.is_breakeven_activated
        assert s2.current_stop >= 100.0
        assert s2.status in ("TAKE_PROFIT_1", "ACTIVE")

    def test_ratchet_invariant_never_decreases(self):
        # Test tinh chat bat bien: Stop Loss tuyet doi khong bao gio bi ha xuong
        state = initialize_trailing_stop(
            symbol="SSI",
            entry_price=30.0,
            swing_low=28.5,  # R = 1.5
            atr_14=1.0,
        )
        # Gia bứt phá len 35.0 (R gain = 5.0 / 1.5 = +3.33R)
        s_peak = update_trailing_stop(state, current_price=35.0, chandelier_multiplier=2.0)
        highest_stop = s_peak.current_stop
        assert highest_stop >= 30.0  # Da vuot qua ca hoa von

        # Phien sau gia rung lac giat nguoc xuong 33.5 -> Stop loss khong duoc giam
        s_pullback = update_trailing_stop(s_peak, current_price=33.5)
        assert s_pullback.current_stop == highest_stop
        assert s_pullback.current_stop >= 30.0

    def test_stopped_out_trigger(self):
        state = initialize_trailing_stop(
            symbol="MWG",
            entry_price=60.0,
            swing_low=57.0,  # SL = 57.0
            atr_14=2.0,
        )
        # Gia roi xuong 56.5 duoi SL -> STOPPED_OUT
        s_exit = update_trailing_stop(state, current_price=56.5)
        assert s_exit.status == "STOPPED_OUT"


class TestT25ExposureEvaluation:
    """Kiểm thử Đánh giá Phơi nhiễm Vùng Đóng Băng T+2.5 cho Cổ phiếu."""

    def test_frozen_stage_with_critical_basis(self):
        # Hang T+0, phai sinh am sau -15 diem -> CRITICAL
        report = evaluate_t25_exposure(
            symbol="VHM",
            shares=50_000,
            t_stage="T+0",
            basis_points=-15.0,
            market_breadth_pct=35.0,
        )
        assert report.is_frozen is True
        assert report.exposure_level == "CRITICAL"
        assert report.pause_new_buying is True
        assert report.recommended_cash_pct >= 60.0
        assert "Tuyệt đối KHÔNG mở mua mới" in report.action_message

    def test_frozen_stage_with_safe_market(self):
        # Hang T+1 nhung thi truong tot (Basis +3.5) -> SAFE
        report = evaluate_t25_exposure(
            symbol="FPT",
            shares=20_000,
            t_stage="T+1",
            basis_points=3.5,
            market_breadth_pct=75.0,
        )
        assert report.is_frozen is True
        assert report.exposure_level == "SAFE"
        assert report.pause_new_buying is False
        assert "VÙNG MUA AN TOÀN" in report.action_message

    def test_available_stage_afternoon_t2(self):
        # Hang da ve tai khoan chieu T+2 -> Khong con dong bang
        report = evaluate_t25_exposure(
            symbol="TCB",
            shares=30_000,
            t_stage="T+2_AFTERNOON",
            basis_points=-5.0,
        )
        assert report.is_frozen is False
        assert report.exposure_level == "SAFE"
        assert report.pause_new_buying is False
        assert "HÀNG ĐÃ VỀ KHẢ DỤNG" in report.action_message
