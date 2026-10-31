"""Volatility-Adjusted & Retail Cold-Start T+2.5 Position Sizing (HOSE Lot-100)."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class PositionSizeResult:
    """Kết quả tính quy mô vị thế chuẩn theo ATR(14)."""

    symbol: str
    target_shares: int
    total_outlay_vnd: float
    max_risk_vnd: float
    stop_loss_price: float


@dataclass
class RetailPositionPlan:
    """Kế hoạch đi vốn thực chiến cho nhà đầu tư cá nhân nhỏ lẻ chịu ràng buộc T+2.5 & lô 100 cp."""

    symbol: str
    equity_vnd: float
    target_shares: int
    total_outlay_vnd: float
    position_pct_nav: float
    max_risk_vnd: float
    stop_loss_price_vnd: float
    max_cap_pct_nav: float
    allow_margin: bool
    is_lot100_feasible: bool
    can_split_tp1_tp2: bool
    lot_warning: str


def calculate_atr_position_size(
    equity_vnd: float,
    current_price: float,
    atr_vnd: float,
    risk_pct: float = 1.5,
    atr_multiplier: float = 1.5,
    symbol: str = "STOCK",
    max_position_pct: Optional[float] = None,
) -> PositionSizeResult:
    """Tính số lượng cổ phiếu mua an toàn theo độ biến động thực tế ATR(14) làm tròn lô 100."""
    max_risk = equity_vnd * (risk_pct / 100.0)
    per_share_risk = max(atr_vnd * atr_multiplier, current_price * 0.03)
    shares = int(max_risk / per_share_risk)

    if max_position_pct is not None and max_position_pct > 0 and current_price > 0:
        cap_shares = int((equity_vnd * max_position_pct) / current_price)
        shares = min(shares, cap_shares)

    shares = (shares // 100) * 100
    stop_loss = round(current_price - per_share_risk, 0)
    outlay = shares * current_price

    return PositionSizeResult(
        symbol=symbol,
        target_shares=max(shares, 0),
        total_outlay_vnd=max(outlay, 0.0),
        max_risk_vnd=round(max_risk, 0),
        stop_loss_price=max(stop_loss, 0.0),
    )


def calculate_retail_t25_position_size(
    equity_vnd: float,
    current_price_vnd: float,
    stop_loss_price_vnd: float,
    available_t0_ratio: float = 0.0,
    risk_pct: float = 1.25,
    symbol: str = "STOCK",
) -> RetailPositionPlan:
    """Tính khối lượng giải ngân an toàn cho NĐT cá nhân chưa có đệm hàng T+0 (Cold-Start).

    Quy tắc bảo vệ nhỏ lẻ (BM-07):
    - Nếu tài khoản chưa có sẵn >= 35% hàng T+0 (Cold-Start): Khóa trần tối đa <= 20% NAV/mã
      và CẤM dùng Margin (0% Margin) trong suốt thời gian hàng đóng băng chờ T+2.5.
    - Tự động đổi đơn vị giá nghìn đồng (21.20 -> 21,200 VND) để kiểm tra tính khả thi lô chẵn
      100 cổ phiếu sàn HOSE và khả năng chia 50/50 chốt lời tại TP1 / TP2 (>= 200 cp).
    """
    price_vnd = current_price_vnd * 1000.0 if 0 < current_price_vnd < 1000.0 else current_price_vnd
    sl_vnd = stop_loss_price_vnd * 1000.0 if 0 < stop_loss_price_vnd < 1000.0 else stop_loss_price_vnd

    has_t0_cushion = available_t0_ratio >= 0.35
    max_cap_pct = 0.30 if has_t0_cushion else 0.20
    allow_margin = bool(has_t0_cushion)

    if equity_vnd <= 0 or price_vnd <= 0:
        return RetailPositionPlan(
            symbol=symbol,
            equity_vnd=max(equity_vnd, 0.0),
            target_shares=0,
            total_outlay_vnd=0.0,
            position_pct_nav=0.0,
            max_risk_vnd=0.0,
            stop_loss_price_vnd=max(sl_vnd, 0.0),
            max_cap_pct_nav=max_cap_pct * 100.0,
            allow_margin=False,
            is_lot100_feasible=False,
            can_split_tp1_tp2=False,
            lot_warning="Dữ liệu vốn hoặc thị giá không hợp lệ",
        )

    max_budget_vnd = equity_vnd * max_cap_pct
    min_lot100_cost = 100.0 * price_vnd

    # Kiểm tra thị giá cao vượt trần phân bổ 20% NAV cho 1 lô chẵn 100 cp (VD: VIC 239.70 với NAV 100tr)
    if min_lot100_cost > max_budget_vnd:
        return RetailPositionPlan(
            symbol=symbol,
            equity_vnd=equity_vnd,
            target_shares=0,
            total_outlay_vnd=0.0,
            position_pct_nav=0.0,
            max_risk_vnd=0.0,
            stop_loss_price_vnd=round(sl_vnd, 0),
            max_cap_pct_nav=round(max_cap_pct * 100.0, 1),
            allow_margin=False,
            is_lot100_feasible=False,
            can_split_tp1_tp2=False,
            lot_warning=(
                f"⚠️ Thị giá cao (1 lô 100 cp = {min_lot100_cost/1e6:.1f}tr > trần {max_cap_pct*100:.0f}% NAV "
                f"{max_budget_vnd/1e6:.0f}tr cho vốn {equity_vnd/1e6:.0f}tr — Bỏ qua hoặc dùng tài khoản lớn)"
            ),
        )

    per_share_risk = max(price_vnd - sl_vnd, price_vnd * 0.045)
    max_risk_budget = equity_vnd * (risk_pct / 100.0)

    shares_by_risk = int(max_risk_budget / per_share_risk)
    shares_by_cap = int(max_budget_vnd / price_vnd)
    raw_shares = min(max(shares_by_risk, 100), shares_by_cap)
    target_shares = (raw_shares // 100) * 100

    outlay = target_shares * price_vnd
    actual_risk = target_shares * per_share_risk
    pos_pct = round((outlay / equity_vnd) * 100.0, 1)

    if target_shares < 100:
        return RetailPositionPlan(
            symbol=symbol,
            equity_vnd=equity_vnd,
            target_shares=0,
            total_outlay_vnd=0.0,
            position_pct_nav=0.0,
            max_risk_vnd=0.0,
            stop_loss_price_vnd=round(sl_vnd, 0),
            max_cap_pct_nav=round(max_cap_pct * 100.0, 1),
            allow_margin=False,
            is_lot100_feasible=False,
            can_split_tp1_tp2=False,
            lot_warning="⚠️ Không đủ ngân sách mua tối thiểu 1 lô 100 cp",
        )

    can_split = target_shares >= 200
    if not can_split:
        lot_note = (
            f"ℹ️ Vốn {equity_vnd/1e6:.0f}tr mua tối đa 100 cp (~{outlay/1e6:.1f}tr, {pos_pct:.1f}% NAV) "
            "— 1 lô chẵn HOSE duy nhất: Chốt gọn 1 lần tại TP1/Trailing, không chia 50/50"
        )
    else:
        lot_note = (
            f"✅ Vốn {equity_vnd/1e6:.0f}tr: Tối đa {target_shares:,d} cp (~{outlay/1e6:.1f}tr, {pos_pct:.1f}% NAV "
            f"<= {max_cap_pct*100:.0f}% NAV, chia 2 lô chốt TP1/TP2)"
        )

    return RetailPositionPlan(
        symbol=symbol,
        equity_vnd=equity_vnd,
        target_shares=target_shares,
        total_outlay_vnd=round(outlay, 0),
        position_pct_nav=pos_pct,
        max_risk_vnd=round(actual_risk, 0),
        stop_loss_price_vnd=round(sl_vnd, 0),
        max_cap_pct_nav=round(max_cap_pct * 100.0, 1),
        allow_margin=allow_margin,
        is_lot100_feasible=True,
        can_split_tp1_tp2=can_split,
        lot_warning=lot_note,
    )
