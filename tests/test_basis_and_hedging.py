"""Kiểm thử tính toán Basis phái sinh VN30F1M và hệ số phòng hộ danh mục."""
from src.microstructure_engine.basis_tracker import analyze_vn30_basis, calculate_portfolio_beta_hedge


def test_basis_calculation_and_regimes():
    """Kiểm tra phân loại trạng thái Contango và Backwardation cực đại."""
    b1 = analyze_vn30_basis(1320.0, 1312.0)
    assert b1.basis_points == 8.0
    assert b1.regime == "CONTANGO_EXPANDED"
    assert b1.short_squeeze_alert is False

    b2 = analyze_vn30_basis(1290.0, 1305.0)
    assert b2.basis_points == -15.0
    assert b2.regime == "BACKWARDATION_EXTREME"
    assert b2.short_squeeze_alert is True


def test_portfolio_short_hedging_contracts():
    """Kiểm tra công thức tính số lượng hợp đồng VN30F1M cần Short phòng hộ."""
    # Danh mục 1.315 tỷ VND, beta = 1.0, VN30F1M = 1,315 điểm -> đúng 10 hợp đồng
    contracts = calculate_portfolio_beta_hedge(
        portfolio_value_vnd=1_315_000_000.0,
        portfolio_beta=1.0,
        vn30f1m_price=1315.0
    )
    assert contracts == 10
