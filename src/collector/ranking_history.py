"""Hệ thống Lưu trữ & Theo vết Lịch sử Xếp hạng Top Cổ phiếu (Ranking History Tracker).

Tuân thủ nghiêm ngặt Zero-Waste Mandate (< 15MB):
1. Ghi nhận chuỗi thời gian xếp hạng vào data/ranking_history.jsonl dạng nén JSON lines siêu nhẹ.
2. Tự động cắt tỉa (Rolling Window) duy trì tối đa 500 bản ghi (~30KB), không gây phình to ổ đĩa.
3. So sánh đối chiếu tự động với phiên trước:
   - Tính toán biến động thứ hạng (Delta Rank): +N (thăng hạng), -N (tụt hạng), 0 (giữ hạng).
   - Đánh dấu cổ phiếu mới toanh bứt phá vào bảng xếp hạng (NEW).
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class RankingSnapshot:
    """Snapshot dữ liệu xếp hạng của một cổ phiếu tại một thời điểm quét."""

    timestamp: str  # ISO 8601 (UTC+7)
    symbol: str
    rank: int
    score: float
    price: float
    signal_type: str
    stop_loss: float
    tp1: float
    tp2: float
    rr_ratio: float
    adtv20_billion: float


class RankingHistoryTracker:
    """Bộ theo dõi và lưu trữ lịch sử xếp hạng qua các phiên quét định kỳ."""

    DEFAULT_PATH = Path("data/ranking_history.jsonl")
    MAX_RECORDS = 500  # Giữ tối đa 500 bản ghi để dung lượng luôn < 50KB

    def __init__(self, history_file: Optional[Path] = None, max_records: int = MAX_RECORDS):
        self.file_path = Path(history_file) if history_file else self.DEFAULT_PATH
        self.max_records = max_records

    @staticmethod
    def current_vn_time_str() -> str:
        """Lấy chuỗi thời gian hiện tại theo giờ Việt Nam (UTC+7)."""
        vn_tz = timezone(timedelta(hours=7))
        return datetime.now(vn_tz).strftime("%Y-%m-%d %H:%M:%S")

    def record_snapshot(
        self,
        candidates: List[Any],
        timestamp: Optional[str] = None,
    ) -> int:
        """Ghi nhận snapshot danh sách ứng viên Top N vào file JSONL.

        Args:
            candidates: Danh sách FialdaCandidate hoặc đối tượng có các thuộc tính tương ứng.
            timestamp: Chuỗi thời gian quét (nếu None sẽ lấy giờ VN hiện tại).

        Returns:
            Số lượng bản ghi đã được ghi thành công.
        """
        if not candidates:
            return 0

        ts = timestamp or self.current_vn_time_str()
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        new_records: List[Dict[str, Any]] = []
        for idx, c in enumerate(candidates, 1):
            snap = RankingSnapshot(
                timestamp=ts,
                symbol=getattr(c, "symbol", "UNKNOWN"),
                rank=idx,
                score=round(float(getattr(c, "ranking_score", 0.0)), 2),
                price=round(float(getattr(c, "price", 0.0)), 2),
                signal_type=str(getattr(c, "signal_type", "CHO_MUA")),
                stop_loss=round(float(getattr(c, "stop_loss", 0.0)), 2),
                tp1=round(float(getattr(c, "tp1", getattr(c, "entry_high", 0.0))), 2),
                tp2=round(float(getattr(c, "tp2", getattr(c, "target_1m", 0.0))), 2),
                rr_ratio=round(float(getattr(c, "rr_ratio", 2.5)), 2),
                adtv20_billion=round(float(getattr(c, "adtv20_billion", 25.0)), 1),
            )
            new_records.append(asdict(snap))

        # Đọc các bản ghi hiện có
        existing_records = self.load_all_records()
        combined = existing_records + new_records

        # Cắt tỉa (Rolling Window) nếu vượt quá max_records
        if len(combined) > self.max_records:
            combined = combined[-self.max_records :]

        with open(self.file_path, "w", encoding="utf-8") as f:
            for item in combined:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        return len(new_records)

    def load_all_records(self) -> List[Dict[str, Any]]:
        """Đọc toàn bộ các bản ghi lịch sử từ file JSONL."""
        if not self.file_path.exists():
            return []

        records: List[Dict[str, Any]] = []
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))
        except Exception:
            return []
        return records

    def get_last_scan_ranks(self) -> Dict[str, int]:
        """Lấy thứ hạng của các cổ phiếu trong phiên quét gần nhất trước đó.

        Returns:
            Dictionary {symbol: rank}.
        """
        records = self.load_all_records()
        if not records:
            return {}

        # Tìm các mốc timestamp duy nhất theo thứ tự xuất hiện
        timestamps = []
        for r in records:
            ts = r.get("timestamp")
            if ts and (not timestamps or timestamps[-1] != ts):
                timestamps.append(ts)

        if not timestamps:
            return {}

        # Phiên quét gần nhất là mốc timestamp cuối cùng
        last_ts = timestamps[-1]
        last_batch = [r for r in records if r.get("timestamp") == last_ts]
        return {r["symbol"]: int(r["rank"]) for r in last_batch if "symbol" in r and "rank" in r}

    def calculate_rank_changes(
        self,
        current_candidates: List[Any],
        use_last_batch: bool = True,
    ) -> Dict[str, Dict[str, Any]]:
        """Tính toán biến động thứ hạng (Delta Rank) giữa danh sách hiện tại và phiên trước.

        Args:
            current_candidates: Danh sách ứng viên hiện tại.
            use_last_batch: True để so sánh với phiên gần nhất đã lưu.

        Returns:
            Dictionary map: {symbol: {'delta_rank': int|None, 'status': str, 'badge': str, 'prev_rank': int|None}}.
        """
        prev_ranks = self.get_last_scan_ranks() if use_last_batch else {}
        results: Dict[str, Dict[str, Any]] = {}

        for idx, c in enumerate(current_candidates, 1):
            sym = getattr(c, "symbol", "")
            if not sym:
                continue

            current_rank = idx
            if sym in prev_ranks:
                prev_rank = prev_ranks[sym]
                # prev_rank = 5, current_rank = 2 -> thăng hạng +3 bậc
                delta = prev_rank - current_rank
                if delta > 0:
                    status = "UP"
                    badge = f"↗ +{delta}"
                elif delta < 0:
                    status = "DOWN"
                    badge = f"↘ {delta}"
                else:
                    status = "SAME"
                    badge = "="
                results[sym] = {
                    "delta_rank": delta,
                    "status": status,
                    "badge": badge,
                    "prev_rank": prev_rank,
                }
            else:
                results[sym] = {
                    "delta_rank": None,
                    "status": "NEW",
                    "badge": "🆕 MỚI",
                    "prev_rank": None,
                }

        return results

    def get_symbol_timeline(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Truy xuất chuỗi lịch sử biến động thứ hạng của một mã cổ phiếu cụ thể."""
        records = self.load_all_records()
        sym_records = [r for r in records if r.get("symbol") == symbol.upper()]
        return sym_records[-limit:]
