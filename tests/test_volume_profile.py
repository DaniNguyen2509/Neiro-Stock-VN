"""Kiểm thử thuật toán Volume Profile POC, VAH, VAL, HVN, LVN."""
import pytest
from src.microstructure_engine.volume_profile import compute_volume_profile


def test_volume_profile_poc_identification():
    """Kiểm tra POC được xác định chính xác tại mức giá có Volume lớn nhất."""
    prices = [28.0, 28.5, 29.0, 28.5, 28.5, 30.0]
    volumes = [1000, 50000, 2000, 60000, 40000, 500]
    
    vp = compute_volume_profile(prices, volumes, symbol="HPG", num_bins=10)
    assert vp.poc_price == pytest.approx(28.5, abs=0.5)
    assert vp.val_price <= vp.poc_price <= vp.vah_price
    assert len(vp.bins) == 10
    assert len(vp.hvn_levels) >= 1
