"""Module Sổ Cái Tín Hiệu Ngầm, Rada Chống Mua Đuổi & ML Dataset Pipeline v2 (ADR-011 / ADR-019).

Chạy ngầm 100% trên GitHub Actions & Local Pipeline:
1. Neo giữ mốc Giá Khuyến Nghị Ban Đầu (T0 Original Entry Price), Stop Loss, TP1, TP2 theo signal_id duy nhất.
2. Đo lường tỷ lệ trượt giá lũy kế Δ%, số ngày lịch và số phiên giao dịch thực tế (VN Trading Sessions) T+2.5.
3. Kích hoạt Rada Kiểm Soát Quyền Mua Mới (5-Gate Anti-FOMO & Anti-Falling-Knife Guard):
   - -1.5% <= Δ% <= +3.0% (<= 2 phiên giao dịch thực, vĩ mô an toàn): BUY_OK (Vùng mua chuẩn).
   - +3.0% < Δ% <= +5.0% hoặc -2.5% <= Δ% < -1.5%: BUY_CAUTION (Thăm dò <= 30%, 0% Margin).
   - Δ% > +5.0% (Quá điểm mua), MFE > +5.0% rồi xìu (Bull-Trap), Δ% < -2.5% (Gãy vùng gom - Cấm bắt dao rơi),
     >= 3 phiên giao dịch thực (Stale Signal), hoặc Cầu chì Vĩ mô T+2.5 bật: CẤM MỞ MUA MỚI 100%.
4. Chuẩn hóa Feature Vector T0 (Vi cấu trúc + Cơ bản + Vĩ mô) & Ground Truth Labels chốt cứng (Terminal Latch) cho ML.
5. Lưu trữ lịch sử đa vòng sóng (signal_history_ml.jsonl) không mất mẫu cũ, đồng bộ Google Sheets & xuất ml_signals_dataset.csv.
"""

import json
import logging
import os
import re
from dataclasses import asdict, dataclass, fields
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd

from src.collector.google_sheets_client import GoogleSheetsLedgerClient

logger = logging.getLogger(__name__)

# Các ngày nghỉ lễ cố định hàng năm tại Việt Nam (Tết Dương lịch, Giải phóng miền Nam, Quốc tế Lao động, Quốc khánh)
_VN_FIXED_HOLIDAYS: set[tuple[int, int]] = {
    (1, 1),
    (4, 30),
    (5, 1),
    (9, 2),
}


def count_vn_trading_days(start_date: date, end_date: date) -> int:
    """Đếm số phiên giao dịch thực tế trên sàn HOSE/HNX giữa 2 mốc ngày (loại trừ Thứ Bảy, Chủ Nhật và lễ cố định)."""
    if end_date <= start_date:
        return 0
    sessions = 0
    cur = start_date + timedelta(days=1)
    while cur <= end_date:
        if cur.weekday() < 5 and (cur.month, cur.day) not in _VN_FIXED_HOLIDAYS:
            sessions += 1
        cur += timedelta(days=1)
    return sessions


def format_public_anti_fomo_badge(
    buy_permission: str,
    pnl_pct: float = 0.0,
    holding_days: int = 0,
    status: str = "ACTIVE",
    advice_note: str = "",
) -> str:
    """Định dạng nhãn Quyền Mua Mới thống nhất giữa Sổ cái ngầm, Báo cáo Markdown và Web Dashboard."""
    if status == "STOPPED_OUT":
        return "⛔ VI PHẠM SL (CẤM BẮT DAO RƠI)"
    if status == "TP2_REACHED":
        return "🎯 ĐÃ ĐẠT TP2 (CHỐT LỜI - NGỪNG MUA)"
    if "CẦU CHÌ" in advice_note and buy_permission == "EXTENDED_NO_CHASING":
        return "⛔ CẦU CHÌ T+2.5: NGỪNG MUA"
    if buy_permission == "EXTENDED_NO_CHASING":
        if pnl_pct < 0.0:
            return "⛔ ĐÃ SUY YẾU (CẤM BẮT DAO RƠI)"
        if pnl_pct <= 5.0 and holding_days >= 3:
            return f"🟠 QUÁ HẠN T+{holding_days} (NGỪNG MUA)"
        return f"🔴 CẤM MUA ĐUỔI ({pnl_pct:+.1f}% TỪ T0)"
    if buy_permission == "BULL_TRAP_REJECT":
        return "🔴 CẤM MUA (BẪY BULL-TRAP)"
    if buy_permission == "STALE_SIGNAL":
        return f"🟠 QUÁ HẠN T+{max(holding_days, 3)} (NGỪNG MUA)"
    if buy_permission == "BUY_CAUTION":
        if pnl_pct < 0.0:
            return f"🟡 RUNG LẮC NỀN ({pnl_pct:+.1f}% • <=30%)"
        return f"🟡 VÙNG VỚI ({pnl_pct:+.1f}% • <=30%)"
    return "🟢 VÙNG MUA CHUẨN"


@dataclass
class ActiveSignal:
    """Cấu trúc dữ liệu một vị thế tín hiệu được theo dõi trong sổ cái định lượng & ML Dataset v2."""

    symbol: str
    first_signal_date: str          # Thời điểm bùng nổ tín hiệu đầu tiên T0 (YYYY-MM-DD HH:MM:SS)
    last_updated: str               # Thời điểm quét cập nhật gần nhất
    entry_original: float           # Mức giá khuyến nghị gốc ban đầu T0 (bất biến)
    current_price: float            # Thị giá cập nhật mới nhất
    pnl_pct: float                  # % Lãi/Lỗ lũy kế: ((current_price - entry_original) / entry_original) * 100
    holding_days: int               # Số ngày lịch đã trôi qua kể từ T0
    initial_stop_loss: float        # Ngưỡng cắt lỗ bảo toàn vốn ban đầu
    current_stop_loss: float        # Ngưỡng Trailing Stop hiện tại (tự nâng khi đạt TP1)
    tp1: float                      # Mục tiêu chốt lời 1 (1.5R Net Fee)
    tp2: float                      # Mục tiêu chốt lời 2 (2.5R Net Fee)
    status: str                     # 'ACTIVE', 'TP1_REACHED', 'TP2_REACHED', 'STOPPED_OUT', 'TIME_OUT'
    buy_permission: str             # 'BUY_OK', 'BUY_CAUTION', 'EXTENDED_NO_CHASING', 'BULL_TRAP_REJECT', 'STALE_SIGNAL'
    advice_note: str                # Khuyến nghị hành động thực chiến chi tiết

    # Định danh duy nhất & Phiên bản Schema ML
    signal_id: str = ""             # Mã khóa chính: {SYMBOL}_{YYYYMMDD_HHMMSS}
    schema_version: str = "v2"      # 'v2' (chuẩn đầy đủ features) hoặc 'v1_legacy'
    trading_days: int = 0           # Số phiên giao dịch thực tế (loại T7, CN, lễ) kể từ T0

    # ML Feature Vector tại T0 (Immutable snapshot lúc bắt đầu khuyến nghị)
    signal_type: str = "CHO_MUA_CHAN_SONG"
    composite_rating: int = 80
    rs_1m: int = 80
    acc_diss_rating: str = "A"
    rrg_r: float = 100.0
    rrg_m: float = 100.0
    foreign_net_value_billion: float = 0.0
    ranking_score: float = 80.0
    catalyst: str = ""
    adtv20_billion: float = 25.0
    adv20_shares: int = 1_000_000
    liquidity_score: float = 80.0
    t25_exposure_level: str = "SAFE"
    prop_net_value_billion: float = 0.0
    flow_regime: str = "NOI_CAN_HANG"
    flow_badge: str = "🟢 NỘI GOM CÂN HÀNG"
    has_actual_prop_flow_t0: bool = False
    atr_pct_t0: float = 0.0
    atr_dist_from_poc_t0: float = 0.0
    poc_price_t0: float = 0.0
    val_price_t0: float = 0.0
    slippage_est_pct_t0: float = 0.0
    market_breadth_pct_t0: float = 55.0
    vn30_basis_t0: float = 0.0
    pe_t0: float = 0.0
    pb_t0: float = 0.0
    eps_ttm_t0: float = 0.0
    camel_score_t0: float = 0.0

    # ML Labels & Tracking biến động theo chu kỳ T+2.5 đến T+20 (Ground Truth)
    max_price_reached: float = 0.0
    min_price_reached: float = 0.0
    mfe_pct: float = 0.0            # Max Favorable Excursion (% lãi cực đại tiềm năng)
    mae_pct: float = 0.0            # Max Adverse Excursion (% sụt giảm sâu nhất)
    pnl_t25_pct: float = 0.0        # PnL thực tế tại chu kỳ T+2.5 (phiên thực >= 2, khi hàng về khả dụng)
    pnl_t5_pct: float = 0.0         # PnL thực tế tại phiên giao dịch T+5
    pnl_t10_pct: float = 0.0        # PnL thực tế tại phiên giao dịch T+10
    pnl_t25_recorded: bool = False
    pnl_t5_recorded: bool = False
    pnl_t10_recorded: bool = False
    outcome_label: str = "ACTIVE"   # 'WIN_TP1', 'WIN_TP2', 'STOP_LOSS', 'TIME_OUT', 'ACTIVE'
    target_win_binary: int = 0      # 1 nếu đạt MFE >= +5.0% trước khi chạm cắt lỗ ban đầu, ngược lại 0
    is_closed: bool = False         # True khi vị thế đã kết thúc vòng đời (STOPPED_OUT / TP2_REACHED / TIME_OUT)
    closed_at: str = ""             # Thời điểm đóng vòng đời tín hiệu
    is_ml_ready: bool = False       # True khi mẫu đủ điều kiện đưa vào tập train có giám sát (is_closed hoặc trading_days >= 5)


class SignalTracker:
    """Bộ điều phối Sổ Cái Tín Hiệu Ngầm, Kiểm Soát Rủi Ro & Pipeline Dữ Liệu ML v2."""

    DEFAULT_FILE = Path("data/active_signals.jsonl")
    DEFAULT_ARCHIVE_FILE = Path("data/signal_history_ml.jsonl")
    DEFAULT_SCORECARD = Path("data/advisory_scorecard.md")
    DEFAULT_ML_DATASET = Path("data/ml_signals_dataset.csv")
    MAX_HOLDING_DAYS = 20           # Đóng vòng đời tín hiệu sau 20 phiên giao dịch thực (~1 tháng)
    MAX_ARCHIVE_RECORDS = 2000      # Rolling window tối đa 2,000 mẫu (~450 KB) bảo đảm Zero-Waste < 15MB

    def __init__(
        self,
        signals_file: Optional[Path] = None,
        scorecard_file: Optional[Path] = None,
        ml_dataset_file: Optional[Path] = None,
        archive_file: Optional[Path] = None,
    ):
        self.file_path = Path(signals_file) if signals_file else self.DEFAULT_FILE
        self.scorecard_path = Path(scorecard_file) if scorecard_file else self.DEFAULT_SCORECARD
        self.ml_dataset_path = Path(ml_dataset_file) if ml_dataset_file else self.DEFAULT_ML_DATASET
        if archive_file is not None:
            self.archive_path = Path(archive_file)
        elif signals_file is not None:
            p = Path(signals_file)
            self.archive_path = p.with_name(f"{p.stem}_archive.jsonl")
        else:
            self.archive_path = self.DEFAULT_ARCHIVE_FILE

    @staticmethod
    def current_vn_time() -> datetime:
        """Lấy datetime hiện tại theo múi giờ Việt Nam (UTC+7)."""
        return datetime.now(timezone(timedelta(hours=7)))

    @staticmethod
    def format_time(dt: datetime) -> str:
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def build_signal_id(symbol: str, first_signal_date: str) -> str:
        clean_ts = re.sub(r"[^0-9]", "", str(first_signal_date or ""))
        if not clean_ts:
            clean_ts = "00000000000000"
        elif len(clean_ts) > 8:
            clean_ts = f"{clean_ts[:8]}_{clean_ts[8:14]}"
        return f"{symbol.upper().strip()}_{clean_ts}"

    @staticmethod
    def parse_time(ts_str: str) -> Optional[datetime]:
        if not ts_str:
            return None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(ts_str, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone(timedelta(hours=7)))
                return dt
            except Exception:
                pass
        return None

    def _normalize_loaded_signal(self, sig: ActiveSignal, had_schema_version: bool) -> ActiveSignal:
        """Chuẩn hóa & phục hồi toàn vẹn dữ liệu cho cả bản ghi v1_legacy lẫn v2."""
        if not sig.signal_id:
            sig.signal_id = self.build_signal_id(sig.symbol, sig.first_signal_date)
        if not had_schema_version:
            sig.schema_version = "v1_legacy"

        ref_p = sig.entry_original if sig.entry_original > 0 else sig.current_price
        cur_p = sig.current_price if sig.current_price > 0 else ref_p
        if ref_p > 0:
            if sig.max_price_reached <= 0:
                sig.max_price_reached = max(ref_p, cur_p)
            if sig.min_price_reached <= 0:
                sig.min_price_reached = min(ref_p, cur_p)
            calc_mfe = round(((sig.max_price_reached - ref_p) / ref_p) * 100.0, 2)
            calc_mae = round(((sig.min_price_reached - ref_p) / ref_p) * 100.0, 2)
            sig.mfe_pct = max(sig.mfe_pct, calc_mfe)
            sig.mae_pct = min(sig.mae_pct, calc_mae)

        f_dt = self.parse_time(sig.first_signal_date)
        l_dt = self.parse_time(sig.last_updated)
        if f_dt and l_dt and sig.trading_days == 0 and l_dt.date() > f_dt.date():
            sig.trading_days = count_vn_trading_days(f_dt.date(), l_dt.date())

        if sig.pnl_t25_pct != 0.0:
            sig.pnl_t25_recorded = True
        if sig.pnl_t5_pct != 0.0:
            sig.pnl_t5_recorded = True
        if sig.pnl_t10_pct != 0.0:
            sig.pnl_t10_recorded = True

        if sig.status in ("STOPPED_OUT", "TP2_REACHED", "TIME_OUT") or sig.outcome_label in (
            "STOP_LOSS",
            "WIN_TP2",
            "TIME_OUT",
        ):
            sig.is_closed = True
            if not sig.closed_at:
                sig.closed_at = sig.last_updated or sig.first_signal_date

        sig.is_ml_ready = bool(sig.is_closed or sig.trading_days >= 5)
        return sig

    def load_active_signals(self) -> Dict[str, ActiveSignal]:
        """Đọc danh sách các vị thế đang hoạt động từ file JSONL."""
        if not self.file_path.exists():
            return {}

        valid_fields = {f.name for f in fields(ActiveSignal)}
        signals: Dict[str, ActiveSignal] = {}
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    sym = data.get("symbol")
                    if sym:
                        had_schema = "schema_version" in data
                        filtered = {k: v for k, v in data.items() if k in valid_fields}
                        sig = ActiveSignal(**filtered)
                        signals[sym] = self._normalize_loaded_signal(sig, had_schema_version=had_schema)
        except Exception as e:
            logger.warning(f"Lỗi khi đọc file active_signals: {e}")
            return {}
        return signals

    def load_archived_signals(self) -> Dict[str, ActiveSignal]:
        """Đọc kho lưu trữ các vòng sóng đã hoàn tất (keyed theo signal_id) phục vụ huấn luyện ML."""
        if not self.archive_path.exists():
            return {}

        valid_fields = {f.name for f in fields(ActiveSignal)}
        archived: Dict[str, ActiveSignal] = {}
        try:
            with open(self.archive_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    if data.get("symbol"):
                        had_schema = "schema_version" in data
                        filtered = {k: v for k, v in data.items() if k in valid_fields}
                        sig = self._normalize_loaded_signal(ActiveSignal(**filtered), had_schema_version=had_schema)
                        archived[sig.signal_id] = sig
        except Exception as e:
            logger.warning(f"Lỗi khi đọc file signal_history_ml: {e}")
            return {}
        return archived

    def _archive_closed_signal(self, sig: ActiveSignal) -> None:
        """Lưu trữ bất biến một vòng giao dịch đã đóng vào signal_history_ml.jsonl (giới hạn Rolling Window)."""
        if "PYTEST_CURRENT_TEST" in os.environ and self.archive_path == self.DEFAULT_ARCHIVE_FILE:
            return

        archived = self.load_archived_signals()
        if not sig.signal_id:
            sig.signal_id = self.build_signal_id(sig.symbol, sig.first_signal_date)
        archived[sig.signal_id] = sig

        ordered = sorted(archived.values(), key=lambda s: (s.first_signal_date, s.symbol))
        if len(ordered) > self.MAX_ARCHIVE_RECORDS:
            ordered = ordered[-self.MAX_ARCHIVE_RECORDS :]

        self.archive_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.archive_path, "w", encoding="utf-8") as f:
            for item in ordered:
                f.write(json.dumps(asdict(item), ensure_ascii=False) + "\n")

    def save_active_signals(self, signals: Dict[str, ActiveSignal]) -> None:
        """Lưu lại danh sách các vị thế vào file JSONL (bỏ qua nếu đang chạy pytest trên file thật)."""
        if "PYTEST_CURRENT_TEST" in os.environ and self.file_path == self.DEFAULT_FILE:
            return

        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.file_path, "w", encoding="utf-8") as f:
            for sig in signals.values():
                f.write(json.dumps(asdict(sig), ensure_ascii=False) + "\n")

    def export_ml_dataset(self, signals: Optional[Dict[str, ActiveSignal]] = None) -> Path:
        """Xuất bản hợp nhất Kho Lưu Trữ Đã Đóng + Sổ Cái Hiện Hành thành CSV phẳng chuẩn Machine Learning."""
        if "PYTEST_CURRENT_TEST" in os.environ and self.ml_dataset_path == self.DEFAULT_ML_DATASET:
            return self.ml_dataset_path

        active_signals = signals if signals is not None else self.load_active_signals()
        archived_signals = self.load_archived_signals()

        merged_by_id: Dict[str, ActiveSignal] = {}
        for arch in archived_signals.values():
            sid = arch.signal_id or self.build_signal_id(arch.symbol, arch.first_signal_date)
            merged_by_id[sid] = arch
        for act in active_signals.values():
            sid = act.signal_id or self.build_signal_id(act.symbol, act.first_signal_date)
            merged_by_id[sid] = act

        if not merged_by_id:
            return self.ml_dataset_path

        try:
            self.ml_dataset_path.parent.mkdir(parents=True, exist_ok=True)
            ordered_records = [
                asdict(sig)
                for sig in sorted(merged_by_id.values(), key=lambda s: (s.first_signal_date, s.symbol))
            ]
            df = pd.DataFrame(ordered_records)
            df.to_csv(self.ml_dataset_path, index=False, encoding="utf-8")
        except Exception as e:
            logger.warning(f"Lỗi khi xuất ml_dataset CSV: {e}")

        return self.ml_dataset_path

    def sync_to_google_sheets(self, signals: Dict[str, ActiveSignal]) -> bool:
        """Đồng bộ danh sách tín hiệu sang Google Sheets qua Webhook."""
        client = GoogleSheetsLedgerClient()
        return client.sync_signals(list(signals.values()))

    def is_in_stopout_cooldown(
        self,
        sig: ActiveSignal,
        now_dt: Optional[datetime] = None,
        cooldown_days: int = 3,
    ) -> bool:
        """Kiểm tra mã vừa vi phạm cắt lỗ (STOPPED_OUT) trong chu kỳ đóng băng 3 PHIÊN GIAO DỊCH THỰC gần nhất."""
        if sig.status != "STOPPED_OUT":
            return False
        ref_now = now_dt or self.current_vn_time()
        ref_close_ts = sig.closed_at or sig.last_updated or sig.first_signal_date
        stopped_dt = self.parse_time(ref_close_ts) or self.parse_time(sig.first_signal_date)
        if stopped_dt is None:
            return True
        trading_sessions_since = count_vn_trading_days(stopped_dt.date(), ref_now.date())
        return trading_sessions_since <= cooldown_days

    def _is_closed_cooldown_expired(
        self,
        sig: ActiveSignal,
        now_dt: datetime,
        cooldown_sessions: int = 3,
    ) -> bool:
        """Kiểm tra vị thế đã đóng (STOPPED_OUT / TP2_REACHED / TIME_OUT) đã qua hết thời gian nghỉ giữa 2 vòng sóng chưa."""
        if not sig.is_closed:
            return False
        ref_close_ts = sig.closed_at or sig.last_updated or sig.first_signal_date
        closed_dt = self.parse_time(ref_close_ts) or self.parse_time(sig.first_signal_date)
        if closed_dt is None:
            return False
        return count_vn_trading_days(closed_dt.date(), now_dt.date()) > cooldown_sessions

    def evaluate_status_and_advice(
        self,
        entry_orig: float,
        cur_price: float,
        cur_stop: float,
        tp1: float,
        tp2: float,
        holding_days: int,
        mfe_pct: float = 0.0,
        trading_days: Optional[int] = None,
    ) -> tuple[str, str, str, float]:
        """Đánh giá trạng thái vị thế, quyền mở mua mới (cả chiều lên lẫn chiều suy yếu dưới nền) và câu tư vấn."""
        if entry_orig <= 0:
            pnl_pct = 0.0
        else:
            pnl_pct = round(((cur_price - entry_orig) / entry_orig) * 100.0, 2)
        effective_mfe = max(float(mfe_pct or 0.0), pnl_pct)
        eff_sessions = trading_days if trading_days is not None else holding_days
        display_days = max(holding_days, eff_sessions)
        new_stop = cur_stop

        # 1. Cơ chế Trailing Stop / Nâng chặn lỗ bảo toàn vốn
        if tp1 > 0 and cur_price >= tp1:
            new_stop = max(new_stop, entry_orig)

        # 2. Đánh giá trạng thái vị thế (status)
        if cur_price <= new_stop:
            status = "STOPPED_OUT"
            buy_permission = "EXTENDED_NO_CHASING"
            advice_note = (
                f"❌ VI PHẠM CẮT LỖ (Giá {cur_price:.2f} <= Stop {new_stop:.2f}). "
                "Bán dứt khoát thoát vị thế, bảo toàn vốn tối đa."
            )
            return status, buy_permission, advice_note, new_stop

        if tp2 > 0 and cur_price >= tp2:
            status = "TP2_REACHED"
            buy_permission = "EXTENDED_NO_CHASING"
            advice_note = (
                f"🎯 ĐẠT MỤC TIÊU LỚN TP2 ({tp2:.2f}, Lãi {pnl_pct:+.1f}%). "
                "Khuyến nghị chốt lời toàn bộ phần vị thế còn lại, TUYỆT ĐỐI CẤM MUA MỚI."
            )
            return status, buy_permission, advice_note, new_stop

        if tp1 > 0 and cur_price >= tp1:
            status = "TP1_REACHED"
            buy_permission = "EXTENDED_NO_CHASING"
            advice_note = (
                f"🚀 ĐẠT MỤC TIÊU 1 TP1 ({tp1:.2f}, Lãi {pnl_pct:+.1f}%). "
                f"Chốt lời 50% tiền tươi, dời Stop Loss lên giá mua {entry_orig:.2f} (Hòa vốn) để gồng lãi 50% còn lại. "
                "CẤM MUA ĐUỔI vì rủi ro rung lắc T+2.5 rất cao."
            )
            return status, buy_permission, advice_note, new_stop

        status = "ACTIVE"

        # 3. Rada Kiểm Soát Quyền Mua Mới (Anti-FOMO / Bull-Trap / Stale Session / Anti-Falling-Knife)
        if pnl_pct > 5.0:
            buy_permission = "EXTENDED_NO_CHASING"
            advice_note = (
                f"🔴 QUÁ ĐIỂM MUA - CẤM MUA ĐUỔI (Đã tăng {pnl_pct:+.1f}% từ điểm kích hoạt ban đầu {entry_orig:.2f}, nắm giữ {display_days} phiên). "
                "Chỉ ưu tiên người đã có sẵn hàng tiếp tục gồng lãi. "
                "Người chưa có hàng TUYỆT ĐỐI KHÔNG ĐƯỢC MUA ĐUỔI để tránh bẫy điều chỉnh kẹp T+2.5."
            )
        elif effective_mfe > 5.0:
            buy_permission = "BULL_TRAP_REJECT"
            advice_note = (
                f"🔴 CẤM MUA (BẪY XẢ SAU KÉO RƯỚN): Mã từng kéo tăng +{effective_mfe:.1f}% từ T0 ({entry_orig:.2f}) "
                f"rồi suy yếu ngược về {cur_price:.2f} ({pnl_pct:+.1f}%). Tuyệt đối không bắt dao rơi T+2.5."
            )
        elif eff_sessions >= 3:
            buy_permission = "STALE_SIGNAL"
            advice_note = (
                f"🟠 QUÁ HẠN T+{max(display_days, 3)} (Biến động {pnl_pct:+.1f}% so với T0 {entry_orig:.2f} sau {max(display_days, 3)} phiên): "
                "Động lượng bứt phá đầu sóng suy yếu, KHÔNG MỞ MUA MỚI."
            )
        elif pnl_pct < -2.5:
            buy_permission = "EXTENDED_NO_CHASING"
            advice_note = (
                f"⛔ ĐÃ SUY YẾU DƯỚI VÙNG GOM ({pnl_pct:+.1f}% so với T0 {entry_orig:.2f}): "
                f"Người đang có hàng tuân thủ chặt điểm cắt lỗ {new_stop:.2f}. "
                "Người cầm tiền TUYỆT ĐỐI KHÔNG BẮT DAO RƠI / KHÔNG BÌNH QUÂN GIÁ XUỐNG T+2.5."
            )
        elif 3.0 < pnl_pct <= 5.0:
            buy_permission = "BUY_CAUTION"
            advice_note = (
                f"🟡 VÙNG VỚI (Tăng {pnl_pct:+.1f}% từ điểm bùng nổ {entry_orig:.2f}). "
                "Chỉ giải ngân tối đa 30% vị thế thăm dò, tuyệt đối không dùng margin."
            )
        elif -2.5 <= pnl_pct < -1.5:
            buy_permission = "BUY_CAUTION"
            advice_note = (
                f"🟡 RUNG LẮC KIỂM ĐỊNH NỀN ({pnl_pct:+.1f}% so với T0 {entry_orig:.2f}). "
                f"Chỉ thăm dò tối đa 30% vị thế nếu cầu hấp thụ giữ vững trên hỗ trợ Stop {new_stop:.2f}, không dùng margin."
            )
        else:
            buy_permission = "BUY_OK"
            advice_note = (
                f"🟢 VÙNG MUA CHUẨN (Thị giá {cur_price:.2f} trong biên độ an toàn so với điểm bùng nổ {entry_orig:.2f}). "
                f"Được phép mở mua mới vị thế chuẩn. Cắt lỗ tại {new_stop:.2f}."
            )

        return status, buy_permission, advice_note, new_stop

    def _apply_price_tick_to_existing(
        self,
        existing: ActiveSignal,
        price: float,
        now_dt: datetime,
        now_str: str,
        macro_pause_buying: bool = False,
    ) -> None:
        """Cập nhật giá, MFE/MAE, nhãn PnL T+2.5/T+5/T+10 và chốt trạng thái đóng (Terminal Latch) cho 1 vị thế."""
        first_dt = self.parse_time(existing.first_signal_date) or now_dt
        holding_days = max(0, (now_dt.date() - first_dt.date()).days)
        trading_days = count_vn_trading_days(first_dt.date(), now_dt.date())

        existing.holding_days = holding_days
        existing.trading_days = trading_days

        # Terminal State Latch: Vị thế đã đóng (STOPPED_OUT / TP2_REACHED / TIME_OUT) không bao giờ bị mở lại hay sửa nhãn thắng/thua
        if existing.is_closed:
            existing.is_ml_ready = True
            return

        if price <= 0:
            price = existing.current_price

        entry_ref = existing.entry_original if existing.entry_original > 0 else (price if price > 0 else 1.0)
        pnl = round(((price - entry_ref) / entry_ref) * 100.0, 2)
        cur_max = max(existing.max_price_reached or entry_ref, price)
        cur_min = min(existing.min_price_reached or entry_ref, price)
        mfe = max(existing.mfe_pct, round(((cur_max - entry_ref) / entry_ref) * 100.0, 2))
        mae = min(existing.mae_pct, round(((cur_min - entry_ref) / entry_ref) * 100.0, 2))

        status, buy_perm, advice, new_sl = self.evaluate_status_and_advice(
            entry_orig=existing.entry_original,
            cur_price=price,
            cur_stop=existing.current_stop_loss,
            tp1=existing.tp1,
            tp2=existing.tp2,
            holding_days=holding_days,
            mfe_pct=mfe,
            trading_days=trading_days,
        )

        # Đồng bộ Cầu chì Vĩ mô T+2.5 xuống sổ cái & bảng đối chiếu
        if macro_pause_buying and status not in ("STOPPED_OUT", "TP2_REACHED"):
            buy_perm = "EXTENDED_NO_CHASING"
            advice = (
                f"⛔ CẦU CHÌ VĨ MÔ T+2.5 ĐANG KÍCH HOẠT: Tạm ngừng mở mua mới / gia tăng tỷ trọng mã {existing.symbol}. "
                f"Người đang nắm giữ tuân thủ điểm chặn lỗ {new_sl:.2f}."
            )

        existing.current_price = price
        existing.last_updated = now_str
        existing.pnl_pct = pnl
        existing.current_stop_loss = new_sl
        existing.status = status
        existing.buy_permission = buy_perm
        existing.advice_note = advice

        existing.max_price_reached = cur_max
        existing.min_price_reached = cur_min
        existing.mfe_pct = mfe
        existing.mae_pct = mae

        # Ghi nhận Ground Truth PnL theo đúng số phiên giao dịch thực tế (chỉ chốt 1 lần đầu đạt mốc)
        if trading_days >= 2 and not existing.pnl_t25_recorded:
            existing.pnl_t25_pct = pnl
            existing.pnl_t25_recorded = True
        if trading_days >= 5 and not existing.pnl_t5_recorded:
            existing.pnl_t5_pct = pnl
            existing.pnl_t5_recorded = True
        if trading_days >= 10 and not existing.pnl_t10_recorded:
            existing.pnl_t10_pct = pnl
            existing.pnl_t10_recorded = True

        # MFE +5.0% Win Latch: Nếu đã đạt >= +5.0% trước khi chạm cắt lỗ ban đầu thì chốt nhãn thắng = 1
        if existing.target_win_binary == 1:
            pass
        elif status == "STOPPED_OUT" and mfe < 5.0:
            existing.target_win_binary = 0
        elif mfe >= 5.0 and cur_min > existing.initial_stop_loss:
            existing.target_win_binary = 1

        # Cập nhật outcome_label & đóng vị thế khi chạm trạng thái kết thúc
        if status == "STOPPED_OUT":
            existing.outcome_label = "STOP_LOSS"
            existing.is_closed = True
            existing.closed_at = now_str
        elif status == "TP2_REACHED":
            existing.outcome_label = "WIN_TP2"
            existing.is_closed = True
            existing.closed_at = now_str
        elif trading_days >= self.MAX_HOLDING_DAYS:
            existing.status = "TIME_OUT"
            existing.buy_permission = "EXTENDED_NO_CHASING"
            existing.outcome_label = "WIN_TP1" if mfe >= 5.0 else "TIME_OUT"
            existing.is_closed = True
            existing.closed_at = now_str
        elif status == "TP1_REACHED" or existing.outcome_label == "WIN_TP1":
            existing.outcome_label = "WIN_TP1"
        else:
            existing.outcome_label = "ACTIVE"

        existing.is_ml_ready = bool(existing.is_closed or trading_days >= 5)

    def update_signals(
        self,
        current_candidates: List[Any],
        current_time: Optional[datetime] = None,
        live_prices: Optional[Dict[str, float]] = None,
        macro_pause_buying: bool = False,
    ) -> Dict[str, ActiveSignal]:
        """Cập nhật sổ cái tín hiệu, làm mới giá các mã rớt Top 20, đồng bộ cầu chì vĩ mô và xuất ML Dataset v2."""
        now_dt = current_time or self.current_vn_time()
        now_str = self.format_time(now_dt)
        extra_prices = live_prices or {}

        active_signals = self.load_active_signals()
        updated_syms: set[str] = set()

        for c in current_candidates:
            sym = str(getattr(c, "symbol", "") or "").upper().strip()
            if not sym:
                continue

            price = round(float(getattr(c, "price", 0.0)), 2)
            sl = round(float(getattr(c, "stop_loss", price * 0.945)), 2)
            tp1_val = round(float(getattr(c, "tp1", price * 1.08)), 2)
            tp2_val = round(float(getattr(c, "tp2", getattr(c, "target_1m", price * 1.25))), 2)

            t25_exp = str(getattr(c, "t25_exposure_level", "SAFE"))
            cand_perm = str(getattr(c, "buy_permission", "BUY_OK"))
            is_watchlist_only = bool(getattr(c, "is_watchlist_only", False))

            # Nếu mã cũ đã ĐÓNG và đã qua hết 3 phiên nghỉ cooldown -> Lưu trữ sóng cũ vào Archive để sẵn sàng đón sóng mới
            if sym in active_signals and active_signals[sym].is_closed:
                old_sig = active_signals[sym]
                can_open_new_wave = (
                    not macro_pause_buying
                    and not is_watchlist_only
                    and t25_exp != "CRITICAL"
                    and cand_perm in ("BUY_OK", "BUY_CAUTION")
                    and self._is_closed_cooldown_expired(old_sig, now_dt=now_dt, cooldown_sessions=3)
                )
                if can_open_new_wave:
                    self._archive_closed_signal(old_sig)
                    del active_signals[sym]

            if sym in active_signals:
                updated_syms.add(sym)
                self._apply_price_tick_to_existing(
                    existing=active_signals[sym],
                    price=price,
                    now_dt=now_dt,
                    now_str=now_str,
                    macro_pause_buying=macro_pause_buying,
                )
            else:
                # Chặn ghi khống tín hiệu T0 mới khi Cầu chì Vĩ mô bật, mã thuộc Watchlist tạm, hoặc đã bị khóa quyền mua mới
                if (
                    macro_pause_buying
                    or is_watchlist_only
                    or t25_exp == "CRITICAL"
                    or cand_perm not in ("BUY_OK", "BUY_CAUTION")
                ):
                    continue

                updated_syms.add(sym)
                sig_type = str(getattr(c, "signal_type", "CHO_MUA_CHAN_SONG"))
                comp_rating = int(getattr(c, "composite_rating", 80))
                rs_1m_val = int(getattr(c, "rs_1m", 80))
                acc_diss = str(getattr(c, "acc_diss_rating", "A"))
                rrg_r_val = float(getattr(c, "rrg_r", 100.0))
                rrg_m_val = float(getattr(c, "rrg_m", 100.0))
                f_net = float(getattr(c, "foreign_net_value_billion", 0.0))
                rank_sc = float(getattr(c, "ranking_score", 80.0))
                cat = str(getattr(c, "catalyst", ""))
                adtv20 = float(getattr(c, "adtv20_billion", 25.0))
                adv20 = int(getattr(c, "adv20_shares", 1_000_000))
                liq_sc = float(getattr(c, "liquidity_score", 80.0))
                prop_val = float(getattr(c, "prop_net_value_billion", 0.0))
                fl_regime = str(getattr(c, "flow_regime", "NOI_CAN_HANG"))
                fl_badge = str(getattr(c, "flow_badge", "🟢 NỘI GOM CÂN HÀNG"))
                has_prop = bool(getattr(c, "has_actual_prop_flow", False))
                atr_val = float(getattr(c, "atr_14", 0.0))
                atr_pct = round((atr_val / price) * 100.0, 2) if price > 0 and atr_val > 0 else 0.0
                atr_dist_poc = float(getattr(c, "atr_dist_from_poc", 0.0))
                poc_p = float(getattr(c, "poc_price", 0.0))
                val_p = float(getattr(c, "val_price", 0.0))
                slip_pct = float(getattr(c, "slippage_est_pct", 0.0))
                breadth_t0 = float(getattr(c, "market_breadth_pct_t0", 55.0))
                basis_t0 = float(getattr(c, "vn30_basis_t0", 0.0))
                pe_t0 = float(getattr(c, "pe_t0", 0.0))
                pb_t0 = float(getattr(c, "pb_t0", 0.0))
                eps_t0 = float(getattr(c, "eps_ttm_t0", 0.0))
                camel_t0 = float(getattr(c, "camel_score_t0", 0.0))

                status, buy_perm, advice, new_sl = self.evaluate_status_and_advice(
                    entry_orig=price,
                    cur_price=price,
                    cur_stop=sl,
                    tp1=tp1_val,
                    tp2=tp2_val,
                    holding_days=0,
                    trading_days=0,
                )
                if cand_perm == "BUY_CAUTION" and buy_perm == "BUY_OK":
                    buy_perm = "BUY_CAUTION"

                active_signals[sym] = ActiveSignal(
                    symbol=sym,
                    signal_id=self.build_signal_id(sym, now_str),
                    schema_version="v2",
                    first_signal_date=now_str,
                    last_updated=now_str,
                    entry_original=price,
                    current_price=price,
                    pnl_pct=0.0,
                    holding_days=0,
                    trading_days=0,
                    initial_stop_loss=sl,
                    current_stop_loss=new_sl,
                    tp1=tp1_val,
                    tp2=tp2_val,
                    status=status,
                    buy_permission=buy_perm,
                    advice_note=advice,
                    signal_type=sig_type,
                    composite_rating=comp_rating,
                    rs_1m=rs_1m_val,
                    acc_diss_rating=acc_diss,
                    rrg_r=rrg_r_val,
                    rrg_m=rrg_m_val,
                    foreign_net_value_billion=f_net,
                    ranking_score=rank_sc,
                    catalyst=cat,
                    adtv20_billion=adtv20,
                    adv20_shares=adv20,
                    liquidity_score=liq_sc,
                    t25_exposure_level=t25_exp,
                    prop_net_value_billion=prop_val,
                    flow_regime=fl_regime,
                    flow_badge=fl_badge,
                    has_actual_prop_flow_t0=has_prop,
                    atr_pct_t0=atr_pct,
                    atr_dist_from_poc_t0=atr_dist_poc,
                    poc_price_t0=poc_p,
                    val_price_t0=val_p,
                    slippage_est_pct_t0=slip_pct,
                    market_breadth_pct_t0=breadth_t0,
                    vn30_basis_t0=basis_t0,
                    pe_t0=pe_t0,
                    pb_t0=pb_t0,
                    eps_ttm_t0=eps_t0,
                    camel_score_t0=camel_t0,
                    max_price_reached=price,
                    min_price_reached=price,
                    mfe_pct=0.0,
                    mae_pct=0.0,
                    pnl_t25_pct=0.0,
                    pnl_t5_pct=0.0,
                    pnl_t10_pct=0.0,
                    pnl_t25_recorded=False,
                    pnl_t5_recorded=False,
                    pnl_t10_recorded=False,
                    outcome_label="ACTIVE",
                    target_win_binary=0,
                    is_closed=False,
                    closed_at="",
                    is_ml_ready=False,
                )

        # Cập nhật toàn bộ các vị thế đang mở nhưng đã rớt khỏi Top 20 bằng live_prices (chống Survivorship Bias & đóng băng nhãn 0.0)
        for sym, existing in active_signals.items():
            if sym in updated_syms:
                continue
            live_p = float(extra_prices.get(sym) or 0.0)
            tick_price = round(live_p, 2) if live_p > 0 else existing.current_price
            self._apply_price_tick_to_existing(
                existing=existing,
                price=tick_price,
                now_dt=now_dt,
                now_str=now_str if live_p > 0 else existing.last_updated,
                macro_pause_buying=macro_pause_buying,
            )

        self.save_active_signals(active_signals)
        self.generate_scorecard_markdown(active_signals, now_str)
        self.export_ml_dataset(active_signals)

        try:
            self.sync_to_google_sheets(active_signals)
        except Exception as e:
            logger.warning(f"Lỗi khi đồng bộ Google Sheets: {e}")

        return active_signals

    def get_advisory(self, symbol: str) -> str:
        """Truy xuất câu trả lời tư vấn đối chiếu trực tiếp cho một mã cổ phiếu."""
        active_signals = self.load_active_signals()
        sym = symbol.upper().strip()
        if sym not in active_signals:
            return (
                f"ℹ️ Mã {sym} hiện chưa có trong Sổ Cái Tín Hiệu Chân Sóng của Neiro-Stock-VN. "
                "Cần kiểm tra lại vi cấu trúc dòng tiền và BCTC cơ bản trước khi ra quyết định."
            )

        sig = active_signals[sym]
        badge = format_public_anti_fomo_badge(
            sig.buy_permission,
            sig.pnl_pct,
            sig.holding_days,
            status=sig.status,
            advice_note=sig.advice_note,
        )

        prop_part = (
            f"Tự doanh thực tế: {sig.prop_net_value_billion:+.1f} tỷ"
            if sig.prop_net_value_billion != 0.0
            else "Tự doanh: Chưa công bố EOD"
        )
        flow_info = f"{sig.flow_badge} (Khối ngoại: {sig.foreign_net_value_billion:+.1f} tỷ | {prop_part})"

        return (
            f"**[TƯ VẤN ĐỊNH LƯỢNG {sym}]** - {badge}\n"
            f"- Điểm kích hoạt gốc (T0): **{sig.entry_original:.2f}** ({sig.first_signal_date})\n"
            f"- Thị giá hiện tại: **{sig.current_price:.2f}** (Lãi/Lỗ: **{sig.pnl_pct:+.1f}%** sau {sig.holding_days} phiên)\n"
            f"- Ma trận Dòng tiền Kép: {flow_info}\n"
            f"- Cắt lỗ: {sig.current_stop_loss:.2f} | Mục tiêu: TP1 {sig.tp1:.2f} / TP2 {sig.tp2:.2f}\n"
            f"- Khuyến nghị: {sig.advice_note}"
        )

    def generate_scorecard_markdown(
        self,
        signals: Dict[str, ActiveSignal],
        updated_at_str: str,
    ) -> str:
        """Sinh bản báo cáo tóm tắt ngầm data/advisory_scorecard.md phục vụ kiểm tra trên GitHub."""
        if "PYTEST_CURRENT_TEST" in os.environ and self.scorecard_path == self.DEFAULT_SCORECARD:
            return ""

        rows = []
        for s in sorted(signals.values(), key=lambda x: x.pnl_pct, reverse=True):
            badge = format_public_anti_fomo_badge(
                s.buy_permission,
                s.pnl_pct,
                s.holding_days,
                status=s.status,
                advice_note=s.advice_note,
            )
            pnl_str = f"**{s.pnl_pct:+.1f}%**"
            rows.append(
                f"| **{s.symbol}** | {s.first_signal_date[:10]} | {s.entry_original:.2f} | {s.current_price:.2f} | "
                f"{pnl_str} | {s.trading_days} phiên ({s.holding_days}d) | {s.current_stop_loss:.2f} | {s.tp1:.2f} / {s.tp2:.2f} | {badge} |"
            )

        table_body = "\n".join(rows) if rows else "| Không có tín hiệu | - | - | - | - | - | - | - | - |"
        content = f"""# 🛡️ Bảng Đối Chiếu Tín Hiệu & Rada Chống Mua Đuổi (Anti-FOMO Scorecard)
*Cập nhật tự động ngầm trên GitHub lúc: `{updated_at_str}` (Giờ VN UTC+7)*

| Mã CP | Ngày Bùng Nổ | Giá Entry Gốc | Giá Hiện Tại | Lãi/Lỗ (%) | Nắm Giữ | Stop Loss | TP1 / TP2 | Quyết Nghị Mua Mới |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
{table_body}

---
💡 **Nguyên Tắc Định Chế Sống Còn Tại TTCK Việt Nam (Chu Kỳ T+2.5):**
1. **🟢 MUA ĐƯỢC:** Thị giá nằm trong biên `-1.5% .. +3.0%` từ điểm bùng nổ gốc T0 (<= 2 phiên giao dịch thực) và vĩ mô an toàn.
2. **🟡 THĂM DÒ THẬN TRỌNG (<=30%):** Thị giá trượt `+3.1% .. +5.0%` (vùng với) hoặc `-2.5% .. -1.5%` (rung lắc nền), tuyệt đối 0% margin.
3. **🔴/⛔ CẤM MUA MỚI:** Đã tăng `> +5.0%`, bẫy Bull-Trap, suy yếu `< -2.5%` dưới T0 (cấm bắt dao rơi), quá hạn `>= 3` phiên thực, hoặc Cầu chì Vĩ mô T+2.5 đang kích hoạt!
"""
        self.scorecard_path.parent.mkdir(parents=True, exist_ok=True)
        self.scorecard_path.write_text(content, encoding="utf-8")
        return content
