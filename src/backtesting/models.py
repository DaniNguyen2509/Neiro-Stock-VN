"""Data models va Cau truc du lieu cho Backtest Engine Viet Nam T+2.5."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class Exchange(str, Enum):
    """San giao dich chung khoan Viet Nam va bien do dao dong gia."""
    HOSE = "HOSE"    # Bien do +/- 7%
    HNX = "HNX"      # Bien do +/- 10%
    UPCOM = "UPCOM"  # Bien do +/- 15%


@dataclass(frozen=True)
class PriceBand:
    """Bien do gia tran/san theo quy dinh So Giao dich."""
    exchange: Exchange
    reference_price: float
    ceiling_price: float
    floor_price: float

    @classmethod
    def calculate(cls, reference_price: float, exchange: Exchange = Exchange.HOSE) -> "PriceBand":
        """Tinh toan gia tran va san theo bien do phan tram cua tung san."""
        if exchange == Exchange.HOSE:
            rate = 0.07
        elif exchange == Exchange.HNX:
            rate = 0.10
        elif exchange == Exchange.UPCOM:
            rate = 0.15
        else:
            rate = 0.07

        # Tinh toan lam tron chuan (giu 2 chu so thap phan cho don vi 1,000 VND hoac gia tuyet doi)
        ceiling = round(reference_price * (1.0 + rate), 2)
        floor = round(reference_price * (1.0 - rate), 2)
        return cls(
            exchange=exchange,
            reference_price=reference_price,
            ceiling_price=ceiling,
            floor_price=floor,
        )


class TradeAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class MarketBar:
    """Du lieu nen gia lich su cho mot ma co phieu."""
    symbol: str
    date: str  # YYYY-MM-DD
    open: float
    high: float
    low: float
    close: float
    volume: float
    reference_price: float = 0.0
    ceiling_price: float = 0.0
    floor_price: float = 0.0
    ofi: float = 0.0  # Order Flow Imbalance (-1.0 den +1.0)
    exchange: Exchange = Exchange.HOSE

    def __post_init__(self):
        # Tu dong dien gia tham chieu neu chua co (mac dinh bang gia open hoac close)
        if self.reference_price <= 0.0:
            object.__setattr__(self, "reference_price", self.open)
        if self.ceiling_price <= 0.0 or self.floor_price <= 0.0:
            band = PriceBand.calculate(self.reference_price, self.exchange)
            object.__setattr__(self, "ceiling_price", band.ceiling_price)
            object.__setattr__(self, "floor_price", band.floor_price)


@dataclass
class SettlementBatch:
    """Lo co phieu cho ve theo chu ky thanh toan T+2.5."""
    shares: int
    buy_date: str
    settle_day_index: int  # Bar index khi hang bat dau co the ban (chieu T+2)
    buy_price: float
    buy_fee: float
    buy_day_idx: int = 0


@dataclass
class Position:
    """Vi the nam giu co phieu trong tai khoan."""
    symbol: str
    total_shares: int = 0
    available_shares: int = 0  # So luong hang da ve, co the ban ngay
    avg_cost: float = 0.0
    batches: List[SettlementBatch] = field(default_factory=list)

    def add_batch(self, batch: SettlementBatch):
        """Them lo mua moi vao vi the."""
        old_cost_val = self.total_shares * self.avg_cost
        new_cost_val = batch.shares * batch.buy_price
        self.total_shares += batch.shares
        self.avg_cost = (old_cost_val + new_cost_val) / self.total_shares if self.total_shares > 0 else 0.0
        self.batches.append(batch)

    def update_settlement(self, current_day_index: int):
        """Kiem tra va chuyen hang cho ve sang hang kha dung ban."""
        available = 0
        for b in self.batches:
            if current_day_index >= b.settle_day_index:
                available += b.shares
        self.available_shares = available


@dataclass
class TradeRecord:
    """Nhat ky chi tiet cua mot giao dich da dong (Round-trip trade)."""
    trade_id: int
    symbol: str
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    shares: int
    buy_fee: float
    sell_fee: float
    sell_tax: float
    gross_pnl: float
    net_pnl: float
    return_pct: float
    holding_days: int
    reason: str = "SIGNAL"


@dataclass
class DailyEquity:
    """Ghi nhan gia tri tai san rong (NAV) hang ngay."""
    date: str
    cash: float
    stock_value: float
    total_nav: float
    benchmark_price: float
    benchmark_nav: float
    daily_return: float = 0.0
    drawdown_pct: float = 0.0


@dataclass
class BacktestConfig:
    """Cau hinh tham so he thong Backtesting."""
    initial_capital: float = 1_000_000_000.0  # 1 ty VND
    buy_fee_pct: float = 0.0015                # 0.15% phi moi gioi mua
    sell_fee_pct: float = 0.0015               # 0.15% phi moi gioi ban
    sell_tax_pct: float = 0.0010               # 0.10% thue TNCN chieu ban
    max_portfolio_positions: int = 5           # Toi da 5 co phieu dong thoi
    position_allocation_pct: float = 0.20      # 20% NAV moi ma
    min_holding_bars: int = 2                  # T+2.5: Bar 0 mua -> Bar 2 chieu moi duoc ban
    risk_free_rate_annual: float = 0.045       # Lai suat phi rui ro 4.5%/nam (Trai phieu CP 10Y)


@dataclass
class BacktestResult:
    """Ket qua toan dien cua phien kiem dinh backtesting."""
    config: BacktestConfig
    initial_capital: float
    final_equity: float
    total_return_pct: float
    cagr_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    calmar_ratio: float
    win_rate_pct: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    trades: List[TradeRecord]
    equity_curve: List[DailyEquity]
    benchmark_return_pct: float
    benchmark_cagr_pct: float
    benchmark_mdd_pct: float
    alpha_pct: float  # Total return - Benchmark return
    period_label: str = "FULL"  # IN_SAMPLE, OUT_OF_SAMPLE, FULL
    floor_lock_blocked_count: int = 0
    t25_blocked_count: int = 0
