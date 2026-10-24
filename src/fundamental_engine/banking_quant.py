"""Module Dinh Luong Ngan Hang Thuong Mai Theo Khung CAMEL & Basel II/III.

Ap dung rieng cho nhom Co phieu Ngan hang thuong mai tai TTCK Viet Nam,
khac phuc hoan toan gioi han khong the tinh Piotroski F-score cua nganh tai chinh.
"""
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class BankCamelMetrics:
    """Cac chi so tai chinh goc cua Ngan hang theo chuan CAMEL & Basel II/III."""
    symbol: str
    bank_name: str
    price: float
    car: float               # Capital Adequacy Ratio (Ty le an toan von TT41/Basel II, %)
    equity_multiplier: float  # Don bay tai san = Tong tai san / Von chu so huu (lan)
    npl: float               # Non-Performing Loans = Ty le no xau nhom 3,4,5 (%)
    llr: float               # Loan Loss Reserve = Ty le bao phu no xau (%)
    cir: float               # Cost to Income Ratio = Ty le chi phi / Thu nhap (%)
    casa: float              # Current Account Savings Account = Ty le tien gui khong ky han (%)
    nim: float               # Net Interest Margin = Bien lai thuan (%)
    roe: float               # Return on Equity = Loi nhuan tren von chu so huu (%)
    ldr: float               # Loan to Deposit Ratio = Ty le du no tren von huy dong (%)
    pb: float                # Price to Book
    pe: float                # Price to Earnings


@dataclass(frozen=True)
class BankCamelScore:
    """Ket qua cham diem va xep hang CAMEL cho Ngan hang thuong mai."""
    symbol: str
    bank_name: str
    price: float
    c_score: float           # Diem An toan von (Toi da 20 diem)
    a_score: float           # Diem Chat luong tai san & Du phong (Toi da 25 diem)
    m_score: float           # Diem Hieu qua quan tri chi phi CIR (Toi da 15 diem)
    e_score: float           # Diem Loi nhuan & CASA (Toi da 25 diem)
    l_score: float           # Diem Thanh khoan & Dinh gia P/B (Toi da 15 diem)
    total_score: float       # Tong diem CAMEL (Thang diem 100)
    tier: str                # Hang danh gia: HANG A (TINH HOA), HANG B (TANG TRUONG), HANG C (TAI CO CAU)
    badge: str               # Nhan the che
    metrics: BankCamelMetrics


def calculate_bank_camel_score(m: BankCamelMetrics) -> BankCamelScore:
    """Tinh toan diem so CAMEL Rating (0-100 diem) theo chuan vi cau truc ngan hang VN."""
    # 1. Tru cot C - Capital Adequacy (Toi da 20 diem)
    c = 0.0
    if m.car >= 12.0:
        c += 15.0
    elif m.car >= 10.0:
        c += 10.0
    elif m.car >= 8.0:
        c += 5.0

    if m.equity_multiplier <= 11.0:
        c += 5.0
    elif m.equity_multiplier <= 13.0:
        c += 3.0
    else:
        c += 1.0

    # 2. Tru cot A - Asset Quality & LLR (Toi da 25 diem)
    a = 0.0
    if m.npl <= 1.2:
        a += 15.0
    elif m.npl <= 1.8:
        a += 10.0
    elif m.npl <= 2.5:
        a += 5.0

    if m.llr >= 200.0:
        a += 10.0
    elif m.llr >= 150.0:
        a += 8.0
    elif m.llr >= 100.0:
        a += 5.0
    elif m.llr >= 60.0:
        a += 2.0

    # 3. Tru cot M - Management Efficiency (Toi da 15 diem)
    mgmt = 0.0
    if m.cir <= 32.0:
        mgmt += 15.0
    elif m.cir <= 36.0:
        mgmt += 10.0
    elif m.cir <= 42.0:
        mgmt += 5.0

    # 4. Tru cot E - Earnings & CASA (Toi da 25 diem)
    e = 0.0
    if m.casa >= 35.0:
        e += 10.0
    elif m.casa >= 25.0:
        e += 7.0
    elif m.casa >= 15.0:
        e += 4.0

    if m.nim >= 4.2:
        e += 8.0
    elif m.nim >= 3.5:
        e += 5.0
    elif m.nim >= 2.8:
        e += 3.0

    if m.roe >= 20.0:
        e += 7.0
    elif m.roe >= 16.0:
        e += 5.0
    elif m.roe >= 12.0:
        e += 2.0

    # 5. Tru cot L - Liquidity & Valuation (Toi da 15 diem)
    l = 0.0
    if m.ldr <= 82.0:
        l += 8.0
    elif m.ldr <= 85.0:
        l += 5.0

    if m.pb <= 1.2:
        l += 7.0
    elif m.pb <= 1.6:
        l += 5.0
    elif m.pb <= 2.2:
        l += 3.0

    total = round(c + a + mgmt + e + l, 1)

    if total >= 80.0:
        tier = "HẠNG A (TINH HOA)"
        badge = "TINH HOA ĐỊNH CHẾ"
    elif total >= 65.0:
        tier = "HẠNG B (TĂNG TRƯỞNG)"
        badge = "TĂNG TRƯỞNG TỐT"
    else:
        tier = "HẠNG C (TÁI CƠ CẤU)"
        badge = "CẦN THEO DÕI"

    return BankCamelScore(
        symbol=m.symbol,
        bank_name=m.bank_name,
        price=m.price,
        c_score=round(c, 1),
        a_score=round(a, 1),
        m_score=round(mgmt, 1),
        e_score=round(e, 1),
        l_score=round(l, 1),
        total_score=total,
        tier=tier,
        badge=badge,
        metrics=m,
    )


def screen_banks_camel(banks_metrics: List[BankCamelMetrics]) -> List[BankCamelScore]:
    """Cham diem va sap xep bang xep hang CAMEL cho danh sach ngan hang."""
    scored = [calculate_bank_camel_score(m) for m in banks_metrics]
    scored.sort(key=lambda x: x.total_score, reverse=True)
    return scored


def get_benchmark_vn_banks() -> List[BankCamelMetrics]:
    """Cung cap bo du lieu chuan hoa 10 ngan hang tieu bieu tren thi truong chung khoan VN."""
    return [
        BankCamelMetrics(
            symbol="VCB",
            bank_name="Vietcombank",
            price=56.80,
            car=12.5,
            equity_multiplier=10.2,
            npl=0.98,
            llr=230.0,
            cir=31.5,
            casa=34.2,
            nim=3.2,
            roe=21.5,
            ldr=79.5,
            pb=2.1,
            pe=12.5,
        ),
        BankCamelMetrics(
            symbol="MBB",
            bank_name="Ngân hàng Quân Đội",
            price=19.80,
            car=11.6,
            equity_multiplier=10.1,
            npl=1.42,
            llr=160.0,
            cir=29.8,
            casa=39.5,
            nim=4.6,
            roe=22.8,
            ldr=81.2,
            pb=1.6,
            pe=8.4,
        ),
        BankCamelMetrics(
            symbol="ACB",
            bank_name="Ngân hàng Á Châu",
            price=21.30,
            car=12.8,
            equity_multiplier=9.8,
            npl=1.21,
            llr=135.0,
            cir=32.0,
            casa=24.1,
            nim=4.1,
            roe=23.1,
            ldr=80.5,
            pb=1.4,
            pe=6.8,
        ),
        BankCamelMetrics(
            symbol="TCB",
            bank_name="Techcombank",
            price=24.50,
            car=14.5,
            equity_multiplier=7.2,
            npl=1.35,
            llr=110.0,
            cir=33.5,
            casa=40.2,
            nim=4.4,
            roe=16.8,
            ldr=82.0,
            pb=1.1,
            pe=7.2,
        ),
        BankCamelMetrics(
            symbol="BID",
            bank_name="BIDV",
            price=39.20,
            car=9.8,
            equity_multiplier=14.2,
            npl=1.52,
            llr=158.0,
            cir=34.2,
            casa=21.5,
            nim=2.8,
            roe=18.5,
            ldr=83.5,
            pb=1.8,
            pe=11.2,
        ),
        BankCamelMetrics(
            symbol="CTG",
            bank_name="VietinBank",
            price=28.40,
            car=10.2,
            equity_multiplier=13.8,
            npl=1.45,
            llr=165.0,
            cir=32.8,
            casa=22.8,
            nim=3.0,
            roe=17.9,
            ldr=83.0,
            pb=1.3,
            pe=8.9,
        ),
        BankCamelMetrics(
            symbol="HDB",
            bank_name="HDBank",
            price=26.70,
            car=12.6,
            equity_multiplier=9.5,
            npl=1.65,
            llr=95.0,
            cir=35.2,
            casa=14.8,
            nim=5.1,
            roe=24.2,
            ldr=78.5,
            pb=1.5,
            pe=7.5,
        ),
        BankCamelMetrics(
            symbol="VPB",
            bank_name="VPBank",
            price=19.10,
            car=14.2,
            equity_multiplier=6.8,
            npl=4.20,
            llr=52.0,
            cir=28.5,
            casa=18.2,
            nim=5.6,
            roe=12.5,
            ldr=82.5,
            pb=1.0,
            pe=11.5,
        ),
        BankCamelMetrics(
            symbol="STB",
            bank_name="Sacombank",
            price=68.50,
            car=10.1,
            equity_multiplier=11.5,
            npl=2.10,
            llr=72.0,
            cir=42.5,
            casa=19.5,
            nim=3.6,
            roe=15.2,
            ldr=84.0,
            pb=1.2,
            pe=9.8,
        ),
        BankCamelMetrics(
            symbol="EIB",
            bank_name="Eximbank",
            price=17.85,
            car=10.5,
            equity_multiplier=11.8,
            npl=2.45,
            llr=62.0,
            cir=46.2,
            casa=15.2,
            nim=2.8,
            roe=10.5,
            ldr=84.5,
            pb=1.2,
            pe=14.5,
        ),
    ]
