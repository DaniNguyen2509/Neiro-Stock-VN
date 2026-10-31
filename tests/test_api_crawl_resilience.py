"""Bộ kiểm thử hồi quy toàn diện cho tầng API & Data Crawling (ADR-018).

Bao phủ 9 lỗi thực chiến phát hiện khi kiểm định trực tiếp các API:
1. Pooled Session + Batch GetExpertAZ giảm ~85% truy vấn đơn lẻ, chống nghẽn TLS Handshake.
2. Khai thác dữ liệu Tự doanh thực tế từ Fialda Market/GetTuDoanhV2 (thay trường ảo PropTrade).
3. Phân luồng BCTC KQKD chuẩn ngành: Ngân hàng (TOI/PPOP), Chứng khoán, Bảo hiểm, Sản xuất.
4. Chặn rò rỉ lịch cổ tức giả (2026-11-15) khi online: UpcomingEvents [] -> RecentEvents -> [].
5. Lọc nhiễu tin tức relevance=0 và xử lý an toàn shortContent=None.
6. Chuẩn hóa trường DailyStatistic.avgVol20D & Failover OHLCV sang Fialda TradingView/GetOHLC.
7. Chuẩn hóa trường 'noChange' (số ít) từ GetIndexData trong parse_market_breadth_dict.
8. Loại bỏ request lỗi HTTP 400 (/ohlcs/stock?symbol=VN30F1M) và bổ sung VPS derivative fallback.
9. Sửa lỗi sai lệch đơn vị 1,000 lần (1e9 -> 1e6) cho VPS fBValue/fSValue trên Live HUD & chặn HTML login false-positive trên Google Sheets Webhook.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from src.collector.fialda_scanner import FialdaCandidate, FialdaScanner, format_top_5_markdown
from src.collector.google_sheets_client import GoogleSheetsLedgerClient
from src.collector.vn_market_client import VNMarketClient
from src.hud.terminal import generate_terminal_html
from src.sector_engine.market_breadth import parse_market_breadth_dict


def _make_json_response(payload: dict | list, status_code: int = 200, url: str = "https://v2papi.fialda.com") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.url = url
    resp.text = "OK"
    resp.json.return_value = payload
    return resp


def test_expert_az_batch_prefills_ratings_and_only_queries_missing_symbols():
    """GetExpertAZ lấy sẵn >300 mã trong 1 request; chỉ gọi GetExpertRating cho mã ngoài danh sách."""
    scanner = FialdaScanner(username="u", password="p")
    scanner.token = "eyJhbGciOiJIUzI1NiJ9.live_test.sig"

    mock_cho_mua = {
        "HPG": {"item1": True, "item2": 21.0, "item3": 21.5},
        "FRT": {"item1": True, "item2": 146.0, "item3": 149.0},
        "VGC": {"item1": True, "item2": 42.0, "item3": 43.2},
    }
    mock_infos = {
        "HPG": {"PriceInfo": {"currentPrice": 21.3, "totalVal": 320e9}, "ForeignTrade": {"totalForeignNetValue": 18e9}},
        "FRT": {"PriceInfo": {"currentPrice": 148.5, "totalVal": 140e9}, "ForeignTrade": {"totalForeignNetValue": 6.3e9}},
        "VGC": {"PriceInfo": {"currentPrice": 42.8, "totalVal": 95e9}, "ForeignTrade": {"totalForeignNetValue": 4.1e9}},
    }
    az_prefill = {
        "HPG": {"symbol": "HPG", "rS1M": 84, "compositeRating": 88, "accDissRating": "A"},
        "FRT": {"symbol": "FRT", "rS1M": 91, "compositeRating": 92, "accDissRating": "A"},
    }

    with patch.object(scanner, "get_expert_buy_signals", return_value=mock_cho_mua), \
         patch.object(scanner, "get_expert_value_surge", return_value=[]), \
         patch.object(scanner, "get_rrg_data", return_value={s: {"r": 103.0, "m": 102.0} for s in mock_cho_mua}), \
         patch.object(scanner, "get_market_top_symbols", return_value=[]), \
         patch.object(scanner, "get_stock_infos", return_value=mock_infos), \
         patch.object(scanner, "get_recent_ohlcv_batch", return_value={}), \
         patch.object(scanner, "get_market_breadth", return_value={"advances": 210, "declines": 110, "noChange": 45, "totalValue": 19000e9}), \
         patch.object(scanner, "get_live_basis_points", return_value=2.0), \
         patch.object(scanner, "get_prop_trading_map", return_value={"FRT": 8.4}), \
         patch.object(scanner, "get_expert_az_ratings", return_value=az_prefill) as mock_az, \
         patch.object(scanner, "get_expert_rating", return_value={"rS1M": 79, "compositeRating": 81, "accDissRating": "B"}) as mock_single:

        cands = scanner.scan_top_rockets(top_n=10, record_history=False)

    assert mock_az.call_count == 1
    # HPG và FRT đã có trong GetExpertAZ -> chỉ gọi đơn lẻ đúng 1 lần cho VGC!
    assert mock_single.call_count == 1
    assert mock_single.call_args[0][0] == "VGC"

    frt = next(c for c in cands if c.symbol == "FRT")
    assert frt.composite_rating == 92
    assert frt.has_actual_prop_flow is True
    assert frt.prop_net_value_billion == 8.4


def test_get_prop_trading_summary_parses_tudoanh_v2_accurately():
    """GetTuDoanhV2 bóc tách chuẩn giá trị Tự doanh toàn sàn và từng cổ phiếu (VND -> tỷ VND)."""
    scanner = FialdaScanner(username="u", password="p")
    scanner.token = "eyJhbGciOiJIUzI1NiJ9.live_test.sig"

    payload = {
        "result": {
            "indices": [
                {"indexCode": "VNINDEX", "tuDoanh_MuaRong_Total": 87_061_509_080.0},
            ],
            "stocks": [
                {"symbol": "ACB", "tuDoanh": -17_018_730_000.0, "tuDoanhVol": -812200.0},
                {"symbol": "FRT", "tuDoanh": 14_520_000_000.0, "tuDoanhVol": 98000.0},
            ],
        }
    }
    with patch.object(scanner.session, "get", return_value=_make_json_response(payload)):
        summary = scanner.get_prop_trading_summary()

    assert summary["market_net_billion"] == 87.06
    assert summary["stocks"]["ACB"] == -17.019
    assert summary["stocks"]["FRT"] == 14.52


def test_income_statement_routes_bank_security_insurance_and_general_schemas():
    """BCTC Ngân hàng (TPB/VCB), Chứng khoán (VND), Bảo hiểm (BVH) không còn trả về 0.0 tỷ doanh thu."""
    scanner = FialdaScanner(username="u", password="p")
    scanner.token = "eyJhbGciOiJIUzI1NiJ9.live_test.sig"

    # 1. Ngân hàng TPB -> gọi trực tiếp GetFS_IncomeStatement_Bank (isB38 = TOI, isB40 = PPOP)
    bank_payload = {
        "result": [
            {"quarter": 2, "year": 2026, "isB38": 5_195_200_000_000.0, "isB40": 3_210_400_000_000.0, "isA20": 1_845_000_000_000.0},
            {"quarter": 1, "year": 2026, "isB38": 4_810_000_000_000.0, "isB40": 2_950_000_000_000.0, "isA20": 1_690_000_000_000.0},
        ]
    }
    with patch.object(scanner.session, "get", return_value=_make_json_response(bank_payload)) as mock_get:
        tpb_q = scanner.get_income_statement("TPB", is_quarter=True)
        assert "GetFS_IncomeStatement_Bank" in mock_get.call_args[0][0]
        assert tpb_q[0]["revenue_billion"] == 5195.2
        assert tpb_q[0]["gross_profit_billion"] == 3210.4
        assert tpb_q[0]["net_profit_billion"] == 1845.0

    # 2. Mã ngân hàng mới chưa có trong danh sách tĩnh: General trả isA1/isA3=None -> Tự động Failover sang Bank!
    general_empty_rev = {"result": [{"quarter": 2, "year": 2026, "isA1": None, "isA3": None, "isA20": 500_000_000_000.0}]}
    with patch.object(
        scanner.session,
        "get",
        side_effect=[_make_json_response(general_empty_rev), _make_json_response(bank_payload)],
    ) as mock_chain:
        new_bank_q = scanner.get_income_statement("NEWBANK", is_quarter=True)
        assert mock_chain.call_count == 2
        assert new_bank_q[0]["revenue_billion"] == 5195.2

    # 3. Bảo hiểm BVH -> GetFS_IncomeStatement_Insurance (isI105, isI87, isA20)
    ins_payload = {
        "result": [
            {"quarter": 3, "year": 2026, "isI105": 11_420_000_000_000.0, "isI87": 1_280_000_000_000.0, "isA20": 615_000_000_000.0},
        ]
    }
    with patch.object(scanner.session, "get", return_value=_make_json_response(ins_payload)) as mock_ins:
        bvh_q = scanner.get_income_statement("BVH", is_quarter=True)
        assert "GetFS_IncomeStatement_Insurance" in mock_ins.call_args[0][0]
        assert bvh_q[0]["revenue_billion"] == 11420.0
        assert bvh_q[0]["gross_profit_billion"] == 1280.0
        assert bvh_q[0]["net_profit_billion"] == 615.0


def test_company_events_live_mode_falls_back_to_recent_events_never_fake_dividend():
    """Khi online (HTTP 200), nếu UpcomingEvents rỗng thì lấy RecentEvents; nếu vẫn rỗng phải trả [] trung thực."""
    scanner = FialdaScanner(username="u", password="p")
    scanner.token = "eyJhbGciOiJIUzI1NiJ9.live_test.sig"

    # Trường hợp 1: Upcoming rỗng [], Recent có sự kiện thật
    recent_payload = {
        "result": [
            {"eventName": "FRT: Nghị quyết HĐQT thông qua kế hoạch mở rộng chuỗi Long Châu", "publicDate": "2026-10-18T00:00:00"}
        ]
    }
    with patch.object(
        scanner.session,
        "get",
        side_effect=[_make_json_response({"result": []}), _make_json_response(recent_payload)],
    ):
        evs = scanner.get_company_events("FRT")
        assert len(evs) == 1
        assert "Long Châu" in evs[0]["event_name"]
        assert evs[0]["date"] == "2026-10-18"
        assert "2026-11-15" not in evs[0]["date"]

    # Trường hợp 2: Cả Upcoming lẫn Recent đều trả về [] trên HTTP 200 -> Trả về [] (KHÔNG bịa cổ tức 2026-11-15!)
    with patch.object(
        scanner.session,
        "get",
        side_effect=[_make_json_response({"result": []}), _make_json_response({"result": []})],
    ):
        empty_evs = scanner.get_company_events("TCH")
        assert empty_evs == []


def test_company_news_filters_zero_relevance_noise_and_handles_null_short_content():
    """Tin tức xử lý mượt shortContent=None, loại bỏ tin rác relevance=0 và không lặp tiêu đề trên Markdown."""
    scanner = FialdaScanner(username="u", password="p")
    scanner.token = "eyJhbGciOiJIUzI1NiJ9.live_test.sig"

    news_payload = {
        "result": {
            "items": [
                {
                    "title": "Bản tin tổng hợp thị trường vàng thế giới cuối tuần",
                    "shortContent": None,
                    "source": "Báo Chung",
                    "publishedTime": "2026-10-30T15:00:00",
                },
                {
                    "title": "TPBank bứt phá thu nhập dịch vụ số hóa trong quý 3/2026",
                    "shortContent": None,
                    "source": "CafeF",
                    "publishedTime": "2026-10-29T10:00:00",
                },
            ]
        }
    }
    with patch.object(scanner.session, "get", return_value=_make_json_response(news_payload)):
        items = scanner.get_company_news("TPB", page_size=2)

    assert len(items) == 1
    assert "TPBank" in items[0]["title"]
    assert items[0]["short_content"] == items[0]["title"]

    # Kiểm tra Markdown không in lặp dòng trích dẫn khi short_content trùng hệt title
    cand = FialdaCandidate(
        symbol="TPB", price=17.5, signal_type="CHO_MUA_CHAN_SONG",
        entry_low=17.2, entry_high=17.7, stop_loss=16.5, target_1m=21.5,
        rs_1m=82, composite_rating=84, acc_diss_rating="A",
        rrg_r=102.0, rrg_m=101.0, foreign_net_value_billion=12.0, ranking_score=86.0,
        catalyst="Bank", tp1=19.0, tp2=20.5,
    )
    with patch.object(scanner, "get_company_news", return_value=items), \
         patch.object(scanner, "get_company_events", return_value=[]), \
         patch.object(scanner, "get_income_statement", return_value=[{"quarter": 3, "year": 2026, "revenue_billion": 5195.2, "gross_profit_billion": 3210.4, "net_profit_billion": 1845.0}]):
        md = format_top_5_markdown([cand], scanner=scanner)

    assert md.count("TPBank bứt phá thu nhập dịch vụ số hóa trong quý 3/2026") == 1
    assert "Chưa ghi nhận lịch chốt quyền" in md


def test_daily_statistic_avg_vol_20d_fallback_and_fialda_ohlcv_failover():
    """Đọc chuẩn DailyStatistic.avgVol20D từ GetStockInfos và tự động Failover sang Fialda TradingView/GetOHLC."""
    scanner = FialdaScanner(username="u", password="p")
    scanner.token = "eyJhbGciOiJIUzI1NiJ9.live_test.sig"

    # 1. Kiểm tra Failover sang TradingView/GetOHLC khi Entrade rỗng
    tv_payload = {
        "result": {
            "bars": [
                {"open": 21.0, "high": 21.5, "low": 20.8, "close": 21.3, "volume": 15_000_000}
                for _ in range(20)
            ]
        }
    }
    with patch.object(scanner, "get_recent_ohlcv", return_value={}), \
         patch.object(scanner.session, "get", return_value=_make_json_response(tv_payload)):
        batch = scanner.get_recent_ohlcv_batch(["HPG"], lookback_days=30)
        assert "HPG" in batch
        assert len(batch["HPG"]["c"]) == 20
        assert batch["HPG"]["c"][-1] == 21.3

    # 2. Kiểm tra DailyStatistic.avgVol20D cứu thanh khoản ADTV20 khi cả 2 nguồn OHLCV đều trống
    mock_infos = {
        "HPG": {
            "PriceInfo": {"currentPrice": 22.0, "totalVal": 0.0},
            "DailyStatistic": {"avgVol20D": 1_500_000},  # 1.5M * 22,000đ = 33.0 tỷ/phiên >= 15 tỷ
            "ForeignTrade": {"totalForeignNetValue": 10e9},
        }
    }
    with patch.object(scanner, "get_expert_buy_signals", return_value={"HPG": {"item1": True, "item2": 21.7, "item3": 22.2}}), \
         patch.object(scanner, "get_expert_value_surge", return_value=[]), \
         patch.object(scanner, "get_rrg_data", return_value={"HPG": {"r": 102.0, "m": 101.5}}), \
         patch.object(scanner, "get_market_top_symbols", return_value=[]), \
         patch.object(scanner, "get_stock_infos", return_value=mock_infos), \
         patch.object(scanner, "get_recent_ohlcv_batch", return_value={}), \
         patch.object(scanner, "get_market_breadth", return_value={"advances": 200, "declines": 100, "noChange": 50}), \
         patch.object(scanner, "get_live_basis_points", return_value=1.0), \
         patch.object(scanner, "get_expert_rating", return_value={"rS1M": 85, "compositeRating": 86, "accDissRating": "A"}):
        res = scanner.scan_top_rockets(top_n=5, record_history=False)

    assert len(res) == 1
    assert res[0].symbol == "HPG"
    assert res[0].adtv20_billion == 33.0


def test_market_breadth_parses_singular_no_change_field():
    """Fialda GetIndexData trả về 'noChange' (số ít) phải được bóc tách chính xác vào unchanged."""
    snap = parse_market_breadth_dict({
        "advances": 180,
        "declines": 130,
        "noChange": 49,
        "totalValue": 16_500_000_000_000.0,
    })
    assert snap.advances == 180
    assert snap.declines == 130
    assert snap.unchanged == 49
    assert snap.total_value_billion == 16500.0


def test_vn_market_client_eliminates_invalid_vn30f1m_stock_400_and_uses_vps_fallback():
    """VNMarketClient không còn bắn request lỗi HTTP 400 (/ohlcs/stock?symbol=VN30F1M) và có dự phòng VPS."""
    client = VNMarketClient(use_mock=False)
    called_pairs = []

    def fake_entrade(sym: str, endpoint_type: str = "index"):
        called_pairs.append((sym, endpoint_type))
        if sym == "VN30":
            return 1855.40
        if sym == "VNINDEX":
            return 1741.20
        return None  # Giả lập Entrade derivative tạm lỗi

    with patch.object(VNMarketClient, "_fetch_entrade_last_close", side_effect=fake_entrade), \
         patch.object(VNMarketClient, "_fetch_vps_derivative_fallback", return_value=1858.00) as mock_vps:
        prices = client.get_spot_and_derivatives_prices()

    assert ("VN30F1M", "stock") not in called_pairs
    assert mock_vps.call_count == 1
    assert prices["VN30_INDEX"] == 1855.40
    assert prices["VN30F1M"] == 1858.00
    assert prices["VNINDEX"] == 1741.20


def test_terminal_js_vps_foreign_flow_uses_1e6_divisor_and_no_store_cache(tmp_path: Path):
    """Client JS trên HUD phải chia VPS fBValue/fSValue (đơn vị 1,000 VND) cho 1e6 để ra đúng Tỷ VND."""
    out_file = tmp_path / "hud_vps_unit.html"
    cand = FialdaCandidate(
        symbol="FRT", price=148.50, signal_type="CHO_MUA_CHAN_SONG",
        entry_low=146.0, entry_high=149.5, stop_loss=139.5, target_1m=182.0,
        rs_1m=91, composite_rating=92, acc_diss_rating="A",
        rrg_r=104.0, rrg_m=103.0, foreign_net_value_billion=6.3, ranking_score=93.5,
        catalyst="Retail leader", tp1=162.0, tp2=175.0,
        prop_net_value_billion=14.5, has_actual_prop_flow=True,
        flow_regime="SIEU_SONG", flow_badge="🟢🟢 ĐỒNG THUẬN GOM",
    )
    generate_terminal_html(
        output_path=str(out_file),
        fialda_candidates=[cand],
        top_n=1,
        spot_deriv_override={"VN30_INDEX": 1855.0, "VN30F1M": 1858.0, "VNINDEX": 1741.0},
    )
    html = out_file.read_text(encoding="utf-8")

    assert "(liveForeignBuyVal - liveForeignSellVal) / 1e6" in html
    assert "(liveForeignBuyVal - liveForeignSellVal) / 1e9" not in html
    assert "(fInfo.fbVal - fInfo.fsVal) / 1e6" in html
    assert "cache: 'no-store'" in html
    assert 'class="live-foreign" data-sym="FRT"' in html
    assert "TD: +14.5t" in html


@patch("src.collector.google_sheets_client.requests.post")
def test_google_sheets_webhook_rejects_html_login_redirect_false_positive(mock_post):
    """Khi Google Apps Script chưa mở quyền Anyone và trả về HTML trang đăng nhập (HTTP 200), phải trả False."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.url = "https://accounts.google.com/ServiceLogin?service=wise"
    mock_resp.text = "<!DOCTYPE html><html><head><title>Sign in - Google Accounts</title></head></html>"
    mock_post.return_value = mock_resp

    client = GoogleSheetsLedgerClient(webhook_url="https://script.google.com/macros/s/AKfycbxRestricted/exec")
    assert client.sync_signals([{"symbol": "HPG", "current_price": 21.3}]) is False


def test_banking_camel_screener_computes_live_pb_and_pe_from_basic_info():
    """Bảng CAMEL Ngân hàng tự động tính lại P/B và P/E live từ bookValuePerShare & eps_TTM trong GetStockInfos."""
    scanner = FialdaScanner(username="u", password="p")
    scanner.token = "eyJhbGciOiJIUzI1NiJ9.live_test.sig"

    fake_stock_infos = {
        "TCB": {
            "PriceInfo": {"currentPrice": 24.0},
            "BasicInfo": {"bookValuePerShare": 20000.0, "eps_TTM": 3000.0},
        }
    }
    with patch.object(scanner, "get_stock_infos", return_value=fake_stock_infos):
        scored = scanner.get_banking_screener_data()

    tcb = next(b for b in scored if b.symbol == "TCB")
    assert tcb.price == 24.0
    assert tcb.metrics.pb == 1.20  # 24,000 / 20,000
    assert tcb.metrics.pe == 8.0   # 24,000 / 3,000
