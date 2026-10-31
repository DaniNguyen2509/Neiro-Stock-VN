"""Unit tests cho module Fialda VIP Expert Scanner."""
from unittest.mock import MagicMock, patch
from src.collector.fialda_scanner import FialdaScanner, FialdaCandidate, format_top_5_report


def test_fialda_candidate_dataclass():
    """Kiem tra khoi tao ung vien FialdaCandidate."""
    candidate = FialdaCandidate(
        symbol="DBC",
        price=16.4,
        signal_type="CHO_MUA_CHAN_SONG",
        entry_low=16.07,
        entry_high=16.42,
        stop_loss=15.19,
        target_1m=20.56,
        rs_1m=84,
        composite_rating=82,
        acc_diss_rating="A",
        rrg_r=101.7,
        rrg_m=100.8,
        foreign_net_value_billion=4.4,
        ranking_score=90.5,
        catalyst="RRG Leading, IBD Composite=82",
    )
    assert candidate.symbol == "DBC"
    assert candidate.stop_loss < candidate.price < candidate.target_1m
    assert candidate.ranking_score > 80.0


def test_fallback_mock_top_5():
    """Kiem tra che do fallback mock khi offline luon tra ve dung 5 ma."""
    top5 = FialdaScanner._fallback_mock_top_5()
    assert len(top5) == 5
    for c in top5:
        assert len(c.symbol) == 3
        assert c.target_1m > c.price
        assert c.stop_loss < c.price


def test_format_top_5_report():
    """Kiem tra ham render bao cao Top 5 ra dinh dang terminal."""
    top5 = FialdaScanner._fallback_mock_top_5()
    breadth = {
        "advances": 144,
        "declines": 156,
        "pe": 12.44,
        "totalValue": 16942000000000.0,
    }
    report = format_top_5_report(top5, breadth)
    assert "TOP 5 SIÊU CỔ PHIẾU" in report
    assert "DBC" in report
    assert "GEX" in report
    assert "16,942 ty" in report


def test_fialda_scanner_ranking_logic():
    """Kiem tra logic tinh diem va sap xep xep hang cua FialdaScanner voi mock API."""
    scanner = FialdaScanner(username="mock_user", password="mock_pwd")
    scanner.token = "mock_token"

    mock_cho_mua = {
        "DBC": {"item1": True, "item2": 16.0, "item3": 16.5},
        "ACB": {"item1": True, "item2": 20.5, "item3": 21.0},
    }
    mock_dot_bien = ["GEX", "CTS"]
    mock_rrg = {
        "DBC": {"r": 103.5, "m": 102.1},
        "ACB": {"r": 101.0, "m": 101.5},
        "GEX": {"r": 102.0, "m": 103.0},
        "CTS": {"r": 104.0, "m": 104.5},
    }
    mock_top_symbols = [
        {"symbol": "DBC", "currentPrice": 16.3, "totalValue": 65e9, "totalForeignerNetBuyValue": 15e9},
        {"symbol": "ACB", "currentPrice": 21.0, "totalValue": 120e9, "totalForeignerNetBuyValue": -5e9},
        {"symbol": "GEX", "currentPrice": 24.5, "totalValue": 95e9, "totalForeignerNetBuyValue": 20e9},
        {"symbol": "CTS", "currentPrice": 38.0, "totalValue": 48e9, "totalForeignerNetBuyValue": 10e9},
    ]

    with patch.object(scanner, "get_expert_buy_signals", return_value=mock_cho_mua), \
         patch.object(scanner, "get_expert_value_surge", return_value=mock_dot_bien), \
         patch.object(scanner, "get_rrg_data", return_value=mock_rrg), \
         patch.object(scanner, "get_market_top_symbols", return_value=mock_top_symbols), \
         patch.object(scanner, "get_stock_infos", return_value={}), \
         patch.object(scanner, "get_recent_ohlcv_batch", return_value={}), \
         patch.object(scanner, "get_expert_rating", return_value={"rS1M": 85, "compositeRating": 88, "accDissRating": "A"}):

        result = scanner.scan_top_5_rockets(record_history=False)
        assert len(result) == 4
        # DBC va ACB phai co tin hieu CHO_MUA_CHAN_SONG
        dbc_item = next(x for x in result if x.symbol == "DBC")
        assert dbc_item.signal_type == "CHO_MUA_CHAN_SONG"
        assert dbc_item.ranking_score > 85.0


def test_format_top_5_markdown():
    """Kiem tra ham format_top_5_markdown sinh chuan GitHub Flavored Markdown."""
    from src.collector.fialda_scanner import format_top_5_markdown
    top5 = FialdaScanner._fallback_mock_top_5()
    breadth = {
        "advances": 144,
        "declines": 156,
        "pe": 12.44,
        "totalValue": 16942000000000.0,
    }
    md = format_top_5_markdown(top5, breadth)
    assert "## 🚀 NEIRO-STOCK-VN" in md
    assert "| STT | Mã CP | Tín Hiệu AI" in md
    assert "**DBC**" in md
    assert "16,942 tỷ VND" in md


def test_get_fundamental_screener_data_fallback():
    """Kiem tra fallback co ban khi offline."""
    data = FialdaScanner._fallback_mock_fundamental()
    assert len(data) >= 5
    hpg = next(x for x in data if x["symbol"] == "HPG")
    assert hpg["price"] > 0
    assert hpg["f_score"] == 9.0
    assert hpg["pe"] == 8.5
    assert hpg["is_institutional"] is True


def test_candidates_trailing_stop_enrichment():
    """Kiem tra candidates duoc enrich day du SL, TP1, TP2, R:R va Delta Rank."""
    top = FialdaScanner._fallback_mock_top_5()
    for c in top:
        assert c.tp1 > c.price
        assert c.tp2 > c.tp1
        assert c.stop_loss < c.price
        assert c.rr_ratio >= 2.4
        assert c.rank_change_badge != ""
        assert "T+0" in c.t25_status_badge


def test_classify_dual_flow_matrix():
    """Kiem tra phan loai Ma Tran Dong Tien Kep trung thuc (khong bia so Tu doanh)."""
    from src.collector.fialda_scanner import classify_dual_flow

    # 1. SIEU_SONG: Ngoai mua + tich luy A/B hoac Tu doanh mua that
    reg1, badge1, prop1 = classify_dual_flow(
        foreign_net_val=15.0, acc_diss="A", signal_type="CHO_MUA_CHAN_SONG", rrg_r=102, rrg_m=101,
        prop_net_actual_billion=12.0,
    )
    assert reg1 == "SIEU_SONG"
    assert "ĐỒNG THUẬN" in badge1
    assert prop1 == 12.0

    # 2. NOI_CAN_HANG: Ngoai ban nhung tich luy hang A/B giu nen chat (khong bia so prop khi chua cong bo)
    reg2, badge2, prop2 = classify_dual_flow(
        foreign_net_val=-8.5, acc_diss="A", signal_type="CHO_MUA_CHAN_SONG", rrg_r=101, rrg_m=102,
        ibd_composite=82, close_position_in_range=0.80,
    )
    assert reg2 == "NOI_CAN_HANG"
    assert "NỘI GOM" in badge2
    assert prop2 == 0.0

    # 3. NGOAI_DO_GIA: Ngoai mua nhung Noi chua day (Acc/Diss = D)
    reg3, badge3, prop3 = classify_dual_flow(
        foreign_net_val=2.5, acc_diss="D", signal_type="THE_CHE_GOM", rrg_r=98, rrg_m=97
    )
    assert reg3 == "NGOAI_DO_GIA"
    assert "NGOẠI ĐỠ" in badge3

    # 4. RUI_RO_XA: Ngoai xa kem phan phoi hang E -> Bat buoc canh bao xa (khong bao gio gan NOI_CAN_HANG)
    reg4, badge4, prop4 = classify_dual_flow(
        foreign_net_val=-12.0, acc_diss="E", signal_type="DOT_BIEN_GIA_TRI", rrg_r=101, rrg_m=101
    )
    assert reg4 == "RUI_RO_XA"
    assert "NGUY HIỂM" in badge4
    assert prop4 == 0.0


def test_dual_flow_integrity_vic_241b_selloff_triggers_rui_ro_xa():
    """BM-03 Scorecard: VIC (-241.7 ty ngoai xa, Acc/Diss=E, IBD=39) tuyet doi khong sinh +362.5 ty gia dinh."""
    from src.collector.fialda_scanner import classify_dual_flow

    regime, badge, prop_verified = classify_dual_flow(
        foreign_net_val=-241.7,
        acc_diss="E",
        signal_type="DOT_BIEN_GIA_TRI",
        rrg_r=96.0,
        rrg_m=95.0,
        prop_net_actual_billion=None,
        ibd_composite=39,
    )
    assert regime == "RUI_RO_XA"
    assert "NGUY HIỂM" in badge
    assert prop_verified == 0.0


def test_anti_climax_blocks_grade_e_distribution_and_poc_overextension():
    """BM-02 Scorecard: Chan 100% ma phan phoi Acc/Diss=E (VIC) va ma keo qua xa POC > 2.5*ATR khoi Mua moi."""
    scanner = FialdaScanner(username="u", password="p")
    scanner.token = "mock_tok"

    mock_cho_mua = {"HPG": {"item1": True, "item2": 21.8, "item3": 22.3}}
    mock_dot_bien = ["VIC", "CLX"]
    mock_rrg = {
        "VIC": {"r": 95.0, "m": 93.0},
        "CLX": {"r": 106.0, "m": 103.0},
        "HPG": {"r": 103.0, "m": 102.0},
    }
    mock_infos = {
        "VIC": {"PriceInfo": {"currentPrice": 239.70, "totalVal": 300e9}, "ForeignTrade": {"totalForeignNetValue": -241.7e9}},
        "CLX": {"PriceInfo": {"currentPrice": 35.00, "totalVal": 55e9}, "ForeignTrade": {"totalForeignNetValue": 4.0e9}},
        "HPG": {"PriceInfo": {"currentPrice": 22.20, "totalVal": 420e9}, "ForeignTrade": {"totalForeignNetValue": 32.0e9}},
    }
    mock_ohlcv = {
        "VIC": {"c": [238.0] * 20, "h": [241.0] * 20, "l": [235.0] * 20, "v": [1_500_000] * 20},
        "CLX": {"c": [25.0] * 18 + [31.0, 35.0], "h": [25.5] * 18 + [31.5, 35.4], "l": [24.6] * 18 + [30.2, 33.8], "v": [2_000_000] * 20},
        "HPG": {"c": [21.6] * 19 + [22.2], "h": [22.0] * 19 + [22.4], "l": [21.3] * 19 + [21.8], "v": [18_000_000] * 20},
    }
    ratings = {
        "VIC": {"rS1M": 6, "compositeRating": 39, "accDissRating": "E"},
        "CLX": {"rS1M": 91, "compositeRating": 82, "accDissRating": "B"},
        "HPG": {"rS1M": 84, "compositeRating": 86, "accDissRating": "A"},
    }

    with patch.object(scanner, "get_expert_buy_signals", return_value=mock_cho_mua), \
         patch.object(scanner, "get_expert_value_surge", return_value=mock_dot_bien), \
         patch.object(scanner, "get_rrg_data", return_value=mock_rrg), \
         patch.object(scanner, "get_market_top_symbols", return_value=[]), \
         patch.object(scanner, "get_stock_infos", return_value=mock_infos), \
         patch.object(scanner, "get_recent_ohlcv_batch", return_value=mock_ohlcv), \
         patch.object(scanner, "get_market_breadth", return_value={"advances": 205, "declines": 120, "totalValue": 18000e9}), \
         patch.object(scanner, "get_live_basis_points", return_value=1.5), \
         patch.object(scanner, "get_expert_rating", side_effect=lambda s: ratings[s]):
        res = scanner.scan_top_rockets(top_n=10, record_history=False)

    res_map = {c.symbol: c for c in res}
    assert "VIC" not in res_map
    assert "CLX" not in res_map
    assert "HPG" in res_map




