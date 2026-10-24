"""Volume Profile (POC, VAH, VAL, HVN, LVN / Air Pockets) cho co phieu VN."""
from dataclasses import dataclass
from typing import List, Tuple, Dict
import numpy as np


@dataclass
class VolumeBin:
    price_level: float
    volume: float
    is_poc: bool
    is_hvn: bool
    is_lvn: bool


@dataclass
class VolumeProfileResult:
    symbol: str
    poc_price: float               # Point of Control (Gia co volume lon nhat)
    vah_price: float               # Value Area High (70% Volume tren)
    val_price: float               # Value Area Low (70% Volume duoi)
    hvn_levels: List[float]        # Danh sach cac moc thanh tri phong thu
    lvn_levels: List[float]        # Danh sach vung chan khong thanh khoan (Air Pockets)
    bins: List[VolumeBin]


def compute_volume_profile(
    prices: List[float],
    volumes: List[float],
    symbol: str = "TICKER",
    num_bins: int = 40
) -> VolumeProfileResult:
    """Phan tich ban do Volume at Price, xac dinh POC, VAH, VAL va vung Air Pockets.
    
    Args:
        prices: Danh sach gia khop
        volumes: Danh sach khoi luong tuong ung
        symbol: Ma co phieu
        num_bins: So buoc gia phan tach
    """
    if len(prices) != len(volumes) or len(prices) == 0:
        raise ValueError("Prices and volumes must be non-empty and have identical length.")

    min_p, max_p = min(prices), max(prices)
    if min_p == max_p:
        # Bien do phang
        return VolumeProfileResult(
            symbol=symbol, poc_price=min_p, vah_price=min_p, val_price=min_p,
            hvn_levels=[min_p], lvn_levels=[],
            bins=[VolumeBin(price_level=min_p, volume=sum(volumes), is_poc=True, is_hvn=True, is_lvn=False)]
        )

    bin_edges = np.linspace(min_p, max_p, num_bins + 1)
    bin_volumes = np.zeros(num_bins)

    for p, v in zip(prices, volumes):
        idx = int(np.digitize(p, bin_edges) - 1)
        idx = min(max(idx, 0), num_bins - 1)
        bin_volumes[idx] += v

    bin_centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])
    total_volume = float(np.sum(bin_volumes))
    mean_vol = float(np.mean(bin_volumes)) if num_bins > 0 else 1.0

    poc_idx = int(np.argmax(bin_volumes))
    poc_price = float(bin_centers[poc_idx])

    # Tinh Value Area (70% Volume bao quanh POC)
    target_va_vol = 0.70 * total_volume
    accumulated_vol = bin_volumes[poc_idx]
    low_idx, high_idx = poc_idx, poc_idx

    while accumulated_vol < target_va_vol and (low_idx > 0 or high_idx < num_bins - 1):
        next_low_vol = bin_volumes[low_idx - 1] if low_idx > 0 else -1.0
        next_high_vol = bin_volumes[high_idx + 1] if high_idx < num_bins - 1 else -1.0

        if next_high_vol >= next_low_vol:
            high_idx += 1
            accumulated_vol += next_high_vol
        else:
            low_idx -= 1
            accumulated_vol += next_low_vol

    val_price = float(bin_centers[low_idx])
    vah_price = float(bin_centers[high_idx])

    # Xac dinh HVN (>= 1.5x MA) va LVN (<= 0.4x MA)
    hvn_levels = []
    lvn_levels = []
    bins_result = []

    for i in range(num_bins):
        price = float(bin_centers[i])
        vol = float(bin_volumes[i])
        is_poc = (i == poc_idx)
        is_hvn = (vol >= 1.5 * mean_vol and not is_poc)
        is_lvn = (vol <= 0.40 * mean_vol and vol > 0)

        if is_hvn or is_poc:
            hvn_levels.append(price)
        if is_lvn:
            lvn_levels.append(price)

        bins_result.append(VolumeBin(
            price_level=price, volume=vol, is_poc=is_poc, is_hvn=is_hvn, is_lvn=is_lvn
        ))

    return VolumeProfileResult(
        symbol=symbol,
        poc_price=round(poc_price, 2),
        vah_price=round(vah_price, 2),
        val_price=round(val_price, 2),
        hvn_levels=[round(x, 2) for x in hvn_levels],
        lvn_levels=[round(x, 2) for x in lvn_levels],
        bins=bins_result
    )
