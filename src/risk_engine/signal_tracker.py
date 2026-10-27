"""Module Sổ Cái Tín Hiệu Ngầm, Rada Chống Mua Đuổi & ML Dataset Pipeline.

Chạy ngầm 100% trên GitHub Actions (không hiển thị lên Web Dashboard):
1. Neo giữ mốc Giá Khuyến Nghị Ban Đầu (T0 Original Entry Price), Stop Loss, TP1, TP2.
2. Đo lường tỷ lệ trượt giá lũy kế Δ% và số ngày nắm giữ chu kỳ T+2.5 sau 4-5 ngày.
3. Kích hoạt Rada Chống Mua Đuổi (Anti-FOMO Guard):
   - Δ% <= +3.0%: BUY_OK (Vùng mua chuẩn an toàn).
   - +3.1% <= Δ% <= +5.0%: BUY_CAUTION (Vùng với, chỉ mua thăm dò tối đa 30%).
   - Δ% > +5.0%: EXTENDED_NO_CHASING (Quá điểm mua - TUYỆT ĐỐI CẤM MUA ĐUỔI).
4. Chuẩn hóa Feature Vector T0 và Ground Truth Labels cho Machine Learning (ML).
5. Tự động đồng bộ lên Google Sheets (online database) và xuất bản data/ml_signals_dataset.csv.
"""

import json
import logging
import os
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd

from src.collector.google_sheets_client import GoogleSheetsLedgerClient

logger = logging.getLogger(__name__)


@dataclass
class ActiveSignal:
    """Cấu trúc dữ liệu một vị thế tín hiệu đang được theo dõi trong sổ cái ngầm."""

    symbol: str
    first_signal_date: str          # Thời điểm bùng nổ tín hiệu đầu tiên T0 (YYYY-MM-DD HH:MM:SS)
    last_updated: str               # Thời điểm quét cập nhật gần nhất
    entry_original: float           # Mức giá khuyến nghị gốc ban đầu
    current_price: float            # Thị giá cập nhật mới nhất
    pnl_pct: float                  # % Lãi/Lỗ lũy kế: ((current_price - entry_original) / entry_original) * 100
    holding_days: int               # Số ngày đã trôi qua kể từ phiên kích hoạt đầu tiên
    initial_stop_loss: float        # Ngưỡng cắt lỗ bảo toàn vốn ban đầu
    current_stop_loss: float        # Ngưỡng Trailing Stop hiện tại (tự nâng khi có lãi)
    tp1: float                      # Mục tiêu chốt lời 1 (1.5R, khuyến nghị chốt 50%)
    tp2: float                      # Mục tiêu chốt lời 2 (2.5R, gồng lãi 50% còn lại)
    status: str                     # 'ACTIVE', 'TP1_REACHED', 'TP2_REACHED', 'STOPPED_OUT'
    buy_permission: str             # 'BUY_OK', 'BUY_CAUTION', 'EXTENDED_NO_CHASING'
    advice_note: str                # Khuyến nghị hành động thực chiến chi tiết

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
    prop_net_value_billion: float = 0.0  # Uoc tinh dong tien noi / Tu doanh gom (ty VND)
    flow_regime: str = "NOI_CAN_HANG"    # 'SIEU_SONG', 'NOI_CAN_HANG', 'NGOAI_DO_GIA', 'RUI_RO_XA'
    flow_badge: str = "🟢 NỘI GOM CÂN HÀNG" # Huy hieu phan loai dong tien kep

    # ML Labels & Tracking biến động theo chu kỳ T+2.5 đến T+20 (Ground Truth)
    max_price_reached: float = 0.0
    min_price_reached: float = 0.0
    mfe_pct: float = 0.0            # Max Favorable Excursion (% lãi cực đại tiềm năng)
    mae_pct: float = 0.0            # Max Adverse Excursion (% sụt giảm sâu nhất)
    pnl_t25_pct: float = 0.0        # PnL thực tế tại chu kỳ T+2.5 (khi hàng về có thể bán)
    pnl_t5_pct: float = 0.0         # PnL tại phiên T+5
    outcome_label: str = "ACTIVE"   # 'WIN_TP1', 'WIN_TP2', 'STOP_LOSS', 'TIME_OUT', 'ACTIVE'
    target_win_binary: int = 0      # 1 nếu lãi >= 5% trước khi chạm cắt lỗ, ngược lại 0


class SignalTracker:
    """Bộ điều phối Sổ Cái Tín Hiệu Ngầm, Kiểm Soát Rủi Ro & Pipeline Dữ Liệu ML."""

    DEFAULT_FILE = Path("data/active_signals.jsonl")
    DEFAULT_SCORECARD = Path("data/advisory_scorecard.md")
    DEFAULT_ML_DATASET = Path("data/ml_signals_dataset.csv")
    MAX_HOLDING_DAYS = 30           # Tự động đóng/lưu trữ tín hiệu sau 30 ngày

    def __init__(
        self,
        signals_file: Optional[Path] = None,
        scorecard_file: Optional[Path] = None,
        ml_dataset_file: Optional[Path] = None,
    ):
        self.file_path = Path(signals_file) if signals_file else self.DEFAULT_FILE
        self.scorecard_path = Path(scorecard_file) if scorecard_file else self.DEFAULT_SCORECARD
        self.ml_dataset_path = Path(ml_dataset_file) if ml_dataset_file else self.DEFAULT_ML_DATASET

    @staticmethod
    def current_vn_time() -> datetime:
        """Lấy datetime hiện tại theo múi giờ Việt Nam (UTC+7)."""
        return datetime.now(timezone(timedelta(hours=7)))

    @staticmethod
    def format_time(dt: datetime) -> str:
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def parse_time(ts_str: str) -> Optional[datetime]:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(ts_str, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone(timedelta(hours=7)))
                return dt
            except Exception:
                pass
        return None

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
                        filtered = {k: v for k, v in data.items() if k in valid_fields}
                        signals[sym] = ActiveSignal(**filtered)
        except Exception as e:
            logger.warning(f"Lỗi khi đọc file active_signals: {e}")
            return {}
        return signals

    def save_active_signals(self, signals: Dict[str, ActiveSignal]) -> None:
        """Lưu lại danh sách các vị thế vào file JSONL (bỏ qua nếu đang chạy pytest trên file thật)."""
        if "PYTEST_CURRENT_TEST" in os.environ and self.file_path == self.DEFAULT_FILE:
            return

        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.file_path, "w", encoding="utf-8") as f:
            for sig in signals.values():
                f.write(json.dumps(asdict(sig), ensure_ascii=False) + "\n")

    def export_ml_dataset(self, signals: Optional[Dict[str, ActiveSignal]] = None) -> Path:
        """Xuất bản toàn bộ lịch sử tín hiệu thành file CSV phẳng chuẩn Machine Learning."""
        if "PYTEST_CURRENT_TEST" in os.environ and self.ml_dataset_path == self.DEFAULT_ML_DATASET:
            return self.ml_dataset_path

        active_signals = signals if signals is not None else self.load_active_signals()
        if not active_signals:
            return self.ml_dataset_path

        try:
            self.ml_dataset_path.parent.mkdir(parents=True, exist_ok=True)
            records = [asdict(sig) for sig in active_signals.values()]
            df = pd.DataFrame(records)
            df.to_csv(self.ml_dataset_path, index=False, encoding="utf-8")
        except Exception as e:
            logger.warning(f"Lỗi khi xuất ml_dataset CSV: {e}")

        return self.ml_dataset_path

    def sync_to_google_sheets(self, signals: Dict[str, ActiveSignal]) -> bool:
        """Đồng bộ danh sách tín hiệu sang Google Sheets qua Webhook."""
        client = GoogleSheetsLedgerClient()
        return client.sync_signals(list(signals.values()))

    def evaluate_status_and_advice(
        self,
        entry_orig: float,
        cur_price: float,
        cur_stop: float,
        tp1: float,
        tp2: float,
        holding_days: int,
    ) -> tuple[str, str, str, float]:
        """Đánh giá trạng thái vị thế, quyền mở mua và câu tư vấn hành động."""
        if entry_orig <= 0:
            pnl_pct = 0.0
        else:
            pnl_pct = round(((cur_price - entry_orig) / entry_orig) * 100.0, 2)
        new_stop = cur_stop

        # 1. Cơ chế Trailing Stop / Nâng chặn lỗ bảo toàn vốn
        if cur_price >= tp1:
            # Khi đã đạt TP1: Tự động nâng Stop Loss lên điểm hòa vốn (Break-even)
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

        if cur_price >= tp2:
            status = "TP2_REACHED"
            buy_permission = "EXTENDED_NO_CHASING"
            advice_note = (
                f"🎯 ĐẠT MỤC TIÊU LỚN TP2 ({tp2:.2f}, Lãi {pnl_pct:+.1f}%). "
                "Khuyến nghị chốt lời toàn bộ phần vị thế còn lại, TUYỆT ĐỐI CẤM MUA MỚI."
            )
            return status, buy_permission, advice_note, new_stop

        if cur_price >= tp1:
            status = "TP1_REACHED"
            buy_permission = "EXTENDED_NO_CHASING"
            advice_note = (
                f"🚀 ĐẠT MỤC TIÊU 1 TP1 ({tp1:.2f}, Lãi {pnl_pct:+.1f}%). "
                f"Chốt lời 50% tiền tươi, dời Stop Loss lên giá mua {entry_orig:.2f} (Hòa vốn) để gồng lãi 50% còn lại. "
                "CẤM MUA ĐUỔI vì rủi ro rung lắc T+2.5 rất cao."
            )
            return status, buy_permission, advice_note, new_stop

        status = "ACTIVE"

        # 3. Rada Kiểm Soát Quyền Mua (Anti-FOMO / Chasing Rule)
        if pnl_pct > 5.0 or holding_days >= 3:
            buy_permission = "EXTENDED_NO_CHASING"
            advice_note = (
                f"🔴 QUÁ ĐIỂM MUA - CẤM MUA ĐUỔI (Đã tăng {pnl_pct:+.1f}% từ điểm kích hoạt ban đầu {entry_orig:.2f}, nắm giữ {holding_days} phiên). "
                "Chỉ ưu tiên người đã có sẵn hàng tiếp tục gồng lãi. "
                "Người chưa có hàng TUYỆT ĐỐI KHÔNG ĐƯỢC MUA ĐUỔI để tránh bẫy điều chỉnh kẹp T+2.5."
            )
        elif 3.0 < pnl_pct <= 5.0:
            buy_permission = "BUY_CAUTION"
            advice_note = (
                f"🟡 VÙNG VỚI (Tăng {pnl_pct:+.1f}% từ điểm bùng nổ {entry_orig:.2f}). "
                "Chỉ giải ngân tối đa 30% vị thế thăm dò, tuyệt đối không dùng margin."
            )
        else:
            buy_permission = "BUY_OK"
            advice_note = (
                f"🟢 VÙNG MUA CHUẨN (Thị giá {cur_price:.2f} trong biên độ an toàn so với điểm bùng nổ {entry_orig:.2f}). "
                f"Được phép mở mua mới vị thế chuẩn. Cắt lỗ tại {new_stop:.2f}."
            )

        return status, buy_permission, advice_note, new_stop

    def update_signals(
        self,
        current_candidates: List[Any],
        current_time: Optional[datetime] = None,
    ) -> Dict[str, ActiveSignal]:
        """Cập nhật sổ cái tín hiệu dựa trên danh sách quét mới nhất và trích xuất ML features."""
        now_dt = current_time or self.current_vn_time()
        now_str = self.format_time(now_dt)

        active_signals = self.load_active_signals()

        for c in current_candidates:
            sym = getattr(c, "symbol", "")
            if not sym:
                continue

            price = round(float(getattr(c, "price", 0.0)), 2)
            sl = round(float(getattr(c, "stop_loss", price * 0.945)), 2)
            tp1_val = round(float(getattr(c, "tp1", price * 1.08)), 2)
            tp2_val = round(float(getattr(c, "tp2", getattr(c, "target_1m", price * 1.25))), 2)

            # Trích xuất metadata ML Features
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
            t25_exp = str(getattr(c, "t25_exposure_level", "SAFE"))
            prop_val = float(getattr(c, "prop_net_value_billion", 0.0))
            fl_regime = str(getattr(c, "flow_regime", "NOI_CAN_HANG"))
            fl_badge = str(getattr(c, "flow_badge", "🟢 NỘI GOM CÂN HÀNG"))

            if sym in active_signals:
                # Cổ phiếu ĐÃ TỪNG XUẤT HIỆN -> Giữ nguyên điểm vào gốc (Anchor) và cập nhật
                existing = active_signals[sym]
                first_dt = self.parse_time(existing.first_signal_date) or now_dt
                holding_days = max(0, (now_dt.date() - first_dt.date()).days)

                status, buy_perm, advice, new_sl = self.evaluate_status_and_advice(
                    entry_orig=existing.entry_original,
                    cur_price=price,
                    cur_stop=existing.current_stop_loss,
                    tp1=existing.tp1,
                    tp2=existing.tp2,
                    holding_days=holding_days,
                )

                entry_ref = existing.entry_original if existing.entry_original > 0 else (price if price > 0 else 1.0)
                pnl = round(((price - entry_ref) / entry_ref) * 100.0, 2)
                existing.current_price = price
                existing.last_updated = now_str
                existing.pnl_pct = pnl
                existing.holding_days = holding_days
                existing.current_stop_loss = new_sl
                existing.status = status
                existing.buy_permission = buy_perm
                existing.advice_note = advice

                # Cập nhật Ground Truth Labels (ML)
                cur_max = max(existing.max_price_reached or entry_ref, price)
                cur_min = min(existing.min_price_reached or entry_ref, price)
                mfe = round(((cur_max - entry_ref) / entry_ref) * 100.0, 2)
                mae = round(((cur_min - entry_ref) / entry_ref) * 100.0, 2)
                existing.max_price_reached = cur_max
                existing.min_price_reached = cur_min
                existing.mfe_pct = mfe
                existing.mae_pct = mae

                # Ghi nhận PnL chu kỳ T+2.5 (phiên 2 hoặc 3)
                if holding_days in (2, 3) and existing.pnl_t25_pct == 0.0:
                    existing.pnl_t25_pct = pnl
                if holding_days >= 5 and existing.pnl_t5_pct == 0.0:
                    existing.pnl_t5_pct = pnl

                # Cập nhật outcome_label
                if status == "STOPPED_OUT":
                    existing.outcome_label = "STOP_LOSS"
                elif status == "TP2_REACHED":
                    existing.outcome_label = "WIN_TP2"
                elif status == "TP1_REACHED":
                    existing.outcome_label = "WIN_TP1"
                elif holding_days >= self.MAX_HOLDING_DAYS:
                    existing.outcome_label = "TIME_OUT"
                else:
                    existing.outcome_label = "ACTIVE"

                # Cập nhật target_win_binary (lãi >= 5% mà không chạm cắt lỗ ban đầu)
                if mfe >= 5.0 and cur_min > existing.initial_stop_loss:
                    existing.target_win_binary = 1
                elif status == "STOPPED_OUT" and mfe < 5.0:
                    existing.target_win_binary = 0

            else:
                # Cổ phiếu MỚI TOANH xuất hiện lần đầu (T0)
                status, buy_perm, advice, new_sl = self.evaluate_status_and_advice(
                    entry_orig=price,
                    cur_price=price,
                    cur_stop=sl,
                    tp1=tp1_val,
                    tp2=tp2_val,
                    holding_days=0,
                )
                active_signals[sym] = ActiveSignal(
                    symbol=sym,
                    first_signal_date=now_str,
                    last_updated=now_str,
                    entry_original=price,
                    current_price=price,
                    pnl_pct=0.0,
                    holding_days=0,
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
                    max_price_reached=price,
                    min_price_reached=price,
                    mfe_pct=0.0,
                    mae_pct=0.0,
                    pnl_t25_pct=0.0,
                    pnl_t5_pct=0.0,
                    outcome_label="ACTIVE",
                    target_win_binary=0,
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
        badge = (
            "🟢 MUA ĐƯỢC"
            if sig.buy_permission == "BUY_OK"
            else ("🟡 VÙNG VỚI" if sig.buy_permission == "BUY_CAUTION" else "🔴 CẤM MUA ĐUỔI")
        )

        flow_info = f"{sig.flow_badge} (Khối ngoại: {sig.foreign_net_value_billion:+.1f} tỷ | Dòng tiền nội ước tính: ~{sig.prop_net_value_billion:+.1f} tỷ)"

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
            badge = (
                "🟢 MUA ĐƯỢC"
                if s.buy_permission == "BUY_OK"
                else ("🟡 VÙNG VỚI" if s.buy_permission == "BUY_CAUTION" else "🔴 CẤM MUA ĐUỔI")
            )
            pnl_str = f"**{s.pnl_pct:+.1f}%**"
            rows.append(
                f"| **{s.symbol}** | {s.first_signal_date[:10]} | {s.entry_original:.2f} | {s.current_price:.2f} | "
                f"{pnl_str} | {s.holding_days} ngày | {s.current_stop_loss:.2f} | {s.tp1:.2f} / {s.tp2:.2f} | {badge} |"
            )

        table_body = "\n".join(rows) if rows else "| Không có tín hiệu | - | - | - | - | - | - | - | - |"
        content = f"""# 🛡️ Bảng Đối Chiếu Tín Hiệu & Rada Chống Mua Đuổi (Anti-FOMO Scorecard)
*Cập nhật tự động ngầm trên GitHub lúc: `{updated_at_str}` (Giờ VN UTC+7)*

| Mã CP | Ngày Bùng Nổ | Giá Entry Gốc | Giá Hiện Tại | Lãi/Lỗ (%) | Nắm Giữ | Stop Loss | TP1 / TP2 | Quyết Nghị Mua Mới |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
{table_body}

---
💡 **Nguyên Tắc Định Chế Sống Còn Tại TTCK Việt Nam (Chu Kỳ T+2.5):**
1. **🟢 MUA ĐƯỢC:** Thị giá nằm trong vùng <= +3% từ điểm bùng nổ gốc ban đầu.
2. **🟡 VÙNG VỚI:** Thị giá trượt +3.1% đến +5.0%, chỉ giải ngân thăm dò tối đa 30%, không dùng margin.
3. **🔴 CẤM MUA ĐUỔI:** Thị giá đã tăng > +5% hoặc nắm giữ > 3 phiên. Người mua đuổi chắc chắn sẽ chịu rủi ro bẫy rung lắc T+2.5 và kẹp hàng. Tuyệt đối không FOMO!
"""
        self.scorecard_path.parent.mkdir(parents=True, exist_ok=True)
        self.scorecard_path.write_text(content, encoding="utf-8")
        return content
