"""Walk-Forward Backtesting Coordinator (In-Sample vs Out-of-Sample Validation).

Dieu phoi kiem dinh da chu ky voi phan chia ro rang:
- Tap In-Sample (IS): 2021-01-04 den 2023-12-29 (Huan luyen & Kiem nghiem tren chu ky Bull/Bear)
- Tap Out-of-Sample (OOS): 2024-01-02 den 2026-10-24 (Kiem chung mu tren tap du lieu chua tung xem)
- Tinh toan Walk-Forward Efficiency (WFE %) de chung minh khong bi Overfitting.
- Ho tro Kiem dinh Thuc chien 3 Nam (2024, 2025, 2026) voi Luat ADR-024 (True Low SL, Time-Stop T+7).
"""

import argparse
import sys
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from src.backtesting.engine import T25BacktestEngine
from src.backtesting.historical_data import (
    fetch_real_historical_market_data_2024_2026,
    generate_benchmark_market_data,
)
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
        position_stops: Dict[str, float] = {}
        cooldown_until: Dict[str, int] = {}

        for i in range(start_idx, end_idx):
            current_date = self.dates[i]
            bench_bar = self.vnindex_bars[i]

            # 1. KHOP LENH MUA CHO TU PHIEN TRUOC (Khop tai gia Open cua phien i -> Triet tieu Look-ahead Bias)
            for sym, alloc_cap, exch, ref_p in pending_buy_orders:
                bar = self.stock_bars[sym][i]
                # Kiem tra lai khong mua duoi neu phien khop Open nhay Gap qua xa nen (> 2.5 * ATR)
                if (bar.open - ma20_close[sym][i]) > 2.5 * atr14_map[sym][i]:
                    continue
                batch = engine.execute_buy(
                    symbol=sym,
                    price=bar.open,
                    date=current_date,
                    day_idx=i,
                    exchange=exch,
                    allocated_capital=alloc_cap,
                    reference_price=bar.reference_price,
                )
                if batch is not None:
                    init_sl = calculate_t25_structural_stop_loss(
                        entry_price=bar.open,
                        atr_14=float(atr14_map[sym][i]),
                    )
                    position_stops[sym] = init_sl
            pending_buy_orders.clear()

            # 2. KIEM TRA TIN HIEU BAN CHO CAC VI THE DANG NAM GIU (ADR-024: True Low SL, Breakeven at TP1, Time-Stop T+7)
            symbols_to_evaluate = list(engine.positions.keys())
            for sym in symbols_to_evaluate:
                pos = engine.positions.get(sym)
                if not pos:
                    continue

                bar = self.stock_bars[sym][i]
                current_sl = position_stops.get(sym)
                if current_sl is None:
                    current_sl = calculate_t25_structural_stop_loss(
                        entry_price=pos.avg_cost,
                        atr_14=float(atr14_map[sym][i]),
                    )
                    position_stops[sym] = current_sl

                # Nang stop loss len hoa von khi gia vuot qua moc TP1 (1.5R)
                if self.config.enable_tp1_breakeven:
                    risk_r = max(pos.avg_cost - current_sl, pos.avg_cost * 0.03)
                    tp1_price = pos.avg_cost + 1.5 * risk_r
                    if bar.high >= tp1_price:
                        # Bu phi thue (0.40%)
                        breakeven_p = pos.avg_cost * 1.004
                        if breakeven_p > current_sl:
                            current_sl = breakeven_p
                            position_stops[sym] = current_sl

                # Cat lo theo day thap nhat trong phien (True Low SL)
                if bar.low <= current_sl:
                    sl_trade = engine.check_and_execute_stop_loss(
                        symbol=sym,
                        bar=bar,
                        day_idx=i,
                        stop_loss_price=current_sl,
                    )
                    if sl_trade is not None:
                        position_stops.pop(sym, None)
                        cooldown_until[sym] = i + self.config.cooldown_bars_after_sl
                        continue

                gain_pct = ((bar.close - pos.avg_cost) / pos.avg_cost) * 100.0 if pos.avg_cost > 0 else 0.0
                should_sell = False
                reason = "SIGNAL"

                # Chot loi khi vuot muc tieu take_profit_pct
                if gain_pct >= self.config.take_profit_pct:
                    should_sell = True
                    reason = "TAKE_PROFIT"
                # Tat toan xoay vong von sau 7 phien (Time-Stop T+7 ADR-024)
                elif self.config.enable_time_stop_t7:
                    first_batch = pos.batches[0] if pos.batches else None
                    first_day = first_batch.buy_day_idx if first_batch else i
                    holding_bars = i - first_day
                    if holding_bars >= 7 and gain_pct < 3.0:
                        should_sell = True
                        reason = "TIME_STOP_T7"
                # Dao chieu dong tien (OFI am kem gia duoi MA20)
                elif bar.close < ma20_close[sym][i] and bar.ofi < -0.20:
                    should_sell = True
                    reason = "TREND_REVERSAL"

                if should_sell:
                    sold_trade = engine.execute_sell(
                        symbol=sym,
                        price=bar.close,
                        date=current_date,
                        day_idx=i,
                        exchange=bar.exchange,
                        reference_price=bar.reference_price,
                        reason=reason,
                    )
                    if sold_trade is not None:
                        position_stops.pop(sym, None)

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

                        # Cooldown sau khi vi pham SL
                        if i < cooldown_until.get(sym, 0):
                            continue

                        # Loc thanh khoan toi thieu ADTV20 neu co cau hinh (ma20_close don vi 1,000 VND -> chia 1e6 ra ty VND)
                        if self.config.min_adtv_billion > 0.0:
                            adtv_bil = (ma20_vol[sym][i] * ma20_close[sym][i]) / 1e6
                            if adtv_bil < self.config.min_adtv_billion:
                                continue

                        bar = self.stock_bars[sym][i]
                        is_quant = self.pit_db.is_quantamental_qualified(sym, current_date)
                        if not is_quant:
                            continue

                        is_ofi_positive = bar.ofi > 0.15
                        is_breakout_vol = bar.volume >= 1.25 * ma20_vol[sym][i]
                        is_price_above_ma = bar.close >= ma20_close[sym][i]
                        # Cong Anti-Chasing BM-02: Khong mua duoi khi gia da keo > 2.5 * ATR(14) xa MA20
                        is_not_overextended = (bar.close - ma20_close[sym][i]) <= (2.5 * atr14_map[sym][i])
                        # Loc Relative Strength 1M: Co phieu phai khoe hon hoac bang VN-Index trong 20 phien (RS Leading)
                        is_leading_rs = True
                        if i >= 20:
                            ret_20d_stock = (bar.close - self.stock_bars[sym][i - 20].close) / max(self.stock_bars[sym][i - 20].close, 1e-4)
                            ret_20d_bench = (bench_bar.close - self.vnindex_bars[i - 20].close) / max(self.vnindex_bars[i - 20].close, 1e-4)
                            is_leading_rs = (ret_20d_stock >= ret_20d_bench)

                        if is_ofi_positive and is_breakout_vol and is_price_above_ma and is_not_overextended and is_leading_rs:
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

    def run_multi_year_2024_2026(self) -> Dict[str, Any]:
        """Chạy kiểm định chi tiết theo từng năm lịch 2024, 2025, 2026 và toàn kỳ 3 năm."""
        idx_2024: Optional[int] = None
        idx_2025: Optional[int] = None
        idx_2026: Optional[int] = None

        for i, d in enumerate(self.dates):
            if idx_2024 is None and d.startswith("2024-"):
                idx_2024 = i
            if idx_2025 is None and d.startswith("2025-"):
                idx_2025 = i
            if idx_2026 is None and d.startswith("2026-"):
                idx_2026 = i

        start_2024 = idx_2024 if idx_2024 is not None else 0
        start_2025 = idx_2025 if idx_2025 is not None else start_2024 + 250
        start_2026 = idx_2026 if idx_2026 is not None else start_2025 + 250
        end_all = self.total_bars

        # 1. Từng năm độc lập
        res_2024 = self.run_simulation(start_2024, min(start_2025, end_all), period_label="YEAR_2024")
        res_2025 = self.run_simulation(start_2025, min(start_2026, end_all), period_label="YEAR_2025") if start_2025 < end_all else None
        res_2026 = self.run_simulation(start_2026, end_all, period_label="YEAR_2026") if start_2026 < end_all else None

        # 2. Toàn kỳ 3 năm liên tục (2024 - 2026)
        res_full_3y = self.run_simulation(start_2024, end_all, period_label="FULL_3Y (2024 - 2026)")

        return {
            "year_2024": res_2024,
            "year_2025": res_2025,
            "year_2026": res_2026,
            "full_3y": res_full_3y,
            "start_date": self.dates[start_2024],
            "end_date": self.dates[end_all - 1],
            "total_bars_3y": end_all - start_2024,
        }


def format_backtest_report_text(title: str, res: BacktestResult) -> str:
    """Định dạng bản báo cáo hiệu suất dạng bảng text chuyên nghiệp."""
    lines = [
        f"============================================================",
        f"  {title.upper()}",
        f"============================================================",
        f"  Lợi nhuận ròng:        {res.total_return_pct:>+8.2f}%",
        f"  Lợi nhuận VN-Index:    {res.benchmark_return_pct:>+8.2f}%",
        f"  Alpha vượt trội:       {res.alpha_pct:>+8.2f}%",
        f"  CAGR (Tăng trưởng kép): {res.cagr_pct:>+7.2f}% / năm",
        f"  Max Drawdown (Sụt giảm): {res.max_drawdown_pct:>7.2f}%",
        f"  Sharpe Ratio:          {res.sharpe_ratio:>8.2f}",
        f"  Sortino Ratio:         {res.sortino_ratio:>8.2f}",
        f"  Calmar Ratio:          {res.calmar_ratio:>8.2f}",
        f"  Win Rate (Tỷ lệ thắng): {res.win_rate_pct:>7.2f}% ({res.winning_trades}/{res.total_trades} lệnh)",
        f"  Profit Factor:         {res.profit_factor:>8.2f}",
        f"  Số lần chặn T+2.5:     {res.t25_blocked_count:>8d}",
        f"  Số lần khóa sàn kẹt:   {res.floor_lock_blocked_count:>8d}",
    ]
    # Phân bổ lý do đóng lệnh
    reasons_count: Dict[str, int] = {}
    for t in res.trades:
        reasons_count[t.reason] = reasons_count.get(t.reason, 0) + 1
    if reasons_count:
        lines.append(f"  Phân bổ lý do thoát:")
        for r, cnt in sorted(reasons_count.items(), key=lambda x: -x[1]):
            lines.append(f"    - {r:<16}: {cnt} lệnh ({round(cnt/len(res.trades)*100, 1)}%)")
    lines.append(f"============================================================")
    return "\n".join(lines)


def run_cli():
    """Entrypoint CLI cho kiểm định lịch sử thực tế."""
    parser = argparse.ArgumentParser(description="Neiro-Stock-VN Historical Backtesting (2024 - 2026)")
    parser.add_argument("--real-data", action="store_true", help="Kéo dữ liệu OHLCV lịch sử thật từ Entrade API")
    parser.add_argument("--min-adtv", type=float, default=15.0, help="Ngưỡng thanh khoản tối thiểu ADTV20 (tỷ VND)")
    args = parser.parse_args()

    print("\n[Backtest 2024-2026] Bắt đầu khởi tạo dữ liệu kiểm định...")
    cfg = BacktestConfig(
        initial_capital=1_000_000_000.0,
        min_adtv_billion=args.min_adtv if args.real_data else 0.0,
        enable_time_stop_t7=True,
        enable_tp1_breakeven=True,
        cooldown_bars_after_sl=3,
    )

    if args.real_data:
        print("[Backtest 2024-2026] Đang nạp dữ liệu lịch sử thật (2023 - 2026) trực tiếp trên RAM...")
        stocks, idx_bars, pit = fetch_real_historical_market_data_2024_2026()
    else:
        print("[Backtest 2024-2026] Đang nạp dữ liệu benchmark chuẩn...")
        stocks, idx_bars, pit = generate_benchmark_market_data()

    coord = WalkForwardCoordinator(
        config=cfg,
        stock_bars_dict=stocks,
        vnindex_bars=idx_bars,
        pit_db=pit,
    )

    results = coord.run_multi_year_2024_2026()
    print(f"\n[Dữ liệu] Từ ngày: {results['start_date']} đến ngày: {results['end_date']} ({results['total_bars_3y']} phiên)")

    if results.get("year_2024"):
        print("\n" + format_backtest_report_text("NĂM 2024 (Out-of-Sample Year 1)", results["year_2024"]))
    if results.get("year_2025"):
        print("\n" + format_backtest_report_text("NĂM 2025 (Out-of-Sample Year 2)", results["year_2025"]))
    if results.get("year_2026"):
        print("\n" + format_backtest_report_text("NĂM 2026 (Out-of-Sample Year 3)", results["year_2026"]))
    if results.get("full_3y"):
        print("\n" + format_backtest_report_text("TỔNG KỲ 3 NĂM (2024 - 2026 TOÀN DIỆN)", results["full_3y"]))


if __name__ == "__main__":
    run_cli()
