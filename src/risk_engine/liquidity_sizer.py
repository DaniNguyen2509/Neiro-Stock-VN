"""Module Bo Loc Thanh Khoan & Suc Chua Danh Muc (Liquidity & Capacity Sizer).

Nang cap nang luc quan tri rui ro danh muc len quy mo Quy Dau Tu:
1. Bo loc ADTV20 (Average Daily Trading Value 20 phien): Loai bo co phieu co ADTV20 < 15 - 30 ty dong/phien.
2. Mo hinh Suc chua Danh muc (Portfolio Capacity Model): Gioi han vi the <= 10% - 15% ADV20, lam tron lo 100.
3. Mo hinh Uoc luong Truot gia Phi tuyen (Nonlinear Slippage Model):
   Slippage (%) = Spread + k * (Order_Size / ADTV20)^alpha dua tren do day so lenh.
4. He thong Cham diem Thanh khoan (Liquidity Scoring 0 - 100).
"""
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union
import math


@dataclass
class LiquidityMetrics:
    """Chi so thanh khoan chi tiet cua co phieu."""
    symbol: str
    current_price: float               # Gia thi truong (hoac nghin dong hoac VND)
    adtv20_billion: float              # Gia tri GD trung binh 20 phien (ty VND)
    adv20_shares: int                  # Khoi luong GD trung binh 20 phien (co phieu)
    bid_ask_spread_pct: float          # Chenh lech gia mua/ban (%)
    liquidity_score: float             # Diem thanh khoan (0 - 100)
    is_institutional_grade: bool       # Dat chuan Quy institutional (>= 30 ty/phien)
    is_liquid: bool                    # Dat bo loc thanh khoan an toan (>= 15 ty/phien)


@dataclass
class CapacityResult:
    """Ket qua tinh toan suc chua danh muc va uoc tinh truot gia cho 1 ma co phieu."""
    symbol: str
    current_price: float
    adtv20_billion: float
    adv20_shares: int
    max_shares_recommended: int        # Khong vuot qua 10% - 15% ADV20, tron lo 100
    max_value_recommended_billion: float # Gia tri mua toi da khuyen nghi (ty VND)
    participation_rate_pct: float      # Ty le tham gia thuc te tren ADTV20 (%)
    estimated_slippage_pct: float      # Uoc luong truot gia (%)
    liquidity_score: float             # Diem thanh khoan (0 - 100)
    is_liquid: bool                    # Co vuot qua bo loc thanh khoan khong
    warning_level: str                 # 'SAFE', 'MODERATE', 'HIGH_SLIPPAGE', 'CRITICAL_OVER_CAPACITY'
    warning_message: str               # Thong diep canh bao chi tiet
    liquidation_days_est: float        # Uoc luong so ngay thoat hang an toan trong T+2.5


def normalize_price_vnd(price: float) -> float:
    """Chuan hoa gia co phieu sang dong (VND).
    
    Neu price < 500.0 (vi du 20.95), he thong hieu la 20.95 nghin VND -> tra ve 20,950 VND.
    Neu price >= 500.0 (vi du 20950.0), tra ve nguyen ban.
    """
    if price <= 0:
        return 1.0
    if price < 500.0:
        return price * 1000.0
    return price


def calculate_adtv20(
    values_billion: Optional[List[float]] = None,
    turnover_vnd: Optional[List[float]] = None,
    prices: Optional[List[float]] = None,
    volumes: Optional[List[float]] = None,
) -> float:
    """Tinh gia tri giao dich trung binh 20 phien (ADTV20) theo don vi ty dong.
    
    Args:
        values_billion: Danh sach gia tri giao dich theo ty dong
        turnover_vnd: Danh sach gia tri giao dich theo VND
        prices: Danh sach gia dong cua cac phien
        volumes: Danh sach khoi luong cac phien
        
    Returns:
        ADTV20 tinh bang ty VND (lam tron 2 chu so thap phan).
    """
    if values_billion:
        window = values_billion[-20:]
        if not window:
            return 0.0
        return round(float(sum(window) / len(window)), 2)

    if turnover_vnd:
        window = turnover_vnd[-20:]
        if not window:
            return 0.0
        return round(float(sum(window) / len(window) / 1e9), 2)

    if prices and volumes:
        n = min(len(prices), len(volumes), 20)
        if n == 0:
            return 0.0
        p_win = prices[-n:]
        v_win = volumes[-n:]
        daily_vals = [normalize_price_vnd(p) * v for p, v in zip(p_win, v_win)]
        return round(float(sum(daily_vals) / len(daily_vals) / 1e9), 2)

    return 0.0


def is_liquidity_sufficient(
    adtv20_billion: float,
    min_threshold_billion: float = 15.0,
) -> bool:
    """Kiem tra xem co phieu co vuot qua nguong thanh khoan toi thieu khong.
    
    Args:
        adtv20_billion: Gia tri GD trung binh 20 phien (ty VND)
        min_threshold_billion: Nguong toi thieu (15 - 30 ty VND/phien)
        
    Returns:
        True neu ADTV20 >= min_threshold_billion, nguoc lai False.
    """
    return adtv20_billion >= min_threshold_billion


def calculate_liquidity_score(
    adtv20_billion: float,
    bid_ask_spread_pct: float = 0.25,
) -> float:
    """Tinh diem thanh khoan tu 0 den 100 theo quy mo ADTV20 va do sau spread.
    
    Phan tang:
    - >= 100 ty/phien: 90 - 100 diem (Sieu thanh khoan - HPG, SSI, VHM, VCB)
    - 50 - 100 ty/phien: 80 - 89.9 diem (Thanh khoan cao - MWG, DBC, GEX, PVD)
    - 25 - 50 ty/phien: 70 - 79.9 diem (Thanh khoan tot - CTS, PTB, ANV, SZC)
    - 15 - 25 ty/phien: 60 - 69.9 diem (Thanh khoan dat nguong - Can kiem soat lenh)
    - < 15 ty/phien: < 60 diem (Khong dat chuan Quy - Loai bo)
    """
    if adtv20_billion <= 0:
        return 0.0

    if adtv20_billion < 15.0:
        base_score = (adtv20_billion / 15.0) * 55.0
    elif adtv20_billion < 30.0:
        base_score = 60.0 + ((adtv20_billion - 15.0) / 15.0) * 15.0
    elif adtv20_billion < 70.0:
        base_score = 75.0 + ((adtv20_billion - 30.0) / 40.0) * 15.0
    elif adtv20_billion < 150.0:
        base_score = 90.0 + ((adtv20_billion - 70.0) / 80.0) * 7.0
    else:
        base_score = 97.0 + min(3.0, (adtv20_billion - 150.0) / 100.0)

    # Tru diem neu spread bid/ask lon (> 0.3%)
    spread_penalty = max(0.0, (bid_ask_spread_pct - 0.25) * 5.0)
    final_score = max(0.0, min(100.0, base_score - spread_penalty))
    return round(final_score, 1)


def estimate_nonlinear_slippage(
    order_size_shares: int,
    adv20_shares: int,
    bid_ask_spread_pct: float = 0.25,
    k: float = 2.5,
    alpha: float = 0.60,
) -> Tuple[float, str, str]:
    """Uoc luong truot gia phi tuyen theo vi cau truc so lenh (Almgren-Chriss / Square-Root Law).
    
    Cong thuc:
        Slippage (%) = Spread + k * (Order_Shares / ADV20)^alpha
        
    Args:
        order_size_shares: So luong co phieu du kien mua
        adv20_shares: Khoi luong GD trung binh 20 phien
        bid_ask_spread_pct: Chenh lech gia mua/ban (%)
        k: He so tac dong thanh khoan (Impact factor, mac dinh 2.5)
        alpha: So mu phi tuyen do loi so lenh (mac dinh 0.60)
        
    Returns:
        (estimated_slippage_pct, warning_level, warning_message)
    """
    if adv20_shares <= 0 or order_size_shares <= 0:
        return round(bid_ask_spread_pct, 2), "SAFE", "Thanh khoan hoac quy mo lenh bang 0."

    participation_ratio = order_size_shares / adv20_shares
    impact = k * math.pow(participation_ratio, alpha)
    total_slippage = round(bid_ask_spread_pct + impact, 2)

    # Phan cap canh bao
    if participation_ratio > 0.15:
        level = "CRITICAL_OVER_CAPACITY"
        msg = f"VƯỢT SỨC CHỨA: Lệnh chiếm {participation_ratio * 100:.1f}% ADV20 (>15%), rủi ro kẹp hàng cao trong chu kỳ T+2.5!"
    elif total_slippage >= 1.50:
        level = "HIGH_SLIPPAGE"
        msg = f"CẢNH BÁO TRƯỢT GIÁ CAO: Ước tính trượt giá {total_slippage:.2f}% (>=1.5%), chi phí thực thi lớn!"
    elif participation_ratio > 0.10:
        level = "MODERATE"
        msg = f"THEO DÕI: Quy mô lệnh chiếm {participation_ratio * 100:.1f}% ADV20, tiệm cận ngưỡng trần an toàn."
    else:
        level = "SAFE"
        msg = f"AN TOÀN: Sức chứa thanh khoản đáp ứng tốt, trượt giá dự kiến {total_slippage:.2f}%."

    return total_slippage, level, msg


def calculate_portfolio_capacity(
    symbol: str,
    current_price: float,
    adtv20_billion: float,
    max_participation_pct: float = 0.10,
    requested_shares: Optional[int] = None,
    requested_value_billion: Optional[float] = None,
    bid_ask_spread_pct: float = 0.25,
    min_adtv_billion: float = 15.0,
    k: float = 2.5,
    alpha: float = 0.60,
) -> CapacityResult:
    """Tinh toan toan dien Suc chua Danh muc & Truot gia cho 1 vi the.
    
    Args:
        symbol: Ma co phieu
        current_price: Gia thi truong (VND hoac 1,000 VND)
        adtv20_billion: Gia tri GD trung binh 20 phien (ty VND)
        max_participation_pct: Ty le tham gia toi da an toan (10% - 15% ADV20)
        requested_shares: So co phieu mong muon mua (tuy chon)
        requested_value_billion: Gia tri mong muon mua (ty VND, tuy chon)
        bid_ask_spread_pct: Chenh lech bid/ask spread (%)
        min_adtv_billion: Nguong ADTV20 toi thieu (15 - 30 ty VND)
        k: He so truot gia phi tuyen
        alpha: So mu do loi so lenh
        
    Returns:
        CapacityResult chua thong tin suc chua, khoi luong max, truot gia va canh bao.
    """
    price_vnd = normalize_price_vnd(current_price)
    is_liquid = is_liquidity_sufficient(adtv20_billion, min_threshold_billion=min_adtv_billion)
    score = calculate_liquidity_score(adtv20_billion, bid_ask_spread_pct=bid_ask_spread_pct)

    # Tinh ADV20 (so luong co phieu trung binh/phien)
    if price_vnd > 0 and adtv20_billion > 0:
        adv20_shares = int((adtv20_billion * 1e9) / price_vnd)
    else:
        adv20_shares = 0

    # Khong qua max_participation_pct cua ADV20, lam tron xuong boi so cua 100 co phieu
    clamped_participation = min(max(max_participation_pct, 0.01), 0.20)
    raw_max_shares = int(adv20_shares * clamped_participation)
    max_shares_recommended = (raw_max_shares // 100) * 100
    max_val_billion = round((max_shares_recommended * price_vnd) / 1e9, 3)

    # Xac dinh khoi luong lenh can danh gia
    if requested_shares is not None:
        eval_shares = max(0, requested_shares)
    elif requested_value_billion is not None and price_vnd > 0:
        eval_shares = int((requested_value_billion * 1e9) / price_vnd)
    else:
        eval_shares = max_shares_recommended

    # Tinh ty le tham gia thuc te tren ADV20
    actual_participation_pct = round((eval_shares / adv20_shares * 100.0), 2) if adv20_shares > 0 else 0.0

    # Tinh truot gia phi tuyen
    slippage_pct, warn_level, warn_msg = estimate_nonlinear_slippage(
        order_size_shares=eval_shares,
        adv20_shares=adv20_shares,
        bid_ask_spread_pct=bid_ask_spread_pct,
        k=k,
        alpha=alpha,
    )

    # Neu co phieu bi loai boi bo loc thanh khoan, cap nhat canh bao
    if not is_liquid:
        warn_level = "CRITICAL_OVER_CAPACITY"
        warn_msg = f"LOẠI BỎ KHỎI QUỸ: ADTV20={adtv20_billion:.1f} tỷ < ngưỡng tối thiểu {min_adtv_billion:.1f} tỷ/phiên!"

    # Uoc luong so ngay thoat hang trong T+2.5
    daily_capacity = adv20_shares * clamped_participation
    if daily_capacity > 0:
        exit_days = round(eval_shares / daily_capacity, 2)
    else:
        exit_days = 99.0

    return CapacityResult(
        symbol=symbol,
        current_price=current_price,
        adtv20_billion=round(adtv20_billion, 2),
        adv20_shares=adv20_shares,
        max_shares_recommended=max_shares_recommended,
        max_value_recommended_billion=max_val_billion,
        participation_rate_pct=actual_participation_pct,
        estimated_slippage_pct=slippage_pct,
        liquidity_score=score,
        is_liquid=is_liquid,
        warning_level=warn_level,
        warning_message=warn_msg,
        liquidation_days_est=exit_days,
    )
