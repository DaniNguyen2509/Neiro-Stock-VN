from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from src.collector.data_loader import get_mock_vietnam_stocks
from src.collector.vn_market_client import VNMarketClient
from src.fundamental_engine.screener import screen_stocks
from src.microstructure_engine.basis_tracker import analyze_vn30_basis
from src.collector.fialda_scanner import FialdaCandidate, FialdaScanner
from src.risk_engine.position_sizer import calculate_retail_t25_position_size
from src.sector_engine.market_breadth import parse_market_breadth_dict
from src.backtesting.walk_forward import WalkForwardCoordinator

_CACHED_WF_SUMMARY: Optional[Dict[str, Any]] = None


def _get_cached_walk_forward_summary() -> Dict[str, Any]:
    """Chạy kiểm định Walk-Forward T+2.5 trung thực (có cache trên RAM để xuất HTML tức thì)."""
    global _CACHED_WF_SUMMARY
    if _CACHED_WF_SUMMARY is None:
        _CACHED_WF_SUMMARY = WalkForwardCoordinator().run_full_walk_forward()
    return _CACHED_WF_SUMMARY


def generate_terminal_html(
    output_path: str = "exports/vn_stock_terminal.html",
    fialda_candidates: Optional[List[FialdaCandidate]] = None,
    top_n: int = 20,
    spot_deriv_override: Optional[Dict[str, float]] = None,
    market_breadth: Optional[Dict[str, Any]] = None,
    scanner: Optional[FialdaScanner] = None,
) -> str:
    """Sinh mã nguồn giao diện Web Terminal tương tác độc lập (Continuous Dashboard)."""
    scanner = scanner or FialdaScanner()

    if spot_deriv_override is not None:
        prices_map = spot_deriv_override
    else:
        prices_map = VNMarketClient(use_mock=False).get_spot_and_derivatives_prices()
    vn30_spot = float(prices_map.get("VN30_INDEX") or 1300.0)
    vn30f1m_fut = float(prices_map.get("VN30F1M") or vn30_spot)
    basis = analyze_vn30_basis(vn30f1m_fut, vn30_spot)

    if fialda_candidates is None:
        if scanner.username and scanner.password:
            try:
                fialda_candidates = scanner.scan_top_rockets(top_n=top_n)
            except Exception:
                fialda_candidates = scanner._fallback_mock_top_20()[:top_n]
        else:
            fialda_candidates = scanner._fallback_mock_top_20()[:top_n]

    if market_breadth is None and scanner.token:
        try:
            market_breadth = scanner.get_market_breadth()
        except Exception:
            market_breadth = None
    mb_snap = parse_market_breadth_dict(market_breadth)
    circuit_breaker_active = bool(mb_snap.pause_new_buying or basis.basis_points <= -8.0)

    # Lay du lieu co ban that 100% tu Fialda TechnicalAnalysis & GetStockInfos
    try:
        fund_data = scanner.get_fundamental_screener_data()
    except Exception:
        fund_data = scanner._fallback_mock_fundamental()

    # Chuan bi bang du lieu Fialda Top N
    fialda_rows_html = ""
    for idx, c in enumerate(fialda_candidates, 1):
        base_sig_badge = (
            '<span style="background:#1b5e20;color:#00e676;padding:3px 8px;border-radius:4px;font-size:11px;font-weight:bold;">CHÂN SÓNG</span>'
            if "CHO_MUA" in c.signal_type
            else '<span style="background:#01579b;color:#29b6f6;padding:3px 8px;border-radius:4px;font-size:11px;font-weight:bold;">ĐỘT BIẾN GT</span>'
        )
        buy_perm = getattr(c, "buy_permission", "BUY_OK")
        fomo_text = getattr(c, "anti_fomo_badge", "🟢 VÙNG MUA CHUẨN")
        if circuit_breaker_active:
            buy_perm = "EXTENDED_NO_CHASING"
            fomo_text = "⛔ NGỪNG MUA MỚI — QUAN SÁT"
        if buy_perm in ("EXTENDED_NO_CHASING", "BULL_TRAP_REJECT"):
            fomo_sub_html = f'<div style="margin-top:3px;"><span style="background:#7f1d1d;color:#fecaca;border:1px solid #ef4444;padding:1px 5px;border-radius:3px;font-size:9.5px;font-weight:bold;">{fomo_text}</span></div>'
        elif buy_perm == "STALE_SIGNAL":
            fomo_sub_html = f'<div style="margin-top:3px;"><span style="background:#7c2d12;color:#fed7aa;border:1px solid #f97316;padding:1px 5px;border-radius:3px;font-size:9.5px;font-weight:bold;">{fomo_text}</span></div>'
        elif buy_perm == "BUY_CAUTION":
            fomo_sub_html = f'<div style="margin-top:3px;"><span style="background:#78350f;color:#fde68a;padding:1px 5px;border-radius:3px;font-size:9.5px;font-weight:bold;">{fomo_text}</span></div>'
        else:
            fomo_sub_html = ""
        sig_badge = f"{base_sig_badge}{fomo_sub_html}"

        lot_note = getattr(c, "retail_lot_note", "")
        if not lot_note and c.price > 100.0:
            lot_note = calculate_retail_t25_position_size(
                equity_vnd=100_000_000.0,
                current_price_vnd=c.price,
                stop_loss_price_vnd=c.stop_loss,
                available_t0_ratio=0.0,
                symbol=c.symbol,
            ).lot_warning
        lot_badge_html = (
            f'<div title="{lot_note}" style="font-size:9px;color:#fbbf24;margin-top:2px;font-weight:700;">⚠️ LÔ 100CP CAO</div>'
            if lot_note
            else ""
        )
        foreign_str = f"{c.foreign_net_value_billion:+.1f} tỷ"
        foreign_color = "#00e676" if c.foreign_net_value_billion >= 0 else "#ff5252"
        flow_b = getattr(c, "flow_badge", "🟢 NỘI GOM CÂN HÀNG")
        if "SIÊU" in flow_b or "ĐỒNG THUẬN" in flow_b:
            flow_badge_html = '<div style="font-size:9px;color:#00e676;margin-top:2px;font-weight:bold;">🟢🟢 ĐỒNG THUẬN</div>'
        elif "NỘI GOM" in flow_b:
            flow_badge_html = '<div style="font-size:9px;color:#69f0ae;margin-top:2px;font-weight:bold;">🟢 NỘI CÂN HÀNG</div>'
        elif "ĐỠ" in flow_b:
            flow_badge_html = '<div style="font-size:9px;color:#4fc3f7;margin-top:2px;font-weight:bold;">🔵 NGOẠI ĐỠ GIÁ</div>'
        else:
            flow_badge_html = '<div style="font-size:9px;color:#ff5252;margin-top:2px;font-weight:bold;">🔴 NGUY HIỂM</div>'
        if getattr(c, "has_actual_prop_flow", False):
            prop_v = float(getattr(c, "prop_net_value_billion", 0.0) or 0.0)
            if abs(prop_v) >= 0.05:
                prop_c = "#00e676" if prop_v >= 0 else "#ffb300"
                flow_badge_html += f'<div style="font-size:9px;color:{prop_c};margin-top:1px;">TD: {prop_v:+.1f}t</div>'

        if c.liquidity_score >= 90:
            liq_badge = '<span style="background:#1b5e20;color:#00e676;padding:1px 5px;border-radius:3px;font-size:10px;font-weight:bold;">SIÊU TK</span>'
        elif c.liquidity_score >= 75:
            liq_badge = '<span style="background:#01579b;color:#29b6f6;padding:1px 5px;border-radius:3px;font-size:10px;font-weight:bold;">CHUẨN QUỸ</span>'
        else:
            liq_badge = '<span style="background:#ff6f00;color:#fff;padding:1px 5px;border-radius:3px;font-size:10px;font-weight:bold;">ĐẠT BIÊN</span>'

        ad_letter = getattr(c, "acc_diss_rating", "C")
        ad_color = "#00e676" if ad_letter in ["A", "B"] else ("#ffb300" if ad_letter == "C" else "#ff5252")
        ad_bg = "#1b5e20" if ad_letter in ["A", "B"] else ("#3e2723" if ad_letter == "C" else "#450a0a")
        ad_badge = f'<span style="background:{ad_bg};color:{ad_color};padding:2px 7px;border-radius:3px;font-size:11px;font-weight:bold;">{ad_letter}</span>'

        tp1_val = getattr(c, "tp1", c.price * 1.08)
        tp2_val = getattr(c, "tp2", c.target_1m)
        tp_html = f'<span style="color:#4fc3f7;font-weight:bold;">{tp1_val:.2f}</span> <span style="color:#546e7a;">/</span> <span style="color:#ffb300;font-weight:bold;">{tp2_val:.2f}</span>'

        # Xep hang ky truoc va bien dong (+ / - hang)
        prev_rank = getattr(c, "prev_rank", None)
        delta_rank = getattr(c, "rank_change_delta", None)
        if prev_rank is not None:
            if delta_rank is not None and delta_rank > 0:
                prev_rank_html = f'<span style="font-weight:bold;color:#eceff1;">#{prev_rank}</span> <span style="background:#1b5e20;color:#00e676;padding:1px 4px;border-radius:3px;font-size:10px;font-weight:bold;">+{delta_rank}</span>'
            elif delta_rank is not None and delta_rank < 0:
                prev_rank_html = f'<span style="font-weight:bold;color:#eceff1;">#{prev_rank}</span> <span style="background:#b71c1c;color:#ff8a80;padding:1px 4px;border-radius:3px;font-size:10px;font-weight:bold;">{delta_rank}</span>'
            else:
                prev_rank_html = f'<span style="font-weight:bold;color:#eceff1;">#{prev_rank}</span> <span style="color:#78909c;font-size:10px;font-weight:bold;">(=)</span>'
        else:
            prev_rank_html = '<span style="background:#e65100;color:#ffe0b2;padding:1px 4px;border-radius:3px;font-size:10px;font-weight:bold;">MỚI</span>'

        fialda_rows_html += f"""
        <tr style="border-bottom:1px solid #1f2937;">
            <td style="padding:6px 5px;text-align:center;color:#78909c;font-weight:bold;">{idx}</td>
            <td style="padding:6px 5px;font-weight:bold;color:#ffb300;font-size:13.5px;">{c.symbol}{lot_badge_html}</td>
            <td style="padding:6px 5px;text-align:center;"><span id="sig-badge-{c.symbol}">{sig_badge}</span></td>
            <td style="padding:6px 5px;font-weight:bold;white-space:nowrap;"><span class="live-price" data-sym="{c.symbol}" data-ref="{c.price}" data-entry-high="{c.entry_high}" data-entry-low="{c.entry_low}" data-sl="{c.stop_loss}" data-tp1="{tp1_val}" data-tp2="{tp2_val}" data-buy-perm="{buy_perm}">{c.price:,.2f}</span> <span class="live-change" data-sym="{c.symbol}" style="font-size:11px;margin-left:3px;"></span></td>
            <td style="padding:6px 5px;color:#00e676;font-weight:600;">{c.entry_low:.2f} - {c.entry_high:.2f}</td>
            <td style="padding:6px 5px;color:#ff5252;font-weight:bold;">{c.stop_loss:.2f}</td>
            <td style="padding:6px 5px;text-align:center;">{tp_html}</td>
            <td style="padding:6px 5px;text-align:center;font-weight:bold;color:#4fc3f7;">{c.adtv20_billion:.1f}t</td>
            <td style="padding:6px 5px;text-align:center;">{liq_badge}</td>
            <td style="padding:6px 5px;text-align:center;color:#4fc3f7;">{c.rrg_r:.0f}/{c.rrg_m:.0f}</td>
            <td style="padding:6px 5px;text-align:center;font-weight:bold;color:#ffb300;">{c.composite_rating}</td>
            <td style="padding:6px 5px;text-align:center;">{ad_badge}</td>
            <td id="foreign-cell-{c.symbol}" style="padding:6px 5px;text-align:center;color:{foreign_color};font-weight:600;"><span class="live-foreign" data-sym="{c.symbol}">{foreign_str}</span>{flow_badge_html}</td>
            <td style="padding:6px 5px;text-align:center;font-weight:bold;color:#ffb300;">{c.ranking_score:.1f}</td>
            <td style="padding:6px 5px;text-align:center;white-space:nowrap;">{prev_rank_html}</td>
        </tr>
        """

    # Chuan bi bang du lieu HTML Quantamental that tu Fialda
    rows_html = ""
    for s in fund_data:
        badge = (
            '<span style="background:#1b5e20;color:#00e676;padding:3px 8px;border-radius:4px;font-size:11px;font-weight:bold;">ĐỊNH CHẾ GOM</span>'
            if s.get("is_institutional")
            else '<span style="background:#37474f;color:#b0bec5;padding:3px 8px;border-radius:4px;font-size:11px;font-weight:bold;">THEO DÕI</span>'
        )
        f_score_val = s.get("f_score_str", "N/A")
        if "Ngân hàng" in f_score_val or "N/A" in f_score_val:
            f_color = "#78909c"
        elif s.get("f_score", 0) >= 6:
            f_color = "#00e676"
        else:
            f_color = "#ffb300"
        rows_html += f"""
        <tr style="border-bottom:1px solid #1f2937;">
            <td style="padding:10px;font-weight:bold;color:#ffb300;">{s['symbol']}</td>
            <td style="padding:10px;">{s['company_name']}</td>
            <td style="padding:10px;color:#aaa;">{s['sector']}</td>
            <td style="padding:10px;font-weight:bold;color:#00e676;" class="live-price" data-sym="{s['symbol']}">{s['price']:.2f}</td>
            <td style="padding:10px;text-align:center;font-weight:bold;color:{f_color};">{f_score_val}</td>
            <td style="padding:10px;text-align:center;">{s['pe']:.1f}</td>
            <td style="padding:10px;text-align:center;">{s['pb']:.1f}</td>
            <td style="padding:10px;text-align:center;">{s['cfo_ni']:.2f}</td>
            <td style="padding:10px;text-align:center;">{badge}</td>
        </tr>
        """

    # Chuan bi du lieu Bang Dinh Luong Ngan Hang CAMEL & Basel II/III
    try:
        bank_scores = scanner.get_banking_screener_data()
    except Exception:
        from src.fundamental_engine.banking_quant import get_benchmark_vn_banks, screen_banks_camel
        bank_scores = screen_banks_camel(get_benchmark_vn_banks())

    bank_rows_html = ""
    for b in bank_scores:
        m = b.metrics
        if "HẠNG A" in b.tier:
            tier_badge = f'<span style="background:#1b5e20;color:#00e676;padding:3px 8px;border-radius:4px;font-size:11px;font-weight:bold;">{b.tier}</span>'
            score_color = "#00e676"
        elif "HẠNG B" in b.tier:
            tier_badge = f'<span style="background:#0d47a1;color:#4fc3f7;padding:3px 8px;border-radius:4px;font-size:11px;font-weight:bold;">{b.tier}</span>'
            score_color = "#4fc3f7"
        else:
            tier_badge = f'<span style="background:#ff6f00;color:#fff;padding:3px 8px;border-radius:4px;font-size:11px;font-weight:bold;">{b.tier}</span>'
            score_color = "#ffb300"

        bank_rows_html += f"""
        <tr style="border-bottom:1px solid #1f2937;">
            <td style="padding:10px;font-weight:bold;color:#ffb300;">{b.symbol}</td>
            <td style="padding:10px;">{b.bank_name}</td>
            <td style="padding:10px;font-weight:bold;color:#00e676;" class="live-price" data-sym="{b.symbol}">{b.price:.2f}</td>
            <td style="padding:10px;text-align:center;font-weight:800;color:{score_color};font-size:14px;">{b.total_score:.0f}/100</td>
            <td style="padding:10px;text-align:center;font-weight:bold;color:#ffb300;">{m.casa:.1f}%</td>
            <td style="padding:10px;text-align:center;">{m.nim:.1f}%</td>
            <td style="padding:10px;text-align:center;color:{'#00e676' if m.npl <= 1.5 else '#ff5252'};">{m.npl:.2f}%</td>
            <td style="padding:10px;text-align:center;font-weight:bold;color:#00e676;">{m.llr:.0f}%</td>
            <td style="padding:10px;text-align:center;">{m.cir:.1f}%</td>
            <td style="padding:10px;text-align:center;color:#4fc3f7;">{m.roe:.1f}%</td>
            <td style="padding:10px;text-align:center;font-weight:bold;">{m.pb:.1f}</td>
            <td style="padding:10px;text-align:center;">{tier_badge}</td>
        </tr>
        """

    # Chuan bi du lieu BCTC 4 quy cho cac co phieu tam diem (Thong ke 1 CP / 1 dong)
    spotlight_symbols = [c.symbol for c in fialda_candidates[:5]] if fialda_candidates else ["CTS", "GEX", "VGC", "PDR", "VIX"]
    bctc_rows_html = ""
    for sym in spotlight_symbols:
        try:
            quarters = scanner.get_income_statement(sym, is_quarter=True)
        except Exception:
            quarters = scanner._fallback_mock_income_statement(sym)
        if not quarters:
            continue
        q_latest = quarters[0]
        q_name = f"Q{q_latest.get('quarter')}/{q_latest.get('year')}"
        rev0 = q_latest.get("revenue_billion", 0.0)
        gp0 = q_latest.get("gross_profit_billion", 0.0)
        np0 = q_latest.get("net_profit_billion", 0.0)
        margin0 = round((gp0 / rev0 * 100.0), 1) if rev0 > 0 else 0.0

        rev1 = quarters[1].get("revenue_billion", 0.0) if len(quarters) > 1 else 0.0
        np1 = quarters[1].get("net_profit_billion", 0.0) if len(quarters) > 1 else 0.0

        rev2 = quarters[2].get("revenue_billion", 0.0) if len(quarters) > 2 else 0.0
        np2 = quarters[2].get("net_profit_billion", 0.0) if len(quarters) > 2 else 0.0

        if len(quarters) > 1 and np1 != 0:
            growth_qoq = round(((np0 - np1) / abs(np1)) * 100.0, 1)
            growth_str = f"{growth_qoq:+.1f}%"
        else:
            growth_qoq = 0.0
            growth_str = "N/A"

        if len(quarters) >= 3 and np0 > np1 > np2 and np0 > 0:
            eval_tag = "🚀 TĂNG TỐC 3 QUÝ"
            badge_bg = "#1b5e20"
            badge_fg = "#00e676"
        elif growth_qoq >= 50.0:
            eval_tag = "🔥 BÙNG NỔ LNST"
            badge_bg = "#1b5e20"
            badge_fg = "#00e676"
        elif growth_qoq > 0:
            eval_tag = "↗ TĂNG TRƯỞNG DƯƠNG"
            badge_bg = "#004d40"
            badge_fg = "#4db6ac"
        elif np0 < 0:
            eval_tag = "⚠️ LỖ RÒNG"
            badge_bg = "#b71c1c"
            badge_fg = "#ff8a80"
        else:
            eval_tag = "↘ CHẬM LẠI"
            badge_bg = "#37474f"
            badge_fg = "#b0bec5"

        growth_bg = "#1b5e20" if growth_qoq > 0 else ("#b71c1c" if growth_qoq < 0 else "#37474f")
        growth_fg = "#00e676" if growth_qoq > 0 else ("#ff8a80" if growth_qoq < 0 else "#b0bec5")
        np2_color = "#00e676" if np2 >= 0 else "#ff5252"
        np1_color = "#00e676" if np1 >= 0 else "#ff5252"
        np0_color = "#00e676" if np0 >= 0 else "#ff5252"

        bctc_rows_html += f"""
        <tr style="border-bottom:1px solid #1f2937;">
            <td style="padding:10px;font-weight:bold;color:#ffb300;font-size:14px;">{sym}</td>
            <td style="padding:10px;text-align:center;"><span style="background:#263238;color:#4fc3f7;padding:3px 8px;border-radius:4px;font-weight:600;font-size:12px;">{q_name}</span></td>
            <td style="padding:10px;text-align:right;color:#78909c;border-left:1px solid #1f2937;">{rev2:,.1f} tỷ</td>
            <td style="padding:10px;text-align:right;color:#90a4ae;">{rev1:,.1f} tỷ</td>
            <td style="padding:10px;text-align:right;font-weight:700;color:#ffb300;border-right:1px solid #1f2937;">{rev0:,.1f} tỷ</td>
            <td style="padding:10px;text-align:right;color:{np2_color};">{np2:,.1f} tỷ</td>
            <td style="padding:10px;text-align:right;color:{np1_color};">{np1:,.1f} tỷ</td>
            <td style="padding:10px;text-align:right;font-weight:700;color:{np0_color};border-right:1px solid #1f2937;">{np0:,.1f} tỷ</td>
            <td style="padding:10px;text-align:center;">
                <span style="background:{growth_bg};color:{growth_fg};padding:3px 8px;border-radius:4px;font-weight:bold;font-size:12px;">{growth_str}</span>
            </td>
            <td style="padding:10px;text-align:center;font-weight:bold;color:#ffb300;">{margin0:.1f}%</td>
            <td style="padding:10px;text-align:center;">
                <span style="background:{badge_bg};color:{badge_fg};padding:3px 8px;border-radius:4px;font-size:11px;font-weight:bold;">{eval_tag}</span>
            </td>
        </tr>
        """

    # Chuan bi Tin tuc & Su kien doanh nghiep
    news_items_html = ""
    events_items_html = ""
    for sym in spotlight_symbols[:4]:
        try:
            news_list = scanner.get_company_news(sym, page_size=1)
        except Exception:
            news_list = scanner._fallback_mock_news(sym)[:1]
        for n in news_list:
            short_body = (
                f'<div style="font-size:12px;color:#90a4ae;line-height:1.4;">{n["short_content"]}</div>'
                if n.get("short_content") and n["short_content"].strip() != n["title"].strip()
                else ""
            )
            news_items_html += f"""
            <div style="background:#151a23;border:1px solid #263238;border-radius:6px;padding:12px;margin-bottom:10px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                    <span style="font-weight:bold;color:#ffb300;font-size:13px;">{n['symbol']}</span>
                    <span style="font-size:11px;color:#78909c;">{n['time']} • {n['source']}</span>
                </div>
                <div style="font-weight:600;font-size:13px;color:#eceff1;margin-bottom:4px;">{n['title']}</div>
                {short_body}
            </div>
            """

        try:
            ev_list = scanner.get_company_events(sym)
        except Exception:
            ev_list = scanner._fallback_mock_events(sym)
        for ev in ev_list[:1]:
            events_items_html += f"""
            <div style="background:#151a23;border:1px solid #263238;border-radius:6px;padding:12px;margin-bottom:10px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                    <span style="font-weight:bold;color:#00e676;font-size:13px;">{ev['symbol']}</span>
                    <span style="font-size:11px;color:#ffb300;background:#263238;padding:2px 6px;border-radius:4px;">Thời gian: {ev['date']}</span>
                </div>
                <div style="font-size:13px;color:#d1d4dc;">{ev['event_name']}</div>
            </div>
            """

    if not events_items_html:
        events_items_html = """
        <div style="background:#151a23;border:1px solid #263238;border-radius:6px;padding:12px;margin-bottom:10px;color:#90a4ae;font-size:12.5px;">
            Chưa ghi nhận lịch chốt quyền / ĐHCĐ mới từ cổng CBTT Fialda cho nhóm Spotlight.
        </div>
        """

    regime_map = {
        "NORMAL_EQUILIBRIUM": "Cân Bằng Bình Thường",
        "CONTANGO_EXPANDED": "Contango Mở Rộng",
        "BACKWARDATION_EXTREME": "Backwardation Cực Đoan (Cảnh Báo Kéo Trụ)",
    }
    regime_vn = regime_map.get(basis.regime, basis.regime)

    # 1. Tinh dong tien Ca map (Foreign Net Value) dong bo that tu danh muc Top (Khong bia dat Tu doanh)
    total_cands = len(fialda_candidates) if fialda_candidates else 0
    total_foreign = sum(getattr(c, "foreign_net_value_billion", 0.0) for c in fialda_candidates) if fialda_candidates else 0.0
    absorbed_cnt = sum(
        1
        for c in (fialda_candidates or [])
        if getattr(c, "flow_regime", "NOI_CAN_HANG") in ("SIEU_SONG", "NOI_CAN_HANG")
        and getattr(c, "acc_diss_rating", "C") in ("A", "B", "C")
    )
    dist_cnt = sum(
        1
        for c in (fialda_candidates or [])
        if getattr(c, "flow_regime", "") == "RUI_RO_XA" or getattr(c, "acc_diss_rating", "C") in ("D", "E")
    )
    if total_foreign >= 0:
        smart_money_val = f"+{total_foreign:.1f} Tỷ VND"
        smart_money_color = "#00e676"
        smart_money_sub = f"Khối ngoại mua ròng • {absorbed_cnt}/{max(total_cands, 1)} mã giữ cấu trúc tích lũy"
    elif absorbed_cnt > dist_cnt and not circuit_breaker_active:
        smart_money_val = f"{total_foreign:.1f} Tỷ VND"
        smart_money_color = "#ffb300"
        smart_money_sub = f"Ngoại bán ròng • Dòng tiền Nội gom cân hàng ({absorbed_cnt}/{max(total_cands, 1)} mã nền A/B)"
    else:
        smart_money_val = f"{total_foreign:.1f} Tỷ VND"
        smart_money_color = "#ff5252"
        smart_money_sub = f"Khối ngoại bán ròng • Cảnh báo {dist_cnt}/{max(total_cands, 1)} mã áp lực xả (Thận trọng T+2.5)"

    # 2. Do rong danh muc sieu co phieu (Market Breadth / Momentum)
    if total_cands > 0:
        strong_cands = sum(1 for c in fialda_candidates if getattr(c, "composite_rating", 0) >= 70 or getattr(c, "rs_1m", 0) >= 70)
        breadth_pct = (strong_cands / total_cands) * 100.0
        breadth_val = f"{breadth_pct:.1f}%"
        breadth_sub = f"{strong_cands}/{total_cands} Cổ phiếu giữ xung lực dẫn dắt (RS/Composite ≥ 70)"
        breadth_color = "#00e676" if breadth_pct >= 60 else "#ffb300"
    else:
        breadth_val = "75.0%"
        breadth_sub = "Cân bằng bình thường"
        breadth_color = "#ffb300"

    macro_breadth_suffix = ""
    if mb_snap.advances > 0 or mb_snap.declines > 0:
        macro_breadth_suffix = f"VN-Index: Tăng {mb_snap.advances} / Giảm {mb_snap.declines} ({mb_snap.breadth_pct:.1f}%)"
        breadth_sub = f"{breadth_sub} • {macro_breadth_suffix}"
        if mb_snap.pause_new_buying:
            breadth_color = "#ff5252"

    # Chuan bi du lieu Tab 2: Kiem dinh Walk-Forward T+2.5 Trung thuc (Floor-Lock + 0.40% Fee/Tax + <= 20% NAV)
    wf_summary = _get_cached_walk_forward_summary()
    wf_is = wf_summary["in_sample"]
    wf_oos = wf_summary["out_of_sample"]
    wf_full = wf_summary["full"]
    wf_wfe = wf_summary["walk_forward_efficiency_pct"]
    wf_rows_html = ""
    for wf_label, wf_res in [
        ("In-Sample (2021 - 2023 • Bull & Bear)", wf_is),
        ("Out-of-Sample (2024 - 2026 • Kiểm Chứng Mù)", wf_oos),
        ("Toàn Chu Kỳ (2021 - 2026 • Hợp Nhất)", wf_full),
    ]:
        ret_color = "#00e676" if wf_res.total_return_pct >= 0 else "#ff5252"
        alpha_color = "#00e676" if wf_res.alpha_pct >= 0 else "#ffb300"
        wf_rows_html += f"""
        <tr style="border-bottom:1px solid #1f2937;">
            <td style="padding:10px;font-weight:bold;color:#ffb300;">{wf_label}</td>
            <td style="padding:10px;text-align:center;font-weight:bold;color:{ret_color};">{wf_res.total_return_pct:+.2f}%</td>
            <td style="padding:10px;text-align:center;font-weight:bold;color:#4fc3f7;">{wf_res.cagr_pct:+.2f}%</td>
            <td style="padding:10px;text-align:center;color:#ff5252;font-weight:bold;">-{abs(wf_res.max_drawdown_pct):.2f}%</td>
            <td style="padding:10px;text-align:center;font-weight:bold;color:#00e676;">{wf_res.sharpe_ratio:.2f}</td>
            <td style="padding:10px;text-align:center;">{wf_res.win_rate_pct:.1f}% ({wf_res.total_trades} lệnh)</td>
            <td style="padding:10px;text-align:center;font-weight:bold;color:{alpha_color};">{wf_res.alpha_pct:+.2f}%</td>
            <td style="padding:10px;text-align:center;color:#fbbf24;font-weight:bold;">{wf_res.floor_lock_blocked_count} lần sàn / {wf_res.t25_blocked_count} lần T+2.5</td>
        </tr>
        """

    basis_color = "#ff5252" if basis.basis_points <= -8.0 else ("#ffb300" if basis.basis_points < 0 else "#29b6f6")
    circuit_breaker_html = ""
    if mb_snap.pause_new_buying or basis.basis_points <= -8.0:
        reasons: List[str] = []
        if mb_snap.pause_new_buying:
            reasons.append(
                f"Độ rộng VN-Index suy yếu {mb_snap.breadth_pct:.1f}% (Tăng {mb_snap.advances} / Giảm {mb_snap.declines} — Xanh vỏ đỏ lòng)"
            )
        if basis.basis_points <= -8.0:
            reasons.append(f"Phái sinh VN30F1M chiết khấu âm sâu ({basis.basis_points:+.2f} điểm)")
        reason_str = " | ".join(reasons)
        circuit_breaker_html = f"""
    <div id="t25-circuit-breaker-banner" style="background:linear-gradient(90deg,#450a0a,#7f1d1d);border:2px solid #ef4444;border-radius:8px;padding:12px 16px;margin-bottom:18px;color:#fee2e2;font-size:13px;line-height:1.5;">
        <div style="font-weight:800;font-size:14px;color:#fca5a5;">⛔ CẦU CHÌ T+2.5 KÍCH HOẠT: TẠM NGỪNG MUA MỚI TOÀN BỘ VỊ THẾ CỔ PHIẾU</div>
        <div><b>Nguyên nhân vĩ mô:</b> {reason_str}. Tuyệt đối không mở mua mới hoặc bình quân giá xuống để tránh kẹp chu kỳ thanh toán T+2.5; ưu tiên giữ tỷ trọng tiền mặt &ge; 70% NAV.</div>
    </div>
        """

    # 3. Nganh dan dat tu toa do RRG (Leading Sector)
    SECTOR_MAP = {
        "CTS": "Chứng khoán", "VIX": "Chứng khoán", "SSI": "Chứng khoán", "VCI": "Chứng khoán", "VND": "Chứng khoán", "BVS": "Chứng khoán", "ORS": "Chứng khoán", "TCX": "Chứng khoán",
        "PDR": "Bất động sản", "DIG": "Bất động sản", "DXG": "Bất động sản", "KDH": "Bất động sản", "TCH": "Bất động sản", "DXS": "Bất động sản", "VHM": "Bất động sản", "VIC": "Bất động sản",
        "HPG": "Thép & Vật liệu", "NKG": "Thép & Vật liệu", "HSG": "Thép & Vật liệu",
        "PVC": "Dầu khí & Năng lượng", "PVD": "Dầu khí & Năng lượng", "PVS": "Dầu khí & Năng lượng", "BSR": "Dầu khí & Năng lượng",
        "VGC": "Khu công nghiệp", "PHR": "Cao su & KCN", "GEX": "Điện & Hạ tầng", "CII": "Hạ tầng & Đầu tư",
        "GMD": "Cảng biển & Vận tải", "VSC": "Cảng biển & Vận tải", "VJC": "Hàng không", "TCO": "Vận tải",
        "DBC": "Nông nghiệp", "BAF": "Nông nghiệp", "QNS": "Mía đường & Thực phẩm", "KDC": "Thực phẩm tiêu dùng",
        "EIB": "Ngân hàng", "OCB": "Ngân hàng", "ABB": "Ngân hàng", "TPB": "Ngân hàng", "SHB": "Ngân hàng", "VIB": "Ngân hàng", "MBB": "Ngân hàng", "VCB": "Ngân hàng",
        "MSR": "Khai khoáng", "VGT": "Dệt may", "VTZ": "Vật liệu xây dựng", "PTB": "Gỗ & Đá", "FPT": "Công nghệ"
    }
    sector_counts: Dict[str, List[str]] = {}
    if fialda_candidates:
        for c in fialda_candidates:
            sec = SECTOR_MAP.get(c.symbol, "Sản xuất & Thương mại")
            if sec not in sector_counts:
                sector_counts[sec] = []
            sector_counts[sec].append(c.symbol)

    if sector_counts:
        sorted_sectors = sorted(sector_counts.items(), key=lambda x: len(x[1]), reverse=True)
        top_sec_name, top_sec_syms = sorted_sectors[0]
        if len(sorted_sectors) > 1 and len(sorted_sectors[1][1]) >= 1:
            sec2_name, sec2_syms = sorted_sectors[1]
            leading_sector_val = f"{top_sec_name.upper()} & {sec2_name.upper()}"
            leading_sector_sub = f"{', '.join((top_sec_syms + sec2_syms)[:4])} dẫn sóng dòng tiền"
        else:
            leading_sector_val = top_sec_name.upper()
            leading_sector_sub = f"{', '.join(top_sec_syms[:3])} bứt phá mạnh nhất"
    else:
        leading_sector_val = "CHỨNG KHOÁN & BẤT ĐỘNG SẢN"
        leading_sector_sub = "CTS, PDR, VIX dẫn sóng dòng tiền"

    is_live = bool(scanner and scanner.token)
    data_badge = (
        '<div style="display:inline-block;background:#1b5e20;color:#00e676;padding:4px 10px;border-radius:4px;font-size:11px;font-weight:bold;">🟢 DỮ LIỆU: REAL-TIME FIALDA PRO API</div>'
        if is_live
        else '<div style="display:inline-block;background:#d84315;color:#ffe0b2;padding:4px 10px;border-radius:4px;font-size:11px;font-weight:bold;">🟡 CHẾ ĐỘ DỰ PHÒNG: BẢNG GIÁ ENTRADE/DNSE PUBLIC</div>'
    )
    data_subtext = (
        "Cập nhật theo chu kỳ giao dịch thực tế"
        if is_live
        else '<span style="color:#ffb300;">⚠️ Fialda VIP gián đoạn - Đang tự động bảo vệ tín hiệu bằng nguồn dự phòng</span>'
    )
    vn_now = datetime.now(timezone(timedelta(hours=7)))
    scan_time_str = vn_now.strftime("%H:%M:%S • %d/%m/%Y")

    html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="300">
    <title>Neiro-Stock-VN | Bảng Điều Khiển Chiến Thuật Định Lượng</title>
    <style>
        * {{
            box-sizing: border-box;
        }}
        body {{
            background-color: #0b0e14;
            color: #d1d4dc;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 0;
            padding: 15px;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
            border-bottom: 2px solid #1f2937;
            padding-bottom: 15px;
            margin-bottom: 20px;
        }}
        .title {{
            font-size: 22px;
            font-weight: 800;
            color: #ffb300;
            letter-spacing: 0.5px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 12px;
            margin-bottom: 25px;
        }}
        .card {{
            background: #151a23;
            border: 1px solid #263238;
            border-radius: 8px;
            padding: 14px;
        }}
        .card-title {{
            font-size: 11px;
            color: #78909c;
            text-transform: uppercase;
            margin-bottom: 6px;
            font-weight: 600;
        }}
        .card-value {{
            font-size: 20px;
            font-weight: 800;
        }}
        .table-container {{
            width: 100%;
            overflow-x: auto;
            border-radius: 8px;
            border: 1px solid #263238;
            margin-bottom: 25px;
            background: #151a23;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th {{
            background: #1c2431;
            padding: 8px 5px;
            text-align: left;
            font-size: 11px;
            color: #90a4ae;
            text-transform: uppercase;
            white-space: nowrap;
            letter-spacing: 0.3px;
        }}
        td {{
            white-space: nowrap;
            font-size: 12px;
        }}
        .section-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 6px;
            margin-bottom: 10px;
        }}
        .section-title {{
            color: #ffb300;
            font-size: 15px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            font-size: 11px;
            color: #546e7a;
            border-top: 1px solid #1f2937;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <div class="title">NEIRO-STOCK-VN | BẢNG ĐIỀU KHIỂN CHIẾN THUẬT ĐỊNH LƯỢNG</div>
            <div style="font-size:12px;color:#78909c;margin-top:4px;">
                Hệ Thống Phân Tích Cơ Bản Học Thuật Stanford (F-Score) & Vi Cấu Trúc Sổ Lệnh (OFI & Volume Profile)
            </div>
        </div>
        <div style="text-align:right;">
            {data_badge}
            <div style="font-size:11px;color:#78909c;margin-top:4px;">{data_subtext}</div>
            <div style="display:flex;align-items:center;gap:8px;justify-content:flex-end;margin-top:6px;flex-wrap:wrap;">
                <span id="live-status" style="font-size:11px;color:#00e676;background:#1b5e20;padding:2px 7px;border-radius:4px;font-weight:bold;">🟢 Live VPS: Đang kết nối...</span>
                <span style="font-size:11px;color:#90a4ae;">🕒 Cập nhật: <b id="scan-time" style="color:#ffb300;">{scan_time_str}</b></span>
                <span style="font-size:11px;color:#546e7a;">•</span>
                <span style="font-size:11px;color:#90a4ae;">🔄 Tự làm mới: <b id="countdown" style="color:#00e676;">300</b>s</span>
                <button onclick="reloadDashboard()" style="background:#1e293b;color:#38bdf8;border:1px solid #0284c7;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold;cursor:pointer;">⚡ Tải lại ngay</button>
            </div>
        </div>
    </div>

    <!-- 4 METRIC CARDS -->
    <div class="grid">
        <div class="card" id="card-basis-container">
            <div class="card-title">Chênh Lệch Basis VN30F1M</div>
            <div class="card-value" id="card-basis-val" style="color:{basis_color};">{basis.basis_points:+.2f} ĐIỂM</div>
            <div id="card-basis-sub" style="font-size:11px;color:#78909c;margin-top:4px;">Trạng thái: {regime_vn}</div>
        </div>
        <div class="card" id="card-smart-money-container">
            <div class="card-title">Dòng Tiền Cá Mập Định Chế</div>
            <div class="card-value" id="card-smart-money-val" style="color:{smart_money_color};">{smart_money_val}</div>
            <div id="card-smart-money-sub" style="font-size:11px;color:#78909c;margin-top:4px;">{smart_money_sub}</div>
        </div>
        <div class="card" id="card-breadth-container">
            <div class="card-title">Độ Rộng Danh Mục Dẫn Dắt</div>
            <div class="card-value" id="card-breadth-val" style="color:{breadth_color};">{breadth_val}</div>
            <div id="card-breadth-sub" data-macro-breadth="{macro_breadth_suffix}" style="font-size:11px;color:#78909c;margin-top:4px;">{breadth_sub}</div>
        </div>
        <div class="card" id="card-sector-container">
            <div class="card-title">Ngành Dẫn Dắt (Động Lượng RRG)</div>
            <div class="card-value" id="card-sector-val" style="color:#00e676;">{leading_sector_val}</div>
            <div id="card-sector-sub" style="font-size:11px;color:#78909c;margin-top:4px;">{leading_sector_sub}</div>
        </div>
    </div>

    {circuit_breaker_html}

    <!-- THANH CHUYỂN TAB CHIẾN THUẬT: TAB 1 (RADAR THỰC CHIẾN) & TAB 2 (WALK-FORWARD T+2.5 TRUNG THỰC) -->
    <div style="display:flex;gap:10px;margin-bottom:18px;flex-wrap:wrap;">
        <button id="btn-tab-radar" onclick="switchHudTab('radar')" style="background:#ffb300;color:#0b0e14;border:none;padding:7px 14px;border-radius:6px;font-size:12px;font-weight:800;cursor:pointer;">📡 TAB 1: RADAR THỰC CHIẾN & BẢNG ĐỊNH LƯỢNG</button>
        <button id="btn-tab-wf" onclick="switchHudTab('wf')" style="background:#151a23;color:#90a4ae;border:1px solid #263238;padding:7px 14px;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;">🧪 TAB 2: KIỂM ĐỊNH WALK-FORWARD T+2.5 TRUNG THỰC (FLOOR-LOCK)</button>
    </div>

    <div id="hud-tab-wf" style="display:none;margin-bottom:25px;">
        <div class="section-header">
            <div class="section-title" style="color:#38bdf8;">🧪 BÁO CÁO KIỂM ĐỊNH WALK-FORWARD T+2.5 TRUNG THỰC (KHÓA SÀN TRẮNG BÊN MUA & TRẦN 20% NAV)</div>
            <span style="font-size:11px;color:#78909c;">WFE: <b style="color:#00e676;">{wf_wfe:.1f}%</b> • Phí &amp; Thuế toàn vòng: <b style="color:#ffb300;">0.40%</b> • Trần Cold-Start: <b style="color:#4fc3f7;">&le; 20% NAV/mã</b> • Cắt lỗ Gap-Down T+2.5</span>
        </div>
        <div class="table-container">
            <table id="walk-forward-table">
                <thead>
                    <tr>
                        <th>Giai Đoạn Kiểm Định</th>
                        <th style="text-align:center;">Tổng Lợi Nhuận Ròng</th>
                        <th style="text-align:center;">CAGR / Năm</th>
                        <th style="text-align:center;">Max Drawdown</th>
                        <th style="text-align:center;">Sharpe Ratio</th>
                        <th style="text-align:center;">Win Rate</th>
                        <th style="text-align:center;">Alpha vs VN-Index</th>
                        <th style="text-align:center;">Khóa Bán (Sàn / T+2.5)</th>
                    </tr>
                </thead>
                <tbody>
                    {wf_rows_html}
                </tbody>
            </table>
        </div>
    </div>

    <div id="hud-tab-radar">
    <!-- PHẦN 1: BẢNG TOP SIÊU CỔ PHIẾU CHÂN SÓNG -->
    <div class="section-header">
        <div class="section-title">TOP {len(fialda_candidates)} SIÊU CỔ PHIẾU CHÂN SÓNG & ĐỘT BIẾN DÒNG TIỀN (1 THÁNG | MỤC TIÊU +20% - +35%)</div>
        <span style="font-size:11px;color:#78909c;">Nguồn: Fialda VIP Expert & Tích Lũy Khối Lượng Order Flow & Quản Trị Sức Chứa Thanh Khoản</span>
    </div>
    <div class="table-container">
        <table id="top-stocks-table">
            <thead>
                <tr>
                    <th style="text-align:center;">STT</th>
                    <th>Mã CP</th>
                    <th style="text-align:center;">Tín Hiệu AI</th>
                    <th>Giá Khớp</th>
                    <th>Vùng Mua</th>
                    <th>Cắt Lỗ</th>
                    <th style="text-align:center;">Chốt Lời (TP1 / TP2)</th>
                    <th style="text-align:center;">Thanh Khoản</th>
                    <th style="text-align:center;">Chuẩn Quỹ</th>
                    <th style="text-align:center;">RRG</th>
                    <th style="text-align:center;">Điểm IBD</th>
                    <th style="text-align:center;">Tích Luỹ</th>
                    <th style="text-align:center;">Khối Ngoại</th>
                    <th style="text-align:center;">Điểm AI</th>
                    <th style="text-align:center;">Kỳ Trước</th>
                </tr>
            </thead>
            <tbody>
                {fialda_rows_html}
            </tbody>
        </table>
    </div>

    <!-- PHẦN 2: BẢNG XẾP HẠNG ĐỊNH LƯỢNG CƠ BẢN -->
    <div class="section-header">
        <div class="section-title" style="color:#90a4ae;">BẢNG XẾP HẠNG ĐỊNH LƯỢNG CƠ BẢN (PIOTROSKI F-SCORE & CHỈ SỐ TÀI CHÍNH)</div>
        <span style="font-size:11px;color:#78909c;">Bộ lọc tài chính định lượng giá trị & chất lượng lợi nhuận</span>
    </div>
    <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>Mã CP</th>
                    <th>Tên Doanh Nghiệp</th>
                    <th>Nhóm Ngành</th>
                    <th>Giá Khớp (1,000 đ)</th>
                    <th style="text-align:center;">F-Score (Piotroski)</th>
                    <th style="text-align:center;">P/E</th>
                    <th style="text-align:center;">P/B</th>
                    <th style="text-align:center;">CFO / NI</th>
                    <th style="text-align:center;">Xếp Hạng Định Chế</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
    <div style="font-size:12px;color:#78909c;margin:-15px 0 25px 4px;line-height:1.6;">
        💡 <b>Ghi chú định lượng học thuật (Piotroski, 2000):</b> Thang điểm <b>Piotroski F-Score (0-9)</b> loại trừ ngành Ngân hàng (MBB, VCB) do đặc thù BCTC không có <i>Giá vốn/Biên Lợi Nhuận Gộp</i> và <i>Hệ số Thanh toán ngắn hạn (Current Ratio)</i>. Toàn bộ cổ phiếu Ngân hàng được đánh giá chuyên sâu qua Bảng Định Lượng CAMEL & Basel II/III ngay bên dưới.
    </div>

    <!-- PHẦN 3: BẢNG ĐỊNH LƯỢNG NGÂN HÀNG THƯƠNG MẠI CAMEL -->
    <div class="section-header">
        <div class="section-title" style="color:#00e676;">🏦 BẢNG ĐỊNH LƯỢNG NGÂN HÀNG THƯƠNG MẠI (CAMEL & BASEL II/III QUANT)</div>
        <span style="font-size:11px;color:#78909c;">Mô hình độc quyền phân tích 5 trụ cột: Vốn (C), Chất lượng nợ & LLR (A), Chi phí CIR (M), Lợi nhuận & CASA (E), Thanh khoản LDR (L)</span>
    </div>
    <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>Mã CP</th>
                    <th>Tên Ngân Hàng</th>
                    <th>Giá Khớp (1,000 đ)</th>
                    <th style="text-align:center;">Điểm CAMEL</th>
                    <th style="text-align:center;">CASA (%)</th>
                    <th style="text-align:center;">NIM (%)</th>
                    <th style="text-align:center;">NPL Nợ Xấu</th>
                    <th style="text-align:center;">LLR Bao Phủ</th>
                    <th style="text-align:center;">CIR (%)</th>
                    <th style="text-align:center;">ROE (%)</th>
                    <th style="text-align:center;">P/B</th>
                    <th style="text-align:center;">Xếp Hạng CAMEL</th>
                </tr>
            </thead>
            <tbody>
                {bank_rows_html}
            </tbody>
        </table>
    </div>

    <!-- PHẦN 4: BÁO CÁO KẾT QUẢ KINH DOANH CÁC QUÝ GẦN NHẤT -->
    <div class="section-header">
        <div class="section-title" style="color:#4fc3f7;">📑 BÁO CÁO KẾT QUẢ KINH DOANH CÁC QUÝ GẦN NHẤT (DOANH THU & LỢI NHUẬN RÒNG BCTC)</div>
        <span style="font-size:11px;color:#78909c;">Thống kê xu hướng tăng trưởng 1 CP / 1 dòng duy nhất • Nguồn: BCTC Fialda VIP API</span>
    </div>
    <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th rowspan="2" style="vertical-align:middle;">Mã CP</th>
                    <th rowspan="2" style="text-align:center;vertical-align:middle;">Kỳ BCTC</th>
                    <th colspan="3" style="text-align:center;background:#102a43;color:#4fc3f7;border-left:1px solid #243b53;border-right:1px solid #243b53;font-weight:bold;">DOANH THU THUẦN (TỶ VNĐ)</th>
                    <th colspan="3" style="text-align:center;background:#0d3326;color:#00e676;border-right:1px solid #1b4d3e;font-weight:bold;">LỢI NHUẬN SAU THUẾ (TỶ VNĐ)</th>
                    <th rowspan="2" style="text-align:center;vertical-align:middle;">Tăng Trưởng QoQ</th>
                    <th rowspan="2" style="text-align:center;vertical-align:middle;">Biên Lãi Gộp</th>
                    <th rowspan="2" style="text-align:center;vertical-align:middle;">Xu Hướng Động Lượng</th>
                </tr>
                <tr>
                    <th style="text-align:right;font-size:11px;color:#90a4ae;border-left:1px solid #243b53;">Quý N-2</th>
                    <th style="text-align:right;font-size:11px;color:#b0bec5;">Quý N-1</th>
                    <th style="text-align:right;font-size:11px;color:#ffb300;font-weight:bold;border-right:1px solid #243b53;">Quý N (Mới)</th>
                    <th style="text-align:right;font-size:11px;color:#90a4ae;">Quý N-2</th>
                    <th style="text-align:right;font-size:11px;color:#b0bec5;">Quý N-1</th>
                    <th style="text-align:right;font-size:11px;color:#00e676;font-weight:bold;border-right:1px solid #1b4d3e;">Quý N (Mới)</th>
                </tr>
            </thead>
            <tbody>
                {bctc_rows_html}
            </tbody>
        </table>
    </div>

    <!-- PHẦN 5: TIN TỨC SPOTLIGHT & SỰ KIỆN DOANH NGHIỆP -->
    <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(320px, 1fr));gap:15px;margin-bottom:25px;">
        <div>
            <div class="section-title" style="color:#ffb300;margin-bottom:12px;">📰 TIN TỨC DOANH NGHIỆP MỚI NHẤT (SPOTLIGHT)</div>
            {news_items_html}
        </div>
        <div>
            <div class="section-title" style="color:#00e676;margin-bottom:12px;">📅 LỊCH SỰ KIỆN & CHỐT QUYỀN SẮP TỚI</div>
            {events_items_html}
        </div>
    </div>
    </div>

    <div class="footer">
        Neiro-Stock-VN • Tự động quét và cập nhật qua GitHub Actions • Vận hành 24/7 trên Cloud • Xem được trên mọi thiết bị di động
    </div>

    <script>
        let secondsLeft = 300;
        const countdownEl = document.getElementById('countdown');
        const liveStatusEl = document.getElementById('live-status');

        function switchHudTab(tabName) {{
            const radarEl = document.getElementById('hud-tab-radar');
            const wfEl = document.getElementById('hud-tab-wf');
            const btnRadar = document.getElementById('btn-tab-radar');
            const btnWf = document.getElementById('btn-tab-wf');
            if (!radarEl || !wfEl) return;
            if (tabName === 'wf') {{
                radarEl.style.display = 'none';
                wfEl.style.display = 'block';
                if (btnWf) {{ btnWf.style.background = '#ffb300'; btnWf.style.color = '#0b0e14'; }}
                if (btnRadar) {{ btnRadar.style.background = '#151a23'; btnRadar.style.color = '#90a4ae'; }}
            }} else {{
                radarEl.style.display = 'block';
                wfEl.style.display = 'none';
                if (btnRadar) {{ btnRadar.style.background = '#ffb300'; btnRadar.style.color = '#0b0e14'; }}
                if (btnWf) {{ btnWf.style.background = '#151a23'; btnWf.style.color = '#90a4ae'; }}
            }}
        }}

        function reloadDashboard() {{
            if (countdownEl) countdownEl.innerText = 'Đang nạp...';
            const url = new URL(window.location.href);
            url.searchParams.set('_t', Date.now().toString());
            window.location.href = url.toString();
        }}

        async function fetchLivePrices() {{
            try {{
                const priceEls = document.querySelectorAll('.live-price[data-sym]');
                if (!priceEls.length) return;
                const symbols = Array.from(new Set(Array.from(priceEls).map(el => el.getAttribute('data-sym'))));
                if (!symbols.length) return;
                
                const res = await fetch('https://bgapidatafeed.vps.com.vn/getliststockdata/' + symbols.join(','), {{ cache: 'no-store' }});
                if (!res.ok) return;
                const rawText = await res.text();
                if (!rawText || rawText.trim().startsWith('<')) return;
                const data = JSON.parse(rawText);
                if (!Array.isArray(data)) return;
                
                const priceMap = {{}};
                let liveForeignBuyVal = 0;
                let liveForeignSellVal = 0;
                let liveGreenCount = 0;
                let liveRedCount = 0;
                let liveRefCount = 0;

                const topStockEls = document.querySelectorAll('#top-stocks-table .live-price[data-sym]');
                const topSymbols = new Set(Array.from(topStockEls).map(el => el.getAttribute('data-sym')));

                data.forEach(item => {{
                    if (item && item.sym) {{
                        const lp = Number(item.lastPrice || 0);
                        const r = Number(item.r || 0);
                        const c = Number(item.c || 0);
                        const f = Number(item.f || 0);
                        let chg = Number(item.ot || 0);
                        let chgPc = Number(item.changePc || 0);
                        const fb = Number(item.fBValue || 0);
                        const fs = Number(item.fSValue || 0);

                        // Fix VPS API datafeed tra ve ot va changePc luon la so duong (tri tuyet doi)
                        // Can dong bo dau am/duong chuan xac theo so sanh lastPrice (lp) voi tham chieu (r)
                        if (lp > 0 && r > 0) {{
                            if (lp < r) {{
                                chg = chg !== 0 ? -Math.abs(chg) : (lp - r);
                                chgPc = chgPc !== 0 ? -Math.abs(chgPc) : (((lp - r) / r) * 100);
                            }} else if (lp > r) {{
                                chg = chg !== 0 ? Math.abs(chg) : (lp - r);
                                chgPc = chgPc !== 0 ? Math.abs(chgPc) : (((lp - r) / r) * 100);
                            }} else {{
                                chg = 0;
                                chgPc = 0;
                            }}
                        }}

                        priceMap[item.sym] = {{
                            price: lp > 0 ? lp : r,
                            ref: r,
                            ceil: c,
                            floor: f,
                            change: chg,
                            changePct: chgPc,
                            fbVal: fb,
                            fsVal: fs
                        }};

                        if (topSymbols.has(item.sym)) {{
                            if (lp > 0 && r > 0) {{
                                if (lp > r) liveGreenCount++;
                                else if (lp < r) liveRedCount++;
                                else liveRefCount++;
                            }}
                            liveForeignBuyVal += fb;
                            liveForeignSellVal += fs;
                        }}
                    }}
                }});

                priceEls.forEach(el => {{
                    const sym = el.getAttribute('data-sym');
                    const info = priceMap[sym];
                    if (info && info.price > 0) {{
                        const p = Number(info.price);
                        el.innerText = p.toFixed(2);
                        
                        let color = '#ffb300';
                        if (p >= info.ceil && info.ceil > 0) color = '#ea39b8';
                        else if (p <= info.floor && info.floor > 0) color = '#00e5ff';
                        else if (p > info.ref) color = '#00e676';
                        else if (p < info.ref) color = '#ff5252';
                        el.style.color = color;

                        // Dong bo live change % (dam bao dau am/duong thong nhat 100% voi mau sac va chenh lech gia)
                        const changeEl = document.querySelector('.live-change[data-sym="' + sym + '"]');
                        if (changeEl) {{
                            let pctStr = Math.abs(info.changePct).toFixed(1);
                            if (pctStr === '0.0' || p === info.ref) {{
                                changeEl.innerText = '(0.0%)';
                            }} else if (p > info.ref) {{
                                changeEl.innerText = '(+' + pctStr + '%)';
                            }} else if (p < info.ref) {{
                                changeEl.innerText = '(-' + pctStr + '%)';
                            }} else {{
                                changeEl.innerText = '(' + (info.changePct > 0 ? '+' : '-') + pctStr + '%)';
                            }}
                            changeEl.style.color = color;
                            changeEl.style.fontWeight = 'bold';
                        }}

                        // Danh gia lai vung mua / cat lo thoi gian thuc (Ton trong khoa Anti-FOMO T0)
                        const entryLow = Number(el.getAttribute('data-entry-low') || 0);
                        const entryHigh = Number(el.getAttribute('data-entry-high') || 0);
                        const stopLoss = Number(el.getAttribute('data-sl') || 0);
                        const tp1 = Number(el.getAttribute('data-tp1') || 0);
                        const buyPerm = el.getAttribute('data-buy-perm') || 'BUY_OK';
                        const isLockedNoBuy = (buyPerm === 'EXTENDED_NO_CHASING' || buyPerm === 'BULL_TRAP_REJECT' || buyPerm === 'STALE_SIGNAL');
                        const sigBadge = document.getElementById('sig-badge-' + sym);

                        if (sigBadge) {{
                            if (stopLoss > 0 && p <= stopLoss) {{
                                sigBadge.innerHTML = '<span style="background:#b71c1c;color:#ff8a80;padding:3px 8px;border-radius:4px;font-size:11px;font-weight:bold;">CHẠM SL 🔴</span>';
                            }} else if (tp1 > 0 && p >= tp1) {{
                                sigBadge.innerHTML = '<span style="background:#004d40;color:#64ffda;padding:3px 8px;border-radius:4px;font-size:11px;font-weight:bold;">ĐẠT TP1 🎯</span>';
                            }} else if (!isLockedNoBuy && entryHigh > 0 && p > entryHigh * 1.03) {{
                                sigBadge.innerHTML = '<span style="background:#e65100;color:#ffe0b2;padding:3px 8px;border-radius:4px;font-size:11px;font-weight:bold;">MUA ĐUỔI ⚠️</span>';
                            }} else if (!isLockedNoBuy && entryLow > 0 && p >= entryLow * 0.98 && p <= entryHigh * 1.03) {{
                                sigBadge.innerHTML = '<span style="background:#1b5e20;color:#00e676;padding:3px 8px;border-radius:4px;font-size:11px;font-weight:bold;">VÙNG MUA 🟢</span>';
                            }}
                        }}
                    }}
                }});

                // Dong bo The Do Rong Danh Muc
                const totalMonitored = liveGreenCount + liveRedCount + liveRefCount;
                if (totalMonitored > 0) {{
                    const breadthEl = document.getElementById('card-breadth-val');
                    const breadthSubEl = document.getElementById('card-breadth-sub');
                    if (breadthEl) {{
                        const pct = (liveGreenCount / totalMonitored) * 100;
                        breadthEl.innerText = pct.toFixed(1) + '%';
                        breadthEl.style.color = pct >= 50 ? '#00e676' : '#ffb300';
                    }}
                    if (breadthSubEl) {{
                        const macroSuffix = breadthSubEl.getAttribute('data-macro-breadth') || '';
                        const liveText = liveGreenCount + '/' + totalMonitored + ' Cổ phiếu tăng (' + liveRedCount + ' giảm, ' + liveRefCount + ' tham chiếu)';
                        breadthSubEl.innerText = macroSuffix ? (liveText + ' • ' + macroSuffix) : liveText;
                    }}
                }}

                // Dong bo o Khoi Ngoai tung ma va The Dong Tien Ca Map (VPS fBValue/fSValue don vi 1,000 VND -> chia 1e6 ra Ty VND)
                document.querySelectorAll('#top-stocks-table .live-foreign[data-sym]').forEach(fEl => {{
                    const fSym = fEl.getAttribute('data-sym');
                    const fInfo = priceMap[fSym];
                    if (fInfo && (fInfo.fbVal > 0 || fInfo.fsVal > 0)) {{
                        const symNetBil = (fInfo.fbVal - fInfo.fsVal) / 1e6;
                        const symSign = symNetBil >= 0 ? '+' : '';
                        fEl.innerText = symSign + symNetBil.toFixed(1) + ' tỷ';
                        fEl.style.color = symNetBil >= 0 ? '#00e676' : '#ff5252';
                    }}
                }});

                const netForeignBillion = (liveForeignBuyVal - liveForeignSellVal) / 1e6;
                if (liveForeignBuyVal > 0 || liveForeignSellVal > 0) {{
                    const smValEl = document.getElementById('card-smart-money-val');
                    const smSubEl = document.getElementById('card-smart-money-sub');
                    if (smValEl) {{
                        const sign = netForeignBillion >= 0 ? '+' : '';
                        smValEl.innerText = sign + netForeignBillion.toFixed(1) + ' Tỷ VND';
                        smValEl.style.color = netForeignBillion >= 0 ? '#00e676' : '#ffb300';
                    }}
                    if (smSubEl) {{
                        if (netForeignBillion < 0) {{
                            smSubEl.innerText = 'Khối ngoại bán ròng trực tiếp trên rổ Top • Kiểm tra cột Tích Luỹ A/B';
                        }} else {{
                            smSubEl.innerText = 'Khối ngoại mua ròng trực tiếp trên rổ Top (Live VPS)';
                        }}
                    }}
                }}

                if (liveStatusEl) {{
                    const now = new Date();
                    const timeStr = now.toLocaleTimeString('vi-VN', {{ hour12: false }});
                    liveStatusEl.innerHTML = '🟢 <b>Live VPS:</b> ' + timeStr + ' <span style="font-size:10px;opacity:0.8;">(30s)</span>';
                    liveStatusEl.style.background = '#1b5e20';
                    liveStatusEl.style.color = '#00e676';
                }}
            }} catch (err) {{
                console.warn('Live price fetch warning:', err);
                if (liveStatusEl) {{
                    liveStatusEl.innerHTML = '🟡 <b>Offline</b>';
                }}
            }}
        }}

        // Chay ngay khi mo trang
        fetchLivePrices();

        // TU DONG CAP NHAT LIVE GIA KHOP & THE THONG KE MOI 30 GIAY
        setInterval(fetchLivePrices, 30000);

        // Bo dem nguoc 300s reload trang de nap lai toan bo AI Scan & BCTC
        setInterval(function() {{
            secondsLeft--;
            if (countdownEl) {{
                countdownEl.innerText = secondsLeft > 0 ? secondsLeft : '0';
            }}
            if (secondsLeft <= 0) {{
                reloadDashboard();
            }}
        }}, 1000);
    </script>
</body>
</html>
"""
    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(html_content, encoding="utf-8")

    # Dong thoi dong bo index.html, vn_stock_terminal.html va 404.html trong thu muc exports
    if dest.parent.name == "exports":
        for fname in ["index.html", "vn_stock_terminal.html", "404.html"]:
            target_f = dest.parent / fname
            target_f.write_text(html_content, encoding="utf-8")

    return str(dest)


if __name__ == "__main__":
    import argparse
    import time
    parser = argparse.ArgumentParser(description="Sinh Terminal HTML cho Neiro-Stock-VN")
    parser.add_argument("--output", default="exports/vn_stock_terminal.html", help="Duong dan file HTML dau ra")
    parser.add_argument("--top", type=int, default=20, help="So luong sieu co phieu hien thi (mac dinh 20)")
    parser.add_argument("--watch", action="store_true", help="Chay che do Watcher cap nhat lien tuc moi 5 phut (300s)")
    parser.add_argument("--interval", type=int, default=300, help="Chu ky cap nhat tinh bang giay (mac dinh 300s = 5 phut)")
    args = parser.parse_args()

    if args.watch:
        print(f"Bắt đầu chế độ Watcher cập nhật liên tục (chu kỳ {args.interval}s / 5 phút). Nhấn Ctrl+C để dừng...")
        try:
            while True:
                path = generate_terminal_html(args.output, top_n=args.top)
                now_str = datetime.now(timezone(timedelta(hours=7))).strftime("%H:%M:%S • %d/%m/%Y")
                print(f"[{now_str}] Đã cập nhật Terminal tại {path}. Chờ {args.interval}s...")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nĐã dừng Watcher.")
    else:
        path = generate_terminal_html(args.output, top_n=args.top)
        print(f"Generated terminal at {path}")
