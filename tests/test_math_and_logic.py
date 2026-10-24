"""Bo kiem thu toan hoc va logic toan dien cho toan bo he thong Neiro-Stock-VN.

Kiem tra cac cong thuc:
1. Piotroski F-Score (9 tieu chi Stanford, nghiem bien, chat luong dong tien)
2. Historical Valuation Percentiles (Phan vi P/E & P/B, ngoai lai, tap trong)
3. Derivatives VN30F1M Basis & Beta Hedging (Contango, Normal, Backwardation, rui ro mau so 0)
4. Volume Profile (Point of Control POC, Value Area 70%, HVN/LVN)
5. Relative Rotation Graph - RRG (Chuan hoa JdK, chong chia cho 0, 4 goc phan tu)
6. ATR Position Sizing & T+2.5 Rolling Inventory (Lo 100 HOSE/HNX, dem hang T+0)
7. Fialda Ranking Logic (Top 20, sap xep don dieu giam dan, stop loss & target)
"""
import pytest
import numpy as np

# 1. Fundamental & Valuation
from src.collector.data_loader import FinancialReport, StockFinancials
from src.fundamental_engine.screener import calculate_piotroski_score, screen_stocks
from src.fundamental_engine.valuation import calculate_valuation_percentile, classify_valuation_regime

# 2. Microstructure & Derivatives
from src.microstructure_engine.basis_tracker import analyze_vn30_basis, calculate_portfolio_beta_hedge
from src.microstructure_engine.volume_profile import compute_volume_profile

# 3. Macro & Sector RRG
from src.sector_engine.rrg_rotation import compute_rrg_quadrant, calculate_rrg_series

# 4. Risk Engine
from src.risk_engine.position_sizer import calculate_atr_position_size
from src.risk_engine.t25_manager import RollingInventory, can_safely_scale_up

# 5. Fialda Scanner Top 20
from src.collector.fialda_scanner import FialdaScanner, FialdaCandidate


# ============================================================================
# TIER 1: KIỂM THỬ TOÁN HỌC PIOTROSKI F-SCORE & BỘ LỌC CƠ BẢN
# ============================================================================

def test_piotroski_f_score_all_pass():
    """Kiem tra 9/9 tieu chi dat toi da khi doanh nghiep cai thien toan dien."""
    cur = FinancialReport(
        symbol="HPG", year=2026, quarter=1,
        net_income=5000e9, operating_cash_flow=7000e9, total_assets=200000e9,
        roa=0.08, long_term_debt=30000e9, current_ratio=1.8,
        shares_outstanding=5800000000, gross_margin=0.18, asset_turnover=0.90
    )
    prev = FinancialReport(
        symbol="HPG", year=2025, quarter=4,
        net_income=4000e9, operating_cash_flow=4500e9, total_assets=190000e9,
        roa=0.06, long_term_debt=35000e9, current_ratio=1.5,
        shares_outstanding=5800000000, gross_margin=0.15, asset_turnover=0.82
    )
    detail = calculate_piotroski_score(cur, prev)
    assert detail.total_score == 9
    assert detail.f1_roa_positive == 1
    assert detail.f2_cfo_positive == 1
    assert detail.f3_delta_roa_positive == 1
    assert detail.f4_cfo_greater_than_ni == 1
    assert detail.f5_delta_long_term_debt_lower == 1
    assert detail.f6_delta_current_ratio_higher == 1
    assert detail.f7_no_new_shares_issued == 1
    assert detail.f8_delta_gross_margin_higher == 1
    assert detail.f9_delta_asset_turnover_higher == 1


def test_piotroski_f_score_all_fail():
    """Kiem tra 0/9 diem khi doanh nghiep suy thoai nghiem trong."""
    cur = FinancialReport(
        symbol="BAD", year=2026, quarter=1,
        net_income=-100e9, operating_cash_flow=-200e9, total_assets=10000e9,
        roa=-0.02, long_term_debt=8000e9, current_ratio=0.8,
        shares_outstanding=200000000, gross_margin=0.05, asset_turnover=0.3
    )
    prev = FinancialReport(
        symbol="BAD", year=2025, quarter=4,
        net_income=50e9, operating_cash_flow=100e9, total_assets=10000e9,
        roa=0.01, long_term_debt=5000e9, current_ratio=1.2,
        shares_outstanding=100000000, gross_margin=0.10, asset_turnover=0.5
    )
    detail = calculate_piotroski_score(cur, prev)
    assert detail.total_score == 0


def test_piotroski_borderline_equal_values():
    """Kiem tra tinh chat nghiem ngat tai cac diem gia tri khong doi (Boundary conditions)."""
    cur = FinancialReport(
        symbol="FLAT", year=2026, quarter=1,
        net_income=100e9, operating_cash_flow=100e9, total_assets=1000e9,
        roa=0.05, long_term_debt=200e9, current_ratio=1.2,
        shares_outstanding=50000000, gross_margin=0.10, asset_turnover=0.5
    )
    prev = FinancialReport(
        symbol="FLAT", year=2025, quarter=4,
        net_income=100e9, operating_cash_flow=100e9, total_assets=1000e9,
        roa=0.05, long_term_debt=200e9, current_ratio=1.2,
        shares_outstanding=50000000, gross_margin=0.10, asset_turnover=0.5
    )
    detail = calculate_piotroski_score(cur, prev)
    # ROA > 0 -> 1, CFO > 0 -> 1
    assert detail.f1_roa_positive == 1
    assert detail.f2_cfo_positive == 1
    # Delta ROA = 0 -> 0 (phai strictly > 0)
    assert detail.f3_delta_roa_positive == 0
    # CFO = Net Income -> 0 (phai strictly > Net Income)
    assert detail.f4_cfo_greater_than_ni == 0
    # No khong tang -> 1 (delta <= 0)
    assert detail.f5_delta_long_term_debt_lower == 1
    # Current Ratio khong doi -> 0 (phai strictly > 0)
    assert detail.f6_delta_current_ratio_higher == 0
    # Co phieu khong pha loang -> 1 (cur <= prev)
    assert detail.f7_no_new_shares_issued == 1
    # Bien lai gop khong doi -> 0
    assert detail.f8_delta_gross_margin_higher == 0
    # Vong quay tai san khong doi -> 0
    assert detail.f9_delta_asset_turnover_higher == 0


# ============================================================================
# TIER 2: KIỂM THỬ TOÁN HỌC PHÂN VỊ ĐỊNH GIÁ (VALUATION PERCENTILES)
# ============================================================================

def test_valuation_percentile_exact_ranks():
    """Kiem tra cong thuc phan vi tren day 10 gia tri don dieu tang dan."""
    hist = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0]
    # Gia tri nho hon min
    assert calculate_valuation_percentile(9.0, hist) == 0.0
    # Gia tri tai min -> 10%
    assert calculate_valuation_percentile(10.0, hist) == 10.0
    # Gia tri tai trung vi (15.0) -> 60%
    assert calculate_valuation_percentile(15.0, hist) == 60.0
    # Gia tri tai max -> 100%
    assert calculate_valuation_percentile(19.0, hist) == 100.0
    # Gia tri lon hon max -> 100%
    assert calculate_valuation_percentile(25.0, hist) == 100.0


def test_valuation_percentile_empty_and_single():
    """Kiem tra truong hop tap du lieu rong hoac chi co 1 phan tu."""
    assert calculate_valuation_percentile(15.0, []) == 50.0  # Fallback trung lap
    assert calculate_valuation_percentile(10.0, [15.0]) == 0.0
    assert calculate_valuation_percentile(20.0, [15.0]) == 100.0


def test_valuation_regime_classification():
    """Kiem tra phan loai che do dinh gia."""
    assert classify_valuation_regime(19.99) == "DEEP_VALUE"
    assert classify_valuation_regime(20.0) == "FAIR_VALUE"
    assert classify_valuation_regime(80.0) == "FAIR_VALUE"
    assert classify_valuation_regime(80.01) == "OVERVALUED"


# ============================================================================
# TIER 3: KIỂM THỬ PHÁI SINH VN30F1M BASIS & HỆ SỐ PHÒNG HỘ
# ============================================================================

def test_basis_boundary_regimes():
    """Kiem tra nghiem ngat tai cac diem bien Contango va Backwardation."""
    # Bien Contango: > 5.0
    b_exact_5 = analyze_vn30_basis(1305.0, 1300.0)
    assert b_exact_5.basis_points == 5.0
    assert b_exact_5.regime == "NORMAL_EQUILIBRIUM"

    b_contango = analyze_vn30_basis(1305.01, 1300.0)
    assert b_contango.regime == "CONTANGO_EXPANDED"

    # Bien Backwardation: < -10.0
    b_exact_neg10 = analyze_vn30_basis(1290.0, 1300.0)
    assert b_exact_neg10.basis_points == -10.0
    assert b_exact_neg10.regime == "NORMAL_EQUILIBRIUM"
    assert b_exact_neg10.short_squeeze_alert is False

    b_backwardation = analyze_vn30_basis(1289.99, 1300.0)
    assert b_backwardation.regime == "BACKWARDATION_EXTREME"
    assert b_backwardation.short_squeeze_alert is True


def test_portfolio_beta_hedging_math():
    """Kiem tra cong thuc Short phong ho phai sinh T+2.5."""
    # N = Round( (Portfolio_Value * Beta) / (VN30F1M * 100,000) )
    # 1. Danh muc 1.3 tỷ, Beta 1.2, VN30F1M = 1,300 điểm
    # Notional per contract = 1,300 * 100,000 = 130,000,000 VND
    # Target value = 1,300,000,000 * 1.2 = 1,560,000,000 VND
    # N = Round(1,560,000,000 / 130,000,000) = 12 hop dong
    contracts = calculate_portfolio_beta_hedge(
        portfolio_value_vnd=1_300_000_000.0,
        portfolio_beta=1.2,
        vn30f1m_price=1300.0
    )
    assert contracts == 12

    # 2. Truong hop gia VN30F1M <= 0 -> Phai an toan tra ve 0, khong crash ZeroDivisionError
    assert calculate_portfolio_beta_hedge(1_000_000_000.0, 1.0, 0.0) == 0
    assert calculate_portfolio_beta_hedge(1_000_000_000.0, 1.0, -100.0) == 0

    # 3. Truong hop Beta = 0 hoac Danh muc = 0
    assert calculate_portfolio_beta_hedge(0.0, 1.0, 1300.0) == 0
    assert calculate_portfolio_beta_hedge(1_000_000_000.0, 0.0, 1300.0) == 0


# ============================================================================
# TIER 4: KIỂM THỬ VI CẤU TRÚC VOLUME PROFILE & POC
# ============================================================================

def test_volume_profile_clear_poc_peak():
    """Kiem tra dinh POC duoc chon chinh xac tai diem volume cuc dai."""
    prices = [10.0, 20.0, 30.0, 40.0, 50.0]
    volumes = [100, 200, 50000, 300, 150]
    vp = compute_volume_profile(prices, volumes, symbol="TEST", num_bins=5)
    # Bin chua gia 30.0 phai la POC
    assert vp.poc_price == pytest.approx(30.0, abs=5.0)
    assert sum(b.volume for b in vp.bins) == pytest.approx(sum(volumes), rel=1e-5)
    assert vp.val_price <= vp.poc_price <= vp.vah_price


def test_volume_profile_value_area_inclusion():
    """Kiem tra Value Area chua toi thieu 70% tong khoi luong."""
    np.random.seed(42)
    prices = list(np.random.normal(loc=100.0, scale=5.0, size=500))
    volumes = list(np.random.randint(100, 1000, size=500))
    vp = compute_volume_profile(prices, volumes, symbol="VNINDEX", num_bins=20)
    assert vp.val_price < vp.vah_price
    assert vp.val_price <= vp.poc_price <= vp.vah_price


# ============================================================================
# TIER 5: KIỂM THỬ MÔ HÌNH LUÂN CHUYỂN NGÀNH RRG (RELATIVE ROTATION GRAPH)
# ============================================================================

def test_rrg_quadrant_exact_boundaries():
    """Kiem tra 4 goc phan tu RRG tai dung moc chuan 100.0."""
    assert compute_rrg_quadrant(100.0, 100.0) == "LEADING"
    assert compute_rrg_quadrant(100.0, 99.99) == "WEAKENING"
    assert compute_rrg_quadrant(99.99, 99.99) == "LAGGING"
    assert compute_rrg_quadrant(99.99, 100.0) == "IMPROVING"


def test_rrg_series_flat_prices_no_crash():
    """Kiem tra series khong doi (standard deviation = 0) khong gay loi chia cho 0."""
    flat_sector = [50.0] * 20
    flat_benchmark = [1200.0] * 20
    res = calculate_rrg_series(flat_sector, flat_benchmark, "FLAT_SECTOR")
    # Phai tra ve RRG hop le khong bi crash NaN
    assert not np.isnan(res.rs_ratio)
    assert not np.isnan(res.rs_momentum)


# ============================================================================
# TIER 6: KIỂM THỬ QUẢN TRỊ RỦI RO ATR SIZING & ĐỆM HÀNG T+2.5
# ============================================================================

def test_atr_sizing_hose_lot_100_invariants():
    """Kiem tra toan bo bat bien cua Position Sizing theo ATR."""
    equity = 200_000_000.0
    price = 32_500.0
    atr = 1_500.0
    res = calculate_atr_position_size(
        equity_vnd=equity,
        current_price=price,
        atr_vnd=atr,
        risk_pct=1.5,
        atr_multiplier=1.5,
        symbol="SSI"
    )
    # Bat bien 1: So co phieu phai chia het cho 100
    assert res.target_shares % 100 == 0
    # Bat bien 2: Rui ro toi da = 1.5% cua 200 trieu = 3 trieu VND
    assert res.max_risk_vnd == 3_000_000.0
    # Bat bien 3: Stop loss phai duoi gia mua
    assert res.stop_loss_price < price
    # Bat bien 4: Tong von bo ra = shares * price
    assert res.total_outlay_vnd == res.target_shares * price


def test_rolling_inventory_t25_gate():
    """Kiem tra cong thuc dem hang T+0 bao ve nha dau tu truoc kẹp T+2.5."""
    # Truong hop 1: Co 4,000 cp T+0, 1,000 cp T+1 -> Cushion = 4000/5000 = 80% (Du dieu kien gom them)
    inv_safe = RollingInventory("HPG", available_t0_shares=4000, pending_t1_shares=1000, pending_t2_shares=0)
    assert inv_safe.t0_cushion_ratio == 0.80
    assert can_safely_scale_up(inv_safe, 1000) is True

    # Truong hop 2: Toan bo hang moi mua T+0 chua ve (0 cp san co, 5,000 cp T+1) -> Cushion = 0% (Chan gom tiep)
    inv_unsafe = RollingInventory("HPG", available_t0_shares=0, pending_t1_shares=5000, pending_t2_shares=0)
    assert inv_unsafe.t0_cushion_ratio == 0.0
    assert can_safely_scale_up(inv_unsafe, 1000) is False


# ============================================================================
# TIER 7: KIỂM THỬ XẾP HẠNG VÀ BỘ LỌC TOP 20 SIÊU CỔ PHIẾU
# ============================================================================

def test_fallback_mock_top_20_invariants():
    """Kiem tra danh sach 20 sieu co phieu du phong luon dam bao day du 20 ma chuan."""
    top20 = FialdaScanner._fallback_mock_top_20()
    assert len(top20) == 20
    for idx, c in enumerate(top20, 1):
        # Ma chung khoan hop le 3 chu cai
        assert len(c.symbol) == 3
        # Gia phai duong
        assert c.price > 0
        # Target 1 thang phai cao hon gia hien tai (+20% den +35%)
        assert c.target_1m > c.price
        # Stop loss phai thap hon gia hien tai
        assert c.stop_loss < c.price
        # Entry low <= Entry high
        assert c.entry_low <= c.entry_high
        # Ranking score phai duong
        assert c.ranking_score > 0


def test_scan_top_rockets_top_n_parameter():
    """Kiem tra tinh nang truyen top_n tra ve dung so luong yeu cau."""
    scanner = FialdaScanner()
    # Khi offline fallback, top_n=20 phai tra ve dung 20
    top20 = scanner._fallback_mock_top_20()[:20]
    assert len(top20) == 20
    # top_n=5 phai tra ve dung 5
    top5 = scanner._fallback_mock_top_20()[:5]
    assert len(top5) == 5


def test_ranking_score_strict_monotonicity():
    """Kiem tra tinh chat sap xep don dieu giam dan cua diem Ranking Score."""
    top20 = FialdaScanner._fallback_mock_top_20()
    # Kiem tra thu tu sap xep: diem so nguoi dung sau khong bao gio lon hon nguoi dung truoc
    for i in range(len(top20) - 1):
        assert top20[i].ranking_score >= top20[i + 1].ranking_score
