"""Do luong Basis VN30F1M va tinh toan phong ho danh muc co so."""
from dataclasses import dataclass


@dataclass
class BasisState:
    basis_points: float          # VN30F1M - VN30 Index
    regime: str                  # CONTANGO_EXPANDED, NORMAL, BACKWARDATION_EXTREME
    short_squeeze_alert: bool    # Canh bao rut chan ep cat lo phai sinh


def analyze_vn30_basis(vn30f1m_price: float, vn30_index: float) -> BasisState:
    """Phan tich trang thai Basis giua Hop dong tuong lai VN30F1M va chi so co so VN30."""
    basis = round(vn30f1m_price - vn30_index, 2)

    if basis > 5.0:
        regime = "CONTANGO_EXPANDED"
        short_squeeze = False
    elif basis < -10.0:
        regime = "BACKWARDATION_EXTREME"
        short_squeeze = True   # Khi Basis am qua sau de co song keo tru dot ngot
    else:
        regime = "NORMAL_EQUILIBRIUM"
        short_squeeze = False

    return BasisState(
        basis_points=basis,
        regime=regime,
        short_squeeze_alert=short_squeeze
    )


def calculate_portfolio_beta_hedge(
    portfolio_value_vnd: float,
    portfolio_beta: float,
    vn30f1m_price: float,
    contract_multiplier: float = 100_000.0
) -> int:
    """Tinh so hop dong phai sinh VN30F1M can Short de phong ho 100% rui ro danh muc co so.
    
    Formula: N = Round( (Portfolio_Value * Beta) / (VN30F1M * 100,000) )
    """
    if vn30f1m_price <= 0:
        return 0
    contract_notional = vn30f1m_price * contract_multiplier
    contracts = round((portfolio_value_vnd * portfolio_beta) / contract_notional)
    return max(int(contracts), 0)
