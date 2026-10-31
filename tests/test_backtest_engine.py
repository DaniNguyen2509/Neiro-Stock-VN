"""Unit Tests toan dien cho Walk-Forward Backtesting Engine T+2.5.

Kiem thu 100% bat bien toan hoc va cac truong hop bien thuc te cua TTCK Viet Nam:
1. Rang buoc T+2.5: Cam ban truoc chieu ngay T+2.
2. Bien do tran/san HOSE (7%), HNX (10%), UPCoM (15%).
3. Khau tru phi moi gioi 0.15% va thue TNCN 0.10%.
4. Point-in-Time Data Engine: Ngan chan nhin truoc BCTC chua cong bo.
5. Cac cong thuc metric Sharpe, Sortino, MDD, CAGR, Win Rate, Profit Factor.
6. Dieu phoi Walk-Forward In-Sample vs Out-of-Sample.
"""

import pytest
import numpy as np
from src.backtesting.models import (
    Exchange,
    PriceBand,
    BacktestConfig,
    TradeRecord,
)
from src.backtesting.engine import T25BacktestEngine
from src.backtesting.point_in_time import PITFinancialSnapshot, PointInTimeDatabase
from src.backtesting.metrics import (
    calculate_win_rate,
    calculate_profit_factor,
    calculate_cagr,
    calculate_max_drawdown,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_calmar_ratio,
    calculate_walk_forward_efficiency,
)
from src.backtesting.walk_forward import WalkForwardCoordinator


def test_t25_lock_prevents_early_sale():
    """Bat bien 1: Co phieu mua phien ngay T bat buoc khong duoc ban tai T+0 va T+1."""
    config = BacktestConfig(initial_capital=100_000_000.0, min_holding_bars=2)
    engine = T25BacktestEngine(config)

    # 1. Mua tai phien index 0 (Ngay T)
    batch = engine.execute_buy(
        symbol="HPG",
        price=28.0,
        date="2023-01-04",
        day_idx=0,
        allocated_capital=20_000_000.0,
    )
    assert batch is not None
    assert engine.positions["HPG"].total_shares > 0

    # 2. Thu ban ngay trong phien mua (day_idx = 0) -> Bi khoa hoan toan
    sell_t0 = engine.execute_sell(symbol="HPG", price=30.0, date="2023-01-04", day_idx=0)
    assert sell_t0 is None
    assert engine.can_sell_shares("HPG", current_day_idx=0) == 0

    # 3. Thu ban tai ngay tiep theo (day_idx = 1 / T+1) -> Van bi khoa
    sell_t1 = engine.execute_sell(symbol="HPG", price=30.0, date="2023-01-05", day_idx=1)
    assert sell_t1 is None
    assert engine.can_sell_shares("HPG", current_day_idx=1) == 0

    # 4. Ban tai chieu ngay T+2 (day_idx = 2) -> Khop lenh thanh cong
    can_sell = engine.can_sell_shares("HPG", current_day_idx=2)
    assert can_sell == batch.shares
    sell_t2 = engine.execute_sell(symbol="HPG", price=30.0, date="2023-01-06", day_idx=2)
    assert sell_t2 is not None
    assert sell_t2.shares == batch.shares
    assert "HPG" not in engine.positions  # Da dong het vi the


def test_exchange_price_bands_and_limits():
    """Bat bien 2: Kiem tra bien do tran/san HOSE (7%), HNX (10%), UPCoM (15%)."""
    # 1. Kiem tra tinh toan bien do
    band_hose = PriceBand.calculate(50.0, Exchange.HOSE)
    assert band_hose.ceiling_price == 53.5
    assert band_hose.floor_price == 46.5

    band_hnx = PriceBand.calculate(50.0, Exchange.HNX)
    assert band_hnx.ceiling_price == 55.0
    assert band_hnx.floor_price == 45.0

    band_upcom = PriceBand.calculate(50.0, Exchange.UPCOM)
    assert band_upcom.ceiling_price == 57.5
    assert band_upcom.floor_price == 42.5

    # 2. Lenh mua vuot tran bi tu choi
    engine = T25BacktestEngine()
    buy_above_ceiling = engine.execute_buy(
        symbol="FPT",
        price=54.0,  # Vuot tran 53.5
        date="2023-01-04",
        day_idx=0,
        exchange=Exchange.HOSE,
        reference_price=50.0,
    )
    assert buy_above_ceiling is None

    # 3. Lenh mua trong bien do duoc chap nhan
    buy_valid = engine.execute_buy(
        symbol="FPT",
        price=52.0,
        date="2023-01-04",
        day_idx=0,
        exchange=Exchange.HOSE,
        reference_price=50.0,
    )
    assert buy_valid is not None

    # 4. Lenh ban duoi san bi tu choi (trang ben mua)
    sell_below_floor = engine.execute_sell(
        symbol="FPT",
        price=45.0,  # Duoi san 46.5
        date="2023-01-08",
        day_idx=3,
        exchange=Exchange.HOSE,
        reference_price=50.0,
    )
    assert sell_below_floor is None


def test_fees_and_taxes_deduction():
    """Bat bien 3: Tinh toan chinh xac phi mua (0.15%), phi ban (0.15%) va thue ban (0.10%)."""
    config = BacktestConfig(
        initial_capital=100_000_000.0,
        buy_fee_pct=0.0015,
        sell_fee_pct=0.0015,
        sell_tax_pct=0.0010,
    )
    engine = T25BacktestEngine(config)

    # Mua 1,000 co phieu gia 50,000 VND (Gia tri = 50,000,000)
    batch = engine.execute_buy(
        symbol="SSI",
        price=50.0,
        date="2023-01-04",
        day_idx=0,
        allocated_capital=50_080_000.0,
    )
    assert batch is not None
    gross_buy = batch.shares * 50.0
    expected_buy_fee = gross_buy * 0.0015
    assert batch.buy_fee == pytest.approx(expected_buy_fee, rel=1e-3)
    assert engine.cash == pytest.approx(100_000_000.0 - (gross_buy + expected_buy_fee), rel=1e-3)

    # Ban toan bo tai gia 55,000 VND vao day_idx = 2
    trade = engine.execute_sell(
        symbol="SSI",
        price=55.0,
        date="2023-01-06",
        day_idx=2,
    )
    assert trade is not None
    gross_sell = batch.shares * 55.0
    expected_sell_fee = gross_sell * 0.0015
    expected_sell_tax = gross_sell * 0.0010
    expected_net_proceeds = gross_sell - expected_sell_fee - expected_sell_tax

    assert trade.sell_fee == pytest.approx(expected_sell_fee, rel=1e-3)
    assert trade.sell_tax == pytest.approx(expected_sell_tax, rel=1e-3)
    assert trade.net_pnl == pytest.approx(expected_net_proceeds - (gross_buy + expected_buy_fee), rel=1e-3)


def test_point_in_time_database_prevents_bias():
    """Bat bien 4: Point-in-Time Engine ngan chan triet de nhin truoc BCTC."""
    pit = PointInTimeDatabase()
    # BCTC Q1/2023 chot 2023-03-31 nhung den 2023-04-28 moi cong bo
    pit.add_snapshot(PITFinancialSnapshot(
        symbol="HPG", year=2023, quarter=1,
        period_end_date="2023-03-31", filing_date="2023-04-28",
        f_score=8, cfo_ni_ratio=1.5
    ))

    # Kiem tra tai ngay 2023-04-15 (chua den han cong bo) -> Phai tra ve None
    snap_before = pit.get_latest_financial("HPG", "2023-04-15")
    assert snap_before is None
    assert pit.is_quantamental_qualified("HPG", "2023-04-15") is False

    # Kiem tra tai ngay 2023-04-29 (sau khi da cong bo) -> Tra ve snapshot hop le
    snap_after = pit.get_latest_financial("HPG", "2023-04-29")
    assert snap_after is not None
    assert snap_after.f_score == 8
    assert pit.is_quantamental_qualified("HPG", "2023-04-29") is True


def test_mathematical_metrics_invariants():
    """Bat bien 5: Tinh toan Sharpe, Sortino, MDD, CAGR, Win Rate, Profit Factor."""
    # 1. Win Rate & Profit Factor
    trades = [
        TradeRecord(1, "A", "2023-01", "2023-01", 10.0, 12.0, 1000, 15, 18, 12, 2000, 1955, 19.5, 5),
        TradeRecord(2, "B", "2023-02", "2023-02", 20.0, 22.0, 1000, 30, 33, 22, 2000, 1915, 9.5, 4),
        TradeRecord(3, "C", "2023-03", "2023-03", 15.0, 14.0, 1000, 22, 21, 14, -1000, -1057, -7.0, 3),
    ]
    assert calculate_win_rate(trades) == 66.67  # 2/3 = 66.67%
    # Profit Factor = (1955 + 1915) / 1057 = 3870 / 1057 = 3.66
    assert calculate_profit_factor(trades) == pytest.approx(3.66, abs=0.02)

    # 2. CAGR
    # 100 -> 144 trong 2 nam = sqrt(1.44) - 1 = 20%
    assert calculate_cagr(100.0, 144.0, 2.0) == 20.0

    # 3. Max Drawdown
    equity = [100.0, 120.0, 110.0, 90.0, 105.0, 130.0]
    # Peak = 120, day = 90 -> (120 - 90) / 120 = 25.0%
    assert calculate_max_drawdown(equity) == 25.0

    # 4. Calmar Ratio
    assert calculate_calmar_ratio(25.0, 12.5) == 2.0

    # 5. Sharpe & Sortino voi chuoi return duong on dinh
    daily_rets = [0.005] * 50  # Loi nhuan deu dan, std gan bang 0
    # Khi std = 0, ham tra ve an toan 0.0 thay vi crash ZeroDivisionError
    assert calculate_sharpe_ratio(daily_rets) == 0.0

    # Chuoi return bien dong
    rng = np.random.RandomState(42)
    varied_rets = (rng.normal(0.001, 0.01, 100)).tolist()
    sharpe = calculate_sharpe_ratio(varied_rets)
    sortino = calculate_sortino_ratio(varied_rets)
    assert isinstance(sharpe, float)
    assert isinstance(sortino, float)


def test_walk_forward_coordinator_execution():
    """Bat bien 6: Chay hoan chinh bo Walk-Forward tu 2021 den 2026."""
    coordinator = WalkForwardCoordinator()
    wf_results = coordinator.run_full_walk_forward()

    assert "in_sample" in wf_results
    assert "out_of_sample" in wf_results
    assert "full" in wf_results

    res_is = wf_results["in_sample"]
    res_oos = wf_results["out_of_sample"]
    res_full = wf_results["full"]

    # Kiem tra ket qua In-Sample (2021-2023)
    assert res_is.total_trades > 0
    assert len(res_is.equity_curve) > 0
    assert res_is.final_equity > 0

    # Kiem tra ket qua Out-of-Sample (2024-2026)
    assert res_oos.total_trades > 0
    assert len(res_oos.equity_curve) > 0
    assert res_oos.final_equity > 0

    # Kiem tra Walk-Forward Efficiency
    wfe = wf_results["walk_forward_efficiency_pct"]
    assert isinstance(wfe, float)

    # Kiem tra toan bo giao dich deu thoa man T+2.5 (holding_days >= 2)
    for t in res_full.trades:
        assert t.holding_days >= 2


def test_floor_lock_consecutive_t2_t3_limit_down_liquidates_on_t4():
    """BM-08 Scorecard: Mua T0 -> T+2 va T+3 nam san trang ben mua (close == floor_price) -> T+4 moi tat toan duoc."""
    from src.backtesting.models import MarketBar

    cfg = BacktestConfig(initial_capital=100_000_000.0, min_holding_bars=2)
    engine = T25BacktestEngine(cfg)

    batch = engine.execute_buy(
        symbol="DIG",
        price=20.00,
        date="2026-10-26",
        day_idx=0,
        exchange=Exchange.HOSE,
        allocated_capital=20_000_000.0,
        reference_price=20.00,
    )
    assert batch is not None
    stop_loss = 18.80  # -6.0%

    # T+2: Tham chieu 18.60 -> San HOSE = 17.30, dong cua nam san cung 17.30 -> Khong the khop ban!
    bar_t2 = MarketBar("DIG", "2026-10-28", 17.60, 17.60, 17.30, 17.30, 150_000, reference_price=18.60, exchange=Exchange.HOSE)
    assert engine.check_and_execute_stop_loss("DIG", bar_t2, day_idx=2, stop_loss_price=stop_loss) is None

    # T+3: Tham chieu 17.30 -> San HOSE = 16.09, tiep tuc nam san trang ben mua 16.09 -> Van ket hang!
    bar_t3 = MarketBar("DIG", "2026-10-29", 16.09, 16.09, 16.09, 16.09, 80_000, reference_price=17.30, exchange=Exchange.HOSE)
    assert engine.check_and_execute_stop_loss("DIG", bar_t3, day_idx=3, stop_loss_price=stop_loss) is None
    assert engine.floor_lock_blocked_count == 2
    assert "DIG" in engine.positions

    # T+4: Co cau giai cuu tai 15.80 (tren gia san 14.96 cua ref 16.09) -> Tat toan thuc te tai 15.80!
    bar_t4 = MarketBar("DIG", "2026-10-30", 15.80, 16.20, 15.50, 16.00, 12_000_000, reference_price=16.09, exchange=Exchange.HOSE)
    trade = engine.check_and_execute_stop_loss("DIG", bar_t4, day_idx=4, stop_loss_price=stop_loss)
    assert trade is not None
    assert trade.exit_price == 15.80
    assert trade.holding_days == 4
    assert trade.return_pct < -20.0

