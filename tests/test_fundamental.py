"""Kiểm thử tính toán Piotroski F-Score và Valuation Percentiles."""
import pytest
from src.collector.data_loader import FinancialReport, StockFinancials, get_mock_vietnam_stocks
from src.fundamental_engine.screener import calculate_piotroski_score, screen_stocks
from src.fundamental_engine.valuation import calculate_valuation_percentile, classify_valuation_regime


def test_piotroski_f_score_calculation():
    """Kiểm tra F-Score cho doanh nghiệp tăng trưởng toàn diện đạt 9/9 điểm."""
    cur = FinancialReport(
        symbol="HPG", year=2026, quarter=1,
        net_income=3200e9, operating_cash_flow=4500e9, total_assets=190000e9,
        roa=0.068, long_term_debt=35000e9, current_ratio=1.65,
        shares_outstanding=5814785700, gross_margin=0.165, asset_turnover=0.85
    )
    prev = FinancialReport(
        symbol="HPG", year=2025, quarter=4,
        net_income=2800e9, operating_cash_flow=3100e9, total_assets=185000e9,
        roa=0.061, long_term_debt=38000e9, current_ratio=1.55,
        shares_outstanding=5814785700, gross_margin=0.142, asset_turnover=0.81
    )
    detail = calculate_piotroski_score(cur, prev)
    assert detail.total_score == 9
    assert detail.f1_roa_positive == 1
    assert detail.f4_cfo_greater_than_ni == 1
    assert detail.f5_delta_long_term_debt_lower == 1


def test_screen_stocks_ranking():
    """Kiểm tra chức năng sàng lọc và phân loại cổ phiếu định chế."""
    stocks = get_mock_vietnam_stocks()
    results = screen_stocks(stocks)
    assert len(results) == len(stocks)
    # Cổ phiếu đầu bảng phải có F-score >= 7
    assert results[0].f_score >= 7
    assert results[0].is_institutional_grade is True


def test_valuation_percentiles():
    """Kiểm tra tính toán phân vị P/E và phân loại chế độ định giá."""
    history = [10.0, 12.0, 14.0, 16.0, 18.0]
    # Giá trị 10.0 là mức thấp nhất -> phân vị 20%
    p20 = calculate_valuation_percentile(10.0, history)
    assert p20 == 20.0
    assert classify_valuation_regime(15.0) == "DEEP_VALUE"
    assert classify_valuation_regime(85.0) == "OVERVALUED"
    assert classify_valuation_regime(50.0) == "FAIR_VALUE"
