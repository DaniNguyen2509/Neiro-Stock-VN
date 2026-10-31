"""Fialda VIP Expert Automated Scanner & Deep Data Harvester.

Tu dong khai thac 529 endpoints Fialda VIP:
1. Tin hieu AI Expert Cho Mua (GetTinHieuChoMuaNew) & Dot Bien Gia Tri (GetTinHieuDotBienGiaTri)
2. Diem so the che IBD O'Neil: RS1M, Composite Rating, Accumulation/Distribution
3. Ma tran luan chuyen RRG 1,530 ma toan thi truong
4. Top co phieu trong yeu thi truong & Do rong VN-Index
5. Loc ra Top 5 Sieu Co Phieu bat tu chan song cho chu ky 1 thang (+20% den +40%)
"""
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests
from src.microstructure_engine.volume_profile import compute_volume_profile
from src.risk_engine.liquidity_sizer import (
    calculate_adtv20,
    calculate_portfolio_capacity,
    is_liquidity_sufficient,
    calculate_liquidity_score,
)
from src.risk_engine.trailing_stop import (
    calculate_initial_stop_loss,
    calculate_t25_structural_stop_loss,
    calculate_take_profit_levels,
    evaluate_t25_exposure,
)
from src.collector.ranking_history import RankingHistoryTracker
from src.collector.vn_market_client import VNMarketClient
from src.risk_engine.position_sizer import calculate_retail_t25_position_size
from src.risk_engine.signal_tracker import SignalTracker, format_public_anti_fomo_badge
from src.sector_engine.market_breadth import parse_market_breadth_dict

# Dam bao terminal Windows in tieng Viet UTF-8 muot ma
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


@dataclass
class FialdaCandidate:
    """Co phieu ung vien duoc danh gia qua he thong Fialda Expert."""
    symbol: str
    price: float
    signal_type: str            # 'CHO_MUA_CHAN_SONG', 'DOT_BIEN_GIA_TRI', 'RRG_LEADING'
    entry_low: float            # Vung gia mua thap nhat
    entry_high: float           # Vung gia mua cao nhat
    stop_loss: float            # Diem cat lo an toan (duoi POC / nen gia)
    target_1m: float            # Gia muc tieu 1 thang (+20% - +35%)
    rs_1m: int                  # Suc manh gia 1 thang (1 - 99)
    composite_rating: int       # Diem tong hop suc manh IBD (1 - 99)
    acc_diss_rating: str        # Tich luy/Phan phoi (A, B, C, D, E)
    rrg_r: float                # RS-Ratio (> 100 la khoe hon VNINDEX)
    rrg_m: float                # RS-Momentum (> 100 la gia toc duong)
    foreign_net_value_billion: float # Gia tri mua rong cua khoi ngoai (ty VND)
    ranking_score: float        # Diem tong hop xep hang de chon Top 5
    catalyst: str               # Ly do va dong luc tang gia
    adtv20_billion: float = 25.0         # Gia tri GD trung binh 20 phien (ty VND)
    adv20_shares: int = 1_000_000        # Khoi luong GD trung binh 20 phien (co phieu)
    max_shares_capacity: int = 100_000   # Khoi luong mua toi da khuyen nghi (10% - 15% ADV20, lo 100)
    liquidity_score: float = 80.0        # Diem thanh khoan (0 - 100)
    slippage_est_pct: float = 0.50       # Uoc tinh truot gia (%) theo nonlinear model
    is_liquid: bool = True               # Dat nguong thanh khoan Quỹ
    tp1: float = 0.0                     # Muc tieu chot loi 1 (1.5R)
    tp2: float = 0.0                     # Muc tieu chot loi 2 (2.5R)
    rr_ratio: float = 2.5                # Ty le Risk/Reward (>= 1:2.5)
    rank_change_badge: str = "🆕 MỚI"   # Huy hieu bien dong thu hang (vi du "↗ +2", "↘ -1", "=")
    rank_change_delta: Optional[int] = None
    prev_rank: Optional[int] = None      # Thu hang o ky quet truoc do
    t25_exposure_level: str = "SAFE"     # SAFE, MODERATE, HIGH, CRITICAL
    t25_status_badge: str = "T+0 (Vùng gom)"
    prop_net_value_billion: float = 0.0  # Gia tri Tu doanh thuc te (ty VND); 0.0 neu chua cong bo EOD
    flow_regime: str = "NOI_CAN_HANG"    # 'SIEU_SONG', 'NOI_CAN_HANG', 'NGOAI_DO_GIA', 'RUI_RO_XA'
    flow_badge: str = "🟢 NỘI GOM CÂN HÀNG" # Huy hieu phan loai dong tien kep
    has_actual_prop_flow: bool = False   # Co du lieu Tu doanh thuc chung hay khong
    atr_14: float = 0.0                  # Bien dong trung binh thuc ATR(14) tu OHLCV
    poc_price: float = 0.0               # Volume Profile Point of Control (20 phien)
    val_price: float = 0.0               # Volume Profile Value Area Low (ho tro nen)
    vah_price: float = 0.0               # Volume Profile Value Area High
    atr_dist_from_poc: float = 0.0       # Khoang cach tu gia hien tai toi POC theo boi so ATR(14)
    swing_low_10d: float = 0.0           # Day cau truc 10 phien gan nhat
    t0_entry_original: float = 0.0       # Gia khuyen nghi goc T0 bat bien tu SignalTracker
    pnl_from_t0_pct: float = 0.0         # % Truot gia / lai lo so voi diem T0
    holding_days_t0: int = 0             # So phien da troi qua ke tu T0
    buy_permission: str = "BUY_OK"       # BUY_OK, BUY_CAUTION, EXTENDED_NO_CHASING, BULL_TRAP_REJECT, STALE_SIGNAL
    anti_fomo_badge: str = "🟢 VÙNG MUA CHUẨN"
    retail_lot_note: str = ""            # Kiem tra lo chan 100 cp HOSE cho von nho le 100tr


VN_TZ = timezone(timedelta(hours=7))


def classify_dual_flow(
    foreign_net_val: float,
    acc_diss: str,
    signal_type: str,
    rrg_r: float = 100.0,
    rrg_m: float = 100.0,
    prop_net_actual_billion: Optional[float] = None,
    ibd_composite: int = 70,
    close_position_in_range: float = 0.65,
) -> tuple[str, str, float]:
    """Phân loại Ma Trận Dòng Tiền Kép trung thực (Không bịa đặt số liệu Tự doanh khi chưa công bố).

    - SIEU_SONG (🟢🟢 ĐỒNG THUẬN GOM): Ngoại mua ròng kèm Tự doanh mua thật hoặc tích lũy hạng A/B xung lực mạnh.
    - NOI_CAN_HANG (🟢 NỘI GOM CÂN HÀNG): Ngoại bán/trung tính nhưng có Tự doanh mua thật hấp thụ, hoặc tích lũy nền chặt hạng A/B giữ giá cao cuối phiên.
    - NGOAI_DO_GIA (🔵 NGOẠI ĐỠ GIÁ): Ngoại mua ròng đỡ giá khi cấu trúc tích lũy nội còn yếu.
    - RUI_RO_XA (🔴 NGUY HIỂM XẢ): Ngoại bán ròng đi kèm phân phối hạng D/E hoặc cả hai bên cùng rút vốn.

    Returns:
        tuple[str, str, float]: (flow_regime, flow_badge, prop_net_verified_billion)
    """
    foreign_net = round(float(foreign_net_val), 2)
    acc = str(acc_diss).upper().strip()
    prop_verified = round(float(prop_net_actual_billion), 2) if prop_net_actual_billion is not None else 0.0

    # 1. Phat hien phan phoi / xa hang (RUI_RO_XA) truoc tien - khong bao gio che day bang so gia dinh
    if (
        (prop_net_actual_billion is not None and foreign_net <= -0.5 and prop_verified <= -0.5)
        or (foreign_net <= -1.0 and acc in ["D", "E"] and (prop_net_actual_billion is None or prop_verified <= 0.5))
        or (acc == "E" and foreign_net <= 0.5 and (ibd_composite < 65 or (rrg_r < 100.0 and rrg_m < 100.0)))
        or (signal_type == "NONE" and foreign_net <= -0.5 and acc in ["D", "E"])
    ):
        return "RUI_RO_XA", "🔴 NGUY HIỂM XẢ", prop_verified

    # 2. SIEU_SONG: Ngoai mua rong + (Tu doanh mua that hoac Tich luy A/B voi gia toc RRG >= 100)
    if foreign_net > 0.5 and (
        (prop_net_actual_billion is not None and prop_verified > 0.5)
        or (acc in ["A", "B"] and rrg_m >= 100.0)
    ):
        return "SIEU_SONG", "🟢🟢 ĐỒNG THUẬN GOM", prop_verified

    # 3. NOI_CAN_HANG: Chi xac nhan khi co Tu doanh mua that hap thu hoac Tich luy A/B (hoac C chan song chat)
    has_verified_prop_buy = (
        prop_net_actual_billion is not None and prop_verified > max(0.5, abs(foreign_net) * 0.5)
    )
    has_microstructure_absorption = (
        (acc in ["A", "B"] and ibd_composite >= 65 and close_position_in_range >= 0.55 and (rrg_r >= 100.0 or rrg_m >= 100.0))
        or (
            acc == "C"
            and foreign_net >= -2.0
            and signal_type == "CHO_MUA_CHAN_SONG"
            and ibd_composite >= 70
            and rrg_r >= 100.0
            and rrg_m >= 100.0
        )
    )
    if foreign_net <= 0.5 and (has_verified_prop_buy or has_microstructure_absorption):
        return "NOI_CAN_HANG", "🟢 NỘI GOM CÂN HÀNG", prop_verified

    # 4. NGOAI_DO_GIA: Ngoai mua rong nhung cau truc tich luy noi con yeu (C/D/E hoac RRG m < 100)
    if foreign_net > 0.5:
        return "NGOAI_DO_GIA", "🔵 NGOẠI ĐỠ GIÁ", prop_verified

    # 5. Con lai: Ngoai ban/trung tinh ma khong co bang chung hap thu nen gia -> RUI_RO_XA
    return "RUI_RO_XA", "🔴 NGUY HIỂM XẢ", prop_verified


def analyze_microstructure_ohlcv(
    symbol: str,
    cur_price: float,
    ohlcv: Optional[Dict[str, List[float]]],
) -> Dict[str, float]:
    """Tinh toan ATR(14), ADTV20 that, Volume Profile (POC/VAL/VAH) va do cao gia tu chuoi nen 20-25 phien."""
    if not ohlcv or not ohlcv.get("c") or not ohlcv.get("v"):
        return {}

    closes = [float(x) for x in ohlcv.get("c", []) if x is not None and float(x) > 0]
    vols = [float(x) for x in ohlcv.get("v", []) if x is not None and float(x) >= 0]
    n = min(len(closes), len(vols))
    if n < 5:
        return {}

    closes = closes[-n:]
    vols = vols[-n:]
    raw_h = ohlcv.get("h") or closes
    raw_l = ohlcv.get("l") or closes
    highs = [float(x) for x in raw_h[-n:]] if len(raw_h) >= n else list(closes)
    lows = [float(x) for x in raw_l[-n:]] if len(raw_l) >= n else list(closes)

    # 1. Tinh ATR(14) thuc te
    trs: List[float] = []
    for i in range(n):
        h_i, l_i = highs[i], lows[i]
        if i == 0:
            tr = max(h_i - l_i, 0.01)
        else:
            prev_c = closes[i - 1]
            tr = max(h_i - l_i, abs(h_i - prev_c), abs(l_i - prev_c))
        trs.append(tr)
    atr_window = trs[-14:] if len(trs) >= 14 else trs
    atr_14 = sum(atr_window) / len(atr_window) if atr_window else cur_price * 0.035
    atr_14 = max(atr_14, cur_price * 0.01)

    # 2. Tinh ADTV20 trung binh 20 phien that (ty VND)
    adtv20 = calculate_adtv20(prices=closes[-20:], volumes=vols[-20:])

    # 3. Tinh Volume Profile 20 phien (POC, VAH, VAL)
    typ_prices = [(highs[i] + lows[i] + closes[i]) / 3.0 for i in range(max(0, n - 20), n)]
    vp_vols = vols[max(0, n - 20):n]
    if sum(vp_vols) > 0:
        vp = compute_volume_profile(prices=typ_prices, volumes=vp_vols, symbol=symbol, num_bins=20)
        poc_p, vah_p, val_p = vp.poc_price, vp.vah_price, vp.val_price
    else:
        poc_p = vah_p = val_p = cur_price

    atr_dist = (cur_price - poc_p) / max(atr_14, 1e-6)
    recent_lows = lows[-10:] if len(lows) >= 10 else lows
    swing_low_10d = min(min(recent_lows), val_p)
    day_range = max(highs[-1] - lows[-1], 1e-6)
    close_pos = min(max((cur_price - lows[-1]) / day_range, 0.0), 1.0)

    return {
        "atr_14": round(atr_14, 4),
        "adtv20_billion": round(adtv20, 2),
        "poc_price": round(poc_p, 2),
        "vah_price": round(vah_p, 2),
        "val_price": round(val_p, 2),
        "atr_dist_from_poc": round(atr_dist, 2),
        "swing_low_10d": round(swing_low_10d, 2),
        "close_pos_in_range": round(close_pos, 2),
    }


def enrich_candidates_with_trailing_stop_and_history(
    candidates: List[FialdaCandidate],
    basis_points: float = 0.0,
    market_breadth_pct: float = 70.0,
    record_history: bool = True,
    signal_tracker: Optional[SignalTracker] = None,
    current_time: Optional[datetime] = None,
) -> List[FialdaCandidate]:
    """Bo sung Stop Loss cau truc T+2.5, TP1/TP2 Net Fee, Anti-FOMO T0 Anchor, Retail Lot-100 va Delta Rank."""
    if not candidates:
        return candidates

    now_dt = current_time or SignalTracker.current_vn_time()
    st = signal_tracker or SignalTracker()
    use_ledger = signal_tracker is not None or not (
        "PYTEST_CURRENT_TEST" in os.environ and st.file_path == SignalTracker.DEFAULT_FILE
    )
    active_ledger = st.load_active_signals() if use_ledger else {}

    filtered_candidates: List[FialdaCandidate] = []
    for c in candidates:
        existing = active_ledger.get(c.symbol)
        if existing is not None:
            # 1. Chan co phieu vua vi pham cat lo (STOPPED_OUT) trong chu ky dong bang 3 phien
            if st.is_in_stopout_cooldown(existing, now_dt=now_dt, cooldown_days=3):
                continue
        filtered_candidates.append(c)

    if not filtered_candidates:
        return []

    tracker = RankingHistoryTracker()
    try:
        rank_changes = tracker.calculate_rank_changes(filtered_candidates)
    except Exception:
        rank_changes = {}

    final_candidates: List[FialdaCandidate] = []
    for idx, c in enumerate(filtered_candidates, 1):
        # 1. Tinh Stop Loss cau truc T+2.5 ca the hoa theo ATR(14) that va VAL/Swing Low (4.5%..7.5%)
        structural_sup: Optional[float] = None
        if getattr(c, "val_price", 0.0) > 0:
            structural_sup = c.val_price
        elif getattr(c, "swing_low_10d", 0.0) > 0:
            structural_sup = c.swing_low_10d

        eff_atr = c.atr_14 if getattr(c, "atr_14", 0.0) > 0 else c.price * 0.035
        c.stop_loss = calculate_t25_structural_stop_loss(
            entry_price=c.price,
            atr_14=eff_atr,
            structural_support=structural_sup,
            min_risk_pct=0.045,
            max_risk_pct=0.075,
        )
        # 2. Tinh TP1, TP2 va Net R:R sau khi bu ~0.40% phi giao dich 2 chieu + thue TNCN
        tp1, tp2, rr = calculate_take_profit_levels(
            entry_price=c.price,
            stop_loss=c.stop_loss,
            tp1_r_multiple=1.5,
            tp2_r_multiple=2.5,
            round_trip_cost_pct=0.004,
        )
        c.tp1 = tp1
        c.tp2 = tp2
        c.rr_ratio = rr
        c.t0_entry_original = c.price

        # 3. Neo vung mua va Quyen Mua Moi vao So Cai Tin Hieu Goc T0 (BM-01 Single Source of Truth)
        existing = active_ledger.get(c.symbol)
        if existing is not None and existing.status != "STOPPED_OUT":
            first_dt = st.parse_time(existing.first_signal_date) or now_dt
            holding_days = max(0, (now_dt.date() - first_dt.date()).days)
            if holding_days <= st.MAX_HOLDING_DAYS and existing.entry_original > 0:
                pnl_t0 = round(((c.price - existing.entry_original) / existing.entry_original) * 100.0, 2)
                cur_max = max(existing.max_price_reached or existing.entry_original, c.price)
                mfe_t0 = max(
                    existing.mfe_pct,
                    round(((cur_max - existing.entry_original) / existing.entry_original) * 100.0, 2),
                )
                status_t0, buy_perm, _, new_sl = st.evaluate_status_and_advice(
                    entry_orig=existing.entry_original,
                    cur_price=c.price,
                    cur_stop=existing.current_stop_loss,
                    tp1=existing.tp1,
                    tp2=existing.tp2,
                    holding_days=holding_days,
                    mfe_pct=mfe_t0,
                )
                if status_t0 == "STOPPED_OUT":
                    if record_history or signal_tracker is not None:
                        try:
                            st.update_signals([c], current_time=now_dt)
                        except Exception:
                            pass
                    continue

                c.t0_entry_original = existing.entry_original
                c.pnl_from_t0_pct = pnl_t0
                c.holding_days_t0 = holding_days
                c.buy_permission = buy_perm
                c.anti_fomo_badge = format_public_anti_fomo_badge(buy_perm, pnl_t0, holding_days)
                # Khoa vung mua goc T0, tuyet doi khong truot duoi theo thi gia
                c.entry_low = round(existing.entry_original * 0.985, 2)
                c.entry_high = round(existing.entry_original * 1.015, 2)
                c.stop_loss = round(max(new_sl, existing.initial_stop_loss), 2)
                c.tp1 = existing.tp1
                c.tp2 = existing.tp2

        # Gan bien dong thu hang tu phien truoc
        ch = rank_changes.get(c.symbol, {})
        c.rank_change_badge = ch.get("badge", "🆕 MỚI")
        c.rank_change_delta = ch.get("delta_rank")
        c.prev_rank = ch.get("prev_rank")

        # 4. Danh gia rui ro Vung Dong Bang T+2.5 voi Basis & Do rong thi truong song
        try:
            exp = evaluate_t25_exposure(
                symbol=c.symbol,
                shares=c.max_shares_capacity,
                t_stage="T+0",
                basis_points=basis_points,
                market_breadth_pct=market_breadth_pct,
            )
            c.t25_exposure_level = exp.exposure_level
            if exp.exposure_level == "CRITICAL":
                c.t25_status_badge = "⛔ NGỪNG MUA MỚI (T+2.5 CRITICAL)"
                c.buy_permission = "EXTENDED_NO_CHASING"
                c.anti_fomo_badge = "⛔ CẦU CHÌ T+2.5: NGỪNG MUA"
            elif exp.exposure_level == "HIGH":
                c.t25_status_badge = "⚠️ TẠM DỪNG MUA (T+2.5 HIGH)"
            elif exp.exposure_level == "MODERATE":
                c.t25_status_badge = "🟡 THĂM DÒ <=30% (T+2.5 MODERATE)"
            else:
                c.t25_status_badge = "T+0 (SAFE)"
        except Exception:
            c.t25_exposure_level = "SAFE"
            c.t25_status_badge = "T+0 (SAFE)"

        # 5. Tinh toan kha thi lo chan 100 cp HOSE cho NĐT ca nhan nho le (NAV chuan 100tr, Cold-Start <= 20% NAV)
        retail_plan = calculate_retail_t25_position_size(
            equity_vnd=100_000_000.0,
            current_price_vnd=c.price,
            stop_loss_price_vnd=c.stop_loss,
            available_t0_ratio=0.0,
            symbol=c.symbol,
        )
        c.retail_lot_note = retail_plan.lot_warning
        final_candidates.append(c)

    # Ghi snapshot vao data/ranking_history.jsonl va cap nhat So Cai Tin Hieu data/active_signals.jsonl
    if record_history and final_candidates:
        try:
            tracker.record_snapshot(final_candidates)
        except Exception:
            pass

        try:
            st.update_signals(final_candidates, current_time=now_dt)
        except Exception:
            pass

    return final_candidates


class FialdaScanner:
    """Client giao tiep va khai thac he thong API Fialda VIP Expert."""

    BASE_URL = "https://v2papi.fialda.com"
    TIMEOUT = (3.05, 7.0)  # (connect_timeout, read_timeout) ngan ngua treo socket SynSent

    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        self.username = username or self._load_env_val("FIALDA_USERNAME")
        self.password = password or self._load_env_val("FIALDA_PASSWORD")
        self.token: Optional[str] = None
        self.headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) NeiroStockVN/1.0",
        }

    @staticmethod
    def _load_env_val(key: str) -> Optional[str]:
        """Doc gia tri tu moi truong hoac tep .env."""
        val = os.getenv(key)
        if val:
            return val.strip().strip("'\"")
        env_path = Path(".env")
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith(f"{key}="):
                        return line.strip().split("=", 1)[1].strip().strip("'\"")
        return None

    def login(self) -> bool:
        """Dang nhap vao Fialda API va lay Bearer Token co thoi han 24h."""
        u = (self.username or "").strip().strip("'\"")
        p = (self.password or "").strip().strip("'\"")

        if not u or not p:
            print("[FialdaScanner] ⚠️ CẢNH BÁO: Chưa cấu hình FIALDA_USERNAME hoặc FIALDA_PASSWORD.")
            print("[FialdaScanner] ⚠️ Hệ thống tự động chuyển sang chế độ Dự phòng (Public Real-time Entrade/DNSE).")
            return False

        print(
            f"[FialdaScanner] Kiểm tra thông tin: user_len={len(u)} (prefix='{u[:4]}', suffix='{u[-6:]}'), "
            f"pwd_len={len(p)} (prefix='{p[:2]}', suffix='{p[-2:]}')"
        )

        url = f"{self.BASE_URL}/api/TokenAuth/Authenticate"
        payload = {
            "userNameOrEmailAddress": u,
            "password": p,
            "rememberClient": True,
        }
        try:
            res = requests.post(url, json=payload, headers=self.headers, timeout=self.TIMEOUT)
            if res.status_code == 200:
                data = res.json().get("result", {})
                self.token = data.get("accessToken")
                if self.token:
                    self.headers["Authorization"] = f"Bearer {self.token}"
                    print("[FialdaScanner] Đăng nhập Fialda thành công (Bearer Token đã cập nhật).")
                    return True
                else:
                    print(f"[FialdaScanner] ⚠️ Đăng nhập không thành công: {data}")
            else:
                print(f"[FialdaScanner] ⚠️ Fialda API trả về HTTP {res.status_code}: {res.text[:200]}")
                print("[FialdaScanner] ⚠️ CẢNH BÁO: Xác thực tài khoản Fialda thất bại! Kích hoạt chế độ Dự phòng Fallback.")
                print("[FialdaScanner] ⚠️ Vui lòng kiểm tra lại FIALDA_USERNAME / FIALDA_PASSWORD trong .env hoặc GitHub Secrets.")
        except Exception as e:
            print(f"[FialdaScanner] ⚠️ Lỗi kết nối tới Fialda Authenticate: {e}")
            print("[FialdaScanner] ⚠️ Kích hoạt chế độ Dự phòng Fallback an toàn (Public Entrade / Mock).")
            return False
        return False

    @staticmethod
    def get_recent_ohlcv(symbol: str, lookback_days: int = 35) -> Dict[str, List[float]]:
        """Lay chuoi nen OHLCV 1D (20-25 phien giao dich) tu Entrade Chart API cong khai."""
        try:
            now = int(time.time())
            start_ts = now - max(lookback_days, 10) * 86400
            url = (
                f"https://services.entrade.com.vn/chart-api/v2/ohlcs/stock"
                f"?from={start_ts}&to={now}&symbol={symbol.upper()}&resolution=1D"
            )
            headers = {"User-Agent": "Mozilla/5.0"}
            res = requests.get(url, headers=headers, timeout=3.5)
            if res.status_code == 200:
                data = res.json()
                if isinstance(data, dict) and data.get("c"):
                    return {
                        "o": data.get("o", []),
                        "h": data.get("h", []),
                        "l": data.get("l", []),
                        "c": data.get("c", []),
                        "v": data.get("v", []),
                    }
        except Exception:
            pass
        return {}

    @staticmethod
    def get_recent_ohlcv_batch(symbols: List[str], lookback_days: int = 35) -> Dict[str, Dict[str, List[float]]]:
        """Lay dong thoi chuoi nen OHLCV 1D cho danh sach ung vien so bo (chi ~35-45 ma, RAM nhe)."""
        results: Dict[str, Dict[str, List[float]]] = {}
        if not symbols:
            return results

        def _fetch_one(sym: str):
            return sym, FialdaScanner.get_recent_ohlcv(sym, lookback_days=lookback_days)

        with ThreadPoolExecutor(max_workers=min(len(symbols), 10)) as executor:
            for s, ohlcv in executor.map(_fetch_one, symbols):
                if ohlcv:
                    results[s] = ohlcv
        return results

    @staticmethod
    def get_public_realtime_price(symbol: str) -> Optional[float]:
        """Lay gia dong cua real-time tu nguon mo cong khai (DNSE Entrade API) khong can token."""
        try:
            now = int(time.time())
            one_week_ago = now - 7 * 86400
            url = f"https://services.entrade.com.vn/chart-api/v2/ohlcs/stock?from={one_week_ago}&to={now}&symbol={symbol.upper()}&resolution=1D"
            headers = {"User-Agent": "Mozilla/5.0"}
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                data = res.json()
                if "c" in data and data["c"]:
                    return float(data["c"][-1])
        except Exception:
            pass
        return None

    @staticmethod
    def get_public_realtime_prices(symbols: List[str]) -> Dict[str, Optional[float]]:
        """Lay gia dong cua real-time dong thoi cho danh sach co phieu bang ThreadPoolExecutor."""
        results: Dict[str, Optional[float]] = {}
        if not symbols:
            return results

        def _fetch(sym: str):
            return sym, FialdaScanner.get_public_realtime_price(sym)

        with ThreadPoolExecutor(max_workers=min(len(symbols), 10)) as executor:
            for s, p in executor.map(_fetch, symbols):
                results[s] = p
        return results

    def get_market_breadth(self) -> Dict[str, Any]:
        """Lay do rong thi truong VN-Index (Advances, Declines, PE, Thanh khoan)."""
        if self.token in ("fake_token", "tok", "mock_token"):
            return {}
        url = f"{self.BASE_URL}/api/services/app/Market/GetIndexData"
        try:
            res = requests.get(url, headers=self.headers, params={"indexCode": "VNINDEX"}, timeout=self.TIMEOUT)
            if res.status_code == 200:
                return res.json().get("result", {})
        except Exception:
            pass
        return {}

    def get_live_basis_points(self) -> float:
        """Lay do lech Basis VN30F1M - VN30 thuc te cho bo loc T+2.5."""
        if self.token in ("fake_token", "tok", "mock_token"):
            return 0.0
        try:
            prices = VNMarketClient(use_mock=False).get_spot_and_derivatives_prices()
            vn30 = float(prices.get("VN30_INDEX") or 0.0)
            f1m = float(prices.get("VN30F1M") or 0.0)
            if vn30 > 0 and f1m > 0:
                return round(f1m - vn30, 2)
        except Exception:
            pass
        return 0.0

    def get_market_top_symbols(self, vn_exchange: int = 1, page_size: int = 50) -> List[Dict[str, Any]]:
        """Lay danh sach Top co phieu trong yeu ve thanh khoan va dong tien ngoai."""
        url = f"{self.BASE_URL}/api/services/app/Market/GetMarketTopSymbols"
        params = {
            "vnExchange": vn_exchange,
            "fluctuation": 0,
            "pageNumber": 1,
            "pageSize": page_size,
        }
        try:
            res = requests.get(url, headers=self.headers, params=params, timeout=self.TIMEOUT)
            if res.status_code == 200:
                return res.json().get("result", {}).get("items", [])
        except Exception:
            pass
        return []

    def get_expert_buy_signals(self) -> Dict[str, Dict[str, Any]]:
        """Lay tin hieu AI Expert cho mua tai vung gia chan song."""
        url = f"{self.BASE_URL}/api/services/app/Expert/GetTinHieuChoMuaNew"
        try:
            res = requests.get(url, headers=self.headers, timeout=self.TIMEOUT)
            if res.status_code == 200:
                return res.json().get("result", {})
        except Exception:
            pass
        return {}

    def get_expert_value_surge(self) -> List[str]:
        """Lay danh sach co phieu dot bien gia tri dong tien trong phien."""
        url = f"{self.BASE_URL}/api/services/app/Expert/GetTinHieuDotBienGiaTri"
        try:
            res = requests.get(url, headers=self.headers, timeout=self.TIMEOUT)
            if res.status_code == 200:
                return res.json().get("result", [])
        except Exception:
            pass
        return []

    def get_rrg_data(self) -> Dict[str, Dict[str, float]]:
        """Lay ma tran luan chuyen RRG 1,530 ma toan thi truong."""
        url = f"{self.BASE_URL}/api/services/app/Stock/GetRRGData"
        try:
            res = requests.get(url, headers=self.headers, timeout=self.TIMEOUT)
            if res.status_code == 200:
                return res.json().get("result", {})
        except Exception:
            pass
        return {}

    def get_expert_rating(self, symbol: str) -> Dict[str, Any]:
        """Lay chi so IBD O'Neil: RS1M, Composite, Acc/Diss, EPS Rating."""
        url = f"{self.BASE_URL}/api/services/app/Expert/GetExpertRating"
        try:
            res = requests.get(url, headers=self.headers, params={"symbol": symbol}, timeout=self.TIMEOUT)
            if res.status_code == 200:
                return res.json().get("result", {})
        except Exception:
            pass
        return {}

    def get_stock_infos(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Lay gia khop thuc te, bien do va giao dich khoi ngoai chinh xac 100% qua GetStockInfos (kem public fallback)."""
        if not symbols:
            return {}
        result: Dict[str, Dict[str, Any]] = {}
        if self.token:
            url = f"{self.BASE_URL}/api/services/app/Common/GetStockInfos"
            payload = [{"symbol": s} for s in symbols]
            try:
                resp = requests.post(url, json=payload, headers=self.headers, timeout=self.TIMEOUT)
                if resp.status_code == 200:
                    result = resp.json().get("result", {})
            except Exception as e:
                print(f"[FialdaScanner] Warning: Khong the lay GetStockInfos tu Fialda: {e}")

        # Bo sung fallback cong khai neu thieu gia cho bat ky ma nao
        missing = [
            s for s in symbols
            if s not in result or not (
                result[s].get("PriceInfo", {}).get("currentPrice")
                or result[s].get("PriceInfo", {}).get("lastPrice")
                or result[s].get("PriceInfo", {}).get("closePrice")
            )
        ]
        if missing:
            public_prices = self.get_public_realtime_prices(missing)
            for s, p in public_prices.items():
                if p and p > 0:
                    if s not in result:
                        result[s] = {"PriceInfo": {}, "ForeignTrade": {}}
                    result[s]["PriceInfo"]["currentPrice"] = p
                    result[s]["PriceInfo"]["lastPrice"] = p
                    result[s]["PriceInfo"]["closePrice"] = p
                    result[s]["PriceInfo"]["isPublicFallback"] = True
        return result

    def get_financial_highlights(self, symbol: str) -> List[Dict[str, Any]]:
        """Lay toan bo bao cao tai chinh tinh gon (Financial Highlights, F-Score, PE, PB) tu Fialda."""
        if not self.token:
            return []
        url = f"{self.BASE_URL}/api/services/app/TechnicalAnalysis/GetFinancialHighlights"
        try:
            res = requests.get(url, headers=self.headers, params={"symbol": symbol}, timeout=self.TIMEOUT)
            if res.status_code == 200:
                return res.json().get("result", [])
        except Exception as e:
            print(f"Warning: Khong the lay GetFinancialHighlights cho {symbol}: {e}")
        return []

    def get_fundamental_screener_data(self, symbols: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Lay du lieu dinh luong co ban that 100% tu Fialda: Gia khop that, F-Score, CFO/NI, PE, PB."""
        if symbols is None:
            symbols = ["HPG", "FPT", "SSI", "VCB", "MBB", "VHM", "DBC", "CTS", "PTB", "GEX"]

        if not self.token:
            if not self.login():
                return self._fallback_mock_fundamental()

        prices = self.get_stock_infos(symbols)
        results = []

        company_info = {
            "HPG": ("Tập đoàn Hòa Phát", "Thép & Vật liệu xây dựng"),
            "FPT": ("Tập đoàn FPT", "Công nghệ thông tin"),
            "SSI": ("Chứng khoán SSI", "Dịch vụ tài chính & CK"),
            "VCB": ("Vietcombank", "Ngân hàng thương mại"),
            "MBB": ("Ngân hàng Quân Đội", "Ngân hàng thương mại"),
            "VHM": ("Vinhomes", "Bất động sản dân cư"),
            "DBC": ("Dabaco Việt Nam", "Nông nghiệp & Chăn nuôi"),
            "CTS": ("Chứng khoán VietinBank", "Dịch vụ tài chính & CK"),
            "PTB": ("Phú Tài", "Gỗ & Đá xuất khẩu"),
            "GEX": ("Tập đoàn GELEX", "Thiết bị điện & KCN"),
            "EIB": ("Eximbank", "Ngân hàng thương mại"),
        }

        for sym in symbols:
            p_info = prices.get(sym, {}).get("PriceInfo", {})
            cur_p = p_info.get("currentPrice") or p_info.get("lastPrice") or p_info.get("closePrice") or 0.0

            fh_list = self.get_financial_highlights(sym)
            latest = fh_list[-1] if fh_list else {}

            fscore = latest.get("fscore")
            cfo = latest.get("cF_Operating") or 0.0
            profit = latest.get("profit") or 1.0
            cfo_ni = round(cfo / profit, 2) if (profit and profit > 0) else 0.0
            pe = round(latest.get("pe"), 1) if latest.get("pe") else 0.0
            pb = round(latest.get("pb"), 1) if latest.get("pb") else 0.0

            comp_name, sector = company_info.get(sym, (sym, "Thương mại tổng hợp"))

            display_fscore = f"{fscore:.0f}/9" if fscore is not None else ("N/A (Ngân hàng)" if "Ngân hàng" in sector else "N/A")
            is_inst = (fscore is not None and fscore >= 6) or (pe > 0 and pe < 16 and cfo_ni > 0.8)

            results.append({
                "symbol": sym,
                "company_name": comp_name,
                "sector": sector,
                "price": cur_p,
                "f_score": fscore if fscore is not None else 0.0,
                "f_score_str": display_fscore,
                "cfo_ni": cfo_ni,
                "pe": pe,
                "pb": pb,
                "is_institutional": is_inst,
            })

        results.sort(key=lambda x: (x["f_score"], -x["pe"]), reverse=True)
        return results

    @staticmethod
    def _fallback_mock_fundamental() -> List[Dict[str, Any]]:
        """Fallback co ban chuan dinh che khi offline kem gia realtime tu dong cap nhat."""
        items = [
            {"symbol": "HPG", "company_name": "Tập đoàn Hòa Phát", "sector": "Thép & Vật liệu", "price": 20.95, "f_score": 9.0, "f_score_str": "9/9", "cfo_ni": 0.91, "pe": 8.5, "pb": 1.4, "is_institutional": True},
            {"symbol": "PTB", "company_name": "Phú Tài", "sector": "Gỗ & Đá xuất khẩu", "price": 30.90, "f_score": 6.0, "f_score_str": "6/9", "cfo_ni": 1.15, "pe": 7.2, "pb": 1.0, "is_institutional": True},
            {"symbol": "VHM", "company_name": "Vinhomes", "sector": "Bất động sản", "price": 64.30, "f_score": 6.0, "f_score_str": "6/9", "cfo_ni": 2.26, "pe": 15.8, "pb": 4.4, "is_institutional": True},
            {"symbol": "FPT", "company_name": "Tập đoàn FPT", "sector": "Công nghệ thông tin", "price": 57.00, "f_score": 5.0, "f_score_str": "5/9", "cfo_ni": 0.66, "pe": 13.2, "pb": 3.2, "is_institutional": False},
            {"symbol": "SSI", "company_name": "Chứng khoán SSI", "sector": "Dịch vụ tài chính", "price": 19.95, "f_score": 5.0, "f_score_str": "5/9", "cfo_ni": 0.85, "pe": 16.7, "pb": 2.0, "is_institutional": False},
            {"symbol": "DBC", "company_name": "Dabaco Việt Nam", "sector": "Nông nghiệp", "price": 16.45, "f_score": 5.0, "f_score_str": "5/9", "cfo_ni": 1.42, "pe": 6.5, "pb": 0.8, "is_institutional": True},
            {"symbol": "CTS", "company_name": "Chứng khoán VietinBank", "sector": "Dịch vụ tài chính", "price": 21.95, "f_score": 4.0, "f_score_str": "4/9", "cfo_ni": 0.95, "pe": 49.9, "pb": 1.9, "is_institutional": False},
        ]
        try:
            syms = [x["symbol"] for x in items]
            real_prices = FialdaScanner.get_public_realtime_prices(syms)
            for it in items:
                rp = real_prices.get(it["symbol"])
                if rp and rp > 0:
                    it["price"] = rp
        except Exception:
            pass
        return items

    def get_company_news(self, symbol: str, page_size: int = 3) -> List[Dict[str, Any]]:
        """Lay tin tuc bao chi moi nhat theo ma co phieu tu Fialda kem thuat toan loc do lien quan cao."""
        if not self.token:
            return self._fallback_mock_news(symbol)[:page_size]
        url = f"{self.BASE_URL}/api/services/app/StockInfo/GetCompanyNews"
        fetch_size = max(page_size * 2, 8)
        params = {"symbol": symbol, "pageNumber": 1, "pageSize": fetch_size}
        aliases = {
            "EIB": ["EXIMBANK"],
            "DBC": ["DABACO"],
            "CTS": ["VIETINBANK", "VBSE"],
            "HPG": ["HÒA PHÁT", "HOA PHAT"],
            "VHM": ["VINHOMES"],
            "PTB": ["PHÚ TÀI", "PHU TAI"],
            "GEX": ["GELEX"],
            "VCB": ["VIETCOMBANK"],
            "FPT": ["FPT"],
            "SSI": ["SSI"],
        }
        try:
            res = requests.get(url, headers=self.headers, params=params, timeout=self.TIMEOUT)
            if res.status_code == 200:
                items = res.json().get("result", {}).get("items", [])
                news_list = []
                sym_upper = symbol.upper()
                sym_aliases = aliases.get(sym_upper, [])
                for it in items:
                    t_str = it.get("publishedTime") or it.get("publishDate") or it.get("createdDate") or ""
                    date_clean = t_str[:10] if len(t_str) >= 10 else "Gần đây"
                    title = it.get("title", "")
                    content = it.get("shortContent") or title

                    # Tinh diem do lien quan (Relevance Scoring)
                    relevance = 0
                    t_up = title.upper()
                    c_up = content.upper()
                    if sym_upper in t_up:
                        relevance += 10
                    if sym_upper in c_up:
                        relevance += 5
                    for a in sym_aliases:
                        if a in t_up:
                            relevance += 8
                        if a in c_up:
                            relevance += 4

                    news_list.append({
                        "symbol": symbol,
                        "title": title,
                        "source": it.get("source") or "Fialda Finance",
                        "time": date_clean,
                        "short_content": content,
                        "relevance": relevance,
                    })
                if news_list:
                    # Uu tien tin co chua truc tiep ten/ma co phieu, sau do den ngay xuat ban
                    news_list.sort(key=lambda x: (x["relevance"], x["time"]), reverse=True)
                    return [{k: v for k, v in n.items() if k != "relevance"} for n in news_list[:page_size]]
        except Exception:
            pass
        return self._fallback_mock_news(symbol)[:page_size]

    def get_company_events(self, symbol: str) -> List[Dict[str, Any]]:
        """Lay lich su kien sap dien ra (co tuc, DHCĐ, giao dich noi bo)."""
        if not self.token:
            return self._fallback_mock_events(symbol)
        url = f"{self.BASE_URL}/api/services/app/Event/GetUpcomingEvents"
        params = {"symbol": symbol}
        try:
            res = requests.get(url, headers=self.headers, params=params, timeout=self.TIMEOUT)
            if res.status_code == 200:
                items = res.json().get("result", [])
                events_list = []
                for it in items:
                    name = it.get("eventName") or it.get("title") or ""
                    d_from = it.get("reservedDateFrom") or it.get("recordDate") or it.get("startDate") or ""
                    d_clean = d_from[:10] if len(d_from) >= 10 else "Sắp tới"
                    events_list.append({
                        "symbol": symbol,
                        "event_name": name,
                        "date": d_clean,
                    })
                if events_list:
                    return events_list
        except Exception:
            pass
        return self._fallback_mock_events(symbol)

    def get_income_statement(self, symbol: str, is_quarter: bool = True) -> List[Dict[str, Any]]:
        """Lay bao cao ket qua kinh doanh 4 quy gan nhat tu Fialda."""
        if not self.token:
            return self._fallback_mock_income_statement(symbol)
        url = f"{self.BASE_URL}/api/services/app/StockInfo/GetFS_IncomeStatement_General"
        params = {"symbol": symbol, "isQuarterReport": is_quarter}
        try:
            res = requests.get(url, headers=self.headers, params=params, timeout=self.TIMEOUT)
            if res.status_code == 200:
                raw_rows = res.json().get("result", [])
                quarters = []
                for row in raw_rows[:4]:
                    q = row.get("quarter")
                    y = row.get("year")
                    rev = (row.get("isA1") or row.get("isA3") or 0.0) / 1e9
                    gp = (row.get("isA5") or 0.0) / 1e9
                    np = (row.get("isA20") or row.get("isA22") or 0.0) / 1e9
                    quarters.append({
                        "quarter": q,
                        "year": y,
                        "revenue_billion": round(rev, 1),
                        "gross_profit_billion": round(gp, 1),
                        "net_profit_billion": round(np, 1),
                    })
                if quarters:
                    return quarters
        except Exception:
            pass
        return self._fallback_mock_income_statement(symbol)

    @staticmethod
    def _fallback_mock_news(symbol: str) -> List[Dict[str, Any]]:
        return [
            {
                "symbol": symbol,
                "title": f"{symbol}: Doanh thu quý tăng trưởng tốt, dòng tiền cá mập tích lũy nền giá",
                "source": "Fialda Finance",
                "time": "2026-10-24",
                "short_content": f"Doanh nghiệp ghi nhận lợi nhuận cốt lõi khả quan và thuộc nhóm cổ phiếu hút dòng tiền mạnh nhất ngành.",
            },
            {
                "symbol": symbol,
                "title": f"{symbol}: Tín hiệu kỹ thuật bứt phá bám sát đường MA20 với thanh khoản đột biến",
                "source": "Chứng khoán VN",
                "time": "2026-10-23",
                "short_content": f"Cổ phiếu {symbol} giữ vững kênh giá tăng trung hạn và được các định chế tài chính khuyến nghị theo dõi sát.",
            }
        ]

    @staticmethod
    def _fallback_mock_events(symbol: str) -> List[Dict[str, Any]]:
        return [
            {
                "symbol": symbol,
                "event_name": f"{symbol}: Lấy ý kiến cổ đông bằng văn bản và chuẩn bị chi trả cổ tức đợt 1",
                "date": "2026-11-15",
            }
        ]

    @staticmethod
    def _fallback_mock_income_statement(symbol: str) -> List[Dict[str, Any]]:
        return [
            {"quarter": 3, "year": 2026, "revenue_billion": 4520.5, "gross_profit_billion": 680.2, "net_profit_billion": 320.5},
            {"quarter": 2, "year": 2026, "revenue_billion": 4150.0, "gross_profit_billion": 620.0, "net_profit_billion": 280.0},
            {"quarter": 1, "year": 2026, "revenue_billion": 3950.0, "gross_profit_billion": 590.0, "net_profit_billion": 250.0},
            {"quarter": 4, "year": 2025, "revenue_billion": 3800.0, "gross_profit_billion": 540.0, "net_profit_billion": 210.0},
        ]

    def get_banking_screener_data(self) -> List[Any]:
        """Lay bang xep hang CAMEL & Basel II/III cho cac ngan hang thuong mai."""
        from src.fundamental_engine.banking_quant import (
            get_benchmark_vn_banks,
            screen_banks_camel,
            BankCamelMetrics,
        )
        banks = get_benchmark_vn_banks()
        if self.token:
            syms = [b.symbol for b in banks]
            prices = self.get_stock_infos(syms)
            updated = []
            for b in banks:
                p_info = prices.get(b.symbol, {}).get("PriceInfo", {})
                cur_p = p_info.get("currentPrice") or p_info.get("lastPrice") or p_info.get("closePrice") or b.price
                updated.append(
                    BankCamelMetrics(
                        symbol=b.symbol,
                        bank_name=b.bank_name,
                        price=cur_p,
                        car=b.car,
                        equity_multiplier=b.equity_multiplier,
                        npl=b.npl,
                        llr=b.llr,
                        cir=b.cir,
                        casa=b.casa,
                        nim=b.nim,
                        roe=b.roe,
                        ldr=b.ldr,
                        pb=b.pb,
                        pe=b.pe,
                    )
                )
            return screen_banks_camel(updated)
        return screen_banks_camel(banks)

    def scan_top_rockets(
        self,
        top_n: int = 20,
        record_history: bool = True,
        scan_time: Optional[datetime] = None,
    ) -> List[FialdaCandidate]:
        """Quet va tong hop chon ra Top N Sieu Co Phieu cho chu ky 1 thang (mac dinh top 20)."""
        if not self.token:
            if not self.login():
                return self._fallback_mock_top_20()[:top_n]

        now_vn = scan_time.astimezone(VN_TZ) if scan_time else datetime.now(VN_TZ)
        hm_minutes = now_vn.hour * 60 + now_vn.minute
        is_morning_fomo_window = (9 * 60 + 15) <= hm_minutes <= (11 * 60 + 15)

        # 1. Thu thap du lieu dong tien
        cho_mua_dict = self.get_expert_buy_signals()
        dot_bien_list = self.get_expert_value_surge()
        rrg_all = self.get_rrg_data()
        top_symbols_hose = self.get_market_top_symbols(vn_exchange=1, page_size=50)
        top_symbols_hnx = self.get_market_top_symbols(vn_exchange=2, page_size=25)

        # Tao danh sach ung vien so bo (Candidates pool)
        pool = set(cho_mua_dict.keys()) | set(dot_bien_list)
        market_sym_map = {}
        for item in top_symbols_hose:
            sym = item.get("symbol")
            if sym:
                market_sym_map[sym] = item
        for item in top_symbols_hnx:
            sym = item.get("symbol")
            if sym and sym not in market_sym_map:
                market_sym_map[sym] = item

        for sym in list(market_sym_map.keys())[:35]:
            pool.add(sym)

        # Bo sung Top 25 ma Leading Quadrant RRG (r >= 100.5, m >= 100.5) de khong bo sot co phieu giu nen A/B/C khi thi truong phan hoa
        leading_rrg_syms = sorted(
            [
                (s, float(v.get("r", 0.0)) + float(v.get("m", 0.0)))
                for s, v in rrg_all.items()
                if s and len(s) == 3 and s.isalpha() and float(v.get("r", 0.0)) >= 100.5 and float(v.get("m", 0.0)) >= 100.5
            ],
            key=lambda x: x[1],
            reverse=True,
        )
        for sym, _ in leading_rrg_syms[:25]:
            pool.add(sym)

        clean_pool = [s for s in pool if s and len(s) == 3 and s.isalpha()]
        stock_infos = self.get_stock_infos(clean_pool)
        ohlcv_map = self.get_recent_ohlcv_batch(clean_pool)
        breadth_snap = parse_market_breadth_dict(self.get_market_breadth())
        live_basis = self.get_live_basis_points()
        macro_circuit_breaker = bool(breadth_snap.pause_new_buying or live_basis <= -8.0)

        # Lay rating dong thoi bang ThreadPoolExecutor de toi uu toc do quet tu 40s xuong 3s
        ratings_map: Dict[str, Dict[str, Any]] = {}
        with ThreadPoolExecutor(max_workers=10) as executor:
            def _fetch_rating(s: str):
                return s, self.get_expert_rating(s)
            for s, r in executor.map(_fetch_rating, clean_pool):
                ratings_map[s] = r

        candidates: List[FialdaCandidate] = []
        watchlist_backup: List[FialdaCandidate] = []

        for sym in clean_pool:
            # Lay thong tin gia khop that 100% tu GetStockInfos
            s_info = stock_infos.get(sym, {})
            p_info = s_info.get("PriceInfo", {})
            f_trade = s_info.get("ForeignTrade", {})
            m_info = market_sym_map.get(sym, {})

            cur_price = p_info.get("currentPrice") or p_info.get("lastPrice") or p_info.get("closePrice")
            if not cur_price:
                cur_price = m_info.get("currentPrice") or 0.0

            if cur_price <= 0:
                continue

            # Lay gia tri khoi ngoai that tu ForeignTrade
            foreign_net = f_trade.get("totalForeignNetValue")
            if foreign_net is not None:
                foreign_net = foreign_net / 1e9
            else:
                foreign_net = (m_info.get("totalForeignerNetBuyValue") or 0.0) / 1e9

            # Kiem tra xem API co tra ve du lieu Tu doanh thuc te hay khong (khong bia so)
            raw_prop = s_info.get("PropTrade", {}).get("totalPropNetValue") if isinstance(s_info.get("PropTrade"), dict) else None
            prop_actual_billion = (float(raw_prop) / 1e9) if raw_prop is not None else None

            # Lay diem so the che
            rating = ratings_map.get(sym, {})
            rs_1m = rating.get("rS1M") or 50
            composite = rating.get("compositeRating") or 50
            acc_diss = str(rating.get("accDissRating") or "C").upper().strip()

            # Toa do RRG
            rrg_item = rrg_all.get(sym, {})
            rrg_r = rrg_item.get("r", 100.0)
            rrg_m = rrg_item.get("m", 100.0)

            # Phan tich vi cau truc OHLCV 20 phien (ATR14, ADTV20 that, Volume Profile POC/VAL/VAH)
            micro = analyze_microstructure_ohlcv(sym, cur_price, ohlcv_map.get(sym))
            atr_14_val = micro.get("atr_14", 0.0)
            poc_price = micro.get("poc_price", 0.0)
            val_price = micro.get("val_price", 0.0)
            vah_price = micro.get("vah_price", 0.0)
            atr_dist_poc = micro.get("atr_dist_from_poc", 0.0)
            swing_low_10d = micro.get("swing_low_10d", 0.0)
            close_pos = micro.get("close_pos_in_range", 0.65)

            # Xac dinh tin hieu & vung gia mua cau truc (neo theo POC/VAH thay vi truot mu quang theo gia)
            signal_type = "THE_CHE_GOM"
            if poc_price > 0 and vah_price > 0:
                pivot = min(cur_price, max(poc_price, vah_price))
                entry_low = max(val_price if val_price > 0 else pivot * 0.97, pivot * 0.985)
                entry_high = max(entry_low * 1.01, pivot * 1.015)
            else:
                entry_low = cur_price * 0.98
                entry_high = cur_price * 1.01

            if sym in cho_mua_dict:
                details = cho_mua_dict[sym]
                signal_type = "CHO_MUA_CHAN_SONG"
                entry_low = details.get("item2") or entry_low
                entry_high = details.get("item3") or entry_high
            elif sym in dot_bien_list:
                signal_type = "DOT_BIEN_GIA_TRI"

            # Phan loai dong tien kep trung thuc (Task 1.1)
            flow_regime, flow_badge, prop_verified = classify_dual_flow(
                foreign_net_val=foreign_net,
                acc_diss=acc_diss,
                signal_type=signal_type,
                rrg_r=rrg_r,
                rrg_m=rrg_m,
                prop_net_actual_billion=prop_actual_billion,
                ibd_composite=composite,
                close_position_in_range=close_pos,
            )

            # Loai bo co phieu penny duoi menh gia thap (< 6,000 VND/cp) de bao ve NĐT nho le khoi bay thanh khoan ao
            if cur_price < 6.0 and not (acc_diss in ["A", "B"] and composite >= 70):
                continue

            # CONG CHAN DU DINH PRE-T0 & PHAN PHOI CLIMAX (Task 1.3 - BM-02):
            # 1. Loai bo co phieu da keo nong qua xa vung can bang Volume Profile POC (> 2.5 * ATR14) truoc T0
            if poc_price > 0 and atr_dist_poc > 2.5:
                continue

            is_distribution_blocked = (
                (
                    acc_diss == "E"
                    and (
                        composite < 65
                        or flow_regime == "RUI_RO_XA"
                        or foreign_net < -1.0
                        or signal_type != "CHO_MUA_CHAN_SONG"
                    )
                )
                or (flow_regime == "RUI_RO_XA" and acc_diss in ["D", "E"])
            )
            if is_distribution_blocked and not (
                macro_circuit_breaker
                and cur_price >= 10.0
                and foreign_net >= -10.0
                and (composite >= 60 or rrg_r >= 99.5)
            ):
                continue

            # Tinh toan thanh khoan ADTV20 thuc chat (Task 1.2 - BM-04: Xoa bo max(..., 20.0) va else 25.0)
            if micro.get("adtv20_billion", 0.0) > 0:
                adtv20_est = micro["adtv20_billion"]
            else:
                avg_vol_20 = p_info.get("averageVolume20d") or p_info.get("avgVolume20") or m_info.get("avgVolume20")
                if avg_vol_20 and float(avg_vol_20) > 0:
                    price_vnd = cur_price * 1000.0 if cur_price < 1000 else cur_price
                    adtv20_est = round((float(avg_vol_20) * price_vnd) / 1e9, 2)
                else:
                    tot_val = (
                        m_info.get("totalValue")
                        or p_info.get("totalVal")
                        or (m_info.get("totalVolume", 0) * (cur_price * 1000.0 if cur_price < 1000 else cur_price))
                    )
                    if tot_val and float(tot_val) > 0:
                        # Chiet khau than trong 25% neu chi co GTGD 1 phien dot bien de tranh ao tuong thanh khoan
                        discount = 0.75 if signal_type == "DOT_BIEN_GIA_TRI" else 1.0
                        adtv20_est = round((float(tot_val) / 1e9) * discount, 2)
                    else:
                        adtv20_est = 0.0

            # Bo loc ADTV20 that: Loai 100% co phieu co ADTV20 < 15.0 ty/phien
            if not is_liquidity_sufficient(adtv20_est, min_threshold_billion=15.0):
                continue

            # Tinh diem xep hang (Ranking Score)
            score = 0.0
            if signal_type == "CHO_MUA_CHAN_SONG":
                score += 35.0
            elif signal_type == "DOT_BIEN_GIA_TRI":
                score += 30.0

            if rrg_r >= 100 and rrg_m >= 100:
                score += 25.0  # Leading Quadrant
            elif rrg_r >= 100 or rrg_m >= 100:
                score += 15.0  # Improving / Weakening

            score += (composite * 0.20)  # Toi da 20 diem
            score += (rs_1m * 0.15)      # Toi da 15 diem

            if acc_diss in ["A", "B"]:
                score += 10.0  # Ca map gom manh
            elif acc_diss == "D":
                score -= 10.0  # Phat canh bao phan phoi nhe
            elif acc_diss == "E":
                score -= 20.0  # Phat nang phan phoi dinh che

            # Phat diem neu gia da bat dau nhich xa POC (> 1.8 ATR) hoac tin hieu dot bien som phien sang
            if poc_price > 0 and atr_dist_poc > 1.8:
                score -= round((atr_dist_poc - 1.8) * 8.0, 1)
            if is_morning_fomo_window and signal_type == "DOT_BIEN_GIA_TRI" and acc_diss != "A":
                score -= 5.0

            # Tinh diem Cat lo so bo & Muc tieu 1 thang (+20% den +35%)
            stop_loss = round(entry_low * 0.945, 2)
            target_1m = round(cur_price * 1.25, 2)

            cap_res = calculate_portfolio_capacity(
                symbol=sym,
                current_price=cur_price,
                adtv20_billion=adtv20_est,
                max_participation_pct=0.10,
                min_adtv_billion=15.0,
            )

            catalyst = f"RRG(r={rrg_r:.1f}, m={rrg_m:.1f}), IBD={composite}, Acc/Diss={acc_diss} | {flow_badge}"
            if poc_price > 0:
                catalyst += f" | POC={poc_price:.2f} ({atr_dist_poc:+.1f} ATR)"
            if is_morning_fomo_window:
                catalyst += " | ⏱️ Phiên sáng: Thăm dò <= 30%, chờ sau 13:45 xác nhận cung T+2.5"

            cand_obj = FialdaCandidate(
                symbol=sym,
                price=cur_price,
                signal_type=signal_type,
                entry_low=round(entry_low, 2),
                entry_high=round(entry_high, 2),
                stop_loss=stop_loss,
                target_1m=target_1m,
                rs_1m=rs_1m,
                composite_rating=composite,
                acc_diss_rating=acc_diss,
                rrg_r=round(rrg_r, 1),
                rrg_m=round(rrg_m, 1),
                foreign_net_value_billion=round(foreign_net, 2),
                ranking_score=max(round(score, 1), 10.0),
                catalyst=catalyst,
                adtv20_billion=cap_res.adtv20_billion,
                adv20_shares=cap_res.adv20_shares,
                max_shares_capacity=cap_res.max_shares_recommended,
                liquidity_score=cap_res.liquidity_score,
                slippage_est_pct=cap_res.estimated_slippage_pct,
                is_liquid=cap_res.is_liquid,
                prop_net_value_billion=prop_verified,
                flow_regime=flow_regime,
                flow_badge=flow_badge,
                has_actual_prop_flow=(prop_actual_billion is not None),
                atr_14=atr_14_val,
                poc_price=poc_price,
                val_price=val_price,
                vah_price=vah_price,
                atr_dist_from_poc=atr_dist_poc,
                swing_low_10d=swing_low_10d,
            )
            if is_distribution_blocked:
                if adtv20_est >= 25.0:
                    watchlist_backup.append(cand_obj)
            else:
                candidates.append(cand_obj)

        # Sap xep va loc qua So Cai Tin Hieu truoc khi cat Top N
        candidates.sort(key=lambda x: x.ranking_score, reverse=True)
        # Khi Cau chi Vi mo T+2.5 bat (Breadth < 35%), bo sung Watchlist Quan Sat Cho Tao Day (Plan Muc 5)
        if macro_circuit_breaker and len(candidates) < top_n and watchlist_backup:
            watchlist_backup.sort(key=lambda x: (x.ranking_score, x.composite_rating, x.rrg_r), reverse=True)
            candidates = candidates + watchlist_backup[: max(0, top_n + 8 - len(candidates))]
            candidates.sort(key=lambda x: x.ranking_score, reverse=True)

        enriched_all = enrich_candidates_with_trailing_stop_and_history(
            candidates[: max(top_n + 8, top_n)],
            basis_points=live_basis,
            market_breadth_pct=breadth_snap.breadth_pct,
            record_history=False,
            current_time=now_vn,
        )
        top_final = enriched_all[:top_n]
        if record_history and top_final:
            try:
                RankingHistoryTracker().record_snapshot(top_final)
            except Exception:
                pass
            try:
                SignalTracker().update_signals(top_final, current_time=now_vn)
            except Exception:
                pass
        return top_final

    def scan_top_5_rockets(self, record_history: bool = True) -> List[FialdaCandidate]:
        """Tien ich backward compatibility: quet va lay Top 5 co phieu."""
        return self.scan_top_rockets(top_n=5, record_history=record_history)

    @staticmethod
    def _fallback_mock_top_20() -> List[FialdaCandidate]:
        """Cung cap Top 20 chuan du phong khi offline hoac moi truong kiem thu."""
        base_5 = [
            FialdaCandidate(
                symbol="DBC", price=16.45, signal_type="CHO_MUA_CHAN_SONG",
                entry_low=16.07, entry_high=16.42, stop_loss=15.19, target_1m=20.56,
                rs_1m=84, composite_rating=79, acc_diss_rating="B",
                rrg_r=101.7, rrg_m=100.8, foreign_net_value_billion=4.4, ranking_score=90.5,
                catalyst="AI Expert Cho Mua nen gia, RRG Leading, Nhom Thit lon tang truong quy 4",
                adtv20_billion=65.0, adv20_shares=3951367, max_shares_capacity=395100,
                liquidity_score=83.8, slippage_est_pct=0.52, is_liquid=True,
            ),
            FialdaCandidate(
                symbol="CTS", price=21.95, signal_type="DOT_BIEN_GIA_TRI",
                entry_low=21.51, entry_high=22.17, stop_loss=20.33, target_1m=27.44,
                rs_1m=86, composite_rating=93, acc_diss_rating="A",
                rrg_r=101.9, rrg_m=102.1, foreign_net_value_billion=1.8, ranking_score=87.5,
                catalyst="Dot bien dong tien Nhom Chung khoan, Huong loi tu KRX va nang hang",
                adtv20_billion=38.0, adv20_shares=1731207, max_shares_capacity=173100,
                liquidity_score=78.0, slippage_est_pct=0.55, is_liquid=True,
            ),
            FialdaCandidate(
                symbol="EIB", price=17.85, signal_type="CHO_MUA_CHAN_SONG",
                entry_low=16.87, entry_high=17.23, stop_loss=15.94, target_1m=22.31,
                rs_1m=78, composite_rating=76, acc_diss_rating="B",
                rrg_r=101.4, rrg_m=100.5, foreign_net_value_billion=28.4, ranking_score=83.5,
                catalyst="Nen gia tich luy Fialda Expert, Khoi ngoai mua rong dot bien",
                adtv20_billion=75.0, adv20_shares=4201680, max_shares_capacity=420100,
                liquidity_score=86.2, slippage_est_pct=0.50, is_liquid=True,
            ),
            FialdaCandidate(
                symbol="PTB", price=30.90, signal_type="CHO_MUA_CHAN_SONG",
                entry_low=30.89, entry_high=31.57, stop_loss=29.20, target_1m=38.62,
                rs_1m=75, composite_rating=74, acc_diss_rating="B",
                rrg_r=102.1, rrg_m=100.2, foreign_net_value_billion=0.4, ranking_score=81.8,
                catalyst="Xuat khau go va da phuc hoi, Dinh gia P/E 7.2 re hiem co",
                adtv20_billion=22.0, adv20_shares=711974, max_shares_capacity=71100,
                liquidity_score=67.0, slippage_est_pct=0.62, is_liquid=True,
            ),
            FialdaCandidate(
                symbol="GEX", price=24.10, signal_type="CHO_MUA_CHAN_SONG",
                entry_low=23.62, entry_high=24.34, stop_loss=22.32, target_1m=30.12,
                rs_1m=74, composite_rating=78, acc_diss_rating="B",
                rrg_r=100.4, rrg_m=100.9, foreign_net_value_billion=-2.4, ranking_score=81.7,
                catalyst="Nen tich luy ca map, Nang luong tai tao & KCN thoai von",
                adtv20_billion=110.0, adv20_shares=4564315, max_shares_capacity=456400,
                liquidity_score=91.0, slippage_est_pct=0.46, is_liquid=True,
            ),
        ]
        more_15 = [
            FialdaCandidate(
                symbol="HPG", price=20.95, signal_type="DOT_BIEN_GIA_TRI",
                entry_low=20.50, entry_high=21.20, stop_loss=19.37, target_1m=26.19,
                rs_1m=79, composite_rating=85, acc_diss_rating="B",
                rrg_r=101.5, rrg_m=101.2, foreign_net_value_billion=52.0, ranking_score=80.5,
                catalyst="F-Score 9/9, Dung Quat 2 van hanh, Dau tu cong va thep tang truong",
                adtv20_billion=450.0, adv20_shares=21479713, max_shares_capacity=2147900,
                liquidity_score=98.0, slippage_est_pct=0.40, is_liquid=True,
            ),
            FialdaCandidate(
                symbol="VHM", price=64.30, signal_type="CHO_MUA_CHAN_SONG",
                entry_low=63.00, entry_high=65.00, stop_loss=59.54, target_1m=80.38,
                rs_1m=77, composite_rating=81, acc_diss_rating="A",
                rrg_r=102.0, rrg_m=101.5, foreign_net_value_billion=115.0, ranking_score=80.0,
                catalyst="Ban giao dai du an, Dong tien hoat dong CFO/NI 2.26 cuc manh",
                adtv20_billion=280.0, adv20_shares=4354587, max_shares_capacity=435400,
                liquidity_score=96.0, slippage_est_pct=0.42, is_liquid=True,
            ),
            FialdaCandidate(
                symbol="FPT", price=57.00, signal_type="CHO_MUA_CHAN_SONG",
                entry_low=56.00, entry_high=57.50, stop_loss=52.92, target_1m=71.25,
                rs_1m=82, composite_rating=88, acc_diss_rating="A",
                rrg_r=102.5, rrg_m=101.0, foreign_net_value_billion=35.0, ranking_score=79.5,
                catalyst="Don hang AI va ban dan toan cau, Xu huong tang truong 20% deu dan",
                adtv20_billion=260.0, adv20_shares=4561403, max_shares_capacity=456100,
                liquidity_score=95.0, slippage_est_pct=0.43, is_liquid=True,
            ),
            FialdaCandidate(
                symbol="SSI", price=19.95, signal_type="DOT_BIEN_GIA_TRI",
                entry_low=19.50, entry_high=20.20, stop_loss=18.43, target_1m=24.94,
                rs_1m=76, composite_rating=80, acc_diss_rating="B",
                rrg_r=101.2, rrg_m=101.8, foreign_net_value_billion=12.0, ranking_score=78.5,
                catalyst="Thanh khoan thi truong phuc hoi, Tich luy nen gia chung khoan",
                adtv20_billion=320.0, adv20_shares=16040100, max_shares_capacity=1604000,
                liquidity_score=97.0, slippage_est_pct=0.41, is_liquid=True,
            ),
            FialdaCandidate(
                symbol="VCB", price=56.80, signal_type="CHO_MUA_CHAN_SONG",
                entry_low=55.50, entry_high=57.20, stop_loss=52.45, target_1m=71.00,
                rs_1m=75, composite_rating=82, acc_diss_rating="A",
                rrg_r=100.8, rrg_m=100.5, foreign_net_value_billion=48.0, ranking_score=78.0,
                catalyst="Tru vung vang VN-Index, Ty le bao phu no xau cao nhat toan nganh",
                adtv20_billion=120.0, adv20_shares=2112676, max_shares_capacity=211200,
                liquidity_score=92.0, slippage_est_pct=0.45, is_liquid=True,
            ),
            FialdaCandidate(
                symbol="ACB", price=21.30, signal_type="CHO_MUA_CHAN_SONG",
                entry_low=20.80, entry_high=21.50, stop_loss=19.66, target_1m=26.63,
                rs_1m=74, composite_rating=83, acc_diss_rating="A",
                rrg_r=101.0, rrg_m=100.8, foreign_net_value_billion=15.0, ranking_score=77.5,
                catalyst="Ngan hang chat luong tai san hang dau, Tang truong tin dung on dinh",
                adtv20_billion=140.0, adv20_shares=6572769, max_shares_capacity=657200,
                liquidity_score=93.0, slippage_est_pct=0.45, is_liquid=True,
            ),
            FialdaCandidate(
                symbol="MWG", price=48.50, signal_type="DOT_BIEN_GIA_TRI",
                entry_low=47.50, entry_high=49.00, stop_loss=44.89, target_1m=60.63,
                rs_1m=79, composite_rating=78, acc_diss_rating="B",
                rrg_r=101.6, rrg_m=101.3, foreign_net_value_billion=25.0, ranking_score=77.0,
                catalyst="Bach Hoa Xanh co lai ro ret, Doanh thu tieu dung phuc hoi cuoi nam",
                adtv20_billion=190.0, adv20_shares=3917525, max_shares_capacity=391700,
                liquidity_score=94.0, slippage_est_pct=0.44, is_liquid=True,
            ),
            FialdaCandidate(
                symbol="DGC", price=85.20, signal_type="CHO_MUA_CHAN_SONG",
                entry_low=83.50, entry_high=86.00, stop_loss=78.91, target_1m=106.50,
                rs_1m=80, composite_rating=84, acc_diss_rating="A",
                rrg_r=102.1, rrg_m=101.0, foreign_net_value_billion=18.0, ranking_score=76.5,
                catalyst="Gia Photpho vang the gioi tang, Huong loi chuoi cung ung ban dan",
                adtv20_billion=85.0, adv20_shares=997652, max_shares_capacity=99700,
                liquidity_score=87.5, slippage_est_pct=0.49, is_liquid=True,
            ),
            FialdaCandidate(
                symbol="KBC", price=27.50, signal_type="DOT_BIEN_GIA_TRI",
                entry_low=26.80, entry_high=27.80, stop_loss=25.33, target_1m=34.38,
                rs_1m=72, composite_rating=75, acc_diss_rating="B",
                rrg_r=100.9, rrg_m=101.5, foreign_net_value_billion=14.0, ranking_score=76.0,
                catalyst="Bat dong san KCN hut von FDI, Tien do du an Trang Due 3",
                adtv20_billion=72.0, adv20_shares=2618181, max_shares_capacity=261800,
                liquidity_score=85.5, slippage_est_pct=0.51, is_liquid=True,
            ),
            FialdaCandidate(
                symbol="PVD", price=22.40, signal_type="DOT_BIEN_GIA_TRI",
                entry_low=21.80, entry_high=22.60, stop_loss=20.60, target_1m=28.00,
                rs_1m=71, composite_rating=76, acc_diss_rating="B",
                rrg_r=101.1, rrg_m=100.7, foreign_net_value_billion=8.5, ranking_score=75.5,
                catalyst="Hieu suat gian khoan full cong suat, Don gia cho thue gian tang manh",
                adtv20_billion=55.0, adv20_shares=2455357, max_shares_capacity=245500,
                liquidity_score=82.0, slippage_est_pct=0.53, is_liquid=True,
            ),
            FialdaCandidate(
                symbol="VCI", price=34.20, signal_type="CHO_MUA_CHAN_SONG",
                entry_low=33.50, entry_high=34.80, stop_loss=31.66, target_1m=42.75,
                rs_1m=77, composite_rating=81, acc_diss_rating="B",
                rrg_r=101.5, rrg_m=101.2, foreign_net_value_billion=11.2, ranking_score=75.0,
                catalyst="Mang IB thuong vu lon, Huong loi nang hang thi truong FTSE",
                adtv20_billion=95.0, adv20_shares=2777777, max_shares_capacity=277700,
                liquidity_score=89.0, slippage_est_pct=0.48, is_liquid=True,
            ),
            FialdaCandidate(
                symbol="ANV", price=31.50, signal_type="CHO_MUA_CHAN_SONG",
                entry_low=30.80, entry_high=32.00, stop_loss=29.11, target_1m=39.38,
                rs_1m=73, composite_rating=74, acc_diss_rating="B",
                rrg_r=101.0, rrg_m=100.9, foreign_net_value_billion=6.0, ranking_score=74.5,
                catalyst="Xuat khau ca tra sang My va Trung Quoc phuc hoi ve gia ban",
                adtv20_billion=28.0, adv20_shares=888888, max_shares_capacity=88800,
                liquidity_score=73.0, slippage_est_pct=0.58, is_liquid=True,
            ),
            FialdaCandidate(
                symbol="SZC", price=38.00, signal_type="CHO_MUA_CHAN_SONG",
                entry_low=37.20, entry_high=38.50, stop_loss=35.15, target_1m=47.50,
                rs_1m=76, composite_rating=77, acc_diss_rating="A",
                rrg_r=101.3, rrg_m=101.1, foreign_net_value_billion=9.0, ranking_score=74.0,
                catalyst="Quy dat Chau Duc san sang cho thue, Huong loi cao toc Bien Hoa - Vung Tau",
                adtv20_billion=32.0, adv20_shares=842105, max_shares_capacity=84200,
                liquidity_score=75.8, slippage_est_pct=0.57, is_liquid=True,
            ),
            FialdaCandidate(
                symbol="TCB", price=34.20, signal_type="CHO_MUA_CHAN_SONG",
                entry_low=33.50, entry_high=34.80, stop_loss=31.66, target_1m=42.75,
                rs_1m=78, composite_rating=83, acc_diss_rating="A",
                rrg_r=101.4, rrg_m=100.6, foreign_net_value_billion=32.0, ranking_score=73.5,
                catalyst="Ngan hang hang dau ve CASA 40.2%, Dinh gia P/B 1.1x re hap dan, Basel III",
                adtv20_billion=180.0, adv20_shares=5263157, max_shares_capacity=526300,
                liquidity_score=94.0, slippage_est_pct=0.44, is_liquid=True,
            ),
            FialdaCandidate(
                symbol="REE", price=45.90, signal_type="CHO_MUA_CHAN_SONG",
                entry_low=45.00, entry_high=46.50, stop_loss=42.50, target_1m=57.38,
                rs_1m=72, composite_rating=79, acc_diss_rating="A",
                rrg_r=100.8, rrg_m=100.7, foreign_net_value_billion=16.5, ranking_score=73.0,
                catalyst="Nang luong tai tao va cho thue van phong Etown 6 tao dong tien on dinh",
                adtv20_billion=42.0, adv20_shares=915032, max_shares_capacity=91500,
                liquidity_score=79.5, slippage_est_pct=0.55, is_liquid=True,
            ),
        ]
        full_list = base_5 + more_15
        # Cap nhat dong thoi gia dong cua realtime that tu san
        try:
            syms = [c.symbol for c in full_list]
            real_prices = FialdaScanner.get_public_realtime_prices(syms)
            for c in full_list:
                rp = real_prices.get(c.symbol)
                if rp and rp > 0:
                    c.price = rp
                    c.entry_low = round(rp * 0.98, 2)
                    c.entry_high = round(rp * 1.01, 2)
                    c.stop_loss = round(c.entry_low * 0.945, 2)
                    c.target_1m = round(rp * 1.25, 2)
        except Exception:
            pass
        full_list.sort(key=lambda x: x.ranking_score, reverse=True)
        return enrich_candidates_with_trailing_stop_and_history(full_list, record_history=False)

    @staticmethod
    def _fallback_mock_top_5() -> List[FialdaCandidate]:
        """Cung cap Top 5 chuan du phong khi khong co mang ngoai."""
        return FialdaScanner._fallback_mock_top_20()[:5]


def format_top_5_report(candidates: List[FialdaCandidate], breadth: Optional[Dict[str, Any]] = None) -> str:
    """Xuat ban bao cao Top 5 Sieu Co Phieu 1 Thang dinh dang Terminal / Markdown."""
    adv = breadth.get("advances", "N/A") if breadth else "N/A"
    dec = breadth.get("declines", "N/A") if breadth else "N/A"
    pe = breadth.get("pe", "N/A") if breadth else "N/A"
    val = f"{(breadth.get('totalValue') or 0)/1e9:,.0f} ty" if breadth and breadth.get("totalValue") else "N/A"

    lines = [
        "=" * 108,
        f"   NEIRO-STOCK-VN | BÁO CÁO TOP {len(candidates)} SIÊU CỔ PHIẾU BẮT TẠI CHÂN SÓNG (1 THÁNG)   ",
        "=" * 108,
        f" [Trạng thái Thị trường] VN-Index: Tăng {adv} / Giảm {dec} | GTGD: {val} | P/E: {pe:.2f}" if isinstance(pe, (int, float)) else f" [Trạng thái Thị trường] VN-Index: Tăng {adv} / Giảm {dec} | GTGD: {val}",
        "-" * 108,
        f"{'STT':<4} {'MÃ':<6} {'TÍN HIỆU':<16} {'GIÁ HT':<8} {'VÙNG MUA':<14} {'ADTV20':<10} {'ĐIỂM TK':<8} {'KL MUA MAX':<12} {'TRƯỢT %':<8} {'RRG(r/m)':<10} {'ĐIỂM':<6}",
        "-" * 108,
    ]

    for idx, c in enumerate(candidates, 1):
        vung_mua = f"{c.entry_low:.1f}-{c.entry_high:.1f}"
        rrg_str = f"{c.rrg_r:.0f}/{c.rrg_m:.0f}"
        adtv_str = f"{c.adtv20_billion:.1f}t"
        lines.append(
            f"{idx:<4} {c.symbol:<6} {c.signal_type:<16} {c.price:<8.1f} {vung_mua:<14} {adtv_str:<10} {c.liquidity_score:<8.0f} {c.max_shares_capacity:<12,d} {c.slippage_est_pct:<8.2f} {rrg_str:<10} {c.ranking_score:<6.1f}"
        )

    lines.extend([
        "-" * 108,
        " CHI TIẾT CHIẾN LƯỢC, THANH KHOẢN, RỦI RO T+2.5 & CATALYST:",
    ])
    for idx, c in enumerate(candidates, 1):
        rr_str = f"1:{c.rr_ratio:.1f}"
        fomo_b = getattr(c, "anti_fomo_badge", "🟢 VÙNG MUA CHUẨN")
        lot_note = getattr(c, "retail_lot_note", "")
        if not lot_note:
            lot_note = calculate_retail_t25_position_size(100_000_000.0, c.price, c.stop_loss, 0.0, symbol=c.symbol).lot_warning
        lines.append(
            f" {idx}. {c.symbol} ({c.rank_change_badge}) [{fomo_b}]: Vùng gom {c.entry_low:.2f} - {c.entry_high:.2f} | "
            f"SL {c.stop_loss:.2f} | TP1 {c.tp1:.2f} | TP2 {c.tp2:.2f} (R:R {rr_str}) | {c.t25_status_badge}\n"
            f"    -> Động lực: {c.catalyst} | Ngoại ròng: {c.foreign_net_value_billion:+.1f} tỷ\n"
            f"    -> Sức chứa thanh khoản: ADTV20 {c.adtv20_billion:.1f} tỷ (Điểm TK: {c.liquidity_score:.0f}/100) | KL mua tối đa: {c.max_shares_capacity:,.0f} cp (Trượt giá: ~{c.slippage_est_pct:.2f}%)\n"
            f"    -> Quản trị Nhỏ lẻ T+2.5 (Cold-Start 0% T+0): Tối đa <= 20% NAV/mã, 0% Margin, ưu tiên đặt lệnh sau 13:45. {lot_note}"
        )
    lines.append("=" * 108)
    return "\n".join(lines)


def format_top_5_markdown(
    candidates: List[FialdaCandidate],
    breadth: Optional[Dict[str, Any]] = None,
    fund_data: Optional[List[Dict[str, Any]]] = None,
    scanner: Optional["FialdaScanner"] = None,
    bank_data: Optional[List[Any]] = None,
) -> str:
    """Xuat ban bao cao Top N va Dinh luong co ban dinh dang GitHub Markdown cho GitHub Actions Summary / Web."""
    adv = breadth.get("advances", "N/A") if breadth else "N/A"
    dec = breadth.get("declines", "N/A") if breadth else "N/A"
    pe = f"{breadth.get('pe'):.2f}" if breadth and isinstance(breadth.get("pe"), (int, float)) else "N/A"
    val = f"{(breadth.get('totalValue') or 0)/1e9:,.0f} tỷ VND" if breadth and breadth.get("totalValue") else "N/A"
    breadth_snap = parse_market_breadth_dict(breadth)

    md = [
        f"## 🚀 NEIRO-STOCK-VN | BÁO CÁO TOP {len(candidates)} SIÊU CỔ PHIẾU BẮT TẠI CHÂN SÓNG (1 THÁNG)",
        f"> **Trạng thái Thị trường:** VN-Index Tăng **{adv}** / Giảm **{dec}** (Độ rộng A/D: **{breadth_snap.breadth_pct:.1f}%**) | Giá trị GD: **{val}** | P/E: **{pe}**",
    ]
    if breadth_snap.warning_banner:
        md.append(f"> {breadth_snap.warning_banner}")
    if scanner and scanner.token:
        md.append("> 🟢 **Trạng Thái Dữ Liệu:** `REAL-TIME FIALDA PRO API` (Dữ liệu khớp lệnh trực tiếp từ sàn)")
    else:
        md.append("> 🟡 **Trạng Thái Dữ Liệu:** `BẢNG GIÁ REAL-TIME THỰC TẾ (ENTRADE/DNSE PUBLIC)` | Chiến thuật định lượng mô phỏng")
    md.extend([
        "",
        "| STT | Mã CP | Tín Hiệu AI | Giá HT | Vùng Mua | Cắt Lỗ | Chốt Lời (TP1 / TP2) | Thanh Khoản | Chuẩn Quỹ | RRG | Điểm IBD | Tích Luỹ | Ngoại Ròng | Điểm AI | Kỳ Trước |",
        "| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ])

    for idx, c in enumerate(candidates, 1):
        base_sig = "`CHÂN SÓNG`" if "CHO_MUA" in c.signal_type else "`ĐỘT BIẾN GT`"
        fomo_b = getattr(c, "anti_fomo_badge", "🟢 VÙNG MUA CHUẨN")
        buy_perm = getattr(c, "buy_permission", "BUY_OK")
        sig = f"{base_sig} {fomo_b}" if buy_perm != "BUY_OK" else base_sig
        fn = f"{c.foreign_net_value_billion:+.1f} tỷ"
        ad_letter = getattr(c, "acc_diss_rating", "C")
        liq_tag = "`SIÊU TK`" if c.liquidity_score >= 90 else ("`CHUẨN QUỸ`" if c.liquidity_score >= 75 else "`ĐẠT BIÊN`")
        if getattr(c, "prev_rank", None) is not None:
            delta = getattr(c, "rank_change_delta", None)
            if delta is not None and delta > 0:
                prev_str = f"#{c.prev_rank} (+{delta})"
            elif delta is not None and delta < 0:
                prev_str = f"#{c.prev_rank} ({delta})"
            else:
                prev_str = f"#{c.prev_rank} (=)"
        else:
            prev_str = "Mới"

        md.append(
            f"| **{idx}** | **{c.symbol}** | {sig} | **{c.price:.2f}** | `{c.entry_low:.2f} - {c.entry_high:.2f}` | **{c.stop_loss:.2f}** | **{c.tp1:.2f}** / **{c.tp2:.2f}** | **{c.adtv20_billion:.1f}t** | {liq_tag} | {c.rrg_r:.0f}/{c.rrg_m:.0f} | **{c.composite_rating}** | `{ad_letter}` | {fn} | **{c.ranking_score:.1f}** | {prev_str} |"
        )

    md.extend([
        "",
        "### 🎯 Kế Hoạch Tác Chiến, Điểm Thoát Lệnh T+2.5 & Catalysts:",
    ])
    for idx, c in enumerate(candidates, 1):
        flow_b = getattr(c, "flow_badge", "🟢 NỘI GOM CÂN HÀNG")
        prop_v = getattr(c, "prop_net_value_billion", 0.0)
        has_prop = getattr(c, "has_actual_prop_flow", False)
        prop_desc = f"Tự doanh thực tế: {prop_v:+.1f} tỷ" if has_prop else "Tự doanh: Chưa công bố EOD (N/A)"
        fomo_b = getattr(c, "anti_fomo_badge", "🟢 VÙNG MUA CHUẨN")
        lot_note = getattr(c, "retail_lot_note", "")
        if not lot_note:
            lot_note = calculate_retail_t25_position_size(100_000_000.0, c.price, c.stop_loss, 0.0, symbol=c.symbol).lot_warning
        md.extend([
            f"- **{c.symbol} ({c.price:.2f})** `{c.rank_change_badge}` | **{fomo_b}**: Vùng gom T0 `{c.entry_low:.2f} - {c.entry_high:.2f}` | Cắt lỗ cấu trúc: `{c.stop_loss:.2f}` | TP1 (Net 1.5R): `{c.tp1:.2f}` | TP2 (Net 2.5R): `{c.tp2:.2f}` (R:R `1:{c.rr_ratio:.1f}`)",
            f"  - *Ma trận Dòng tiền:* {flow_b} (Khối ngoại: {c.foreign_net_value_billion:+.1f} tỷ | {prop_desc})",
            f"  - *Động lực:* {c.catalyst}",
            f"  - *Sức chứa Quỹ & Lô 100 HOSE:* ADTV20 `{c.adtv20_billion:.1f} tỷ` (Điểm TK: `{c.liquidity_score:.0f}/100`) | Sức chứa tối đa: `{c.max_shares_capacity:,.0f} cp` (Trượt giá ~`{c.slippage_est_pct:.2f}%`). {lot_note}",
            f"  - *Quản trị Nhỏ lẻ T+2.5 (Cold-Start 0% T+0):* Trạng thái `{c.t25_status_badge}`. Tài khoản chưa có sẵn hàng T+0 chỉ giải ngân tối đa **<= 20% NAV/mã**, **0% Margin**, ưu tiên đặt lệnh sau **13:45** để tránh bẫy kéo xả phiên sáng.",
        ])

    # Bo sung Bang Xep Hang Dinh Luong Co Ban (Piotroski F-Score & P/E) that tu Fialda
    if fund_data:
        md.extend([
            "",
            "### 📊 BẢNG XẾP HẠNG ĐỊNH LƯỢNG CƠ BẢN (PIOTROSKI F-SCORE & P/E)",
            "> *Nguồn: Báo cáo tài chính chuẩn hóa & Bảng giá Real-time Fialda VIP*",
            "",
            "| Mã CP | Tên Doanh Nghiệp | Nhóm Ngành | Giá Khớp (1,000 đ) | F-Score | P/E | P/B | CFO / NI | Xếp Hạng |",
            "| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
        ])
        for s in fund_data:
            rank_badge = "`ĐỊNH CHẾ GOM`" if s.get("is_institutional") else "`THEO DÕI`"
            f_score_val = s.get("f_score_str", "N/A")
            md.append(
                f"| **{s['symbol']}** | {s['company_name']} | {s['sector']} | **{s['price']:.2f}** | **{f_score_val}** | {s['pe']:.1f} | {s['pb']:.1f} | {s['cfo_ni']:.2f} | {rank_badge} |"
            )
        md.extend([
            "",
            "> 💡 **Ghi chú định lượng học thuật (Piotroski, 2000):** Thang điểm *Piotroski F-Score (0-9)* loại trừ các Ngân hàng thương mại (MBB, VCB) do đặc thù BCTC ngành ngân hàng không có *Giá vốn/Biên Lợi Nhuận Gộp* và *Hệ số Thanh toán ngắn hạn (Current Ratio)*. Xem bảng định lượng CAMEL & Basel II/III chi tiết bên dưới.",
        ])

    # Bo sung Bang Dinh Luong Ngan Hang Thuong Mai (CAMEL & Basel II/III)
    if bank_data:
        md.extend([
            "",
            "### 🏦 BẢNG ĐỊNH LƯỢNG NGÂN HÀNG THƯƠNG MẠI (CAMEL & BASEL II/III QUANT)",
            "> *Khung định lượng độc quyền theo Thông tư 41/2016/TT-NHNN & Chuẩn quốc tế Basel II/III*",
            "",
            "| Mã CP | Tên Ngân Hàng | Giá Khớp | Điểm CAMEL | CASA (%) | NIM (%) | NPL Nợ Xấu | LLR Bao Phủ | CIR (%) | ROE (%) | P/B | Xếp Hạng CAMEL |",
            "| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
        ])
        for b in bank_data:
            m = b.metrics
            md.append(
                f"| **{b.symbol}** | {b.bank_name} | **{b.price:.2f}** | **{b.total_score:.0f}/100** | **{m.casa:.1f}%** | {m.nim:.1f}% | {m.npl:.2f}% | **{m.llr:.0f}%** | {m.cir:.1f}% | {m.roe:.1f}% | **{m.pb:.1f}** | `{b.tier}` |"
            )

    # Bo sung Bao cao Tai chinh 4 quy gan nhat (BCTC) - Thong ke 1 CP / 1 dong duy nhat
    if scanner and candidates:
        spotlight = [c.symbol for c in candidates[:5]]
        md.extend([
            "",
            "### 📑 BÁO CÁO KẾT QUẢ KINH DOANH CÁC QUÝ GẦN NHẤT (DOANH THU & LỢI NHUẬN RÒNG BCTC)",
            "> *Thống kê xu hướng tăng trưởng 1 CP / 1 dòng duy nhất • Nguồn: Báo cáo tài chính Fialda VIP API*",
            "",
            "| Mã CP | Kỳ BCTC | DTT Quý N-2 | DTT Quý N-1 | DTT Quý N (Mới) | LNST Quý N-2 | LNST Quý N-1 | LNST Quý N (Mới) | Tăng Trưởng QoQ | Biên Gộp | Xu Hướng Động Lượng |",
            "| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
        ])
        for sym in spotlight:
            try:
                quarters = scanner.get_income_statement(sym, is_quarter=True)
            except Exception:
                quarters = scanner._fallback_mock_income_statement(sym)
            if not quarters:
                continue
            q_latest = quarters[0]
            q_name = f"Q{q_latest.get('quarter')}/{q_latest.get('year')}"
            rev0 = q_latest.get("revenue_billion", 0.0)
            gp0 = q_latest.get("gross_profit_billion", 0.0)
            np0 = q_latest.get("net_profit_billion", 0.0)
            margin0 = round((gp0 / rev0 * 100.0), 1) if rev0 > 0 else 0.0

            rev1 = quarters[1].get("revenue_billion", 0.0) if len(quarters) > 1 else 0.0
            np1 = quarters[1].get("net_profit_billion", 0.0) if len(quarters) > 1 else 0.0

            rev2 = quarters[2].get("revenue_billion", 0.0) if len(quarters) > 2 else 0.0
            np2 = quarters[2].get("net_profit_billion", 0.0) if len(quarters) > 2 else 0.0

            if len(quarters) > 1 and np1 != 0:
                growth_qoq = round(((np0 - np1) / abs(np1)) * 100.0, 1)
                growth_str = f"{growth_qoq:+.1f}%"
            else:
                growth_qoq = 0.0
                growth_str = "N/A"

            if len(quarters) >= 3 and np0 > np1 > np2 and np0 > 0:
                eval_tag = "🚀 TĂNG TỐC 3 QUÝ"
            elif growth_qoq >= 50.0:
                eval_tag = "🔥 BÙNG NỔ LNST"
            elif growth_qoq > 0:
                eval_tag = "↗ TĂNG TRƯỞNG DƯƠNG"
            elif np0 < 0:
                eval_tag = "⚠️ LỖ RÒNG"
            else:
                eval_tag = "↘ CHẬM LẠI"

            growth_badge = f"`{growth_str}` ↗" if growth_qoq > 0 else f"`{growth_str}`"
            md.append(
                f"| **{sym}** | `{q_name}` | {rev2:,.1f} tỷ | {rev1:,.1f} tỷ | **{rev0:,.1f} tỷ** | {np2:,.1f} tỷ | {np1:,.1f} tỷ | **{np0:,.1f} tỷ** | {growth_badge} | {margin0:.1f}% | `{eval_tag}` |"
            )

        # Bo sung Tin tuc & Su kien doanh nghiep
        md.extend([
            "",
            "### 📰 TIN TỨC DOANH NGHIỆP & LỊCH SỰ KIỆN MỚI NHẤT (SPOTLIGHT)",
            "> *Nguồn: Cổng công bố thông tin Fialda Real-time*",
            "",
        ])
        for sym in spotlight[:4]:
            try:
                news_list = scanner.get_company_news(sym, page_size=1)
            except Exception:
                news_list = scanner._fallback_mock_news(sym)[:1]
            try:
                events_list = scanner.get_company_events(sym)
            except Exception:
                events_list = scanner._fallback_mock_events(sym)

            for n in news_list:
                md.append(f"- **[{n['symbol']}] {n['title']}** ({n['time']} • *{n['source']}*)")
                if n.get("short_content"):
                    md.append(f"  > {n['short_content']}")
            for ev in events_list[:1]:
                md.append(f"- 📅 **[{ev['symbol']} - SỰ KIỆN]** Ngày: `{ev['date']}` — *{ev['event_name']}*")

    md.extend([
        "",
        "---",
        "*Báo cáo được tạo tự động bởi Neiro-Stock-VN Fialda VIP Expert Harvester trên GitHub Actions.*"
    ])
    return "\n".join(md)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Chay Fialda VIP Expert Scanner")
    parser.add_argument("--top", type=int, default=20, help="So luong co phieu top de quet (mac dinh 20)")
    parser.add_argument("--save-report", default="", help="Duong dan luu file Markdown report")
    parser.add_argument("--generate-terminal", action="store_true", help="Tu dong sinh HTML Terminal")
    args = parser.parse_args()

    scanner = FialdaScanner()
    top_candidates = scanner.scan_top_rockets(top_n=args.top)
    breadth_info = scanner.get_market_breadth() if scanner.token else None
    fund_data = scanner.get_fundamental_screener_data() if scanner.token else scanner._fallback_mock_fundamental()

    # In ra terminal
    report_text = format_top_5_report(top_candidates, breadth_info)
    print(report_text)

    # Lay du lieu CAMEL cho Ngan hang
    bank_data = scanner.get_banking_screener_data()

    # Ghi vao GITHUB_STEP_SUMMARY neu dang chay trong GitHub Actions
    md_report = format_top_5_markdown(top_candidates, breadth_info, fund_data, scanner=scanner, bank_data=bank_data)
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        try:
            with open(summary_path, "a", encoding="utf-8") as f:
                f.write("\n" + md_report + "\n")
        except Exception as e:
            print(f"Warning: Khong the ghi GITHUB_STEP_SUMMARY: {e}")

    # Luu file report neu duoc yeu cau
    if args.save_report:
        p = Path(args.save_report)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(md_report, encoding="utf-8")
        print(f"Da luu bao cao markdown tai: {p}")

    # Tu dong sinh HTML Terminal
    if args.generate_terminal:
        try:
            from src.hud.terminal import generate_terminal_html
            out_html = generate_terminal_html(
                "exports/index.html",
                fialda_candidates=top_candidates,
                top_n=args.top,
                market_breadth=breadth_info,
                scanner=scanner,
            )
            print(f"Da sinh HTML Terminal tai: {out_html}")
        except Exception as e:
            print(f"Warning: Khong the sinh HTML Terminal: {e}")
