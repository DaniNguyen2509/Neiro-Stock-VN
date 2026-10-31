"""Walk-Forward Backtesting Coordinator (In-Sample vs Out-of-Sample Validation).

Dieu phoi kiem dinh da chu ky voi phan chia ro rang:
- Tap In-Sample (IS): 2021-01-04 den 2023-12-29 (Huan luyen & Kiem nghiem tren chu ky Bull/Bear)
- Tap Out-of-Sample (OOS): 2024-01-02 den 2026-10-24 (Kiem chung mu tren tap du lieu chua tung xem)
- Tinh toan Walk-Forward Efficiency (WFE %) de chung minh khong bi Overfitting.
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from src.backtesting.engine import T25BacktestEngine
from src.backtesting.historical_data import generate_benchmark_market_data
from src.backtesting.metrics import calculate_walk_forward_efficiency
from src.backtesting.models import BacktestConfig, BacktestResult, Exchange, MarketBar
from src.backtesting.point_in_time import PointInTimeDatabase
from src.risk_engine.trailing_stop import calculate_t25_structural_stop_loss


class WalkForwardCoordinator:
    """Dieu phoi qua trinh kiem dinh Walk-Forward khong thien lech."""

    def __init__(
        self,
        config: Optional[BacktestConfig] = None,
        stock_bars_dict: Optional[Dict[str, List[MarketBar]]] = None,
        vnindex_bars: Optional[List[MarketBar]] = None,
        pit_db: Optional[PointInTimeDatabase] = None,
    ):
        self.config = config or BacktestConfig()
        if stock_bars_dict is None or vnindex_bars is None or pit_db is None:
            self.stock_bars, self.vnindex_bars, self.pit_db = generate_benchmark_market_data()
        else:
            self.stock_bars = stock_bars_dict
            self.vnindex_bars = vnindex_bars
            self.pit_db = pit_db

        self.dates = [b.date for b in self.vnindex_bars]
        self.total_bars = len(self.dates)

        # Xac dinh chi so phan chia In-Sample (2021-2023) va Out-of-Sample (2024-2026)
        self.split_idx = 750  # Bar ket thuc nam 2023 (~250 phien/nam * 3 nam)
        for idx, d in enumerate(self.dates):
            if d.startswith("2024-"):
                self.split_idx = idx
                break

    def run_simulation(
        self,
        start_idx: int,
        end_idx: int,
        period_label: str = "FULL",
    ) -> BacktestResult:
        """Chay mo phong kiem dinh tren mot khoang thoi gian cu the tu start_idx den end_idx."""
        engine = T25BacktestEngine(self.config)
        engine.reset()

        symbols = list(self.stock_bars.keys())
        bench_sub = self.vnindex_bars[start_idx:end_idx]
        initial_bench_price = bench_sub[0].close if bench_sub else 1100.0

        # Tinh toan MA20 va ATR(14) cho tung co phieu tren toan chuoi
        ma20_close: Dict[str, np.ndarray] = {}
        ma20_vol: Dict[str, np.ndarray] = {}
        atr14_map: Dict[str, np.ndarray] = {}
        for sym in symbols:
            bars_sym = self.stock_bars[sym]
            closes = np.array([b.close for b in bars_sym])
            highs = np.array([b.high for b in bars_sym])
            lows = np.array([b.low for b in bars_sym])
            vols = np.array([b.volume for b in bars_sym])
            ma_c = np.zeros(len(closes))
            ma_v = np.zeros(len(vols))
            trs = np.zeros(len(closes))
            atrs = np.zeros(len(closes))
            for i in range(len(closes)):
                w_start = max(0, i - 19)
                ma_c[i] = np.mean(closes[w_start:i + 1])
                ma_v[i] = np.mean(vols[w_start:i + 1])
                if i == 0:
                    trs[i] = max(highs[i] - lows[i], closes[i] * 0.01)
                else:
                    trs[i] = max(
                        highs[i] - lows[i],
                        abs(highs[i] - closes[i - 1]),
                        abs(lows[i] - closes[i - 1]),
                    )
                atr_start = max(0, i - 13)
                atrs[i] = max(float(np.mean(trs[atr_start:i + 1])), closes[i] * 0.01)
            ma20_close[sym] = ma_c
            ma20_vol[sym] = ma_v
            atr14_map[sym] = atrs

        effective_alloc_pct = min(self.config.position_allocation_pct, 0.20)
        pending_buy_orders: List[Tuple[str, float, Exchange, float]] = []

        for i in range(start_idx, end_idx):
            current_date = self.dates[i]
            bench_bar = self.vnindex_bars[i]

            # 1. KHOP LENH MUA CHO TU PHIEN TRUOC (Khop tai gia Open cua phien i -> Triet tieu Look-ahead Bias)
            for sym, alloc_cap, exch, ref_p in pending_buy_orders:
                bar = self.stock_bars[sym][i]
                # Kiem tra lai khong mua duoi neu phien khop Open nhay Gap qua xa nen (> 2.5 * ATR)
                if (bar.open - ma20_close[sym][i]) > 2.5 * atr14_map[sym][i]:
                    continue
                engine.execute_buy(
                    symbol=sym,
                    price=bar.open,
                    date=current_date,
                    day_idx=i,
                    exchange=exch,
                    allocated_capital=alloc_cap,
                    reference_price=bar.reference_price,
                )
            pending_buy_orders.clear()

            # 2. KIEM TRA TIN HIEU BAN CHO CAC VI THE DANG NAM GIU (Uu tien Cat lo Gap-Down & Khoa San)
            symbols_to_evaluate = list(engine.positions.keys())
            for sym in symbols_to_evaluate:
                pos = engine.positions.get(sym)
                if not pos:
                    continue

                bar = self.stock_bars[sym][i]
                pos_sl = calculate_t25_structural_stop_loss(
                    entry_price=pos.avg_cost,
                    atr_14=float(atr14_map[sym][i]),
                )
                if bar.low <= pos_sl:
                    engine.check_and_execute_stop_loss(
                        symbol=sym,
                        bar=bar,
                        day_idx=i,
                        stop_loss_price=pos_sl,
                    )
                    continue

                gain_pct = ((bar.close - pos.avg_cost) / pos.avg_cost) * 100.0 if pos.avg_cost > 0 else 0.0
                should_sell = False
                reason = "SIGNAL"

                # Chot loi khi vuot muc tieu +20%
                if gain_pct >= 20.0:
                    should_sell = True
                    reason = "TAKE_PROFIT"
                # Dao chieu dong tien (OFI am kem gia duoi MA20)
                elif bar.close < ma20_close[sym][i] and bar.ofi < -0.20:
                    should_sell = True
                    reason = "TREND_REVERSAL"

                if should_sell:
                    engine.execute_sell(
                        symbol=sym,
                        price=bar.close,
                        date=current_date,
                        day_idx=i,
                        exchange=bar.exchange,
                        reference_price=bar.reference_price,
                        reason=reason,
                    )

            # 3. QUET TIN HIEU MUA MOI TAI CUOI PHIEN i (Dong bo Live Safeguards: Breadth + Anti-Chasing <= 2.5*ATR + <= 20% NAV)
            if i < end_idx - 1:
                macro_pause = False
                if len(symbols) >= 4:
                    adv_cnt = sum(
                        1 for s in symbols if self.stock_bars[s][i].close >= self.stock_bars[s][i].reference_price
                    )
                    universe_breadth_pct = (adv_cnt / len(symbols)) * 100.0
                    if universe_breadth_pct < 35.0 and bench_bar.ofi < -0.15:
                        macro_pause = True

                if not macro_pause:
                    for sym in symbols:
                        if sym in engine.positions:
                            continue
                        if len(engine.positions) + len(pending_buy_orders) >= self.config.max_portfolio_positions:
                            break

                        bar = self.stock_bars[sym][i]
                        is_quant = self.pit_db.is_quantamental_qualified(sym, current_date)
                        if not is_quant:
                            continue

                        is_ofi_positive = bar.ofi > 0.15
                        is_breakout_vol = bar.volume >= 1.25 * ma20_vol[sym][i]
                        is_price_above_ma = bar.close >= ma20_close[sym][i]
                        # Cong Anti-Chasing BM-02: Khong mua duoi khi gia da keo > 2.5 * ATR(14) xa MA20
                        is_not_overextended = (bar.close - ma20_close[sym][i]) <= (2.5 * atr14_map[sym][i])

                        if is_ofi_positive and is_breakout_vol and is_price_above_ma and is_not_overextended:
                            alloc = self.config.initial_capital * effective_alloc_pct
                            pending_buy_orders.append((sym, alloc, bar.exchange, bar.close))

            # 4. GHI NHAN GIA TRI TAI SAN RONG (NAV) CUOI PHIEN
            current_close_prices = {sym: self.stock_bars[sym][i].close for sym in symbols}
            engine.record_daily_equity(
                date=current_date,
                current_prices=current_close_prices,
                benchmark_price=bench_bar.close,
                initial_benchmark_price=initial_bench_price,
            )

        bench_prices = [b.close for b in bench_sub]
        return engine.build_result(period_label=period_label, benchmark_prices=bench_prices)

    def run_full_walk_forward(self) -> Dict[str, Any]:
        """Thuc thi toan bo quy trinh Walk-Forward: In-Sample, Out-of-Sample, va Toan ky."""
        # 1. Chay In-Sample (2021 - 2023)
        res_is = self.run_simulation(0, self.split_idx, period_label="IN_SAMPLE (2021 - 2023)")

        # 2. Chay Out-of-Sample (2024 - 2026) voi cung tham so
        res_oos = self.run_simulation(self.split_idx, self.total_bars, period_label="OUT_OF_SAMPLE (2024 - 2026)")

        # 3. Chay Toan ky (2021 - 2026)
        res_full = self.run_simulation(0, self.total_bars, period_label="FULL_PERIOD (2021 - 2026)")

        # 4. Tinh toan Walk-Forward Efficiency (WFE %)
        wfe = calculate_walk_forward_efficiency(res_oos.sharpe_ratio, res_is.sharpe_ratio)

        return {
            "in_sample": res_is,
            "out_of_sample": res_oos,
            "full": res_full,
            "walk_forward_efficiency_pct": wfe,
            "split_date": self.dates[self.split_idx],
            "total_bars": self.total_bars,
        }
