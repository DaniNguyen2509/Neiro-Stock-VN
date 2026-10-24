"""Unit tests cho module Fialda VIP Expert Scanner."""
from unittest.mock import MagicMock, patch
from src.collector.fialda_scanner import FialdaScanner, FialdaCandidate, format_top_5_report


def test_fialda_candidate_dataclass():
    """Kiem tra khoi tao ung vien FialdaCandidate."""
    candidate = FialdaCandidate(
        symbol="DBC",
        price=16.4,
        signal_type="CHO_MUA_CHAN_SONG",
        entry_low=16.07,
        entry_high=16.42,
        stop_loss=15.19,
        target_1m=20.56,
        rs_1m=84,
        composite_rating=82,
        acc_diss_rating="A",
        rrg_r=101.7,
        rrg_m=100.8,
        foreign_net_value_billion=4.4,
        ranking_score=90.5,
        catalyst="RRG Leading, IBD Composite=82",
    )
    assert candidate.symbol == "DBC"
    assert candidate.stop_loss < candidate.price < candidate.target_1m
    assert candidate.ranking_score > 80.0


def test_fallback_mock_top_5():
    """Kiem tra che do fallback mock khi offline luon tra ve dung 5 ma."""
    top5 = FialdaScanner._fallback_mock_top_5()
    assert len(top5) == 5
    for c in top5:
        assert len(c.symbol) == 3
        assert c.target_1m > c.price
        assert c.stop_loss < c.price


def test_format_top_5_report():
    """Kiem tra ham render bao cao Top 5 ra dinh dang terminal."""
    top5 = FialdaScanner._fallback_mock_top_5()
    breadth = {
        "advances": 144,
        "declines": 156,
        "pe": 12.44,
        "totalValue": 16942000000000.0,
    }
    report = format_top_5_report(top5, breadth)
    assert "TOP 5 SIÊU CỔ PHIẾU" in report
    assert "DBC" in report
    assert "GEX" in report
    assert "16,942 ty" in report


def test_fialda_scanner_ranking_logic():
    """Kiem tra logic tinh diem va sap xep xep hang cua FialdaScanner voi mock API."""
    scanner = FialdaScanner(username="mock_user", password="mock_pwd")
    scanner.token = "mock_token"

    mock_cho_mua = {
        "DBC": {"item1": True, "item2": 16.0, "item3": 16.5},
        "ACB": {"item1": True, "item2": 20.5, "item3": 21.0},
    }
    mock_dot_bien = ["GEX", "CTS"]
    mock_rrg = {
        "DBC": {"r": 103.5, "m": 102.1},
        "ACB": {"r": 101.0, "m": 101.5},
        "GEX": {"r": 102.0, "m": 103.0},
        "CTS": {"r": 104.0, "m": 104.5},
    }
    mock_top_symbols = [
        {"symbol": "DBC", "currentPrice": 16.3, "totalForeignerNetBuyValue": 15e9},
        {"symbol": "ACB", "currentPrice": 21.0, "totalForeignerNetBuyValue": -5e9},
        {"symbol": "GEX", "currentPrice": 24.5, "totalForeignerNetBuyValue": 20e9},
        {"symbol": "CTS", "currentPrice": 38.0, "totalForeignerNetBuyValue": 10e9},
    ]

    with patch.object(scanner, "get_expert_buy_signals", return_value=mock_cho_mua), \
         patch.object(scanner, "get_expert_value_surge", return_value=mock_dot_bien), \
         patch.object(scanner, "get_rrg_data", return_value=mock_rrg), \
         patch.object(scanner, "get_market_top_symbols", return_value=mock_top_symbols), \
         patch.object(scanner, "get_expert_rating", return_value={"rS1M": 85, "compositeRating": 88, "accDissRating": "A"}):

        result = scanner.scan_top_5_rockets()
        assert len(result) == 4
        # DBC va ACB phai co tin hieu CHO_MUA_CHAN_SONG
        dbc_item = next(x for x in result if x.symbol == "DBC")
        assert dbc_item.signal_type == "CHO_MUA_CHAN_SONG"
        assert dbc_item.ranking_score > 85.0


def test_format_top_5_markdown():
    """Kiem tra ham format_top_5_markdown sinh chuan GitHub Flavored Markdown."""
    from src.collector.fialda_scanner import format_top_5_markdown
    top5 = FialdaScanner._fallback_mock_top_5()
    breadth = {
        "advances": 144,
        "declines": 156,
        "pe": 12.44,
        "totalValue": 16942000000000.0,
    }
    md = format_top_5_markdown(top5, breadth)
    assert "## 🚀 NEIRO-STOCK-VN" in md
    assert "| STT | Mã CP | Tín Hiệu AI" in md
    assert "**DBC**" in md
    assert "16,942 tỷ VND" in md


def test_get_fundamental_screener_data_fallback():
    """Kiem tra fallback co ban khi offline."""
    data = FialdaScanner._fallback_mock_fundamental()
    assert len(data) >= 5
    hpg = next(x for x in data if x["symbol"] == "HPG")
    assert hpg["price"] == 20.95
    assert hpg["f_score"] == 9.0
    assert hpg["pe"] == 8.5
    assert hpg["is_institutional"] is True


