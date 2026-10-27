"""Kiem thu don vi cho GoogleSheetsLedgerClient."""

from unittest.mock import MagicMock, patch
import pytest
import requests

from src.collector.google_sheets_client import GoogleSheetsLedgerClient


def test_google_sheets_client_configuration():
    """Kiem tra logic nhan dien cau hinh webhook."""
    # Chua cau hinh
    client_empty = GoogleSheetsLedgerClient(webhook_url="")
    assert not client_empty.is_configured

    # Cau hinh sai (khong phai http)
    client_invalid = GoogleSheetsLedgerClient(webhook_url="invalid_url")
    assert not client_invalid.is_configured

    # Cau hinh dung
    client_valid = GoogleSheetsLedgerClient(
        webhook_url="https://script.google.com/macros/s/AKfycbxTest/exec"
    )
    assert client_valid.is_configured


def test_format_signal_dict():
    """Kiem tra format du lieu tin hieu thanh dictionary chuan."""
    client = GoogleSheetsLedgerClient()

    sample_dict = {
        "symbol": "HPG",
        "first_signal_date": "2026-10-27 09:30:00",
        "entry_original": 20.9,
        "current_price": 21.5,
    }
    formatted = client.format_signal_dict(sample_dict)
    assert formatted["symbol"] == "HPG"
    assert formatted["signal_id"] == "HPG_20261027_093000"


@patch("src.collector.google_sheets_client.requests.post")
def test_sync_signals_success(mock_post):
    """Kiem tra dong bo thanh cong voi HTTP 200."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "OK"
    mock_post.return_value = mock_resp

    client = GoogleSheetsLedgerClient(
        webhook_url="https://script.google.com/macros/s/AKfycbxTest/exec"
    )
    signals = [
        {"symbol": "HPG", "entry_original": 20.9, "current_price": 21.5},
        {"symbol": "SSI", "entry_original": 19.8, "current_price": 20.2},
    ]

    result = client.sync_signals(signals)
    assert result is True
    assert mock_post.called
    args, kwargs = mock_post.call_args
    assert kwargs["json"]["action"] == "upsert_signals"
    assert kwargs["json"]["count"] == 2
    assert len(kwargs["json"]["records"]) == 2


@patch("src.collector.google_sheets_client.requests.post")
def test_sync_signals_http_error(mock_post):
    """Kiem tra khi server tra ve HTTP 500 loi."""
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error"
    mock_post.return_value = mock_resp

    client = GoogleSheetsLedgerClient(
        webhook_url="https://script.google.com/macros/s/AKfycbxTest/exec"
    )
    result = client.sync_signals([{"symbol": "HPG"}])
    assert result is False


@patch("src.collector.google_sheets_client.requests.post")
def test_sync_signals_network_exception_safe(mock_post):
    """Kiem tra bat ngoai le mang an toan, khong lam crash he thong."""
    mock_post.side_effect = requests.exceptions.Timeout("Connection timed out")

    client = GoogleSheetsLedgerClient(
        webhook_url="https://script.google.com/macros/s/AKfycbxTest/exec"
    )
    result = client.sync_signals([{"symbol": "HPG"}])
    assert result is False


def test_sync_signals_unconfigured_safe():
    """Kiem tra che do offline an toan khi chua cau hinh URL."""
    client = GoogleSheetsLedgerClient(webhook_url="")
    assert client.sync_signals([{"symbol": "HPG"}]) is False
    assert client.sync_signals([]) is False
