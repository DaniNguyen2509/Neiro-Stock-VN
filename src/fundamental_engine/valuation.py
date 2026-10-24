"""Dinh gia phan vi lich su PE/PB Banding."""
from typing import List, Tuple


def calculate_valuation_percentile(current_metric: float, historical_metrics: List[float]) -> float:
    """Tinh phan vi tich luy (0.0% - 100.0%) cua dinh gia hien tai so voi lich su.
    
    Args:
        current_metric: P/E hoac P/B hien tai
        historical_metrics: Chuoi du lieu dinh gia trong qua khu (vi du 3 nam)
        
    Returns:
        Phan vi tinh bang % (0.0 den 100.0)
    """
    if not historical_metrics:
        return 50.0
    count_below = sum(1 for val in historical_metrics if val <= current_metric)
    return round((count_below / len(historical_metrics)) * 100.0, 2)


def classify_valuation_regime(percentile: float) -> str:
    """Phan loai che do dinh gia co phieu:
    - DEEP_VALUE: < 20% (Vung chiet khau re hiem co)
    - FAIR_VALUE: 20% - 80% (Vung gia tri hop ly)
    - OVERVALUED: > 80% (Vung dinh gia qua nong, rui ro bong bong)
    """
    if percentile < 20.0:
        return "DEEP_VALUE"
    elif percentile > 80.0:
        return "OVERVALUED"
    return "FAIR_VALUE"
