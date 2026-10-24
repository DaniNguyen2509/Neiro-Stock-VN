"""Client giao tiep du lieu thi truong chung khoan Viet Nam."""
from typing import Dict, Any, List


class VNMarketClient:
    """Client lay du lieu gia co so, phai sinh VN30F1M va dong tien khoi ngoai."""

    def __init__(self, use_mock: bool = True):
        self.use_mock = use_mock

    def get_spot_and_derivatives_prices(self) -> Dict[str, float]:
        """Lay gia giao ngay VN30 Index va gia hop dong tuong lai VN30F1M."""
        if self.use_mock:
            return {
                "VN30_INDEX": 1315.50,
                "VN30F1M": 1312.20,      # Basis = -3.3 diem (Backwardation nhe)
                "VNINDEX": 1285.80,
            }
        raise NotImplementedError("Live API integration will be implemented in Phase 2.")

    def get_institutional_flow(self) -> Dict[str, float]:
        """Lay gia tri mua ban rong cua Khoi ngoai va Tu doanh trong phien (ty VND)."""
        if self.use_mock:
            return {
                "FOREIGN_NET_VALUE_BILLION": 285.5,   # Khong ngoai mua rong +285.5 ty
                "PROP_NET_VALUE_BILLION": 142.0,      # Tu doanh mua rong +142 ty
                "TOTAL_MARKET_TURNOVER_BILLION": 18500.0,
            }
        raise NotImplementedError("Live API integration will be implemented in Phase 2.")
