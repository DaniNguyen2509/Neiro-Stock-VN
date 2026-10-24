"""Kiểm thử ATR Position Sizing, Rolling Inventory và RRG Quadrants."""
from src.risk_engine.position_sizer import calculate_atr_position_size
from src.risk_engine.t25_manager import RollingInventory, can_safely_scale_up
from src.sector_engine.rrg_rotation import compute_rrg_quadrant, calculate_rrg_series


def test_atr_position_sizing_lot_100():
    """Kiểm tra quy mô giải ngân làm tròn đúng lô 100 theo chuẩn sàn HOSE."""
    res = calculate_atr_position_size(
        equity_vnd=100_000_000.0,
        current_price=28500.0,
        atr_vnd=1200.0,
        risk_pct=1.5,
        atr_multiplier=1.5
    )
    assert res.target_shares % 100 == 0
    assert res.stop_loss_price < 28500.0
    assert res.max_risk_vnd == 1_500_000.0


def test_rolling_inventory_cushion():
    """Kiểm tra đệm an toàn hàng sẵn có T+0 trước khi cho phép gia tăng tỷ trọng."""
    # Tài khoản có sẵn 5,000 cp T+0, đang chờ 1,000 cp T+1 -> Tỷ lệ đệm 5000/6000 = 83%
    inv = RollingInventory(symbol="HPG", available_t0_shares=5000, pending_t1_shares=1000, pending_t2_shares=0)
    assert inv.t0_cushion_ratio > 0.80
    assert can_safely_scale_up(inv, additional_shares=2000) is True


def test_rrg_quadrants():
    """Kiểm tra 4 góc phần tư mô hình Relative Rotation Graph."""
    assert compute_rrg_quadrant(105.0, 102.0) == "LEADING"
    assert compute_rrg_quadrant(103.0, 97.0) == "WEAKENING"
    assert compute_rrg_quadrant(95.0, 94.0) == "LAGGING"
    assert compute_rrg_quadrant(96.0, 104.0) == "IMPROVING"
