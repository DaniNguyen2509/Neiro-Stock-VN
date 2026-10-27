"""Lõi Mô phỏng Khớp lệnh Kiem dinh Qua khu (T+2.5 Backtesting Engine).

Mô hình hóa chính xác các ràng buộc khắc nghiệt của Thị trường Chứng khoán Việt Nam:
1. Chu kỳ thanh toán T+2.5 (mua T+0, chỉ được phép bán từ chiều T+2).
2. Kiểm tra biên độ trần/sàn theo từng sàn (HOSE 7%, HNX 10%, UPCoM 15%).
3. Khấu trừ chi phí giao dịch thực tế (0.15% phí mua, 0.15% phí bán, 0.10% thuế TNCN).
4. Khớp lệnh tại bar t+1 để triệt tiêu hoàn toàn Look-ahead Bias.
"""

from typing import Dict, List, Optional, Tuple
from src.backtesting.models import (
    BacktestConfig,
    BacktestResult,
    DailyEquity,
    Exchange,
    MarketBar,
    Position,
    PriceBand,
    SettlementBatch,
    TradeAction,
    TradeRecord,
)
from src.backtesting.metrics import calculate_performance_suite


class T25BacktestEngine:
    """Co che kiem dinh chien thuat voi quan ly vi the va hang cho ve T+2.5."""

    def __init__(self, config: Optional[BacktestConfig] = None):
        self.config = config or BacktestConfig()
        self.cash = self.config.initial_capital
        self.positions: Dict[str, Position] = {}
        self.closed_trades: List[TradeRecord] = []
        self.equity_curve: List[DailyEquity] = []
        self._trade_counter = 0

    def reset(self):
        """Khoi tao lai trang thai ban dau cua engine."""
        self.cash = self.config.initial_capital
        self.positions.clear()
        self.closed_trades.clear()
        self.equity_curve.clear()
        self._trade_counter = 0

    def can_sell_shares(self, symbol: str, current_day_idx: int) -> int:
        """Kiem tra so luong co phieu da du T+2.5 de co the ban.
        
        Args:
            symbol: Ma co phieu.
            current_day_idx: Chi so phien hien tai.
            
        Returns:
            So luong co phieu kha dung ban (available_shares).
        """
        pos = self.positions.get(symbol)
        if not pos or pos.total_shares <= 0:
            return 0
        pos.update_settlement(current_day_idx)
        return pos.available_shares

    def execute_buy(
        self,
        symbol: str,
        price: float,
        date: str,
        day_idx: int,
        exchange: Exchange = Exchange.HOSE,
        allocated_capital: Optional[float] = None,
        reference_price: Optional[float] = None,
    ) -> Optional[SettlementBatch]:
        """Thuc thi lenh mua co phieu tai phien voi kiem tra tran/san va T+2.5.
        
        Args:
            symbol: Ma co phieu.
            price: Gia khop mua (thuong la Open phien t+1).
            date: Ngay khop lenh.
            day_idx: Chi so ngay tren chuoi thoi gian.
            exchange: San giao dich.
            allocated_capital: So tien phan bo cho lenh mua.
            reference_price: Gia tham chieu de tinh bien do tran/san.
            
        Returns:
            SettlementBatch neu khop thanh cong, None neu vi pham quy tac.
        """
        # 1. Kiem tra gioi han so luong ma vi the toi da trong danh muc
        if len(self.positions) >= self.config.max_portfolio_positions and symbol not in self.positions:
            return None

        # 2. Kiem tra gia tran/san
        ref = reference_price if reference_price and reference_price > 0 else price
        band = PriceBand.calculate(ref, exchange)
        if price > band.ceiling_price:
            # Gia khop vuot tran hoac trang ben ban khong the mua
            return None

        # 3. Tinh toan so luong co phieu mua theo lo 100 cp (chuan HOSE/HNX)
        target_capital = allocated_capital or (self.config.initial_capital * self.config.position_allocation_pct)
        target_capital = min(target_capital, self.cash)

        if target_capital < price * 100:
            return None

        raw_shares = int(target_capital / (price * (1.0 + self.config.buy_fee_pct)))
        shares = (raw_shares // 100) * 100

        if shares < 100:
            return None

        gross_val = shares * price
        buy_fee = gross_val * self.config.buy_fee_pct
        total_cost = gross_val + buy_fee

        if total_cost > self.cash:
            return None

        # 4. Tru tien va tao lo hang cho T+2.5 (chieu T+2 moi duoc ban, tuc day_idx + 2)
        self.cash -= total_cost
        batch = SettlementBatch(
            shares=shares,
            buy_date=date,
            settle_day_index=day_idx + self.config.min_holding_bars,
            buy_price=price,
            buy_fee=buy_fee,
            buy_day_idx=day_idx,
        )

        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol=symbol)

        self.positions[symbol].add_batch(batch)
        return batch

    def execute_sell(
        self,
        symbol: str,
        price: float,
        date: str,
        day_idx: int,
        exchange: Exchange = Exchange.HOSE,
        reference_price: Optional[float] = None,
        reason: str = "SIGNAL",
    ) -> Optional[TradeRecord]:
        """Thuc thi lenh ban co phieu voi rang buoc chat che T+2.5 va phi thue.
        
        Args:
            symbol: Ma co phieu.
            price: Gia khop ban.
            date: Ngay ban.
            day_idx: Chi so ngay hien tai.
            exchange: San giao dich.
            reference_price: Gia tham chieu phien.
            reason: Ly do ban (SIGNAL, STOP_LOSS, TAKE_PROFIT).
            
        Returns:
            TradeRecord neu ban thanh cong, None neu chua du T+2.5 hoac vi pham san gia.
        """
        pos = self.positions.get(symbol)
        if not pos or pos.total_shares <= 0:
            return None

        # 1. Kiem tra rang buoc T+2.5: Chi duoc ban so luong co phieu da ve
        pos.update_settlement(day_idx)
        available_shares = pos.available_shares
        if available_shares <= 0:
            # Hang chua ve tai khoan, bi khoa hoan toan khong the cat lo hoac chot loi
            return None

        # 2. Kiem tra bien do san
        ref = reference_price if reference_price and reference_price > 0 else price
        band = PriceBand.calculate(ref, exchange)
        if price < band.floor_price:
            # Gia khop duoi san (hoac trang ben mua), lenh khong the thuc hien
            return None

        # 3. Thuc hien ban toan bo luong hang da ve (FIFO)
        shares_to_sell = available_shares
        gross_val = shares_to_sell * price
        sell_fee = gross_val * self.config.sell_fee_pct
        sell_tax = gross_val * self.config.sell_tax_pct
        net_proceeds = gross_val - sell_fee - sell_tax

        # Tinh toan gia von cac batch tuong ung
        remaining_to_deduct = shares_to_sell
        total_entry_cost = 0.0
        total_buy_fee = 0.0
        first_entry_date = None
        first_entry_day_idx = None
        new_batches: List[SettlementBatch] = []

        for b in pos.batches:
            if remaining_to_deduct <= 0:
                new_batches.append(b)
                continue

            if day_idx >= b.settle_day_index:
                deduct = min(b.shares, remaining_to_deduct)
                ratio = deduct / b.shares
                total_entry_cost += deduct * b.buy_price
                total_buy_fee += b.buy_fee * ratio
                if first_entry_date is None:
                    first_entry_date = b.buy_date
                if first_entry_day_idx is None:
                    first_entry_day_idx = b.buy_day_idx
                remaining_to_deduct -= deduct

                if deduct < b.shares:
                    new_batches.append(SettlementBatch(
                        shares=b.shares - deduct,
                        buy_date=b.buy_date,
                        settle_day_index=b.settle_day_index,
                        buy_price=b.buy_price,
                        buy_fee=b.buy_fee * (1.0 - ratio),
                        buy_day_idx=b.buy_day_idx,
                    ))
            else:
                new_batches.append(b)

        pos.batches = new_batches
        pos.total_shares -= shares_to_sell
        pos.available_shares = 0

        if pos.total_shares <= 0:
            del self.positions[symbol]

        # Cong tien vao tai khoan
        self.cash += net_proceeds
        gross_pnl = gross_val - total_entry_cost
        net_pnl = net_proceeds - (total_entry_cost + total_buy_fee)
        ret_pct = round((net_pnl / (total_entry_cost + total_buy_fee)) * 100.0, 2) if (total_entry_cost + total_buy_fee) > 0 else 0.0

        final_entry_date = first_entry_date or date
        final_entry_day_idx = first_entry_day_idx if first_entry_day_idx is not None else day_idx

        self._trade_counter += 1
        trade = TradeRecord(
            trade_id=self._trade_counter,
            symbol=symbol,
            entry_date=final_entry_date,
            exit_date=date,
            entry_price=round(total_entry_cost / shares_to_sell, 2) if shares_to_sell > 0 else 0.0,
            exit_price=round(price, 2),
            shares=shares_to_sell,
            buy_fee=round(total_buy_fee, 2),
            sell_fee=round(sell_fee, 2),
            sell_tax=round(sell_tax, 2),
            gross_pnl=round(gross_pnl, 2),
            net_pnl=round(net_pnl, 2),
            return_pct=ret_pct,
            holding_days=max(day_idx - final_entry_day_idx, 1),
            reason=reason,
        )
        self.closed_trades.append(trade)
        return trade

    def record_daily_equity(
        self,
        date: str,
        current_prices: Dict[str, float],
        benchmark_price: float,
        initial_benchmark_price: float,
    ) -> DailyEquity:
        """Cap nhat tong gia tri tai san rong (NAV) vao cuoi moi phien giao dich."""
        stock_value = 0.0
        for sym, pos in self.positions.items():
            price = current_prices.get(sym, pos.avg_cost)
            stock_value += pos.total_shares * price

        total_nav = self.cash + stock_value

        # Tinh benchmark NAV tuong duong theo ty le von ban dau
        benchmark_nav = (
            (benchmark_price / initial_benchmark_price) * self.config.initial_capital
            if initial_benchmark_price > 0 else self.config.initial_capital
        )

        daily_ret = 0.0
        drawdown = 0.0
        if self.equity_curve:
            prev_nav = self.equity_curve[-1].total_nav
            daily_ret = (total_nav - prev_nav) / prev_nav if prev_nav > 0 else 0.0
            peak_nav = max(d.total_nav for d in self.equity_curve + [DailyEquity(date, 0, 0, total_nav, 0, 0)])
            drawdown = ((peak_nav - total_nav) / peak_nav) * 100.0 if peak_nav > 0 else 0.0

        record = DailyEquity(
            date=date,
            cash=round(self.cash, 2),
            stock_value=round(stock_value, 2),
            total_nav=round(total_nav, 2),
            benchmark_price=round(benchmark_price, 2),
            benchmark_nav=round(benchmark_nav, 2),
            daily_return=round(daily_ret, 6),
            drawdown_pct=round(drawdown, 2),
        )
        self.equity_curve.append(record)
        return record

    def build_result(
        self,
        period_label: str = "FULL",
        benchmark_prices: Optional[List[float]] = None,
    ) -> BacktestResult:
        """Tong hop ket qua backtest toan dien voi day du chi so hieu suat."""
        equity_values = [d.total_nav for d in self.equity_curve]
        metrics = calculate_performance_suite(
            initial_capital=self.config.initial_capital,
            equity_curve=equity_values,
            trades=self.closed_trades,
            risk_free_rate_annual=self.config.risk_free_rate_annual,
        )

        # Tinh toan thong so Benchmark (VN-Index)
        bench_ret = 0.0
        bench_cagr = 0.0
        bench_mdd = 0.0
        if benchmark_prices and len(benchmark_prices) >= 2:
            bench_start = benchmark_prices[0]
            bench_end = benchmark_prices[-1]
            bench_ret = round(((bench_end - bench_start) / bench_start) * 100.0, 2)
            num_years = max(len(benchmark_prices) / 252.0, 0.05)
            from src.backtesting.metrics import calculate_cagr, calculate_max_drawdown
            bench_cagr = calculate_cagr(bench_start, bench_end, num_years)
            bench_mdd = calculate_max_drawdown(benchmark_prices)

        alpha = round(metrics["total_return_pct"] - bench_ret, 2)

        return BacktestResult(
            config=self.config,
            initial_capital=self.config.initial_capital,
            final_equity=metrics.get("final_equity", self.cash),
            total_return_pct=metrics["total_return_pct"],
            cagr_pct=metrics["cagr_pct"],
            sharpe_ratio=metrics["sharpe_ratio"],
            sortino_ratio=metrics["sortino_ratio"],
            max_drawdown_pct=metrics["max_drawdown_pct"],
            calmar_ratio=metrics["calmar_ratio"],
            win_rate_pct=metrics["win_rate_pct"],
            profit_factor=metrics["profit_factor"],
            total_trades=metrics["total_trades"],
            winning_trades=metrics["winning_trades"],
            losing_trades=metrics["losing_trades"],
            trades=list(self.closed_trades),
            equity_curve=list(self.equity_curve),
            benchmark_return_pct=bench_ret,
            benchmark_cagr_pct=bench_cagr,
            benchmark_mdd_pct=bench_mdd,
            alpha_pct=alpha,
            period_label=period_label,
        )
