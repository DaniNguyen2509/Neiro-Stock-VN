"""Performance Metrics Suite - Tinh toan Thuoc do Hieu suat Toan hoc Chuan Dinh Che."""

from typing import List, Dict, Any
import numpy as np
from src.backtesting.models import TradeRecord


def calculate_win_rate(trades: List[TradeRecord]) -> float:
    """Tinh ty le thang (Win Rate %) cua danh sach giao dich.
    
    Args:
        trades: Danh sach ban ghi giao dich da dong.
        
    Returns:
        Phan tram giao dich co Net PnL > 0 (0.0% den 100.0%).
    """
    if not trades:
        return 0.0
    wins = sum(1 for t in trades if t.net_pnl > 0)
    return round((wins / len(trades)) * 100.0, 2)


def calculate_profit_factor(trades: List[TradeRecord]) -> float:
    """Tinh ty so Loi/Lo (Profit Factor = Tong Tien Lai / Tong Tien Lo).
    
    Args:
        trades: Danh sach ban ghi giao dich da dong.
        
    Returns:
        Profit Factor (neu khong co lenh lo, tra ve 99.0 hoac 0.0 neu khong co lenh lai).
    """
    if not trades:
        return 0.0
    total_gains = sum(t.net_pnl for t in trades if t.net_pnl > 0)
    total_losses = sum(abs(t.net_pnl) for t in trades if t.net_pnl < 0)

    if total_losses == 0.0:
        return 99.0 if total_gains > 0 else 0.0
    return round(total_gains / total_losses, 2)


def calculate_cagr(start_val: float, end_val: float, num_years: float) -> float:
    """Tinh tang truong kep hang nam (Compound Annual Growth Rate - CAGR %).
    
    Args:
        start_val: Gia tri von ban dau.
        end_val: Gia tri von cuoi ky.
        num_years: So nam thuc hien kiem dinh (tinh theo so phien / 252).
        
    Returns:
        CAGR phan tram (%).
    """
    if start_val <= 0 or end_val <= 0 or num_years <= 0:
        return 0.0
    cagr = ((end_val / start_val) ** (1.0 / num_years) - 1.0) * 100.0
    return round(float(cagr), 2)


def calculate_max_drawdown(equity_values: List[float]) -> float:
    """Tinh muc sut giam tai san toi da tu dinh (Maximum Drawdown - MDD %).
    
    Args:
        equity_values: Chuoi gia tri NAV tai san theo thoi gian.
        
    Returns:
        MDD duoi dang phan tram duong (0.0% den 100.0%).
    """
    if len(equity_values) < 2:
        return 0.0

    peak = equity_values[0]
    max_dd = 0.0

    for val in equity_values:
        if val > peak:
            peak = val
        if peak > 0:
            dd = (peak - val) / peak
            if dd > max_dd:
                max_dd = dd

    return round(max_dd * 100.0, 2)


def calculate_sharpe_ratio(daily_returns: List[float], risk_free_rate_annual: float = 0.045) -> float:
    """Tinh he so Sharpe Ratio hang nam hoa (Annualized Sharpe).
    
    Sharpe = sqrt(252) * (Mean(R_daily - Rf_daily) / Std(R_daily))
    
    Args:
        daily_returns: Chuoi loi nhuan phan tram hang ngay (decimal, vi du 0.01 cho 1%).
        risk_free_rate_annual: Lai suat phi rui ro nam (mac dinh 4.5% = 0.045).
        
    Returns:
        He so Sharpe duoc hang nam hoa voi 252 phien giao dich.
    """
    if len(daily_returns) < 5:
        return 0.0

    daily_rf = risk_free_rate_annual / 252.0
    excess_returns = np.array(daily_returns) - daily_rf
    mean_excess = np.mean(excess_returns)
    std_dev = np.std(daily_returns, ddof=1)

    if std_dev <= 1e-8:
        return 0.0

    annualized_sharpe = (mean_excess / std_dev) * np.sqrt(252)
    return round(float(annualized_sharpe), 2)


def calculate_sortino_ratio(daily_returns: List[float], risk_free_rate_annual: float = 0.045) -> float:
    """Tinh he so Sortino Ratio hang nam hoa (chi xet bien dong sut giam Downside Deviation).
    
    Sortino = sqrt(252) * (Mean(R_daily - Rf_daily) / Downside_Std(R_daily))
    
    Args:
        daily_returns: Chuoi loi nhuan phan tram hang ngay.
        risk_free_rate_annual: Lai suat phi rui ro nam.
        
    Returns:
        He so Sortino duoc hang nam hoa.
    """
    if len(daily_returns) < 5:
        return 0.0

    daily_rf = risk_free_rate_annual / 252.0
    excess_returns = np.array(daily_returns) - daily_rf
    mean_excess = np.mean(excess_returns)

    # Chi lay cac do lech am duoi muc lai suat phi rui ro
    downside_diffs = np.minimum(0.0, excess_returns)
    downside_variance = np.mean(downside_diffs ** 2)
    downside_std = np.sqrt(downside_variance)

    if downside_std <= 1e-8:
        return 0.0

    annualized_sortino = (mean_excess / downside_std) * np.sqrt(252)
    return round(float(annualized_sortino), 2)


def calculate_calmar_ratio(cagr_pct: float, max_drawdown_pct: float) -> float:
    """Tinh ty so Calmar Ratio = CAGR (%) / MDD (%)."""
    if max_drawdown_pct <= 0.0:
        return 0.0
    return round(cagr_pct / max_drawdown_pct, 2)


def calculate_walk_forward_efficiency(sharpe_oos: float, sharpe_is: float) -> float:
    """Tinh Ty so Hieu qua Walk-Forward (WFE % = Sharpe_OOS / Sharpe_IS).
    
    Danh gia muc do suy thoai hieu qua giua tap tap luyen va tap kiem chung mu.
    """
    if sharpe_is <= 0.0:
        return 0.0
    return round((sharpe_oos / sharpe_is) * 100.0, 2)


def calculate_performance_suite(
    initial_capital: float,
    equity_curve: List[float],
    trades: List[TradeRecord],
    risk_free_rate_annual: float = 0.045,
) -> Dict[str, Any]:
    """Tong hop toan bo bo chi so hieu suat dinh luong."""
    if not equity_curve:
        return {
            "total_return_pct": 0.0,
            "cagr_pct": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "max_drawdown_pct": 0.0,
            "calmar_ratio": 0.0,
            "win_rate_pct": 0.0,
            "profit_factor": 0.0,
            "total_trades": 0,
        }

    final_equity = equity_curve[-1]
    total_return_pct = round(((final_equity - initial_capital) / initial_capital) * 100.0, 2)
    num_years = max(len(equity_curve) / 252.0, 0.05)
    cagr_pct = calculate_cagr(initial_capital, final_equity, num_years)

    # Tinh daily returns
    eq_arr = np.array(equity_curve)
    daily_returns = np.diff(eq_arr) / eq_arr[:-1]
    daily_returns_list = daily_returns.tolist()

    mdd_pct = calculate_max_drawdown(equity_curve)
    sharpe = calculate_sharpe_ratio(daily_returns_list, risk_free_rate_annual)
    sortino = calculate_sortino_ratio(daily_returns_list, risk_free_rate_annual)
    calmar = calculate_calmar_ratio(cagr_pct, mdd_pct)

    win_rate = calculate_win_rate(trades)
    profit_factor = calculate_profit_factor(trades)

    return {
        "final_equity": final_equity,
        "total_return_pct": total_return_pct,
        "cagr_pct": cagr_pct,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "max_drawdown_pct": mdd_pct,
        "calmar_ratio": calmar,
        "win_rate_pct": win_rate,
        "profit_factor": profit_factor,
        "total_trades": len(trades),
        "winning_trades": sum(1 for t in trades if t.net_pnl > 0),
        "losing_trades": sum(1 for t in trades if t.net_pnl < 0),
    }
