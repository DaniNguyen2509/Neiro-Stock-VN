"""Data ingestion and normalization for Vietnam stock market."""
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class FinancialReport:
    """Bao cao tai chinh quy/nam cua doanh nghiep niem yet."""
    symbol: str
    year: int
    quarter: int
    net_income: float            # Loi nhuan sau thue (VND)
    operating_cash_flow: float   # Dong tien thuan tu HDKD (CFO) (VND)
    total_assets: float          # Tong tai san (VND)
    roa: float                   # Ty suat sinh loi tren tai san (ROA = NetIncome / TotalAssets)
    long_term_debt: float        # No vay dai han (VND)
    current_ratio: float         # Ty so thanh toan hien hanh (Current Assets / Current Liabilities)
    shares_outstanding: int      # So luong co phieu luu hanh
    gross_margin: float          # Bien loi nhuan gop (Gross Profit / Revenue)
    asset_turnover: float        # Vong quay tai san (Revenue / Total Assets)


@dataclass
class StockFinancials:
    """Cap du lieu tai chinh 2 ky lien tiep de tinh F-Score."""
    symbol: str
    company_name: str
    sector: str
    current_price: float
    current: FinancialReport
    previous: FinancialReport
    pe_history: List[float]      # Lich su P/E 3 nam (750 phien)
    pb_history: List[float]      # Lich su P/B 3 nam


def get_mock_vietnam_stocks() -> List[StockFinancials]:
    """Cung cap bo du lieu mock chuan dinh che cho top co phieu tieu bieu VN30."""
    return [
        StockFinancials(
            symbol="HPG",
            company_name="Tap doan Hoa Phat",
            sector="Thep & Vat lieu xay dung",
            current_price=28500.0,
            current=FinancialReport(
                symbol="HPG", year=2026, quarter=1,
                net_income=3200e9, operating_cash_flow=4500e9, total_assets=190000e9,
                roa=0.068, long_term_debt=35000e9, current_ratio=1.65,
                shares_outstanding=5814785700, gross_margin=0.165, asset_turnover=0.85
            ),
            previous=FinancialReport(
                symbol="HPG", year=2025, quarter=4,
                net_income=2800e9, operating_cash_flow=3100e9, total_assets=185000e9,
                roa=0.061, long_term_debt=38000e9, current_ratio=1.55,
                shares_outstanding=5814785700, gross_margin=0.142, asset_turnover=0.81
            ),
            pe_history=[8.5, 9.2, 10.1, 11.5, 12.8, 14.2, 16.0, 18.5, 7.8, 8.2],
            pb_history=[1.1, 1.25, 1.35, 1.5, 1.65, 1.8, 1.95, 2.1, 1.05, 1.15]
        ),
        StockFinancials(
            symbol="FPT",
            company_name="Cong ty Co phan FPT",
            sector="Cong nghe thong tin",
            current_price=135000.0,
            current=FinancialReport(
                symbol="FPT", year=2026, quarter=1,
                net_income=2100e9, operating_cash_flow=2800e9, total_assets=68000e9,
                roa=0.125, long_term_debt=8000e9, current_ratio=1.45,
                shares_outstanding=1270000000, gross_margin=0.395, asset_turnover=0.92
            ),
            previous=FinancialReport(
                symbol="FPT", year=2025, quarter=4,
                net_income=1850e9, operating_cash_flow=2200e9, total_assets=64000e9,
                roa=0.116, long_term_debt=9000e9, current_ratio=1.38,
                shares_outstanding=1270000000, gross_margin=0.388, asset_turnover=0.89
            ),
            pe_history=[16.0, 17.5, 18.2, 19.8, 21.0, 22.5, 24.0, 26.5, 15.5, 16.8],
            pb_history=[3.2, 3.5, 3.8, 4.1, 4.5, 4.8, 5.2, 5.6, 3.0, 3.3]
        ),
        StockFinancials(
            symbol="SSI",
            company_name="Chung khoan SSI",
            sector="Dich vu tai chinh & Chung khoan",
            current_price=32400.0,
            current=FinancialReport(
                symbol="SSI", year=2026, quarter=1,
                net_income=950e9, operating_cash_flow=1400e9, total_assets=58000e9,
                roa=0.065, long_term_debt=12000e9, current_ratio=1.52,
                shares_outstanding=1511000000, gross_margin=0.550, asset_turnover=0.45
            ),
            previous=FinancialReport(
                symbol="SSI", year=2025, quarter=4,
                net_income=820e9, operating_cash_flow=980e9, total_assets=55000e9,
                roa=0.060, long_term_debt=13500e9, current_ratio=1.45,
                shares_outstanding=1511000000, gross_margin=0.525, asset_turnover=0.42
            ),
            pe_history=[12.0, 13.5, 15.0, 17.5, 20.0, 22.5, 25.0, 28.0, 11.0, 12.5],
            pb_history=[1.3, 1.45, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 1.2, 1.35]
        ),
        StockFinancials(
            symbol="VCB",
            company_name="Ngan hang Ngoai thuong Viet Nam",
            sector="Ngan hang",
            current_price=94000.0,
            current=FinancialReport(
                symbol="VCB", year=2026, quarter=1,
                net_income=10500e9, operating_cash_flow=15000e9, total_assets=1850000e9,
                roa=0.023, long_term_debt=50000e9, current_ratio=1.20,
                shares_outstanding=5589000000, gross_margin=0.480, asset_turnover=0.08
            ),
            previous=FinancialReport(
                symbol="VCB", year=2025, quarter=4,
                net_income=9800e9, operating_cash_flow=12000e9, total_assets=1800000e9,
                roa=0.022, long_term_debt=52000e9, current_ratio=1.18,
                shares_outstanding=5589000000, gross_margin=0.470, asset_turnover=0.078
            ),
            pe_history=[11.5, 12.8, 13.5, 14.5, 15.8, 17.0, 18.5, 20.0, 10.8, 11.2],
            pb_history=[2.1, 2.3, 2.5, 2.7, 2.9, 3.1, 3.3, 3.6, 2.0, 2.2]
        )
    ]
