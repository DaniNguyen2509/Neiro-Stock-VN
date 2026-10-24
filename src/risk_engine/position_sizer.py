"""Volatility-Adjusted Position Sizing theo bien dong ATR(14)."""
from dataclasses import dataclass


@dataclass
class PositionSizeResult:
    symbol: str
    target_shares: int
    total_outlay_vnd: float
    max_risk_vnd: float
    stop_loss_price: float


def calculate_atr_position_size(
    equity_vnd: float,
    current_price: float,
    atr_vnd: float,
    risk_pct: float = 1.5,
    atr_multiplier: float = 1.5,
    symbol: str = "STOCK"
) -> PositionSizeResult:
    """Tinh so luong co phieu mua an toan theo do bien dong thuc te ATR(14).
    
    Args:
        equity_vnd: Tong gia tri tai san rong (NAV)
        current_price: Gia thi truong hien tai
        atr_vnd: Gia tri bien dong 14 phien (Average True Range)
        risk_pct: % chap nhan rui ro toi da tren tong tai khoan (vi du 1.5%)
        atr_multiplier: He so dat Stop Loss (1.5x ATR)
    """
    max_risk = equity_vnd * (risk_pct / 100.0)
    per_share_risk = max(atr_vnd * atr_multiplier, current_price * 0.03) # Toi thieu 3% cat lo
    shares = int(max_risk / per_share_risk)
    
    # Lam tron lo 100 co phieu theo quy dinh HOSE/HNX
    shares = (shares // 100) * 100
    stop_loss = round(current_price - per_share_risk, 0)
    outlay = shares * current_price

    return PositionSizeResult(
        symbol=symbol,
        target_shares=shares,
        total_outlay_vnd=outlay,
        max_risk_vnd=round(max_risk, 0),
        stop_loss_price=max(stop_loss, 0.0)
    )
