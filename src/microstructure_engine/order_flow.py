"""Order Flow Imbalance (OFI) va Large Block Detection."""
from typing import List, Dict, Any


def compute_order_flow_imbalance(active_buy_vol: float, active_sell_vol: float) -> float:
    """Tinh ty le mat can bang dong lenh chu dong (OFI: -1.0 den +1.0).
    
    OFI = (Buy - Sell) / (Buy + Sell)
    """
    total = active_buy_vol + active_sell_vol
    if total <= 0:
        return 0.0
    return round((active_buy_vol - active_sell_vol) / total, 3)


def detect_large_blocks(ticks: List[Dict[str, Any]], min_volume: int = 100_000) -> List[Dict[str, Any]]:
    """Loc cac lenh ca map khop lo lon >= min_volume co phieu."""
    return [t for t in ticks if t.get("volume", 0) >= min_volume]
