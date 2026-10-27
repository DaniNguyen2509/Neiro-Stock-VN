"""Piotroski F-Score & Fundamental Quant Screener cho TTCK Viet Nam."""
from dataclasses import dataclass
from typing import List
from src.collector.data_loader import FinancialReport, StockFinancials


@dataclass
class PiotroskiDetail:
    """Chi tiet 9 tieu chi cua Piotroski F-Score."""
    # Profitability (Kha nang sinh loi)
    f1_roa_positive: int
    f2_cfo_positive: int
    f3_delta_roa_positive: int
    f4_cfo_greater_than_ni: int     # Chat luong loi nhuan: CFO > Net Income
    # Leverage, Liquidity and Source of Funds (Don bay & Thanh khoan)
    f5_delta_long_term_debt_lower: int  # No vay dai han giam
    f6_delta_current_ratio_higher: int  # Kha nang thanh toan hien hanh tang
    f7_no_new_shares_issued: int        # Khong pha loang co phieu
    # Operating Efficiency (Hieu qua hoat dong)
    f8_delta_gross_margin_higher: int   # Bien lai gop mo rong
    f9_delta_asset_turnover_higher: int # Vong quay tai san tang

    @property
    def total_score(self) -> int:
        return (
            self.f1_roa_positive + self.f2_cfo_positive + self.f3_delta_roa_positive +
            self.f4_cfo_greater_than_ni + self.f5_delta_long_term_debt_lower +
            self.f6_delta_current_ratio_higher + self.f7_no_new_shares_issued +
            self.f8_delta_gross_margin_higher + self.f9_delta_asset_turnover_higher
        )


@dataclass
class ScreenerResult:
    """Ket qua cham diem Quantamental cho mot ma co phieu."""
    symbol: str
    company_name: str
    sector: str
    price: float
    f_score: int
    earnings_quality_ratio: float  # CFO / Net Income
    is_institutional_grade: bool   # F-Score >= 7
    details: PiotroskiDetail


def calculate_piotroski_score(cur: FinancialReport, prev: FinancialReport) -> PiotroskiDetail:
    """Tinh toan 9 tieu chi F-Score toan dien theo chuan Stanford."""
    f1 = 1 if cur.roa > 0 else 0
    f2 = 1 if cur.operating_cash_flow > 0 else 0
    f3 = 1 if (cur.roa - prev.roa) > 0 else 0
    f4 = 1 if cur.operating_cash_flow > cur.net_income else 0

    f5 = 1 if (cur.long_term_debt - prev.long_term_debt) <= 0 else 0
    f6 = 1 if (cur.current_ratio - prev.current_ratio) > 0 else 0
    f7 = 1 if cur.shares_outstanding <= prev.shares_outstanding else 0

    f8 = 1 if (cur.gross_margin - prev.gross_margin) > 0 else 0
    f9 = 1 if (cur.asset_turnover - prev.asset_turnover) > 0 else 0

    return PiotroskiDetail(
        f1_roa_positive=f1,
        f2_cfo_positive=f2,
        f3_delta_roa_positive=f3,
        f4_cfo_greater_than_ni=f4,
        f5_delta_long_term_debt_lower=f5,
        f6_delta_current_ratio_higher=f6,
        f7_no_new_shares_issued=f7,
        f8_delta_gross_margin_higher=f8,
        f9_delta_asset_turnover_higher=f9
    )


def screen_stocks(stock_list: List[StockFinancials]) -> List[ScreenerResult]:
    """Loc va xep hang danh sach co phieu theo tieu chuan Quantamental."""
    results = []
    for item in stock_list:
        detail = calculate_piotroski_score(item.current, item.previous)
        score = detail.total_score
        net_inc = item.current.net_income
        cfo = item.current.operating_cash_flow
        if abs(net_inc) < 1e-6:
            cfo_ratio = 0.0
        else:
            cfo_ratio = cfo / net_inc

        # Doanh nghiep chi duoc xep hang Dinh che khi F-Score >= 7, co lai va dong tien manh
        is_institutional = bool(score >= 7 and net_inc > 0 and cfo_ratio >= 1.0)

        results.append(ScreenerResult(
            symbol=item.symbol,
            company_name=item.company_name,
            sector=item.sector,
            price=item.current_price,
            f_score=score,
            earnings_quality_ratio=round(cfo_ratio, 2),
            is_institutional_grade=is_institutional,
            details=detail
        ))
    # Xep hang giam dan theo F-score
    results.sort(key=lambda x: x.f_score, reverse=True)
    return results
