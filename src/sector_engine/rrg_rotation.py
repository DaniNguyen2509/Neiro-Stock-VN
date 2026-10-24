"""Mo hinh Relative Rotation Graph (RRG) dinh luong luan chuyen nganh."""
from dataclasses import dataclass
from typing import List, Tuple
import numpy as np


@dataclass
class RRGResult:
    sector_name: str
    rs_ratio: float       # Suc manh gia tuong doi so voi VN-Index (Moc chuan: 100)
    rs_momentum: float    # Gia toc bien dong cua dong tien (Moc chuan: 100)
    quadrant: str         # LEADING, WEAKENING, LAGGING, IMPROVING


def compute_rrg_quadrant(rs_ratio: float, rs_momentum: float) -> str:
    """Xac dinh 4 goc phan tu RRG."""
    if rs_ratio >= 100.0 and rs_momentum >= 100.0:
        return "LEADING"
    elif rs_ratio >= 100.0 and rs_momentum < 100.0:
        return "WEAKENING"
    elif rs_ratio < 100.0 and rs_momentum < 100.0:
        return "LAGGING"
    else:
        return "IMPROVING"


def calculate_rrg_series(
    sector_closes: List[float],
    benchmark_closes: List[float],
    sector_name: str = "SECTOR"
) -> RRGResult:
    """Tinh toan RS-Ratio va RS-Momentum theo chuan Julius de Kempenaer (JdK)."""
    if len(sector_closes) != len(benchmark_closes) or len(sector_closes) < 14:
        # Fallback trung lap
        return RRGResult(sector_name=sector_name, rs_ratio=100.0, rs_momentum=100.0, quadrant="IMPROVING")

    s_arr = np.array(sector_closes, dtype=float)
    b_arr = np.array(benchmark_closes, dtype=float)
    raw_rs = s_arr / b_arr

    # Chuan hoa ve moc trung tam 100
    mean_rs = np.mean(raw_rs)
    std_rs = np.std(raw_rs) if np.std(raw_rs) > 1e-6 else 1.0
    rs_ratio = 100.0 + 10.0 * float((raw_rs[-1] - mean_rs) / std_rs)

    # Gia toc Momentum (bien thien cua RS-Ratio)
    delta_rs = np.diff(raw_rs)
    mean_d = np.mean(delta_rs)
    std_d = np.std(delta_rs) if np.std(delta_rs) > 1e-6 else 1.0
    rs_momentum = 100.0 + 10.0 * float((delta_rs[-1] - mean_d) / std_d)

    quadrant = compute_rrg_quadrant(rs_ratio, rs_momentum)

    return RRGResult(
        sector_name=sector_name,
        rs_ratio=round(rs_ratio, 2),
        rs_momentum=round(rs_momentum, 2),
        quadrant=quadrant
    )
