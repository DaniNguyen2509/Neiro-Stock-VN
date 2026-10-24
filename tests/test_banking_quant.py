"""Kiem thu dinh luong khung CAMEL & Basel II/III danh rieng cho ngan hang thuong mai."""
import pytest
from src.fundamental_engine.banking_quant import (
    BankCamelMetrics,
    BankCamelScore,
    calculate_bank_camel_score,
    screen_banks_camel,
    get_benchmark_vn_banks,
)


def test_bank_camel_score_tier_a():
    """Kiem tra ngan hang hang A (tinh hoa): VCB, MBB dat diem tren 80."""
    vcb_metrics = BankCamelMetrics(
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
    )
    score = calculate_bank_camel_score(vcb_metrics)
    assert score.symbol == "VCB"
    assert score.total_score >= 80.0
    assert "HẠNG A" in score.tier
    assert score.c_score > 0
    assert score.a_score > 0
    assert score.m_score > 0
    assert score.e_score > 0
    assert score.l_score > 0


def test_bank_camel_score_tier_b():
    """Kiem tra ngan hang hang B (tang truong/kha): HDBank dat tu 65 den 79 diem."""
    hdb_metrics = BankCamelMetrics(
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
    )
    score = calculate_bank_camel_score(hdb_metrics)
    assert 65.0 <= score.total_score < 80.0
    assert "HẠNG B" in score.tier


def test_bank_camel_score_tier_c_restructuring():
    """Kiem tra ngan hang hang C (tai co cau/CIR cao): Eximbank dat duoi 65 diem."""
    eib_metrics = BankCamelMetrics(
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
    )
    score = calculate_bank_camel_score(eib_metrics)
    assert score.total_score < 65.0
    assert "HẠNG C" in score.tier


def test_bank_camel_ranking_monotonicity():
    """Kiem tra bang xep hang luon sap xep giam dan theo total_score."""
    banks = get_benchmark_vn_banks()
    ranked = screen_banks_camel(banks)
    assert len(ranked) >= 5
    for i in range(len(ranked) - 1):
        assert ranked[i].total_score >= ranked[i + 1].total_score


def test_bank_camel_score_bounds_invariants():
    """Kiem tra tat ca diem thanh phan va tong diem luon nam trong khoang [0, 100]."""
    banks = get_benchmark_vn_banks()
    ranked = screen_banks_camel(banks)
    for b in ranked:
        assert 0.0 <= b.c_score <= 20.0
        assert 0.0 <= b.a_score <= 25.0
        assert 0.0 <= b.m_score <= 15.0
        assert 0.0 <= b.e_score <= 25.0
        assert 0.0 <= b.l_score <= 15.0
        assert 0.0 <= b.total_score <= 100.0
