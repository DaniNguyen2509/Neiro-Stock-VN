"""Kiem thu chuc nang doc Bao cao tai chinh (BCTC) va Tin tuc, Su kien doanh nghiep tu Fialda."""
import pytest
from src.collector.fialda_scanner import FialdaScanner


def test_fallback_mock_news():
    """Kiem tra ham fallback tin tuc tra ve day du thong tin hop le."""
    news = FialdaScanner._fallback_mock_news("HPG")
    assert len(news) >= 2
    for n in news:
        assert n["symbol"] == "HPG"
        assert len(n["title"]) > 10
        assert "source" in n
        assert "time" in n
        assert "short_content" in n


def test_fallback_mock_events():
    """Kiem tra ham fallback su kien doanh nghiep tra ve hop le."""
    events = FialdaScanner._fallback_mock_events("DBC")
    assert len(events) >= 1
    for ev in events:
        assert ev["symbol"] == "DBC"
        assert len(ev["event_name"]) > 5
        assert "date" in ev


def test_fallback_mock_income_statement():
    """Kiem tra bao cao ket qua kinh doanh 4 quy lien tiep."""
    statements = FialdaScanner._fallback_mock_income_statement("HPG")
    assert len(statements) == 4
    for s in statements:
        assert 1 <= s["quarter"] <= 4
        assert s["year"] >= 2025
        assert s["revenue_billion"] > 0
        assert s["gross_profit_billion"] > 0
        assert s["net_profit_billion"] > 0


def test_fialda_scanner_bctc_and_news_methods_offline():
    """Kiem tra scanner khi offline hoac khong co token luon tra ve fallback an toan, khong loi."""
    scanner = FialdaScanner(username="", password="")
    scanner.token = None

    news = scanner.get_company_news("HPG")
    assert len(news) >= 1
    assert news[0]["symbol"] == "HPG"

    events = scanner.get_company_events("HPG")
    assert len(events) >= 1
    assert events[0]["symbol"] == "HPG"

    income_stmt = scanner.get_income_statement("HPG")
    assert len(income_stmt) == 4
    assert income_stmt[0]["revenue_billion"] > 0
