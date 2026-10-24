"""Quan ly dem hang san co T+0 (Rolling Inventory) va bo dem Margin."""
from dataclasses import dataclass


@dataclass
class RollingInventory:
    symbol: str
    available_t0_shares: int    # Hang da ve tai khoan, co the ban ngay lap tuc
    pending_t1_shares: int      # Hang mua phien hom qua, chieu nay ve
    pending_t2_shares: int      # Hang vua mua hom nay (T+0)
    
    @property
    def total_shares(self) -> int:
        return self.available_t0_shares + self.pending_t1_shares + self.pending_t2_shares

    @property
    def t0_cushion_ratio(self) -> float:
        """Ty le dem hang co the xoa bo rui ro keo sap trong phien."""
        if self.total_shares == 0:
            return 0.0
        return round(self.available_t0_shares / self.total_shares, 2)


def can_safely_scale_up(inventory: RollingInventory, additional_shares: int) -> bool:
    """Chi cho phep gia tang ty trong lon neu tai khoan da co san >= 40% hang T+0."""
    new_total = inventory.total_shares + additional_shares
    if new_total <= 0:
        return True
    cushion = inventory.available_t0_shares / new_total
    return cushion >= 0.35
