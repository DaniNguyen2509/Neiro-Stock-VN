from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from src.collector.data_loader import get_mock_vietnam_stocks
from src.collector.vn_market_client import VNMarketClient
from src.fundamental_engine.screener import screen_stocks
from src.microstructure_engine.basis_tracker import analyze_vn30_basis
from src.collector.fialda_scanner import FialdaCandidate, FialdaScanner, retain_same_day_active_signals
from src.risk_engine.position_sizer import calculate_retail_t25_position_size
from src.sector_engine.market_breadth import parse_market_breadth_dict
from src.backtesting.walk_forward import WalkForwardCoordinator
from src.hud.quant_search import build_quant_search_snapshot, generate_quant_search_cockpit_html

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
    active_signals: Optional[Dict[str, Any]] = None,
    market_foreign_net_billion: Optional[float] = None,
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

    # ADR-023: Duy tri cac vi the da khuyen nghi trong ngay con hieu luc tren Tab 1
    if fialda_candidates:
        fialda_candidates = retain_same_day_active_signals(
            candidates=fialda_candidates,
            active_signals=active_signals,
            now_dt=None,
        )

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

    # 1. Tinh dong tien Ca map (Foreign Net Value) dong bo that tu danh muc Top & So sanh Toan San
    total_cands = len(fialda_candidates) if fialda_candidates else 0
    total_foreign = sum(getattr(c, "foreign_net_value_billion", 0.0) for c in fialda_candidates) if fialda_candidates else 0.0

    # Trich xuat dong tien khoi ngoai toan san tu market_breadth
    if market_foreign_net_billion is None and isinstance(market_breadth, dict):
        raw_m_fnet = market_breadth.get("foreignNetValue")
        if raw_m_fnet is None:
            fb = market_breadth.get("totalForeignBuyValue") if market_breadth.get("totalForeignBuyValue") is not None else market_breadth.get("foreignBuyValue")
            fs = market_breadth.get("totalForeignSellValue") if market_breadth.get("totalForeignSellValue") is not None else market_breadth.get("foreignSellValue")
            if fb is not None or fs is not None:
                raw_m_fnet = float(fb or 0.0) - float(fs or 0.0)
        if raw_m_fnet is not None:
            raw_f_val = float(raw_m_fnet)
            market_foreign_net_billion = round(raw_f_val / 1e9, 1) if abs(raw_f_val) > 1e6 else round(raw_f_val, 1)

    m_net_str = f"{market_foreign_net_billion:.1f}" if market_foreign_net_billion is not None else "N/A"

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

    if market_foreign_net_billion is not None:
        delta_flow = total_foreign - market_foreign_net_billion
        smart_money_val = f'Top: {total_foreign:+.1f}t <span style="font-size:13px;color:#64748b;font-weight:normal;">|</span> <span style="font-size:13px;color:#94a3b8;">Sàn: {market_foreign_net_billion:+.1f}t</span>'
        smart_money_color = "#00e676" if total_foreign >= 0 else "#ff5252"
        if total_foreign > 0 and market_foreign_net_billion <= 0:
            smart_money_sub = f'🟢 ĐÃI CÁT TÌM VÀNG • Độ lệch: <b style="color:#00e676;">{delta_flow:+.1f}t</b> gom Top'
        elif total_foreign > 0 and market_foreign_net_billion > 0:
            smart_money_sub = f'🟢🟢 SIÊU SÓNG ĐỒNG THUẬN • Độ lệch: <b style="color:#00e676;">{delta_flow:+.1f}t</b>'
        elif total_foreign <= 0 and market_foreign_net_billion > 0:
            smart_money_sub = f'🟡 KÉO TRỤ PHÂN HÓA • Rổ Top bị xả ({delta_flow:+.1f}t)'
        else:
            smart_money_sub = f'🔴 ÁP LỰC XẢ DIỆN RỘNG • Độ lệch: {delta_flow:+.1f}t'
    else:
        if total_foreign >= 0:
            smart_money_val = f"+{total_foreign:.1f} Tỷ VND"
            smart_money_color = "#00e676"
            smart_money_sub = f"Rổ Top: Khối ngoại mua ròng • {absorbed_cnt}/{max(total_cands, 1)} mã giữ cấu trúc tích lũy"
        elif absorbed_cnt > dist_cnt and not circuit_breaker_active:
            smart_money_val = f"{total_foreign:.1f} Tỷ VND"
            smart_money_color = "#ffb300"
            smart_money_sub = f"Rổ Top: Ngoại bán ròng • Dòng tiền Nội gom cân hàng ({absorbed_cnt}/{max(total_cands, 1)} mã nền A/B)"
        else:
            smart_money_val = f"{total_foreign:.1f} Tỷ VND"
            smart_money_color = "#ff5252"
            smart_money_sub = f"Rổ Top: Khối ngoại bán ròng • Cảnh báo {dist_cnt}/{max(total_cands, 1)} mã áp lực xả (Thận trọng T+2.5)"

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

    # Chuan bi du lieu Tab 2 & Tab 3: So Cai Vi The Khuyen Nghi, Doi Soat TP/SL & Chi So Tai Thoi Diem Khuyen Nghi (T0)
    from src.risk_engine.signal_tracker import (
        SignalTracker,
        analyze_t0_sl_vs_tp_attribution,
        evaluate_t0_signal_quality_and_diagnosis,
    )

    loaded_from_default_file = active_signals is None
    if active_signals is None:
        try:
            active_signals = SignalTracker().load_active_signals()
        except Exception:
            active_signals = {}

    active_running: List[Any] = []
    closed_signals: List[Any] = []
    seen_signal_keys: set[str] = set()

    if active_signals:
        for s in active_signals.values():
            st_val = getattr(s, "status", "")
            is_cl = getattr(s, "is_closed", False)
            sig_key = str(getattr(s, "signal_id", "") or f"{getattr(s, 'symbol', '')}_{getattr(s, 'first_signal_date', '')}")
            seen_signal_keys.add(sig_key)
            if is_cl or st_val in ("TP2_REACHED", "STOPPED_OUT", "TIME_OUT"):
                closed_signals.append(s)
            else:
                active_running.append(s)

    # Khi chạy thực tế (loaded_from_default_file) hoặc khi chưa có mã đóng, nạp thêm các vị thế đã đóng từ kho lưu trữ
    # (Ưu tiên toàn bộ bản ghi chuẩn v2, các lệnh đạt TP2, và các lệnh từ 28/10 có đầy đủ chỉ số Fialda thực tế tại T0)
    if loaded_from_default_file or not closed_signals:
        try:
            archived = SignalTracker().load_archived_signals()
            for s in archived.values():
                if not getattr(s, "is_closed", False):
                    continue
                sig_key = str(getattr(s, "signal_id", "") or f"{getattr(s, 'symbol', '')}_{getattr(s, 'first_signal_date', '')}")
                if sig_key in seen_signal_keys:
                    continue
                is_v2 = getattr(s, "schema_version", "") == "v2"
                is_tp2 = getattr(s, "status", "") == "TP2_REACHED"
                has_real_t0_catalyst = bool(str(getattr(s, "catalyst", "") or "").strip())
                if is_v2 or (loaded_from_default_file and (is_tp2 or has_real_t0_catalyst)):
                    closed_signals.append(s)
                    seen_signal_keys.add(sig_key)
        except Exception:
            pass

    # Sap xep vi the dang chay mac dinh theo ngay mua gan nhat (T0 len dau), thu cap theo PnL giam dan
    active_running.sort(
        key=lambda x: (str(getattr(x, "first_signal_date", "") or ""), getattr(x, "pnl_pct", 0.0)),
        reverse=True,
    )
    closed_signals.sort(
        key=lambda x: (str(getattr(x, "first_signal_date", "") or getattr(x, "closed_at", "") or ""), getattr(x, "pnl_pct", 0.0)),
        reverse=True,
    )

    tp1_count = sum(1 for s in active_running if getattr(s, "status", "") == "TP1_REACHED")
    tp2_count = sum(1 for s in closed_signals if getattr(s, "status", "") == "TP2_REACHED")
    sl_closed_count = sum(1 for s in closed_signals if getattr(s, "status", "") == "STOPPED_OUT")
    timeout_closed_count = sum(1 for s in closed_signals if getattr(s, "status", "") == "TIME_OUT")

    # Chuan bi du lieu: Bang Tong Hop Toan Bo Vi The Khuyen Nghi & Doi Soat Chi So T0 Toan Vong (ADR-029)
    all_recommended_signals: List[Any] = list(active_running) + list(closed_signals)
    t0_attribution = analyze_t0_sl_vs_tp_attribution(all_recommended_signals)
    tp_st = t0_attribution["tp_stats"]
    sl_st = t0_attribution["sl_stats"]
    to_st = t0_attribution["timeout_stats"]
    act_st = t0_attribution["active_stats"]

    t0_lessons_rows_html = ""
    for lesson in t0_attribution["lessons"]:
        t0_lessons_rows_html += f"""
        <tr style="border-bottom:1px solid #1f2937;">
            <td style="padding:8px 6px;font-weight:bold;color:#ffb300;">{lesson['metric']}</td>
            <td style="padding:8px 6px;color:#00e676;font-weight:600;">{lesson['tp_val']}</td>
            <td style="padding:8px 6px;color:#ff8a80;font-weight:600;">{lesson['sl_val']}</td>
            <td style="padding:8px 6px;text-align:center;"><span style="background:#1e293b;color:#38bdf8;border:1px solid #0284c7;padding:2px 7px;border-radius:4px;font-size:10.5px;font-weight:bold;">{lesson['weight']}</span></td>
            <td style="padding:8px 6px;color:#e2e8f0;white-space:normal;line-height:1.4;">{lesson['action']}</td>
        </tr>
        """

    unified_positions_rows_html = ""
    if not all_recommended_signals:
        unified_positions_rows_html = """
        <tr>
            <td colspan="8" style="padding:25px;text-align:center;color:#78909c;">
                Hiện không có vị thế nào đang nắm giữ. Mọi khuyến nghị trước đó đã đạt mục tiêu chốt lời hoặc đã đóng bảo toàn vốn.
            </td>
        </tr>
        """
    else:
        for idx, sig_item in enumerate(all_recommended_signals, 1):
            diag_info = evaluate_t0_signal_quality_and_diagnosis(sig_item)
            cat = diag_info["category"]
            eff_price = diag_info["effective_price"]
            eff_pnl = diag_info["effective_pnl_pct"]
            diag_text = diag_info["diagnosis"]

            is_act = not getattr(sig_item, "is_closed", False) and getattr(sig_item, "status", "") not in ("TP2_REACHED", "STOPPED_OUT", "TIME_OUT")
            active_flag = "1" if is_act else "0"

            s_sym = getattr(sig_item, "symbol", "")
            s_type = str(getattr(sig_item, "signal_type", "CHO_MUA_CHAN_SONG") or "CHO_MUA_CHAN_SONG")
            if "CHO_MUA" in s_type:
                s_type_badge = '<span style="background:#1b5e20;color:#00e676;padding:1px 5px;border-radius:3px;font-size:9.5px;font-weight:bold;">CHÂN SÓNG</span>'
            elif "THE_CHE" in s_type:
                s_type_badge = '<span style="background:#311b92;color:#b388ff;padding:1px 5px;border-radius:3px;font-size:9.5px;font-weight:bold;">THỂ CHẾ GOM</span>'
            else:
                s_type_badge = '<span style="background:#01579b;color:#29b6f6;padding:1px 5px;border-radius:3px;font-size:9.5px;font-weight:bold;">ĐỘT BIẾN GT</span>'

            s_status = str(getattr(sig_item, "status", "ACTIVE") or "ACTIVE")
            s_outcome = str(getattr(sig_item, "outcome_label", "ACTIVE") or "ACTIVE")
            buy_perm = getattr(sig_item, "buy_permission", "BUY_OK")
            s_tdays = int(getattr(sig_item, "trading_days", 0) or 0)

            if s_status == "TP2_REACHED" or s_outcome == "WIN_TP2":
                res_badge = '<span style="background:#004d40;color:#64ffda;padding:2px 7px;border-radius:4px;font-weight:bold;font-size:11px;">🏆 ĐẠT TP2</span>'
            elif s_status == "TP1_REACHED" or s_outcome == "WIN_TP1":
                res_badge = '<span style="background:#065f46;color:#6ee7b7;padding:2px 7px;border-radius:4px;font-weight:bold;font-size:11px;">🎯 ĐẠT TP1</span>'
            elif s_status == "STOPPED_OUT" or s_outcome == "STOP_LOSS":
                res_badge = '<span style="background:#b71c1c;color:#ff8a80;padding:2px 7px;border-radius:4px;font-weight:bold;font-size:11px;">🛑 CẮT LỖ</span>'
            elif s_status == "TIME_OUT" or s_outcome == "TIME_OUT":
                res_badge = '<span style="background:#374151;color:#fbbf24;padding:2px 7px;border-radius:4px;font-weight:bold;font-size:11px;">⏱️ HẾT SÓNG T+7</span>'
            else:
                res_badge = '<span style="background:#0284c7;color:#e0f2fe;padding:2px 7px;border-radius:4px;font-weight:bold;font-size:11px;">🟢 ĐANG NẮM GIỮ</span>'

            s_first = str(getattr(sig_item, "first_signal_date", "") or "")
            s_closed = str(getattr(sig_item, "closed_at", "") or getattr(sig_item, "last_updated", "") or "")
            s_t0_dt = s_first.split()[0] if s_first else "T0"
            s_cl_dt = s_closed.split()[0] if (getattr(sig_item, "is_closed", False) and s_closed) else "Đang mở"

            if is_act:
                if s_tdays == 0:
                    t_str = '<span style="background:#0284c7;color:#e0f2fe;padding:1px 5px;border-radius:3px;font-weight:bold;font-size:10.5px;">T+0 (Vừa mua)</span>'
                elif s_tdays == 1:
                    t_str = '<span style="background:#0369a1;color:#e0f2fe;padding:1px 5px;border-radius:3px;font-weight:bold;font-size:10.5px;">T+1 (Chờ hàng)</span>'
                elif s_tdays == 2:
                    t_str = '<span style="background:#047857;color:#d1fae5;padding:1px 5px;border-radius:3px;font-weight:bold;font-size:10.5px;">T+2 (Khả dụng chiều)</span>'
                else:
                    t_str = f'<span style="background:#1b5e20;color:#00e676;padding:1px 5px;border-radius:3px;font-weight:bold;font-size:10.5px;">T+{s_tdays} (Khả dụng 100%)</span>'
                time_sub = f'{t_str} • <span style="color:#94a3b8;">Vào: {s_t0_dt}</span>'
            else:
                time_sub = f'<span style="color:#cbd5e1;font-weight:bold;">T+{s_tdays}</span> • Vào: {s_t0_dt} &rarr; Đóng: {s_cl_dt}'

            s_entry = float(getattr(sig_item, "entry_original", 0.0) or 0.0)
            s_cur = float(getattr(sig_item, "current_price", 0.0) or 0.0)
            s_sl = float(getattr(sig_item, "current_stop_loss", 0.0) or getattr(sig_item, "initial_stop_loss", 0.0) or 0.0)
            s_tp1 = float(getattr(sig_item, "tp1", 0.0) or 0.0)
            s_tp2 = float(getattr(sig_item, "tp2", 0.0) or 0.0)
            s_mfe = float(getattr(sig_item, "mfe_pct", 0.0) or 0.0)
            s_mae = float(getattr(sig_item, "mae_pct", 0.0) or 0.0)
            s_low = float(getattr(sig_item, "min_price_reached", 0.0) or 0.0)

            if s_status == "TP1_REACHED" and s_sl >= s_entry:
                sl_str = f'<span style="color:#00e676;font-weight:bold;">{s_sl:.2f}</span> (Hòa vốn)'
            else:
                sl_str = f'<span style="color:#ff8a80;font-weight:bold;">{s_sl:.2f}</span>'

            if s_status == "TP1_REACHED":
                tp_str = f'<span style="text-decoration:line-through;color:#78909c;">{s_tp1:.2f}</span> <b style="color:#00e676;">✓</b>/<b style="color:#38bdf8;">{s_tp2:.2f}</b>'
            else:
                tp_str = f'<span style="color:#4fc3f7;">{s_tp1:.2f}</span>/<b style="color:#38bdf8;">{s_tp2:.2f}</b>'

            if is_act:
                cur_price_html = f'<span class="live-price" data-sym="{s_sym}" style="font-weight:bold;color:#ffb300;">{s_cur:.2f}</span>'
                pnl_col = "#00e676" if eff_pnl > 0 else ("#ff5252" if eff_pnl < 0 else "#ffb300")
                pnl_s = "+" if eff_pnl > 0 else ""
                pnl_html = f'<span class="live-pnl" data-sym="{s_sym}" data-entry="{s_entry:.2f}" style="font-weight:800;color:{pnl_col};font-size:12.5px;">{pnl_s}{eff_pnl:.2f}%</span>'
            else:
                cur_price_html = f'<b style="color:#ffffff;">{eff_price:.2f}</b>'
                pnl_col = "#00e676" if eff_pnl > 0 else ("#ff5252" if eff_pnl < 0 else "#ffb300")
                pnl_s = "+" if eff_pnl > 0 else ""
                pnl_html = f'<span style="font-weight:800;color:{pnl_col};font-size:12.5px;">{pnl_s}{eff_pnl:.2f}%</span>'

            if cat == "SL":
                excursion_sub = f'<div style="font-size:10px;color:#fca5a5;">Đáy MAE: {min(s_mae, eff_pnl):.1f}%</div>'
            else:
                excursion_sub = f'<div style="font-size:10px;color:#94a3b8;">Đỉnh: +{max(s_mfe, 0.0):.1f}% / Đáy: {min(s_mae, 0.0):.1f}%</div>'

            # Action / Reason badge
            if is_act:
                if s_status == "TP1_REACHED":
                    action_badge = '<span style="background:#004d40;color:#64ffda;padding:2px 6px;border-radius:4px;font-size:10.5px;font-weight:bold;">🎯 ĐÃ CHỐT 50% TP1 — GỒNG LÃI TỚI TP2 (CẤM MUA ĐUỔI)</span>'
                elif buy_perm == "EXTENDED_NO_CHASING":
                    action_badge = '<span style="background:#e65100;color:#ffe0b2;padding:2px 6px;border-radius:4px;font-size:10.5px;font-weight:bold;">⚠️ ĐÃ TĂNG XA NỀN — CẤM MUA ĐUỔI</span>'
                elif buy_perm == "BULL_TRAP_REJECT":
                    action_badge = '<span style="background:#bf360c;color:#ffccbc;padding:2px 6px;border-radius:4px;font-size:10.5px;font-weight:bold;">⚠️ BULL-TRAP — NẮM GIỮ / CHỜ HỒI</span>'
                elif buy_perm == "STALE_SIGNAL":
                    action_badge = '<span style="background:#374151;color:#d1d5db;padding:2px 6px;border-radius:4px;font-size:10.5px;font-weight:bold;">🟠 QUÁ HẠN T+3 — THEO DÕI SÁT SL</span>'
                else:
                    action_badge = '<span style="background:#1b5e20;color:#00e676;padding:2px 6px;border-radius:4px;font-size:10.5px;font-weight:bold;">🟢 ĐANG NẮM GIỮ (CHỜ CHẠM TP)</span>'
            else:
                if s_status == "TP2_REACHED":
                    action_badge = f'<span style="color:#64ffda;font-size:11px;font-weight:600;">Đạt mục tiêu TP2 ({s_tp2:.2f}) • Hoàn tất chốt lời 100%</span>'
                elif s_status == "TIME_OUT":
                    action_badge = f'<span style="color:#fbbf24;font-size:11px;font-weight:600;">Tất toán cơ cấu danh mục sau {s_tdays} phiên (thu hồi sức mua)</span>'
                else:
                    if s_low > 0 and s_sl > 0:
                        action_badge = f'<span style="color:#ff8a80;font-size:11px;font-weight:600;">Chạm đáy chu kỳ {s_low:.2f} &le; Ngưỡng Stop {s_sl:.2f}</span>'
                    else:
                        action_badge = '<span style="color:#ff8a80;font-size:11px;font-weight:600;">Chạm ngưỡng cắt lỗ bảo toàn vốn T+2.5</span>'

            s_ai = float(getattr(sig_item, "ranking_score", 0.0) or 0.0)
            s_ibd = int(getattr(sig_item, "composite_rating", 0) or 0)
            s_rs = int(getattr(sig_item, "rs_1m", 0) or 0)
            s_ad = str(getattr(sig_item, "acc_diss_rating", "C") or "C").upper()
            s_r = float(getattr(sig_item, "rrg_r", 100.0) or 100.0)
            s_m = float(getattr(sig_item, "rrg_m", 100.0) or 100.0)
            s_fnet = float(getattr(sig_item, "foreign_net_value_billion", 0.0) or 0.0)
            s_pnet = float(getattr(sig_item, "prop_net_value_billion", 0.0) or 0.0)
            s_adtv = float(getattr(sig_item, "adtv20_billion", 0.0) or 0.0)
            s_poc = float(getattr(sig_item, "poc_price_t0", 0.0) or 0.0)
            s_atrd = float(getattr(sig_item, "atr_dist_from_poc_t0", 0.0) or 0.0)

            ibd_c = "#00e676" if s_ibd >= 75 else ("#ffb300" if s_ibd >= 60 else "#ff5252")
            ad_c = "#00e676" if s_ad in ("A", "B") else ("#ffb300" if s_ad == "C" else "#ff5252")
            ad_bg_c = "#1b5e20" if s_ad in ("A", "B") else ("#3e2723" if s_ad == "C" else "#450a0a")
            if s_r >= 100.0 and s_m >= 100.0:
                rrg_quad = '<span style="color:#00e676;font-size:10px;font-weight:bold;">Dẫn dắt</span>'
            elif s_r < 100.0 and s_m >= 100.0:
                rrg_quad = '<span style="color:#4fc3f7;font-size:10px;font-weight:bold;">Cải thiện</span>'
            elif s_r >= 100.0 and s_m < 100.0:
                rrg_quad = '<span style="color:#ffb300;font-size:10px;font-weight:bold;">Suy yếu</span>'
            else:
                rrg_quad = '<span style="color:#ff5252;font-size:10px;font-weight:bold;">Tụt hậu</span>'

            prop_str = f" • TD:<b style=\"color:{'#00e676' if s_pnet >= 0 else '#ff5252'};\">{s_pnet:+.1f}t</b>" if abs(s_pnet) >= 0.05 else ""
            poc_str = f'<span style="color:{"#00e676" if -0.5 <= s_atrd <= 0.9 else "#ffb300"};">POC:{s_poc:.2f} ({s_atrd:+.1f}ATR)</span> • TK:{s_adtv:.0f}t' if s_poc > 0 else f'TK:{s_adtv:.0f}t'

            unified_positions_rows_html += f"""
            <tr class="unified-pos-row t0-audit-row" data-cat="{cat}" data-active="{active_flag}" style="border-bottom:1px solid #1f2937;">
                <td style="padding:8px 6px;text-align:center;color:#78909c;font-weight:bold;">{idx}</td>
                <td style="padding:8px 6px;">
                    <div style="font-weight:800;color:#ffb300;font-size:13px;">{s_sym}</div>
                    <div style="margin-top:2px;">{s_type_badge}</div>
                </td>
                <td style="padding:8px 6px;text-align:center;">
                    <div>{res_badge}</div>
                    <div style="font-size:10.5px;color:#94a3b8;margin-top:3px;">
                        {time_sub}
                    </div>
                </td>
                <td style="padding:8px 6px;text-align:right;">
                    <div style="font-size:12px;color:#f8fafc;">
                        <b>{s_entry:.2f}</b> &rarr; {cur_price_html}
                    </div>
                    <div style="font-size:10px;color:#64748b;margin-top:2px;">
                        SL:{sl_str} | TP:{tp_str}
                    </div>
                </td>
                <td style="padding:8px 6px;text-align:right;">
                    <div>{pnl_html}</div>
                    {excursion_sub}
                </td>
                <td style="padding:8px 6px;text-align:left;">
                    <div style="font-size:11px;line-height:1.35;">
                        <span style="color:#ffb300;font-weight:bold;">AI:{s_ai:.1f}</span> • 
                        IBD:<b style="color:{ibd_c};">{s_ibd}</b>/RS:<b>{s_rs}</b> • 
                        TL:<span style="background:{ad_bg_c};color:{ad_c};padding:1px 5px;border-radius:3px;font-weight:bold;font-size:10px;">{s_ad}</span>
                    </div>
                    <div style="font-size:10px;color:#94a3b8;margin-top:2px;">
                        RRG:<span style="color:#38bdf8;font-weight:600;">{s_r:.1f}/{s_m:.1f}</span> ({rrg_quad})
                    </div>
                </td>
                <td style="padding:8px 6px;text-align:left;">
                    <div style="font-size:10.5px;">
                        Ngoại:<b style="color:{'#00e676' if s_fnet >= 0 else '#ff5252'};">{s_fnet:+.1f}t</b>{prop_str}
                    </div>
                    <div style="font-size:10px;color:#94a3b8;margin-top:2px;">
                        {poc_str}
                    </div>
                </td>
                <td style="padding:8px 6px;text-align:left;min-width:210px;">
                    <div style="font-size:11px;color:#cbd5e1;line-height:1.35;">{diag_text}</div>
                    <div style="margin-top:4px;" class="pos-badge" data-sym="{s_sym}" data-entry="{s_entry:.2f}" data-sl="{s_sl:.2f}" data-tp1="{s_tp1:.2f}" data-tp2="{s_tp2:.2f}">{action_badge}</div>
                </td>
            </tr>
            """

    active_positions_rows_html = unified_positions_rows_html
    closed_rows_html = ""
    t0_audit_rows_html = unified_positions_rows_html

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

    # Chuan bi du lieu Tim Kiem Dinh Luong & Danh Gia Co Phieu Tuc Thi (Tier 23 / ADR-021)
    quant_search_snapshot = build_quant_search_snapshot(
        fialda_candidates=fialda_candidates,
        active_signals=active_signals,
        scanner=scanner,
        circuit_breaker_active=circuit_breaker_active,
    )
    quant_search_cockpit_html = generate_quant_search_cockpit_html(quant_search_snapshot)

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
            <div class="card-title">Khối Ngoại Ròng: Rổ Top vs. Toàn Sàn</div>
            <div class="card-value" id="card-smart-money-val" data-market-net="{m_net_str}" style="color:{smart_money_color};">{smart_money_val}</div>
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

    {quant_search_cockpit_html}

    <!-- THANH CHUYỂN TAB CHIẾN THUẬT: TAB 1 (RADAR) & TAB 2 (SỔ CÁI & ĐỐI SOÁT VỊ THẾ TOÀN VÒNG) -->
    <div style="display:flex;gap:10px;margin-bottom:18px;flex-wrap:wrap;">
        <button id="btn-tab-radar" onclick="switchHudTab('radar')" style="background:#ffb300;color:#0b0e14;border:none;padding:7px 14px;border-radius:6px;font-size:12px;font-weight:800;cursor:pointer;">📡 TAB 1: RADAR THỰC CHIẾN & BẢNG ĐỊNH LƯỢNG</button>
        <button id="btn-tab-positions" onclick="switchHudTab('positions')" style="background:#151a23;color:#90a4ae;border:1px solid #263238;padding:7px 14px;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;">📋 TAB 2: SỔ CÁI &amp; ĐỐI SOÁT VỊ THẾ TOÀN VÒNG (T+ TRACKER • T0 &rarr; TP/SL) ({len(all_recommended_signals)} MÃ)</button>
    </div>

    <div id="hud-tab-positions" style="display:none;margin-bottom:25px;">
        <div class="section-header">
            <div class="section-title" style="color:#38bdf8;">📋 SỔ CÁI VỊ THẾ KHUYẾN NGHỊ &amp; ĐỐI SOÁT CHỈ SỐ T0 TOÀN VÒNG (T+ TRACKER • T0 &rarr; TP/SL)</div>
            <span style="font-size:11px;color:#78909c;">Chu kỳ: <b style="color:#4fc3f7;">T+2.5</b> • Sắp xếp mặc định: <b style="color:#ffb300;">Vị thế mở &amp; Ngày mua mới nhất (T0)</b> • Giới hạn vị thế: <b style="color:#00e676;">&le; 20% NAV/mã</b> • Phí &amp; Thuế: <b style="color:#ffb300;">0.40%</b> • Đang nắm giữ: <b style="color:#00e676;">{len(active_running)} mã</b> • Đạt TP1: <b style="color:#64ffda;">{tp1_count} mã</b> • Đã chốt lời toàn bộ TP2 &amp; rời bảng: <b style="color:#ffb300;">{tp2_count} mã</b> (Tổng cộng: {len(all_recommended_signals)} mã)</span>
        </div>

        <details id="hud-tab-t0-audit" open style="margin-bottom:18px;background:#10151d;border:1px solid #1f2937;border-radius:8px;padding:12px 14px;">
            <summary style="font-size:12.5px;color:#ffb300;font-weight:bold;cursor:pointer;">
                🧠 AI TÁI ĐÁNH GIÁ CHỈ SỐ T0 TRÊN CÁC LỆNH TP vs. SL &amp; TỰ HỌC CHỌN LỌC KÈO MỚI (Bấm để ẩn/hiện)
            </summary>
            <div style="margin-top:12px;">
                <div class="grid" style="margin-bottom:14px;">
                    <div class="card">
                        <div class="card-title">Tổng Vị Thế Đã Khuyến Nghị</div>
                        <div class="card-value" style="color:#ffb300;">{len(all_recommended_signals)} VỊ THẾ</div>
                        <div style="font-size:11px;color:#94a3b8;margin-top:4px;">
                            🎯 Đạt TP1/TP2: <b style="color:#00e676;">{tp_st['count']}</b> • 🛑 Cắt lỗ SL: <b style="color:#ff5252;">{sl_st['count']}</b> • 🟢 Đang chạy: <b style="color:#38bdf8;">{act_st['count']}</b> • ⏱️ Hết sóng: <b>{to_st['count']}</b>
                        </div>
                    </div>
                    <div class="card">
                        <div class="card-title">Xung Lực &amp; Tích Lũy Tại T0 (TP vs. SL)</div>
                        <div class="card-value" style="color:#00e676;font-size:17px;">TP: IBD {tp_st['avg_ibd']:.0f} | SL: IBD {sl_st['avg_ibd']:.0f}</div>
                        <div style="font-size:11px;color:#94a3b8;margin-top:4px;">
                            Tỷ lệ dính Phân phối (D/E) tại T0: Nhóm SL <b style="color:#ff5252;">{sl_st['weak_acc_diss_pct']:.1f}%</b> vs. Nhóm TP <b style="color:#00e676;">{tp_st['weak_acc_diss_pct']:.1f}%</b>
                        </div>
                    </div>
                    <div class="card">
                        <div class="card-title">Chu Kỳ Ngành RRG &amp; Nền POC T0</div>
                        <div class="card-value" style="color:#38bdf8;font-size:17px;">RRG-M: {tp_st['avg_rrg_m']:.1f} vs. {sl_st['avg_rrg_m']:.1f}</div>
                        <div style="font-size:11px;color:#94a3b8;margin-top:4px;">
                            Lệnh SL mua khi RRG-M &lt; 100: <b style="color:#ff5252;">{sl_st['weak_rrg_m_pct']:.1f}%</b> • Độ lệch POC T0: <b>{sl_st['avg_atr_dist_poc']:+.2f} ATR</b>
                        </div>
                    </div>
                    <div class="card">
                        <div class="card-title">Trọng Số Học Tăng Cường (Self-Learning)</div>
                        <div class="card-value" style="color:#64ffda;font-size:16px;">4 TRỤ CỘT LỌC KÈO</div>
                        <div style="font-size:11px;color:#94a3b8;margin-top:4px;">
                            1. Acc/Diss &ge; C • 2. RRG-M &ge; 100 • 3. IBD &ge; 70 • 4. Cách POC &le; +0.9 ATR
                        </div>
                    </div>
                </div>

                <div class="table-container">
                    <table id="t0-attribution-table">
                        <thead>
                            <tr>
                                <th>Chỉ Số Đánh Giá Tại Thời Điểm Mua (T0)</th>
                                <th>Đặc Trưng Nhóm Thắng (Đạt TP1 / TP2)</th>
                                <th>Đặc Trưng Nhóm Bị Cắt Lỗ (SL)</th>
                                <th style="text-align:center;">Đánh Giá Trọng Số</th>
                                <th>Quy Tắc Tự Cải Thiện Để Chọn Lọc Kèo Mới</th>
                            </tr>
                        </thead>
                        <tbody>
                            {t0_lessons_rows_html}
                        </tbody>
                    </table>
                </div>
            </div>
        </details>

        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;flex-wrap:wrap;gap:8px;">
            <div style="display:flex;gap:6px;flex-wrap:wrap;">
                <button class="pos-filter-btn t0-filter-btn" data-filter="ALL" onclick="filterUnifiedPositions('ALL')" style="background:#ffb300;color:#0b0e14;border:none;padding:5px 12px;border-radius:4px;font-size:11.5px;font-weight:bold;cursor:pointer;">Tất Cả ({len(all_recommended_signals)})</button>
                <button class="pos-filter-btn t0-filter-btn" data-filter="ACTIVE" onclick="filterUnifiedPositions('ACTIVE')" style="background:#151a23;color:#38bdf8;border:1px solid #0284c7;padding:5px 12px;border-radius:4px;font-size:11.5px;font-weight:bold;cursor:pointer;">🟢 Đang Nắm Giữ ({len(active_running)})</button>
                <button class="pos-filter-btn t0-filter-btn" data-filter="TP" onclick="filterUnifiedPositions('TP')" style="background:#151a23;color:#00e676;border:1px solid #1b5e20;padding:5px 12px;border-radius:4px;font-size:11.5px;font-weight:bold;cursor:pointer;">🎯 Đã Chốt Lời TP ({tp_st['count']})</button>
                <button class="pos-filter-btn t0-filter-btn" data-filter="SL" onclick="filterUnifiedPositions('SL')" style="background:#151a23;color:#ff8a80;border:1px solid #b71c1c;padding:5px 12px;border-radius:4px;font-size:11.5px;font-weight:bold;cursor:pointer;">🛑 Đã Cắt Lỗ SL ({sl_st['count']})</button>
                <button class="pos-filter-btn t0-filter-btn" data-filter="TIMEOUT" onclick="filterUnifiedPositions('TIMEOUT')" style="background:#151a23;color:#fbbf24;border:1px solid #78350f;padding:5px 12px;border-radius:4px;font-size:11.5px;font-weight:bold;cursor:pointer;">⏱️ Tất Toán T+7 ({to_st['count']})</button>
            </div>
            <span style="font-size:11px;color:#64748b;">💡 Bảng hợp nhất toàn vòng: Cập nhật giá Live &amp; đồng bộ trọn vẹn Snapshot T0</span>
        </div>

        <div id="t0-recommended-positions-table" class="table-container">
            <table id="active-positions-table" class="unified-positions-table">
                <thead>
                    <tr>
                        <th style="text-align:center;">STT</th>
                        <th>Mã CP</th>
                        <th style="text-align:center;">Trạng Thái &amp; Chu Kỳ (Ngày Vào T0 &bull; Ngày Đóng)</th>
                        <th style="text-align:right;">Giá Vốn &rarr; Thoát/Live</th>
                        <th style="text-align:right;">Lãi/Lỗ PnL %</th>
                        <th>Chỉ Số Đánh Giá Tại T0</th>
                        <th>Dòng Tiền &amp; Nền POC T0</th>
                        <th>AI Chẩn Đoán &amp; Quyết Nghị</th>
                    </tr>
                </thead>
                <tbody>
                    {unified_positions_rows_html}
                </tbody>
            </table>
        </div>
    </div>

    <div id="hud-tab-radar">
    <!-- PHẦN 1: BẢNG TOP SIÊU CỔ PHIẾU CHÂN SÓNG -->
    <div class="section-header">
        <div class="section-title" style="{'color:#ff8a80;' if circuit_breaker_active else ''}">{'⛔ WATCHLIST QUAN SÁT TOP ' + str(len(fialda_candidates)) + ' CỔ PHIẾU THANH KHOẢN (ĐANG KHÓA MUA MỚI T+2.5 — CHỜ TẠO ĐÁY)' if circuit_breaker_active else 'TOP ' + str(len(fialda_candidates)) + ' SIÊU CỔ PHIẾU CHÂN SÓNG & ĐỘT BIẾN DÒNG TIỀN (1 THÁNG | MỤC TIÊU +20% - +35%)'}</div>
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
            const posEl = document.getElementById('hud-tab-positions') || document.getElementById('hud-tab-wf');
            const btnRadar = document.getElementById('btn-tab-radar');
            const btnPos = document.getElementById('btn-tab-positions') || document.getElementById('btn-tab-wf');
            if (!radarEl || !posEl) return;
            if (tabName === 'positions' || tabName === 'wf' || tabName === 't0-audit' || tabName === 't0_audit') {{
                radarEl.style.display = 'none';
                posEl.style.display = 'block';
                if (btnPos) {{ btnPos.style.background = '#ffb300'; btnPos.style.color = '#0b0e14'; }}
                if (btnRadar) {{ btnRadar.style.background = '#151a23'; btnRadar.style.color = '#90a4ae'; }}
            }} else {{
                radarEl.style.display = 'block';
                posEl.style.display = 'none';
                if (btnRadar) {{ btnRadar.style.background = '#ffb300'; btnRadar.style.color = '#0b0e14'; }}
                if (btnPos) {{ btnPos.style.background = '#151a23'; btnPos.style.color = '#90a4ae'; }}
            }}
        }}

        function filterUnifiedPositions(cat) {{
            const rows = document.querySelectorAll('#active-positions-table .unified-pos-row');
            rows.forEach(row => {{
                const rowCat = row.getAttribute('data-cat') || 'ALL';
                const isActive = row.getAttribute('data-active') === '1';
                let show = false;
                if (cat === 'ALL') {{
                    show = true;
                }} else if (cat === 'ACTIVE') {{
                    show = isActive;
                }} else if (cat === 'TP') {{
                    show = (rowCat === 'TP');
                }} else if (cat === 'SL') {{
                    show = (rowCat === 'SL');
                }} else if (cat === 'TIMEOUT') {{
                    show = (rowCat === 'TIMEOUT');
                }}
                row.style.display = show ? '' : 'none';
            }});
            const btns = document.querySelectorAll('.pos-filter-btn, .t0-filter-btn');
            btns.forEach(btn => {{
                if (btn.getAttribute('data-filter') === cat) {{
                    btn.style.background = '#ffb300';
                    btn.style.color = '#0b0e14';
                    btn.style.border = 'none';
                }} else {{
                    btn.style.background = '#151a23';
                    btn.style.color = '#90a4ae';
                    btn.style.border = '1px solid #263238';
                }}
            }});
        }}
        const filterT0AuditRows = filterUnifiedPositions;

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
                            }} else if (!isLockedNoBuy && entryLow > 0 && p < entryLow * 0.985) {{
                                sigBadge.innerHTML = '<span style="background:#bf360c;color:#ffccbc;padding:3px 8px;border-radius:4px;font-size:11px;font-weight:bold;">SUY YẾU ⚠️</span>';
                            }} else if (!isLockedNoBuy && entryLow > 0 && p >= entryLow * 0.985 && p <= entryHigh * 1.03) {{
                                sigBadge.innerHTML = '<span style="background:#1b5e20;color:#00e676;padding:3px 8px;border-radius:4px;font-size:11px;font-weight:bold;">VÙNG MUA 🟢</span>';
                            }}
                        }}
                    }}
                }});

                // Dong bo live PnL % cho Tab 2 So Cai Vi The Theo Doi
                const pnlEls = document.querySelectorAll('.live-pnl[data-sym]');
                pnlEls.forEach(el => {{
                    const sym = el.getAttribute('data-sym');
                    const entry = Number(el.getAttribute('data-entry') || 0);
                    const info = priceMap[sym];
                    if (info && info.price > 0 && entry > 0) {{
                        const p = Number(info.price);
                        const pnl = ((p - entry) / entry) * 100;
                        const sign = pnl >= 0 ? '+' : '';
                        el.innerText = sign + pnl.toFixed(2) + '%';
                        if (p >= info.ceil && info.ceil > 0) {{
                            el.style.color = '#ea39b8';
                        }} else if (p <= info.floor && info.floor > 0) {{
                            el.style.color = '#00e5ff';
                        }} else if (pnl > 0) {{
                            el.style.color = '#00e676';
                        }} else if (pnl < 0) {{
                            el.style.color = '#ff5252';
                        }} else {{
                            el.style.color = '#ffb300';
                        }}
                    }}
                }});

                // Dong bo huy hieu quyet nghi thuc chien Tab 2 khi cham nguong
                const posBadgeEls = document.querySelectorAll('.pos-badge[data-sym]');
                posBadgeEls.forEach(bEl => {{
                    const sym = bEl.getAttribute('data-sym');
                    const info = priceMap[sym];
                    const tp1 = Number(bEl.getAttribute('data-tp1') || 0);
                    const tp2 = Number(bEl.getAttribute('data-tp2') || 0);
                    const sl = Number(bEl.getAttribute('data-sl') || 0);
                    if (info && info.price > 0) {{
                        const p = Number(info.price);
                        if (tp2 > 0 && p >= tp2) {{
                            bEl.innerHTML = '<span style="background:#004d40;color:#64ffda;padding:3px 8px;border-radius:4px;font-size:11px;font-weight:bold;">🏆 CHẠM TP2 — CHỐT LỜI HẾT</span>';
                        }} else if (tp1 > 0 && p >= tp1) {{
                            bEl.innerHTML = '<span style="background:#004d40;color:#64ffda;padding:3px 8px;border-radius:4px;font-size:11px;font-weight:bold;">🎯 ĐẠT TP1 — GỒNG LÃI TỚI TP2 (CẤM MUA)</span>';
                        }} else if (sl > 0 && p <= sl) {{
                            bEl.innerHTML = '<span style="background:#b71c1c;color:#ff8a80;padding:3px 8px;border-radius:4px;font-size:11px;font-weight:bold;">🛑 CHẠM CẮT LỖ — BẢO TOÀN VỐN</span>';
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
                        const topSign = netForeignBillion >= 0 ? '+' : '';
                        const mNetAttr = smValEl.getAttribute('data-market-net');
                        if (mNetAttr && mNetAttr !== 'N/A') {{
                            const mNet = Number(mNetAttr);
                            const mSign = mNet >= 0 ? '+' : '';
                            smValEl.innerHTML = '<span style="color:' + (netForeignBillion >= 0 ? '#00e676' : '#ff5252') + '">Top: ' + topSign + netForeignBillion.toFixed(1) + 't</span> <span style="font-size:13px;color:#64748b;font-weight:normal;">|</span> <span style="font-size:13px;color:#94a3b8;">Sàn: ' + mSign + mNet.toFixed(1) + 't</span>';
                            if (smSubEl) {{
                                const deltaFlow = netForeignBillion - mNet;
                                const deltaSign = deltaFlow >= 0 ? '+' : '';
                                if (netForeignBillion > 0 && mNet <= 0) {{
                                    smSubEl.innerHTML = '<span style="color:#38bdf8;font-weight:bold;">🟢 ĐÃI CÁT TÌM VÀNG</span> • Độ lệch: <b style="color:#00e676;">' + deltaSign + deltaFlow.toFixed(1) + 't</b> gom Top';
                                }} else if (netForeignBillion > 0 && mNet > 0) {{
                                    smSubEl.innerHTML = '<span style="color:#00e676;font-weight:bold;">🟢🟢 SIÊU SÓNG ĐỒNG THUẬN</span> • Độ lệch: <b style="color:#00e676;">' + deltaSign + deltaFlow.toFixed(1) + 't</b>';
                                }} else if (netForeignBillion <= 0 && mNet > 0) {{
                                    smSubEl.innerHTML = '<span style="color:#ffb300;font-weight:bold;">🟡 KÉO TRỤ PHÂN HÓA</span> • Rổ Top bị xả (' + deltaSign + deltaFlow.toFixed(1) + 't)';
                                }} else {{
                                    smSubEl.innerHTML = '<span style="color:#ff5252;font-weight:bold;">🔴 ÁP LỰC XẢ DIỆN RỘNG</span> • Độ lệch: ' + deltaSign + deltaFlow.toFixed(1) + 't';
                                }}
                            }}
                        }} else {{
                            smValEl.innerText = topSign + netForeignBillion.toFixed(1) + ' Tỷ VND';
                            smValEl.style.color = netForeignBillion >= 0 ? '#00e676' : '#ff5252';
                            if (smSubEl) {{
                                if (netForeignBillion < 0) {{
                                    smSubEl.innerText = 'Rổ Top: Khối ngoại bán ròng • Cảnh báo áp lực xả';
                                }} else {{
                                    smSubEl.innerText = 'Rổ Top: Khối ngoại mua ròng trực tiếp (Live VPS)';
                                }}
                            }}
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
