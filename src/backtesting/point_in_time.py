"""Point-in-Time Financial Engine - Ngan chan triet de Point-in-Time Data Bias.

Dam bao tai bat ky thoi diem as_of_date nao trong qua khu, thuat toan CHI DUOC PHEP
su dung Bao cao Tai chinh (BCTC) da thuc su duoc cong bo tren thi truong (filing_date <= as_of_date).
Tuyet doi khong dung so lieu quy truoc khi het han nop BCTC quy dinh boi UBCKNN.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class PITFinancialSnapshot:
    """Ban ghi BCTC voi moc thoi gian cong bo thuc te (Point-in-Time)."""
    symbol: str
    year: int
    quarter: int
    period_end_date: str  # Ngay chot so sach quy (vi du 2023-03-31)
    filing_date: str      # Ngay nop BCTC chinh thuc cong khai (vi du 2023-04-30)
    f_score: int          # Piotroski F-score (0-9)
    cfo_ni_ratio: float   # CFO / Net Income
    is_bank: bool = False
    camel_score: float = 0.0
    camel_tier: str = "N/A"


class PointInTimeDatabase:
    """Co so du lieu luu tru lich su BCTC Point-in-Time."""

    def __init__(self):
        self._records: Dict[str, List[PITFinancialSnapshot]] = {}

    def add_snapshot(self, snapshot: PITFinancialSnapshot):
        """Them mot ban ghi BCTC vao kho du lieu."""
        if snapshot.symbol not in self._records:
            self._records[snapshot.symbol] = []
        self._records[snapshot.symbol].append(snapshot)
        # Sap xep tang dan theo filing_date
        self._records[snapshot.symbol].sort(key=lambda x: x.filing_date)

    def get_latest_financial(self, symbol: str, as_of_date: str) -> Optional[PITFinancialSnapshot]:
        """Lay BCTC moi nhat da duoc cong bo tai thoi diem as_of_date.
        
        Args:
            symbol: Ma co phieu.
            as_of_date: Ngay kiem tra dinh dang YYYY-MM-DD.
            
        Returns:
            Snapshot BCTC hop le hoac None neu chua co BCTC nao duoc cong bo truoc as_of_date.
        """
        snapshots = self._records.get(symbol, [])
        valid_snapshots = [s for s in snapshots if s.filing_date <= as_of_date]
        if not valid_snapshots:
            return None
        return valid_snapshots[-1]

    def is_quantamental_qualified(self, symbol: str, as_of_date: str) -> bool:
        """Kiem tra co phieu co dat tieu chuan Quantamental tai as_of_date hay khong."""
        fin = self.get_latest_financial(symbol, as_of_date)
        if fin is None:
            return False

        if fin.is_bank:
            # Ngan hang: Dat hang A (CAMEL score >= 80)
            return fin.camel_score >= 80.0 or "HẠNG A" in fin.camel_tier
        else:
            # Doanh nghiep thong thuong: F-score >= 7 hoac (F-score >= 6 kem CFO/NI >= 1.0)
            return (fin.f_score >= 7) or (fin.f_score >= 6 and fin.cfo_ni_ratio >= 1.0)
