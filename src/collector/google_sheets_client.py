"""Module Dong Bo So Cai Tin Hieu & Du Lieu ML Len Google Sheets qua Webhook.

Thiet ke toi gian (Zero-Waste, < 150 dong code), khong su dung dependency ngoai nang ne.
Hoat dong qua Google Apps Script Webhook de cap nhat truc tiep len Google Sheets
lam database truc tuyen phuc vu Google Looker Studio va huan luyen Machine Learning.
"""

import logging
import os
from typing import Any, Dict, List, Optional
import requests

logger = logging.getLogger(__name__)


class GoogleSheetsLedgerClient:
    """Client dong bo nhat ky tin hieu sang Google Sheets qua Apps Script Webhook."""

    TIMEOUT = (3.05, 10.0)  # (connect_timeout, read_timeout)

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv("GOOGLE_SHEET_WEBHOOK_URL", "").strip()

    @property
    def is_configured(self) -> bool:
        """Kiem tra xem Webhook URL da duoc thiet lap hay chua."""
        return bool(self.webhook_url and self.webhook_url.startswith("http"))

    def format_signal_dict(self, sig: Any) -> Dict[str, Any]:
        """Chuan hoa mot tin hieu ActiveSignal thanh dictionary phuc vu gui Google Sheets."""
        if hasattr(sig, "__dataclass_fields__"):
            # Dataclass instance
            from dataclasses import asdict
            data = asdict(sig)
        elif isinstance(sig, dict):
            data = dict(sig)
        else:
            data = {
                "symbol": getattr(sig, "symbol", ""),
                "current_price": getattr(sig, "current_price", 0.0),
            }

        # Tao signal_id dinh danh duy nhat neu chua co
        sym = data.get("symbol", "")
        fdate = data.get("first_signal_date", "").replace(":", "").replace("-", "").replace(" ", "_")
        if not data.get("signal_id"):
            data["signal_id"] = f"{sym}_{fdate}" if fdate else sym

        return data

    def sync_signals(self, signals: List[Any]) -> bool:
        """Gui danh sach tin hieu len Google Sheets qua HTTP POST.
        
        Args:
            signals: Danh sach cac ActiveSignal hoac dict tin hieu.
            
        Returns:
            bool: True neu gui thanh cong (HTTP 200), False neu loi hoac chua cau hinh.
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
