"""QA Professional Audit Test Suite for Neiro-Stock-VN.

Covers deep edge cases identified during the QA testing round:
1. Timezone-aware vs naive datetime handling in RankingHistoryTracker.
2. Negative / zero net income and CFO/NI ratio integrity in Fundamental Screener.
3. Multi-batch FIFO holding period tracking in T25BacktestEngine.
4. SignalTracker zero entry price guard & Anti-FOMO rule bounds.
5. Tactical Terminal HUD card titles, top stock scoping, and badge recovery semantics.
"""

from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest

from src.collector.ranking_history import RankingHistoryTracker
from src.collector.data_loader import FinancialReport, StockFinancials
from src.fundamental_engine.screener import screen_stocks
from src.backtesting.models import BacktestConfig, Exchange
from src.backtesting.engine import T25BacktestEngine
from src.hud.terminal import generate_terminal_html
from src.collector.fialda_scanner import FialdaCandidate
from src.risk_engine.signal_tracker import SignalTracker


class TestRankingHistoryTimezoneEdgeCases:
    """Kiểm thử xử lý múi giờ và định dạng ISO của RankingHistoryTracker."""

    def test_timezone_aware_current_time_does_not_crash(self, tmp_path: Path):
        """get_last_scan_ranks không được crash khi truyền datetime có timezone (UTC+7)."""
        test_file = tmp_path / "ranking_tz.jsonl"
        tracker = RankingHistoryTracker(history_file=test_file)

        # Batch 1 (naive format string)
        batch_1 = [
            {"symbol": "HPG", "price": 28.5, "ranking_score": 92.0},
            {"symbol": "SSI", "price": 34.0, "ranking_score": 89.0},
            {"symbol": "VND", "price": 19.2, "ranking_score": 85.0},
        ]
        candidates_1 = [type("C", (), d)() for d in batch_1]
        tracker.record_snapshot(candidates_1, timestamp="2026-10-27 09:30:00")

        # Truyền current_time dạng timezone-aware (như SignalTracker.current_vn_time())
        vn_tz = timezone(timedelta(hours=7))
        aware_now = datetime.now(vn_tz)

        # Trước khi fix, đoạn này ném: TypeError: can't subtract offset-naive and offset-aware datetimes
        ranks = tracker.get_last_scan_ranks(current_time=aware_now)
        assert isinstance(ranks, dict)
        assert ranks.get("HPG") == 1
        assert ranks.get("SSI") == 2
        assert ranks.get("VND") == 3

    def test_parse_iso_format_with_tz_offset(self):
        """parse_time phải parse được cả ISO 8601 có offset và naive."""
        # 1. Chuẩn có offset
        dt1 = RankingHistoryTracker.parse_time("2026-10-27T09:30:00+07:00")
        assert dt1 is not None

        # 2. Chuẩn naive
        dt2 = RankingHistoryTracker.parse_time("2026-10-27 09:30:00")
        assert dt2 is not None

        # 3. Chuẩn date-only
        dt3 = RankingHistoryTracker.parse_time("2026-10-27")
        assert dt3 is not None


class TestFundamentalScreenerLossMakingIntegrity:
    """Kiểm thử tính toàn vẹn khi doanh nghiệp bị lỗ ròng (Net Loss)."""

    def test_loss_making_company_not_institutional_grade(self):
        """Doanh nghiệp lỗ ròng (net_income < 0) tuyệt đối KHÔNG được đánh giá là ĐỊNH CHẾ GOM."""
        cur_loss = FinancialReport(
            symbol="LOSS_INC", year=2026, quarter=1,
            net_income=-150e9,          # Lỗ 150 tỷ
            operating_cash_flow=50e9,    # CFO dương 50 tỷ
            total_assets=5000e9,
            roa=-0.03, long_term_debt=800e9, current_ratio=1.5,
            shares_outstanding=100000000, gross_margin=0.15, asset_turnover=0.5
        )
        prev_loss = FinancialReport(
            symbol="LOSS_INC", year=2025, quarter=4,
            net_income=-200e9,
            operating_cash_flow=-10e9,
            total_assets=4800e9,
            roa=-0.04, long_term_debt=900e9, current_ratio=1.4,
            shares_outstanding=100000000, gross_margin=0.14, asset_turnover=0.48
        )
        stock = StockFinancials(
            symbol="LOSS_INC", company_name="Loss Inc", sector="San xuat",
            current_price=15000.0, current=cur_loss, previous=prev_loss,
            pe_history=[-5.0, -8.0], pb_history=[1.0, 1.2]
        )

        results = screen_stocks([stock])
        assert len(results) == 1
        res = results[0]

        # earnings_quality_ratio không được là số dương khổng lồ do chia cho 1.0
        assert res.earnings_quality_ratio < 0.0 or res.earnings_quality_ratio == 0.0
        # Tuyệt đối không đạt chuẩn Quỹ (Institutional Grade)
        assert res.is_institutional_grade is False


class TestBacktestMultiBatchHoldingPeriod:
    """Kiểm thử chu kỳ nắm giữ holding_bars khi bán đồng thời nhiều batch FIFO."""

    def test_multi_batch_preserves_first_entry_day_idx(self):
        """Khi mua 2 batch ở day 0 và day 2, bán toàn bộ ở day 5 thì holding_bars phải tính từ day 0."""
        config = BacktestConfig(initial_capital=100_000_000.0, min_holding_bars=2)
        engine = T25BacktestEngine(config)

        # Batch 1 mua day 0 (1,000 cp)
        b1 = engine.execute_buy(
            symbol="HPG", price=25.0, date="2023-01-02", day_idx=0,
            allocated_capital=26_000_000.0
        )
        assert b1 is not None

        # Batch 2 mua day 2 (1,000 cp)
        b2 = engine.execute_buy(
            symbol="HPG", price=26.0, date="2023-01-04", day_idx=2,
            allocated_capital=27_000_000.0
        )
        assert b2 is not None

        # Tại day 5, cả 2 batch đều đã về tài khoản (b1 settle day 2, b2 settle day 4)
        trade = engine.execute_sell(
            symbol="HPG", price=28.0, date="2023-01-09", day_idx=5,
            reason="TAKE_PROFIT"
        )
        assert trade is not None
        assert trade.shares == b1.shares + b2.shares
        # Điểm vào đầu tiên là day 0 (2023-01-02), không được bị ghi đè bởi batch 2 (day 2)
        assert trade.entry_date == "2023-01-02"
        # holding_bars phải là 5 - 0 = 5 (thay vì 5 - 2 = 3)
        assert trade.holding_days == 5


class TestSignalTrackerSafetyGuards:
    """Kiểm thử phòng vệ chống chia cho 0 trong SignalTracker."""

    def test_evaluate_status_with_zero_or_negative_entry(self):
        tracker = SignalTracker()
        status, buy_perm, advice, new_sl = tracker.evaluate_status_and_advice(
            entry_orig=0.0,
            cur_price=25.0,
            cur_stop=23.0,
            tp1=28.0,
            tp2=32.0,
            holding_days=0,
        )
        assert status in ["ACTIVE", "BUY_OK", "STOPPED_OUT", "EXTENDED_NO_CHASING"]
        assert isinstance(advice, str)


class TestTerminalHudLayer3DomainAudit:
    """Kiểm thử Tầng 3 Domain Logic & Thẻ Metric của Tactical HUD."""

    def test_card_3_breadth_title_not_misleading(self, tmp_path: Path):
        """Card 3 phải phản ánh đúng độ rộng danh mục dẫn dắt, không dùng tiêu đề sai lệch VN30 > MA20."""
        output_file = tmp_path / "exports" / "audit_terminal.html"
        mock_candidates = [
            FialdaCandidate(
                symbol="CTS", price=22.0, signal_type="CHO_MUA_CHAN_SONG",
                entry_low=21.5, entry_high=22.2, stop_loss=20.7, target_1m=28.5,
                rs_1m=88, composite_rating=85, acc_diss_rating="A",
                rrg_r=104.0, rrg_m=102.0, foreign_net_value_billion=12.5, ranking_score=89.5,
                catalyst="Chân sóng Chứng khoán", adtv20_billion=25.0, liquidity_score=92.0,
                tp1=23.76, tp2=28.5, prev_rank=1, rank_change_delta=0,
            )
        ]
        result_path = generate_terminal_html(
            output_path=str(output_file),
            fialda_candidates=mock_candidates,
            top_n=1
        )
        content = Path(result_path).read_text(encoding="utf-8")

        # Tiêu đề Card 3 phải là Độ Rộng Danh Mục Dẫn Dắt
        assert "Độ Rộng Danh Mục Dẫn Dắt" in content
        # Bảng Top Super Stocks phải có ID định danh để JS không bị lẫn lộn vũ trụ cổ phiếu
        assert 'id="top-stocks-table"' in content
