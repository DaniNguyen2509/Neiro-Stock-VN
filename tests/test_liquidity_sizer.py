"""Bo kiem thu toan hoc va logic cho Module Liquidity & Capacity Sizer.

Kiem tra:
1. Chuan hoa gia co phieu (normalize_price_vnd).
2. Tinh toan ADTV20 tu cac nguon du lieu khac nhau.
3. Kiem tra nghiem bien bo loc ADTV20 (14.9 ty, 15.0 ty, 30.0 ty).
4. He thong cham diem thanh khoan (Liquidity Score 0 - 100).
5. Tinh toan ham truot gia phi tuyen (Nonlinear Slippage Model) va cac nguong canh bao.
6. Mo hinh suc chua danh muc (Portfolio Capacity Model), quy tac lo 100 va so ngay thoat hang T+2.5.
"""
import pytest
import math
from src.risk_engine.liquidity_sizer import (
    normalize_price_vnd,
    calculate_adtv20,
    is_liquidity_sufficient,
    calculate_liquidity_score,
    estimate_nonlinear_slippage,
    calculate_portfolio_capacity,
    LiquidityMetrics,
    CapacityResult,
)


def test_normalize_price_vnd():
    """Kiem tra chuyen doi gia tu don vi 1,000 VND va VND nguyen ban."""
    assert normalize_price_vnd(20.95) == 20950.0
    assert normalize_price_vnd(57.0) == 57000.0
    assert normalize_price_vnd(25000.0) == 25000.0
    assert normalize_price_vnd(0.0) == 1.0


def test_calculate_adtv20_sources():
    """Kiem tra tinh ADTV20 tu list ty dong, list VND va cap gia/khoi luong."""
    # 1. Tu values_billion (20 phien moi phien 25 ty)
    vals = [25.0] * 20
    assert calculate_adtv20(values_billion=vals) == 25.0

    # Test chi lay toi da 20 phien gan nhat
    vals_30 = [10.0] * 10 + [30.0] * 20
    assert calculate_adtv20(values_billion=vals_30) == 30.0

    # 2. Tu turnover_vnd (20 phien moi phien 50 ty VND)
    vnd_vals = [50e9] * 20
    assert calculate_adtv20(turnover_vnd=vnd_vals) == 50.0

    # 3. Tu prices & volumes
    # 20 phien, gia 20 (20,000 VND), khoi luong 1,000,000 cp -> 20 ty/phien
    prices = [20.0] * 20
    volumes = [1_000_000] * 20
    assert calculate_adtv20(prices=prices, volumes=volumes) == 20.0

    # 4. Tap trong hoac rong
    assert calculate_adtv20() == 0.0
    assert calculate_adtv20(values_billion=[]) == 0.0


def test_adtv20_boundary_filtering():
    """Kiem tra nghiem bien cua bo loc thanh khoan Quỹ."""
    # Duoi nguong toi thieu 15 ty -> Bi loai
    assert is_liquidity_sufficient(14.9, min_threshold_billion=15.0) is False
    assert is_liquidity_sufficient(10.0, min_threshold_billion=15.0) is False

    # Dat nguong toi thieu 15 ty -> Duoc chap nhan
    assert is_liquidity_sufficient(15.0, min_threshold_billion=15.0) is True
    assert is_liquidity_sufficient(20.0, min_threshold_billion=15.0) is True

    # Nguong institutional 30 ty
    assert is_liquidity_sufficient(29.9, min_threshold_billion=30.0) is False
    assert is_liquidity_sufficient(30.0, min_threshold_billion=30.0) is True
    assert is_liquidity_sufficient(120.0, min_threshold_billion=30.0) is True


def test_liquidity_scoring_tiers():
    """Kiem tra he thong tinh diem thanh khoan 0 - 100 theo cac tang."""
    # Khong co thanh khoan
    assert calculate_liquidity_score(0.0) == 0.0

    # Thanh khoan duoi chuan (< 15 ty) -> Diem bat buoc < 60
    score_illiquid = calculate_liquidity_score(10.0)
    assert score_illiquid < 60.0

    # Thanh khoan bien (15 - 30 ty) -> 60 <= diem < 75
    score_borderline = calculate_liquidity_score(20.0)
    assert 60.0 <= score_borderline < 75.0

    # Thanh khoan tot (30 - 70 ty) -> 75 <= diem < 90
    score_good = calculate_liquidity_score(50.0)
    assert 75.0 <= score_good < 90.0

    # Sieu thanh khoan (>= 70 ty) -> >= 90 diem
    score_ultra = calculate_liquidity_score(100.0)
    assert score_ultra >= 90.0

    # Kiem tra anh huong cua chenh lech spread
    score_tight_spread = calculate_liquidity_score(50.0, bid_ask_spread_pct=0.25)
    score_wide_spread = calculate_liquidity_score(50.0, bid_ask_spread_pct=0.80)
    assert score_tight_spread > score_wide_spread


def test_nonlinear_slippage_model():
    """Kiem tra ham truot gia phi tuyen va cac nguong canh bao."""
    adv = 2_000_000 # 2 trieu co phieu / ngay
    spread = 0.25

    # 1. Lenh nho (1% ADV20) -> Truot gia rat nho, muc SAFE
    slip_1pct, lvl_1pct, _ = estimate_nonlinear_slippage(20_000, adv, bid_ask_spread_pct=spread)
    assert lvl_1pct == "SAFE"
    assert slip_1pct > spread

    # 2. Tinh don dieu tang: quy mo lenh tang thi truot gia phai tang nghiem ngat
    slip_5pct, _, _ = estimate_nonlinear_slippage(100_000, adv, bid_ask_spread_pct=spread)
    slip_10pct, lvl_10pct, _ = estimate_nonlinear_slippage(200_000, adv, bid_ask_spread_pct=spread)
    slip_14pct, lvl_14pct, _ = estimate_nonlinear_slippage(280_000, adv, bid_ask_spread_pct=spread)
    slip_20pct, lvl_20pct, msg_20pct = estimate_nonlinear_slippage(400_000, adv, bid_ask_spread_pct=spread)

    assert slip_1pct < slip_5pct < slip_10pct < slip_14pct < slip_20pct
    assert lvl_10pct == "SAFE"
    assert lvl_14pct == "MODERATE"
    assert lvl_20pct == "CRITICAL_OVER_CAPACITY"
    assert "VƯỢT SỨC CHỨA" in msg_20pct

    # 3. Kiem tra canh bao HIGH_SLIPPAGE khi truot gia >= 1.5% nhung ratio <= 15%
    slip_high, lvl_high, msg_high = estimate_nonlinear_slippage(250_000, adv, bid_ask_spread_pct=0.8, k=3.5)
    if slip_high >= 1.50 and (250_000 / adv) <= 0.15:
        assert lvl_high == "HIGH_SLIPPAGE"
        assert "TRƯỢT GIÁ CAO" in msg_high


def test_portfolio_capacity_calculation():
    """Kiem tra mo hinh tinh toan suc chua danh muc cho ma HPG."""
    # HPG gia 20.95 (20,950 VND), ADTV20 = 100 ty
    res = calculate_portfolio_capacity(
        symbol="HPG",
        current_price=20.95,
        adtv20_billion=100.0,
        max_participation_pct=0.10,
        min_adtv_billion=15.0,
    )

    # 1. ADV20 = 100 ty / 20,950 = 4,773,269 cp
    assert res.adv20_shares > 4_700_000
    # 2. Max shares 10% lam tron lo 100
    assert res.max_shares_recommended % 100 == 0
    assert 470_000 <= res.max_shares_recommended <= 480_000
    # 3. Kiem tra trang thai thanh khoan
    assert res.is_liquid is True
    assert res.liquidity_score >= 90.0
    assert res.warning_level == "SAFE"
    # 4. Khi mua dung max_shares_recommended, liquidation days phai la 1.0 ngay
    assert res.liquidation_days_est == 1.0


def test_portfolio_capacity_illiquid_stock():
    """Kiem tra voi co phieu thanh khoan thap bi loai boi bo loc."""
    res = calculate_portfolio_capacity(
        symbol="PENNY",
        current_price=5.0,
        adtv20_billion=4.5, # Chi co 4.5 ty/phien < 15 ty
        min_adtv_billion=15.0,
    )
    assert res.is_liquid is False
    assert res.liquidity_score < 60.0
    assert res.warning_level == "CRITICAL_OVER_CAPACITY"
    assert "LOẠI BỎ KHỎI QUỸ" in res.warning_message


def test_portfolio_capacity_custom_requested_order():
    """Kiem tra khi nguoi dung yeu cau mot khoi luong lenh tuy chinh."""
    # Co phieu VND: ADTV20 = 40 ty, gia 20,000 VND -> ADV20 = 2,000,000 cp
    # Nguoi dung muon mua 500,000 cp (chiem 25% ADV20 -> vuot 15%)
    res = calculate_portfolio_capacity(
        symbol="VND",
        current_price=20.0,
        adtv20_billion=40.0,
        requested_shares=500_000,
        max_participation_pct=0.10,
    )
    assert res.participation_rate_pct == 25.0
    assert res.warning_level == "CRITICAL_OVER_CAPACITY"
    assert res.liquidation_days_est == 2.5 # 500,000 / (2,000,000 * 0.10) = 2.5 ngay
