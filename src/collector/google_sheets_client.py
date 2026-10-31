"""Module Đồng Bộ Sổ Cái Tín Hiệu & Dữ Liệu ML Lên Google Sheets qua Webhook.

Thiết kế tối giản (Zero-Waste, < 150 dòng code), không sử dụng dependency ngoài nặng nề.
Hoạt động qua Google Apps Script Webhook để cập nhật trực tiếp lên Google Sheets
làm database trực tuyến phục vụ Google Looker Studio và huấn luyện Machine Learning.
"""

import logging
import os
from typing import Any, Dict, List, Optional
import requests

logger = logging.getLogger(__name__)


class GoogleSheetsLedgerClient:
    """Client đồng bộ nhật ký tín hiệu sang Google Sheets qua Apps Script Webhook."""

    TIMEOUT = (3.05, 10.0)  # (connect_timeout, read_timeout)

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv("GOOGLE_SHEET_WEBHOOK_URL", "").strip()

    @property
    def is_configured(self) -> bool:
        """Kiểm tra xem Webhook URL đã được thiết lập hay chưa."""
        return bool(self.webhook_url and self.webhook_url.startswith("http"))

    def format_signal_dict(self, sig: Any) -> Dict[str, Any]:
        """Chuẩn hóa một tín hiệu ActiveSignal thành dictionary phục vụ gửi Google Sheets."""
        if hasattr(sig, "__dataclass_fields__"):
            from dataclasses import asdict

            data = asdict(sig)
        elif isinstance(sig, dict):
            data = dict(sig)
        else:
            data = {
                "symbol": getattr(sig, "symbol", ""),
                "current_price": getattr(sig, "current_price", 0.0),
            }

        # Tạo signal_id định danh duy nhất nếu chưa có
        sym = data.get("symbol", "")
        fdate = data.get("first_signal_date", "").replace(":", "").replace("-", "").replace(" ", "_")
        if not data.get("signal_id"):
            data["signal_id"] = f"{sym}_{fdate}" if fdate else sym

        return data

    def sync_signals(self, signals: List[Any]) -> bool:
        """Gửi danh sách tín hiệu lên Google Sheets qua HTTP POST.

        Args:
            signals: Danh sách các ActiveSignal hoặc dict tín hiệu.

        Returns:
            bool: True nếu gửi thành công (HTTP 200 JSON/Text hợp lệ), False nếu lỗi, bị chặn login HTML hoặc chưa cấu hình.
        """
        if not self.is_configured:
            logger.info("Google Sheets Webhook URL chua duoc cau hinh. Bo qua dong bo online.")
            return False

        if not signals:
            logger.info("Danh sach tin hieu rong, khong can dong bo.")
            return True

        formatted_records = [self.format_signal_dict(s) for s in signals]
        payload = {
            "action": "upsert_signals",
            "source": "Neiro-Stock-VN",
            "count": len(formatted_records),
            "records": formatted_records,
        }

        try:
            headers = {"Content-Type": "application/json"}
            resp = requests.post(
                self.webhook_url,
                json=payload,
                headers=headers,
                timeout=self.TIMEOUT,
            )
            if 200 <= resp.status_code < 300:
                raw_url = getattr(resp, "url", "")
                resp_url = raw_url.lower() if isinstance(raw_url, str) else ""
                raw_text = getattr(resp, "text", "")
                body_head = raw_text.lstrip()[:64].lower() if isinstance(raw_text, str) else ""
                if "accounts.google.com" in resp_url or body_head.startswith(("<!doctype html", "<html")):
                    logger.warning(
                        "Dong bo Google Sheets bi chan boi trang dang nhap HTML (kiem tra quyen 'Anyone' tren Apps Script)."
                    )
                    return False
                logger.info(f"Dong bo thanh cong {len(formatted_records)} tin hieu len Google Sheets.")
                return True
            else:
                logger.warning(
                    f"Dong bo Google Sheets that bai voi HTTP {resp.status_code}: {resp.text[:200]}"
                )
                return False
        except Exception as e:
            logger.warning(f"Loi ket noi khi dong bo Google Sheets: {e}")
            return False
