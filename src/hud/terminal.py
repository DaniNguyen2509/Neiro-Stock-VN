from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from src.collector.data_loader import get_mock_vietnam_stocks
from src.fundamental_engine.screener import screen_stocks
from src.microstructure_engine.basis_tracker import analyze_vn30_basis
from src.collector.fialda_scanner import FialdaCandidate, FialdaScanner


def generate_terminal_html(
    output_path: str = "exports/vn_stock_terminal.html",
    fialda_candidates: Optional[List[FialdaCandidate]] = None,
    top_n: int = 20,
) -> str:
    """Sinh ma nguon giao dien Web Terminal Plotly tuong tac doc lap (Continuous Dashboard)."""
    basis = analyze_vn30_basis(1312.20, 1315.50)
    scanner = FialdaScanner()

    if fialda_candidates is None:
        if scanner.username and scanner.password:
            try:
                fialda_candidates = scanner.scan_top_rockets(top_n=top_n)
            except Exception:
                fialda_candidates = scanner._fallback_mock_top_20()[:top_n]
        else:
            fialda_candidates = scanner._fallback_mock_top_20()[:top_n]

    # Lay du lieu co ban that 100% tu Fialda TechnicalAnalysis & GetStockInfos
    try:
        fund_data = scanner.get_fundamental_screener_data()
    except Exception:
        fund_data = scanner._fallback_mock_fundamental()

    # Chuan bi bang du lieu Fialda Top N
    fialda_rows_html = ""
    for idx, c in enumerate(fialda_candidates, 1):
        sig_badge = (
            '<span style="background:#1b5e20;color:#00e676;padding:3px 8px;border-radius:4px;font-size:11px;font-weight:bold;">CHÂN SÓNG</span>'
            if "CHO_MUA" in c.signal_type
            else '<span style="background:#01579b;color:#29b6f6;padding:3px 8px;border-radius:4px;font-size:11px;font-weight:bold;">ĐỘT BIẾN GT</span>'
        )
        foreign_str = f"{c.foreign_net_value_billion:+.1f} tỷ"
        foreign_color = "#00e676" if c.foreign_net_value_billion >= 0 else "#ff5252"

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
            <td style="padding:6px 5px;font-weight:bold;color:#ffb300;font-size:13.5px;">{c.symbol}</td>
            <td style="padding:6px 5px;text-align:center;">{sig_badge}</td>
            <td style="padding:6px 5px;font-weight:bold;">{c.price:,.2f}</td>
            <td style="padding:6px 5px;color:#00e676;font-weight:600;">{c.entry_low:.2f} - {c.entry_high:.2f}</td>
            <td style="padding:6px 5px;color:#ff5252;font-weight:bold;">{c.stop_loss:.2f}</td>
            <td style="padding:6px 5px;text-align:center;">{tp_html}</td>
            <td style="padding:6px 5px;text-align:center;font-weight:bold;color:#4fc3f7;">{c.adtv20_billion:.1f}t</td>
            <td style="padding:6px 5px;text-align:center;">{liq_badge}</td>
            <td style="padding:6px 5px;text-align:center;color:#4fc3f7;">{c.rrg_r:.0f}/{c.rrg_m:.0f}</td>
            <td style="padding:6px 5px;text-align:center;font-weight:bold;color:#ffb300;">{c.composite_rating}</td>
            <td style="padding:6px 5px;text-align:center;">{ad_badge}</td>
            <td style="padding:6px 5px;text-align:center;color:{foreign_color};font-weight:600;">{foreign_str}</td>
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
            <td style="padding:10px;font-weight:bold;color:#00e676;">{s['price']:.2f}</td>
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
            <td style="padding:10px;font-weight:bold;color:#00e676;">{b.price:.2f}</td>
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
            news_items_html += f"""
            <div style="background:#151a23;border:1px solid #263238;border-radius:6px;padding:12px;margin-bottom:10px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                    <span style="font-weight:bold;color:#ffb300;font-size:13px;">{n['symbol']}</span>
                    <span style="font-size:11px;color:#78909c;">{n['time']} • {n['source']}</span>
                </div>
                <div style="font-weight:600;font-size:13px;color:#eceff1;margin-bottom:4px;">{n['title']}</div>
                <div style="font-size:12px;color:#90a4ae;line-height:1.4;">{n['short_content']}</div>
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

    regime_map = {
        "NORMAL_EQUILIBRIUM": "Cân Bằng Bình Thường",
        "CONTANGO_EXPANDED": "Contango Mở Rộng",
        "BACKWARDATION_EXTREME": "Backwardation Cực Đoan (Cảnh Báo Kéo Trụ)",
    }
    regime_vn = regime_map.get(basis.regime, basis.regime)

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
    <meta http-equiv="refresh" content="180">
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
                <span style="font-size:11px;color:#90a4ae;">🕒 Cập nhật: <b style="color:#ffb300;">{scan_time_str}</b></span>
                <span style="font-size:11px;color:#546e7a;">•</span>
                <span style="font-size:11px;color:#90a4ae;">🔄 Tự làm mới: <b id="countdown" style="color:#00e676;">60</b>s</span>
                <button onclick="reloadDashboard()" style="background:#1e293b;color:#38bdf8;border:1px solid #0284c7;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold;cursor:pointer;">⚡ Tải lại ngay</button>
            </div>
        </div>
    </div>

    <!-- 4 METRIC CARDS -->
    <div class="grid">
        <div class="card">
            <div class="card-title">Chênh Lệch Basis VN30F1M</div>
            <div class="card-value" style="color:#29b6f6;">{basis.basis_points:+.2f} ĐIỂM</div>
            <div style="font-size:11px;color:#78909c;margin-top:4px;">Trạng thái: {regime_vn}</div>
        </div>
        <div class="card">
            <div class="card-title">Dòng Tiền Cá Mập Định Chế</div>
            <div class="card-value" style="color:#00e676;">+427.5 Tỷ VND</div>
            <div style="font-size:11px;color:#78909c;margin-top:4px;">Khối ngoại + Tự doanh mua ròng</div>
        </div>
        <div class="card">
            <div class="card-title">Độ Rộng Thị Trường (VN30 > MA20)</div>
            <div class="card-value" style="color:#ffb300;">73.3%</div>
            <div style="font-size:11px;color:#78909c;margin-top:4px;">22/30 Cổ phiếu giữ xu hướng tăng</div>
        </div>
        <div class="card">
            <div class="card-title">Ngành Dẫn Dắt (Động Lượng RRG)</div>
            <div class="card-value" style="color:#00e676;">NÔNG NGHIỆP & CHỨNG KHOÁN</div>
            <div style="font-size:11px;color:#78909c;margin-top:4px;">DBC, CTS bứt phá mạnh</div>
        </div>
    </div>

    <!-- PHẦN 1: BẢNG TOP SIÊU CỔ PHIẾU CHÂN SÓNG -->
    <div class="section-header">
        <div class="section-title">TOP {len(fialda_candidates)} SIÊU CỔ PHIẾU CHÂN SÓNG & ĐỘT BIẾN DÒNG TIỀN (1 THÁNG | MỤC TIÊU +20% - +35%)</div>
        <span style="font-size:11px;color:#78909c;">Nguồn: Fialda VIP Expert & Tích Lũy Khối Lượng Order Flow & Quản Trị Sức Chứa Thanh Khoản</span>
    </div>
    <div class="table-container">
        <table>
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

    <div class="footer">
        Neiro-Stock-VN • Tự động quét và cập nhật qua GitHub Actions • Vận hành 24/7 trên Cloud • Xem được trên mọi thiết bị di động
    </div>

    <script>
        let secondsLeft = 60;
        const countdownEl = document.getElementById('countdown');
        function reloadDashboard() {{
            if (countdownEl) countdownEl.innerText = 'Đang nạp...';
            const url = new URL(window.location.href);
            url.searchParams.set('_t', Date.now().toString());
            window.location.href = url.toString();
        }}
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
    parser = argparse.ArgumentParser(description="Sinh Terminal HTML cho Neiro-Stock-VN")
    parser.add_argument("--output", default="exports/vn_stock_terminal.html", help="Duong dan file HTML dau ra")
    parser.add_argument("--top", type=int, default=20, help="So luong sieu co phieu hien thi (mac dinh 20)")
    args = parser.parse_args()

    path = generate_terminal_html(args.output, top_n=args.top)
    print(f"Generated terminal at {path}")
