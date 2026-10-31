"""Module Quản Trị Rủi Ro Động & Điểm Thoát Lệnh T+2.5 (Dynamic Trailing Stop & Risk-Reward Optimizer).

Được thiết kế chuyên biệt cho Nhà Đầu Tư Cổ Phiếu Cơ Sở (Spot Equities Long-Only):
1. Tính toán ngưỡng Cắt Lỗ Cứng ban đầu (Initial Stop Loss) dựa trên Swing Low và ATR(14).
2. Cơ chế Khóa Lợi Nhuận Tự Động (Chandelier Exit & Break-Even Ratchet):
   - Khi giá tăng vượt mốc 1.5R: Tự động nâng Stop Loss lên điểm Hòa Vốn (Break-even).
   - Khi giá tiếp tục bứt phá: Chandelier Trailing Stop bám sát theo biên độ biến động (Ratchet Property: chỉ tăng, không giảm).
3. Đạt Tỷ Lệ Vàng Risk/Reward >= 1:2.5 (Mục tiêu TP1 = 1.5R chốt 50%, TP2 = 2.5R - 3.0R gồng lãi).
4. Quản trị "Vùng Đóng Băng T+0 đến T+2":
   - Đánh giá mức độ phơi nhiễm và đưa ra cảnh báo Radar giao thông (Xanh / Vàng / Đỏ).
   - Khuyến nghị điều tiết tỷ trọng tiền mặt, đệm hàng sẵn có T+0 (Rolling Inventory Cushion),
     và tạm dừng mở mua mới khi thị trường chung xuất hiện rủi ro sập gãy.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class TrailingStopState:
    """Trạng thái Quản trị Rủi ro Động cho một vị thế cổ phiếu cơ sở."""

    symbol: str
    entry_price: float
    initial_stop: float
    current_stop: float
    highest_price: float
    atr_14: float
    r_unit: float
    tp1_price: float
    tp2_price: float
    rr_ratio: float
    is_breakeven_activated: bool = False
    trailing_activated: bool = False
    status: str = "ACTIVE"  # 'ACTIVE', 'STOPPED_OUT', 'TAKE_PROFIT_1', 'TAKE_PROFIT_2'


@dataclass
class T25ExposureReport:
    """Báo cáo Đánh giá Phơi nhiễm Vùng Đóng Băng T+2.5 cho Nhà đầu tư Cổ phiếu."""

    symbol: str
    shares: int
    t_stage: str  # 'T+0', 'T+1', 'T+2_MORNING', 'T+2_AFTERNOON', 'T+3_AVAILABLE'
    is_frozen: bool  # True nếu hàng chưa về, không thể bấm nút bán cắt lỗ cơ sở
    basis_points: float  # Độ lệch Basis VN30F1M - VN30
    exposure_level: str  # 'SAFE', 'MODERATE', 'HIGH', 'CRITICAL'
    pause_new_buying: bool  # Khuyến nghị tạm dừng mở mua mới cổ phiếu
    recommended_cash_pct: float  # Tỷ lệ tiền mặt tối thiểu nên duy trì
    action_message: str  # Thông điệp hành động thực chiến


def calculate_initial_stop_loss(
    entry_price: float,
    swing_low: Optional[float] = None,
    atr_14: Optional[float] = None,
    atr_multiplier: float = 1.5,
    min_risk_pct: float = 0.03,
    max_risk_pct: float = 0.07,
) -> float:
    """Tính toán ngưỡng Cắt Lỗ Cứng Ban Đầu (Initial Stop Loss) cho cổ phiếu cơ sở.

    Kết hợp giữa vùng hỗ trợ đáy nến gần nhất (Swing Low) và biên độ biến động ATR(14),
    khống chế biên độ rủi ro trong khoảng an toàn (mặc định 3% đến 7% theo biên độ sàn HOSE).

    Args:
        entry_price: Giá mua khớp lệnh của cổ phiếu.
        swing_low: Đáy nến gần nhất (ngưỡng hỗ trợ kỹ thuật), nếu có.
        atr_14: Giá trị độ biến động trung bình 14 phiên ATR(14).
        atr_multiplier: Hệ số nhân ATR (mặc định 1.5).
        min_risk_pct: Mức cắt lỗ tối thiểu (3%) tránh bị quét râu nến nhiễu.
        max_risk_pct: Mức cắt lỗ tối đa (7%) bảo vệ tài khoản khỏi giảm sàn.

    Returns:
        Ngưỡng giá cắt lỗ an toàn ban đầu (được làm tròn 2 chữ số thập phân).
    """
    if entry_price <= 0:
        raise ValueError("entry_price phải lớn hơn 0")

    # Nếu không truyền atr_14, mặc định lấy 3.5% thị giá
    effective_atr = atr_14 if (atr_14 is not None and atr_14 > 0) else entry_price * 0.035
    atr_stop = entry_price - (effective_atr * atr_multiplier)

    # Ưu tiên kết hợp Swing Low nếu hợp lệ (nằm dưới entry_price)
    if swing_low is not None and 0 < swing_low < entry_price:
        # Chọn ngưỡng stop loss chặt chẽ hơn giữa swing_low và atr_stop
        # nhưng vẫn tạo đủ không gian dao động
        chosen_stop = max(swing_low, atr_stop)
    else:
        chosen_stop = atr_stop

    # Khống chế giới hạn biên độ rủi ro [min_risk_pct, max_risk_pct]
    hard_lower_limit = entry_price * (1.0 - max_risk_pct)
    hard_upper_limit = entry_price * (1.0 - min_risk_pct)

    final_stop = max(hard_lower_limit, min(chosen_stop, hard_upper_limit))
    return round(final_stop, 2)


def calculate_t25_structural_stop_loss(
    entry_price: float,
    atr_14: Optional[float] = None,
    structural_support: Optional[float] = None,
    min_risk_pct: float = 0.045,
    max_risk_pct: float = 0.075,
) -> float:
    """Tính toán ngưỡng Cắt Lỗ Cấu Trúc Sinh Tồn qua chu kỳ T+2.5 (4.5% đến 7.5%).

    Khắc phục điểm mù kẹp cứng SL -3.0% (BM-05):
    - Nhân biên độ biến động 14 phiên với căn bậc hai thời gian đóng băng T+2.5 (~1.581 * ATR_14).
    - Đặt dưới hỗ trợ cấu trúc Volume Profile VAL / Swing Low 10 phiên một khoảng đệm 0.35 * ATR_14
      để tránh bị quét râu nến rũ bỏ (stop-hunt) khi hàng chưa về tài khoản.
    """
    if entry_price <= 0:
        raise ValueError("entry_price phải lớn hơn 0")

    effective_atr = atr_14 if (atr_14 is not None and atr_14 > 0) else entry_price * 0.035
    # Căn bậc hai của 2.5 phiên đóng băng: sqrt(2.5) ~ 1.5811
    atr_stop = entry_price - (1.5811 * effective_atr)

    if structural_support is not None and 0 < structural_support < entry_price:
        support_stop = structural_support - (0.35 * effective_atr)
        raw_stop = min(atr_stop, support_stop)
    else:
        raw_stop = atr_stop

    hard_lower_limit = entry_price * (1.0 - max_risk_pct)
    hard_upper_limit = entry_price * (1.0 - min_risk_pct)

    final_stop = max(hard_lower_limit, min(raw_stop, hard_upper_limit))
    return round(final_stop, 2)


def calculate_take_profit_levels(
    entry_price: float,
    stop_loss: float,
    tp1_r_multiple: float = 1.5,
    tp2_r_multiple: float = 2.5,
    round_trip_cost_pct: float = 0.0,
) -> Tuple[float, float, float]:
    """Tính toán các mốc Chốt Lời TP1, TP2 theo bội số đơn vị rủi ro R (Risk Unit).

    Công thức:
        R = entry_price - stop_loss
        fee_buffer = entry_price * round_trip_cost_pct (mặc định 0.0; thực chiến VN ~0.004 = 0.40%)
        TP1 = entry_price + (tp1_r_multiple * R) + fee_buffer -> Chốt lời 50% (Net >= 1.5R sau phí/thuế)
        TP2 = entry_price + (tp2_r_multiple * R) + fee_buffer -> Gồng lãi 50% còn lại với Net R:R >= 1:2.5

    Returns:
        Tuple gồm (TP1, TP2, Tỷ lệ Net R:R của TP2).
    """
    if entry_price <= stop_loss:
        raise ValueError(f"entry_price ({entry_price}) phải lớn hơn stop_loss ({stop_loss})")

    r_unit = entry_price - stop_loss
    fee_buffer = max(round_trip_cost_pct, 0.0) * entry_price
    tp1 = entry_price + (r_unit * tp1_r_multiple) + fee_buffer
    tp2 = entry_price + (r_unit * tp2_r_multiple) + fee_buffer
    net_tp2_reward = (tp2 - entry_price) - fee_buffer
    rr_ratio = round(net_tp2_reward / r_unit, 2)

    return round(tp1, 2), round(tp2, 2), rr_ratio


def initialize_trailing_stop(
    symbol: str,
    entry_price: float,
    swing_low: Optional[float] = None,
    atr_14: Optional[float] = None,
    atr_multiplier: float = 1.5,
    tp1_r_multiple: float = 1.5,
    tp2_r_multiple: float = 2.5,
) -> TrailingStopState:
    """Khởi tạo trạng thái Quản trị Rủi ro Động cho vị thế mới mở."""
    initial_stop = calculate_initial_stop_loss(
        entry_price=entry_price,
        swing_low=swing_low,
        atr_14=atr_14,
        atr_multiplier=atr_multiplier,
    )
    tp1, tp2, rr = calculate_take_profit_levels(
        entry_price=entry_price,
        stop_loss=initial_stop,
        tp1_r_multiple=tp1_r_multiple,
        tp2_r_multiple=tp2_r_multiple,
    )
    r_unit = entry_price - initial_stop
    effective_atr = atr_14 if (atr_14 is not None and atr_14 > 0) else entry_price * 0.035

    return TrailingStopState(
        symbol=symbol,
        entry_price=entry_price,
        initial_stop=initial_stop,
        current_stop=initial_stop,
        highest_price=entry_price,
        atr_14=effective_atr,
        r_unit=r_unit,
        tp1_price=tp1,
        tp2_price=tp2,
        rr_ratio=rr,
        is_breakeven_activated=False,
        trailing_activated=False,
        status="ACTIVE",
    )


def update_trailing_stop(
    state: TrailingStopState,
    current_price: float,
    chandelier_multiplier: float = 2.0,
    breakeven_r_trigger: float = 1.5,
) -> TrailingStopState:
    """Cập nhật Trailing Stop & Điểm Hòa Vốn (Break-Even) khi giá biến động.

    Quy tắc Ratchet Property cốt lõi:
    1. Cập nhật đỉnh cao nhất kể từ khi vào lệnh: highest_price = max(highest_price, current_price).
    2. Kích hoạt Hòa Vốn (Break-even): Khi giá tăng đạt >= 1.5R (hoặc 2.0R),
       Stop Loss tự động được nâng lên điểm hòa vốn (entry_price).
    3. Chandelier Exit: Khi giá tăng bứt phá, Stop Loss bám sát:
       chandelier_stop = highest_price - (chandelier_multiplier * atr_14).
    4. BẢO TOÀN TÍNH CHẤT ĐƠN ĐIỆU: new_stop = max(current_stop, chandelier_stop),
       Stop Loss TUYỆT ĐỐI KHÔNG BAO GIỜ BỊ HẠ XUỐNG.
    5. Đánh giá trạng thái vị thế (STOPPED_OUT, TAKE_PROFIT_1, TAKE_PROFIT_2, ACTIVE).
    """
    new_highest = max(state.highest_price, current_price)
    r_gain = (new_highest - state.entry_price) / state.r_unit if state.r_unit > 0 else 0.0

    new_stop = state.current_stop
    breakeven_active = state.is_breakeven_activated
    trailing_active = state.trailing_activated

    # Kích hoạt Hòa Vốn khi lợi nhuận đạt ngưỡng kích hoạt (ví dụ 1.5R)
    if r_gain >= breakeven_r_trigger:
        breakeven_active = True
        new_stop = max(new_stop, state.entry_price)

    # Chandelier Exit bám theo đỉnh cao nhất khi giá vượt 1.5R
    if r_gain >= breakeven_r_trigger:
        trailing_active = True
        chandelier_stop = new_highest - (chandelier_multiplier * state.atr_14)
        new_stop = max(new_stop, chandelier_stop)

    # Ratchet Invariant: Stop Loss không bao giờ giảm
    new_stop = round(max(state.current_stop, new_stop), 2)

    # Xác định trạng thái lệnh
    if current_price <= new_stop:
        status = "STOPPED_OUT"
    elif current_price >= state.tp2_price:
        status = "TAKE_PROFIT_2"
    elif current_price >= state.tp1_price:
        status = "TAKE_PROFIT_1"
    else:
        status = "ACTIVE"

    return TrailingStopState(
        symbol=state.symbol,
        entry_price=state.entry_price,
        initial_stop=state.initial_stop,
        current_stop=new_stop,
        highest_price=round(new_highest, 2),
        atr_14=state.atr_14,
        r_unit=state.r_unit,
        tp1_price=state.tp1_price,
        tp2_price=state.tp2_price,
        rr_ratio=state.rr_ratio,
        is_breakeven_activated=breakeven_active,
        trailing_activated=trailing_active,
        status=status,
    )


def evaluate_t25_exposure(
    symbol: str,
    shares: int,
    t_stage: str,
    basis_points: float,
    stock_beta: float = 1.0,
    market_breadth_pct: float = 70.0,
) -> T25ExposureReport:
    """Đánh giá Rủi ro Phơi nhiễm Vùng Đóng Băng T+2.5 dành riêng cho Nhà Đầu Tư Cổ Phiếu.

    Không yêu cầu Short phái sinh, mà dùng Basis VN30F1M và Độ rộng thị trường làm
    Rada Cảnh Báo Sớm để quản trị tỷ trọng tiền mặt, tạm dừng mở mua mới, và bảo vệ đệm hàng.

    Args:
        symbol: Mã cổ phiếu cơ sở.
        shares: Khối lượng cổ phiếu nắm giữ.
        t_stage: Giai đoạn thanh toán ('T+0', 'T+1', 'T+2_MORNING', 'T+2_AFTERNOON', 'T+3_AVAILABLE').
        basis_points: Độ lệch Basis VN30F1M - VN30 (điểm).
        stock_beta: Hệ số Beta của cổ phiếu so với VN30.
        market_breadth_pct: % Cổ phiếu giữ xu hướng trên MA20.

    Returns:
        T25ExposureReport với phân loại rủi ro và khuyến nghị hành động cụ thể.
    """
    frozen_stages = {"T+0", "T+1", "T+2_MORNING"}
    is_frozen = t_stage.upper() in frozen_stages

    # Đánh giá cấp độ rủi ro dựa trên Basis và độ rộng thị trường khi hàng đang đóng băng
    if is_frozen:
        if (
            market_breadth_pct < 35.0
            or basis_points < -12.0
            or (basis_points < -8.0 and market_breadth_pct < 45.0)
        ):
            exposure_level = "CRITICAL"
            pause_new_buying = True
            cash_pct = 70.0
            action_msg = (
                f"🚨 CẢNH BÁO ĐÓNG BĂNG CAO ĐIỂM ({t_stage}): Cầu chì T+2.5 kích hoạt "
                f"(Độ rộng {market_breadth_pct:.1f}%, Basis {basis_points:+.1f}đ). "
                f"Tuyệt đối KHÔNG mở mua mới! Hạ tỷ trọng hàng khả dụng, nâng tiền mặt >= 70%."
            )
        elif basis_points < -6.0 or market_breadth_pct < 50.0:
            exposure_level = "HIGH"
            pause_new_buying = True
            cash_pct = 50.0
            action_msg = (
                f"⚠️ PHƠI NHIỄM CAO ({t_stage}): Basis am {basis_points:+.1f}d cho thấy Big Boy phòng thủ. "
                f"Tạm dừng mở mua mới, chờ hàng về chiều T+2 mới xử lý."
            )
        elif basis_points < 0.0:
            exposure_level = "MODERATE"
            pause_new_buying = False
            cash_pct = 35.0
            action_msg = (
                f"🟡 PHƠI NHIỄM VỪA PHẢI ({t_stage}): Thị trường rung lắc nhẹ (Basis {basis_points:+.1f}d). "
                f"Chỉ giải ngân đợt 1 tối đa 50% vị thế tại vùng gom an toàn."
            )
        else:
            exposure_level = "SAFE"
            pause_new_buying = False
            cash_pct = 20.0
            action_msg = (
                f"🟢 VÙNG MUA AN TOÀN ({t_stage}): Basis duong {basis_points:+.1f}d, thị trường giữ xu hướng tốt. "
                f"Vị thế vận hành ổn định trong chu kỳ T+2.5."
            )
    else:
        # Hàng đã về tài khoản (chiều T+2 trở đi) -> Có thể bán bất kỳ lúc nào
        exposure_level = "SAFE"
        pause_new_buying = False
        cash_pct = 20.0
        action_msg = (
            f"✅ HÀNG ĐÃ VỀ KHẢ DỤNG ({t_stage}): Vị thế có thể cắt lỗ hoặc chốt lời chủ động bất kỳ lúc nào."
        )

    return T25ExposureReport(
        symbol=symbol,
        shares=shares,
        t_stage=t_stage,
        is_frozen=is_frozen,
        basis_points=basis_points,
        exposure_level=exposure_level,
        pause_new_buying=pause_new_buying,
        recommended_cash_pct=cash_pct,
        action_message=action_msg,
    )
