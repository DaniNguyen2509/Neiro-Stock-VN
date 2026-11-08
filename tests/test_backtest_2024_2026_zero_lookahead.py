"""Kiểm định Toán học Chống Nhìn Trước Dữ Liệu (Zero Look-Ahead Proof) cho Giai đoạn 2024 - 2026.

Kiểm chứng 4 bất biến tối cao:
1. Strict Causal Truncation Proof: Cắt cụt dữ liệu tại t_mid cho kết quả NAV và danh sách lệnh 100% trùng khớp.
2. Point-in-Time BCTC Invariant: Không đọc BCTC trước ngày công bố chính thức (filing_date).
3. Ràng buộc T+2.5, Khóa sàn trắng bên mua, True Low Stop Loss & Time-Stop T+7 (ADR-024).
4. Khả năng phân rã và đo lường độc lập từng năm 2024, 2025, 2026 và toàn kỳ 3 năm.
"""

import pytest
from src.backtesting.models import BacktestConfig, Exchange, MarketBar
from src.backtesting.historical_data import (
    generate_benchmark_market_data,
    fetch_real_historical_market_data_2024_2026,
)
from src.backtesting.walk_forward import WalkForwardCoordinator, format_backtest_report_text
from src.backtesting.point_in_time import PointInTimeDatabase, PITFinancialSnapshot


def test_strict_causal_truncation_proof():
    """Bất biến 1 (Toán học): Strict Causal Truncation Proof.

    Nếu thuật toán thực sự là nhân quả (Causal, 0% Look-ahead bias):
    Chạy mô phỏng từ start_idx đến mid_idx trên dữ liệu bị cắt cụt tại mid_idx
    phải cho kết quả Lệnh Khớp và NAV hoàn toàn TRÙNG KHỚP 100% với khi chạy
    trên dữ liệu kéo dài đến tận cuối kỳ end_idx.
    """
    stocks, idx_bars, pit = generate_benchmark_market_data()

    # Xác định điểm đầu năm 2024 và điểm giữa kỳ 2025
    dates = [b.date for b in idx_bars]
    start_2024 = next(i for i, d in enumerate(dates) if d.startswith("2024-"))
    mid_2025 = start_2024 + 180  # Giữa năm 2025
    end_all = len(dates)

    cfg = BacktestConfig(initial_capital=1_000_000_000.0, enable_time_stop_t7=True)

    # 1. Chạy trên toàn bộ dữ liệu đến cuối kỳ
    coord_full = WalkForwardCoordinator(
        config=cfg,
        stock_bars_dict=stocks,
        vnindex_bars=idx_bars,
        pit_db=pit,
    )
    res_full_sliced = coord_full.run_simulation(start_2024, mid_2025, period_label="FULL_RUN_TO_MID")

    # 2. Cắt cụt toàn bộ dữ liệu tại đúng mid_2025 (không cho engine nhìn thấy bất kỳ bar nào sau mid_2025)
    truncated_stocks = {s: bars[:mid_2025] for s, bars in stocks.items()}
    truncated_idx = idx_bars[:mid_2025]

    coord_truncated = WalkForwardCoordinator(
        config=cfg,
        stock_bars_dict=truncated_stocks,
        vnindex_bars=truncated_idx,
        pit_db=pit,
    )
    res_truncated = coord_truncated.run_simulation(start_2024, mid_2025, period_label="TRUNCATED_RUN")

    # 3. So sánh đối chiếu từng lệnh khớp và từng giá trị NAV
    assert len(res_full_sliced.trades) == len(res_truncated.trades), "Số lượng lệnh khớp phải giống hệt nhau"
    for t_full, t_trunc in zip(res_full_sliced.trades, res_truncated.trades):
        assert t_full.symbol == t_trunc.symbol
        assert t_full.entry_date == t_trunc.entry_date
        assert t_full.exit_date == t_trunc.exit_date
        assert t_full.entry_price == pytest.approx(t_trunc.entry_price, rel=1e-4)
        assert t_full.exit_price == pytest.approx(t_trunc.exit_price, rel=1e-4)
        assert t_full.net_pnl == pytest.approx(t_trunc.net_pnl, rel=1e-4)
        assert t_full.reason == t_trunc.reason

    assert len(res_full_sliced.equity_curve) == len(res_truncated.equity_curve)
    for eq_full, eq_trunc in zip(res_full_sliced.equity_curve, res_truncated.equity_curve):
        assert eq_full.date == eq_trunc.date
        assert eq_full.total_nav == pytest.approx(eq_trunc.total_nav, rel=1e-4)
        assert eq_full.cash == pytest.approx(eq_trunc.cash, rel=1e-4)


def test_point_in_time_bctc_strictness_2024_2026():
    """Bất biến 2: BCTC Quý Q của năm 2024-2026 không được sử dụng trước ngày nộp chính thức."""
    pit = PointInTimeDatabase()
    pit.add_snapshot(PITFinancialSnapshot(
        symbol="HPG", year=2024, quarter=1,
        period_end_date="2024-03-31", filing_date="2024-04-28",
        f_score=8, cfo_ni_ratio=1.4,
    ))

    # Ngày 2024-04-10 (sau ngày kết thúc quý nhưng trước ngày nộp) -> Chưa hợp lệ
    assert pit.is_quantamental_qualified("HPG", "2024-04-10") is False

    # Ngày 2024-04-28 (ngày nộp chính thức) -> Đã hợp lệ
    assert pit.is_quantamental_qualified("HPG", "2024-04-28") is True


def test_multi_year_simulation_and_adr024_rules():
    """Bất biến 3: Kiểm định đầy đủ các năm 2024, 2025, 2026 và toàn kỳ 3 năm."""
    stocks, idx_bars, pit = generate_benchmark_market_data()
    cfg = BacktestConfig(
        initial_capital=1_000_000_000.0,
        enable_time_stop_t7=True,
        enable_tp1_breakeven=True,
        cooldown_bars_after_sl=3,
    )
    coord = WalkForwardCoordinator(
        config=cfg,
        stock_bars_dict=stocks,
        vnindex_bars=idx_bars,
        pit_db=pit,
    )

    results = coord.run_multi_year_2024_2026()
    assert results["year_2024"] is not None
    assert results["year_2025"] is not None
    assert results["year_2026"] is not None
    assert results["full_3y"] is not None

    res_3y = results["full_3y"]
    assert res_3y.total_trades > 0
    assert len(res_3y.equity_curve) > 0
    assert res_3y.final_equity > 0

    # Kiểm tra tất cả các lệnh đều thỏa mãn T+2.5 (holding_days >= 2)
    for t in res_3y.trades:
        assert t.holding_days >= 2

    # Kiểm tra có các lý do đóng lệnh phù hợp quy tắc ADR-024
    reasons = {t.reason for t in res_3y.trades}
    assert "STOP_LOSS" in reasons or "TAKE_PROFIT" in reasons or "TIME_STOP_T7" in reasons

    report_str = format_backtest_report_text("TEST REPORT 3Y", res_3y)
    assert "Lợi nhuận ròng:" in report_str
    assert "CAGR" in report_str

