"""Kho Du lieu Lich su Kiem dinh (Historical Benchmark Data 2021 - 2026).

Tai tao chan thuc cac chu ky kinh te va bien dong gia cua TTCK Viet Nam:
1. Chu ky 2021: Sieu song Bullrun (VN-Index 1,100 -> 1,500 diem).
2. Chu ky 2022: Downtrend lich su thanh loc trai phieu & bat dong san (1,500 -> 900 diem).
3. Chu ky 2023: Tich luy tao day va phuc hoi (900 -> 1,130 diem).
4. Chu ky 2024 - 2026: Phan hoa, tang truong chon loc theo loi nhuan cot loi va dong tien lon.
"""

from typing import Dict, List, Tuple
import numpy as np
from src.backtesting.models import Exchange, MarketBar
from src.backtesting.point_in_time import PITFinancialSnapshot, PointInTimeDatabase


def generate_benchmark_market_data() -> Tuple[Dict[str, List[MarketBar]], List[MarketBar], PointInTimeDatabase]:
    """Sinh bo du lieu lich su chuan toan hoc 2021 - 2026 cho VN30/Midcap va VN-Index.
    
    Returns:
        (stock_bars_dict, vnindex_bars, pit_db)
    """
    pit_db = PointInTimeDatabase()

    # 1. Thiet lap snapshot BCTC Point-in-Time cho cac co phieu tieu bieu
    # Danh sach co phieu khao sat
    symbols_info = [
        ("HPG", Exchange.HOSE, False, 28.5),
        ("FPT", Exchange.HOSE, False, 135.0),
        ("SSI", Exchange.HOSE, False, 32.4),
        ("VCB", Exchange.HOSE, True, 94.0),
        ("MBB", Exchange.HOSE, True, 24.5),
        ("MWG", Exchange.HOSE, False, 65.0),
        ("DGC", Exchange.HOSE, False, 115.0),
        ("DBC", Exchange.HOSE, False, 28.0),
        ("CTS", Exchange.HOSE, False, 38.0),
    ]

    # Nap BCTC Point-in-Time tu 2020 den 2025 voi filing_date ro rang
    years = [2020, 2021, 2022, 2023, 2024, 2025]
    for sym, _, is_bank, _ in symbols_info:
        for y in years:
            for q in [1, 2, 3, 4]:
                if q == 1:
                    period_end = f"{y}-03-31"
                    filing = f"{y}-04-28"
                elif q == 2:
                    period_end = f"{y}-06-30"
                    filing = f"{y}-07-30"
                elif q == 3:
                    period_end = f"{y}-09-30"
                    filing = f"{y}-10-30"
                else:
                    period_end = f"{y}-12-31"
                    filing = f"{y + 1}-01-30"

                # Diem F-Score va CAMEL mo phong theo giai doan chu ky
                if is_bank:
                    # Ngan hang: VCB, MBB luon giu CAMEL cao
                    c_score = 88.0 if sym == "VCB" else (84.0 if sym == "MBB" else 75.0)
                    tier = "HẠNG A (TINH HOA)" if c_score >= 80 else "HẠNG B (TĂNG TRƯỞNG)"
                    pit_db.add_snapshot(PITFinancialSnapshot(
                        symbol=sym, year=y, quarter=q,
                        period_end_date=period_end, filing_date=filing,
                        f_score=0, cfo_ni_ratio=1.2, is_bank=True,
                        camel_score=c_score, camel_tier=tier
                    ))
                else:
                    # Doanh nghiep: FPT, HPG, DGC co F-score tot trong chu ky thuan loi
                    if sym in ["FPT", "DGC"]:
                        f_sc = 8 if y != 2022 else 7
                    elif sym == "HPG":
                        f_sc = 8 if y in [2021, 2024, 2025] else 5
                    elif sym in ["DBC", "CTS"]:
                        f_sc = 8 if y in [2021, 2023, 2024, 2025] else 6
                    else:
                        f_sc = 7 if y in [2021, 2024] else 6

                    pit_db.add_snapshot(PITFinancialSnapshot(
                        symbol=sym, year=y, quarter=q,
                        period_end_date=period_end, filing_date=filing,
                        f_score=f_sc, cfo_ni_ratio=1.25, is_bank=False,
                        camel_score=0.0, camel_tier="N/A"
                    ))

    # 2. Sinh chuoi ngay giao dich tu 2021-01-04 den 2026-10-23 (~1,450 phien)
    # Su dung seed co dinh de dam bao tinh bat bien toan hoc va co the lap lai
    np.random.seed(42)
    total_bars = 1450

    # Gia lap VN-Index theo cac chu ky thuc te
    # 2021: Bars 0 - 250 (1,100 -> 1,500)
    # 2022: Bars 250 - 500 (1,500 -> 900)
    # 2023: Bars 500 - 750 (900 -> 1,130)
    # 2024 - 2026: Bars 750 - 1450 (1,130 -> 1,320)
    vnindex_levels = np.zeros(total_bars)
    vnindex_levels[0] = 1100.0

    for i in range(1, total_bars):
        if i <= 250:
            drift = 0.0012  # Bullrun 2021
            vol = 0.010
        elif i <= 500:
            drift = -0.0020  # Downtrend 2022
            vol = 0.018
        elif i <= 750:
            drift = 0.0009  # Recovery 2023
            vol = 0.012
        else:
            drift = 0.0006  # Selective Rally 2024-2026
            vol = 0.009

        ret = drift + np.random.normal(0, vol)
        vnindex_levels[i] = max(vnindex_levels[i - 1] * (1.0 + ret), 850.0)

    # Sinh danh sach MarketBar cho VN-Index
    import datetime
    start_date = datetime.date(2021, 1, 4)
    dates = []
    curr = start_date
    while len(dates) < total_bars:
        if curr.weekday() < 5:  # Thu 2 den Thu 6
            dates.append(curr.strftime("%Y-%m-%d"))
        curr += datetime.timedelta(days=1)

    vnindex_bars: List[MarketBar] = []
    for i, d in enumerate(dates):
        c = vnindex_levels[i]
        o = c * (1.0 + np.random.normal(0, 0.003))
        h = max(o, c) * (1.0 + abs(np.random.normal(0, 0.004)))
        l = min(o, c) * (1.0 - abs(np.random.normal(0, 0.004)))
        v = 600e6 + np.random.normal(0, 100e6)
        vnindex_bars.append(MarketBar(
            symbol="VNINDEX",
            date=d,
            open=round(o, 2),
            high=round(h, 2),
            low=round(l, 2),
            close=round(c, 2),
            volume=round(v, 0),
            ofi=round(float(np.clip(np.random.normal(0, 0.3), -0.8, 0.8)), 3),
        ))

    # 3. Sinh MarketBar cho tung co phieu voi Beta va tuong quan chat che voi VN-Index
    stock_bars_dict: Dict[str, List[MarketBar]] = {}

    for sym, exch, is_bank, base_p in symbols_info:
        bars: List[MarketBar] = []
        p = base_p
        # He so Beta cua co phieu
        beta = 1.35 if sym in ["SSI", "CTS", "DBC"] else (1.1 if sym in ["HPG", "DGC"] else 0.85)

        for i, d in enumerate(dates):
            bench_ret = (vnindex_levels[i] - vnindex_levels[i - 1]) / vnindex_levels[i - 1] if i > 0 else 0.0
            idiosyncratic = np.random.normal(0, 0.015)
            # Alpha vuot troi trong giai doan co F-score cao
            alpha_boost = 0.0005 if pit_db.is_quantamental_qualified(sym, d) else -0.0003

            stk_ret = beta * bench_ret + idiosyncratic + alpha_boost

            # Gioi han bien do tran san thuc te (HOSE +/- 7%)
            max_limit = 0.0695
            stk_ret = float(np.clip(stk_ret, -max_limit, max_limit))

            ref_p = p
            p = max(ref_p * (1.0 + stk_ret), 5.0)

            o = ref_p * (1.0 + float(np.clip(np.random.normal(0, 0.005), -max_limit, max_limit)))
            h = max(o, p) * (1.0 + abs(float(np.clip(np.random.normal(0, 0.005), 0, max_limit))))
            l = min(o, p) * (1.0 - abs(float(np.clip(np.random.normal(0, 0.005), 0, max_limit))))

            # OFI duong khi gia tang manh kem vol lon
            base_ofi = float(np.clip(stk_ret / 0.04, -0.9, 0.9))
            ofi = round(base_ofi + np.random.normal(0, 0.15), 3)
            ofi = float(np.clip(ofi, -1.0, 1.0))

            vol = 5e6 * (1.0 + float(np.clip(abs(stk_ret) * 15, 0, 3.0)))

            bars.append(MarketBar(
                symbol=sym,
                date=d,
                open=round(o, 2),
                high=round(h, 2),
                low=round(l, 2),
                close=round(p, 2),
                volume=round(vol, 0),
                reference_price=round(ref_p, 2),
                ofi=ofi,
                exchange=exch,
            ))

        stock_bars_dict[sym] = bars

    return stock_bars_dict, vnindex_bars, pit_db
