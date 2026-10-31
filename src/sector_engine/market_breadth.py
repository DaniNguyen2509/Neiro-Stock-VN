"""Bộ Phân Tích Độ Rộng Thị Trường & Cầu Chì Hệ Thống T+2.5 (Market Breadth Circuit Breaker).

Giám sát tỷ lệ mã Tăng / Giảm thực tế của VN-Index (A/D Ratio) để bảo vệ nhà đầu tư
khỏi hội chứng 'Xanh Vỏ Đỏ Lòng' (kéo trụ giữ chỉ số trong khi 70%+ cổ phiếu midcap gãy nền)
trong khoảng thời gian kẹp chu kỳ thanh toán T+2.5.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class MarketBreadthSnapshot:
    """Trạng thái độ rộng thị trường và chế độ cầu chì phòng vệ T+2.5."""

    advances: int
    declines: int
    unchanged: int
    breadth_pct: float
    total_value_billion: float
    regime: str  # 'BULLISH_EXPANSION' | 'SELECTIVE_DIVERGENCE' | 'DISTRIBUTION_DANGER'
    pause_new_buying: bool
    max_total_nav_exposure_pct: float
    warning_banner: str


def analyze_market_breadth(
    advances: int,
    declines: int,
    unchanged: int = 0,
    total_value_billion: float = 0.0,
) -> MarketBreadthSnapshot:
    """Đánh giá chế độ độ rộng thị trường và quyết định kích hoạt Cầu chì T+2.5.

    Quy tắc:
    - breadth_pct = advances / max(advances + declines, 1) * 100
    - >= 55%: BULLISH_EXPANSION (Lan tỏa đồng thuận -> cho phép giải ngân tối đa 80% NAV)
    - 35% .. < 55%: SELECTIVE_DIVERGENCE (Phân hóa chọn lọc -> giới hạn tối đa 40% NAV)
    - < 35%: DISTRIBUTION_DANGER (Xanh vỏ đỏ lòng / Xả diện rộng -> NGỪNG MUA MỚI 100%)
    """
    adv = max(int(advances or 0), 0)
    dec = max(int(declines or 0), 0)
    unch = max(int(unchanged or 0), 0)
    val_bil = max(float(total_value_billion or 0.0), 0.0)

    if adv == 0 and dec == 0:
        return MarketBreadthSnapshot(
            advances=0,
            declines=0,
            unchanged=unch,
            breadth_pct=70.0,
            total_value_billion=round(val_bil, 1),
            regime="BULLISH_EXPANSION",
            pause_new_buying=False,
            max_total_nav_exposure_pct=80.0,
            warning_banner="",
        )

    breadth_pct = round((adv / max(adv + dec, 1)) * 100.0, 1)

    if breadth_pct < 35.0:
        regime = "DISTRIBUTION_DANGER"
        pause_new_buying = True
        max_nav_pct = 0.0
        banner = (
            f"⛔ CẦU CHÌ T+2.5 KÍCH HOẠT: ĐỘ RỘNG THỊ TRƯỜNG SUY YẾU ({breadth_pct:.1f}% — "
            f"Tăng {adv} / Giảm {dec}). TẠM NGỪNG MUA MỚI ĐỂ TRÁNH KẸP HÀNG T+2.5!"
        )
    elif breadth_pct < 55.0:
        regime = "SELECTIVE_DIVERGENCE"
        pause_new_buying = False
        max_nav_pct = 40.0
        banner = (
            f"⚠️ THỊ TRƯỜNG PHÂN HÓA ({breadth_pct:.1f}% — Tăng {adv} / Giảm {dec}): "
            f"Chỉ giải ngân chọn lọc tại nền POC/VAL, giới hạn tổng cổ phiếu <= 40% NAV."
        )
    else:
        regime = "BULLISH_EXPANSION"
        pause_new_buying = False
        max_nav_pct = 80.0
        banner = ""

    return MarketBreadthSnapshot(
        advances=adv,
        declines=dec,
        unchanged=unch,
        breadth_pct=breadth_pct,
        total_value_billion=round(val_bil, 1),
        regime=regime,
        pause_new_buying=pause_new_buying,
        max_total_nav_exposure_pct=max_nav_pct,
        warning_banner=banner,
    )


def parse_market_breadth_dict(breadth_dict: Optional[Dict[str, Any]]) -> MarketBreadthSnapshot:
    """Chuyển đổi dữ liệu thô từ API Fialda GetIndexData sang MarketBreadthSnapshot an toàn."""
    if not breadth_dict or not isinstance(breadth_dict, dict):
        return analyze_market_breadth(advances=0, declines=0)

    raw_adv = breadth_dict.get("advances")
    raw_dec = breadth_dict.get("declines")
    raw_unch = breadth_dict.get(
        "noChange",
        breadth_dict.get("noChanges", breadth_dict.get("unchanged", 0)),
    )
    raw_val = breadth_dict.get("totalValue", breadth_dict.get("total_value_billion", 0.0))

    try:
        adv = int(raw_adv) if raw_adv not in (None, "N/A", "") else 0
        dec = int(raw_dec) if raw_dec not in (None, "N/A", "") else 0
        unch = int(raw_unch) if raw_unch not in (None, "N/A", "") else 0
    except (TypeError, ValueError):
        adv, dec, unch = 0, 0, 0

    try:
        val_f = float(raw_val) if raw_val not in (None, "N/A", "") else 0.0
        val_bil = val_f / 1e9 if val_f > 1e6 else val_f
    except (TypeError, ValueError):
        val_bil = 0.0

    return analyze_market_breadth(
        advances=adv,
        declines=dec,
        unchanged=unch,
        total_value_billion=val_bil,
    )

