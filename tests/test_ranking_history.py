"""Unit tests kiểm thử Module Lưu Trữ & Theo Vết Lịch Sử Xếp Hạng (Ranking History Tracker)."""

import json
from dataclasses import dataclass
from pathlib import Path
import pytest
from src.collector.ranking_history import RankingHistoryTracker, RankingSnapshot


@dataclass
class DummyCandidate:
    symbol: str
    price: float
    ranking_score: float
    signal_type: str = "CHO_MUA"
    stop_loss: float = 48.0
    tp1: float = 54.0
    tp2: float = 58.0
    rr_ratio: float = 2.5
    adtv20_billion: float = 35.0


class TestRankingHistoryTracker:
    """Kiểm thử tính toàn vẹn dữ liệu và logic biến động thứ hạng."""

    def test_record_and_load_snapshots(self, tmp_path: Path):
        test_file = tmp_path / "ranking_test.jsonl"
        tracker = RankingHistoryTracker(history_file=test_file, max_records=10)

        candidates = [
            DummyCandidate("HPG", price=28.5, ranking_score=92.5),
            DummyCandidate("SSI", price=34.0, ranking_score=89.0),
            DummyCandidate("VND", price=19.2, ranking_score=85.5),
        ]

        count = tracker.record_snapshot(candidates, timestamp="2026-10-24 09:30:00")
        assert count == 3
        assert test_file.exists()

        records = tracker.load_all_records()
        assert len(records) == 3
        assert records[0]["symbol"] == "HPG"
        assert records[0]["rank"] == 1
        assert records[1]["symbol"] == "SSI"
        assert records[1]["rank"] == 2

    def test_calculate_rank_changes_up_down_new(self, tmp_path: Path):
        test_file = tmp_path / "ranking_changes.jsonl"
        tracker = RankingHistoryTracker(history_file=test_file)

        # Phien 1: HPG rank 1, SSI rank 2, VND rank 3, MWG rank 4
        batch_1 = [
            DummyCandidate("HPG", price=28.5, ranking_score=92.0),
            DummyCandidate("SSI", price=34.0, ranking_score=89.0),
            DummyCandidate("VND", price=19.2, ranking_score=85.0),
            DummyCandidate("MWG", price=55.0, ranking_score=82.0),
        ]
        tracker.record_snapshot(batch_1, timestamp="2026-10-24 09:30:00")

        # Phien 2:
        # SSI vuot len rank 1 (tu rank 2 -> tang +1 bac)
        # HPG tut xuong rank 2 (tu rank 1 -> tut -1 bac)
        # MWG van giu rank 4 (tu rank 4 -> giu nguyen =)
        # FPT moi xuat hien rank 3 (NEW)
        batch_2 = [
            DummyCandidate("SSI", price=35.0, ranking_score=94.0),
            DummyCandidate("HPG", price=28.3, ranking_score=91.0),
            DummyCandidate("FPT", price=130.0, ranking_score=90.0),
            DummyCandidate("MWG", price=55.5, ranking_score=83.0),
        ]

        changes = tracker.calculate_rank_changes(batch_2)

        # SSI: prev=2, cur=1 -> delta=+1
        assert changes["SSI"]["status"] == "UP"
        assert changes["SSI"]["delta_rank"] == 1
        assert changes["SSI"]["badge"] == "↗ +1"

        # HPG: prev=1, cur=2 -> delta=-1
        assert changes["HPG"]["status"] == "DOWN"
        assert changes["HPG"]["delta_rank"] == -1
        assert changes["HPG"]["badge"] == "↘ -1"

        # MWG: prev=4, cur=4 -> delta=0
        assert changes["MWG"]["status"] == "SAME"
        assert changes["MWG"]["delta_rank"] == 0
        assert changes["MWG"]["badge"] == "="

        # FPT: chua tung co trong phien 1 -> NEW
        assert changes["FPT"]["status"] == "NEW"
        assert changes["FPT"]["delta_rank"] is None
        assert changes["FPT"]["badge"] == "🆕 MỚI"

    def test_rolling_window_prunes_old_records(self, tmp_path: Path):
        # Gioi han toi da 5 records
        test_file = tmp_path / "ranking_prune.jsonl"
        tracker = RankingHistoryTracker(history_file=test_file, max_records=5)

        # Ghi dot 1 (3 records)
        b1 = [DummyCandidate("A", 10, 80), DummyCandidate("B", 20, 70), DummyCandidate("C", 30, 60)]
        tracker.record_snapshot(b1, timestamp="T1")
        assert len(tracker.load_all_records()) == 3

        # Ghi dot 2 (4 records) -> Tong 7, vuot 5 -> Cat tia giu lai 5 records moi nhat
        b2 = [DummyCandidate("D", 40, 90), DummyCandidate("E", 50, 85), DummyCandidate("F", 60, 75), DummyCandidate("G", 70, 65)]
        tracker.record_snapshot(b2, timestamp="T2")

        records = tracker.load_all_records()
        assert len(records) == 5
        # 2 records cuoi cua dot 1 va 4 records cua dot 2? Khong, giu 5 records moi nhat [-5:]
        symbols = [r["symbol"] for r in records]
        assert symbols == ["C", "D", "E", "F", "G"]

    def test_rank_fallback_when_temporarily_absent(self, tmp_path: Path):
        """Ma co phieu rot khoi Top20 tam thoi phai dung rank lich su, khong danh MỚI."""
        test_file = tmp_path / "ranking_fallback.jsonl"
        tracker = RankingHistoryTracker(history_file=test_file)

        # Phien 1: HPG rank 1, SSI rank 2, VND rank 3
        batch_1 = [
            DummyCandidate("HPG", price=28.5, ranking_score=92.0),
            DummyCandidate("SSI", price=34.0, ranking_score=89.0),
            DummyCandidate("VND", price=19.2, ranking_score=85.0),
        ]
        tracker.record_snapshot(batch_1, timestamp="2026-10-24 09:30:00")

        # Phien 2: VND rot khoi Top, FPT thay the
        batch_2 = [
            DummyCandidate("HPG", price=28.5, ranking_score=92.0),
            DummyCandidate("SSI", price=34.0, ranking_score=89.0),
            DummyCandidate("FPT", price=130.0, ranking_score=85.0),
        ]
        tracker.record_snapshot(batch_2, timestamp="2026-10-24 14:00:00")

        # Phien 3: VND quay lai rank 2, NEW_STOCK hoan toan moi
        batch_3 = [
            DummyCandidate("HPG", price=28.5, ranking_score=92.0),
            DummyCandidate("VND", price=19.5, ranking_score=90.0),
            DummyCandidate("NEW_STOCK", price=50.0, ranking_score=85.0),
        ]
        changes = tracker.calculate_rank_changes(batch_3)

        # VND: da tung o rank 3 (phien 1), bay gio rank 2 -> THANG HANG +1, KHONG PHAI MỚI
        assert changes["VND"]["status"] == "UP"
        assert changes["VND"]["prev_rank"] == 3
        assert changes["VND"]["delta_rank"] == 1

        # HPG: van rank 1 -> SAME
        assert changes["HPG"]["status"] == "SAME"

        # NEW_STOCK: chua tung xuat hien trong bat ky phien nao -> MỚI that su
        assert changes["NEW_STOCK"]["status"] == "NEW"
        assert changes["NEW_STOCK"]["delta_rank"] is None
        assert changes["NEW_STOCK"]["badge"] == "🆕 MỚI"
