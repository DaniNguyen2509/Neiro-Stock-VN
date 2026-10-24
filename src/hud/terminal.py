"""Sinh Plotly Tactical Terminal HTML Dark Mode cho TTCK Viet Nam."""
from pathlib import Path
from typing import List
from src.collector.data_loader import get_mock_vietnam_stocks
from src.fundamental_engine.screener import screen_stocks
from src.microstructure_engine.volume_profile import compute_volume_profile
from src.microstructure_engine.basis_tracker import analyze_vn30_basis


def generate_terminal_html(output_path: str = "exports/vn_stock_terminal.html") -> str:
    """Sinh ma nguon giao dien Web Terminal Plotly tuong tac doc lap."""
    stocks = get_mock_vietnam_stocks()
    screened = screen_stocks(stocks)
    basis = analyze_vn30_basis(1312.20, 1315.50)

    # Chuan bi bang du lieu HTML
    rows_html = ""
    for s in screened:
        badge = '<span style="color:#00e676;font-weight:bold;">INSTITUTIONAL</span>' if s.is_institutional_grade else '<span style="color:#ff5252;">NEUTRAL</span>'
        rows_html += f"""
        <tr style="border-bottom:1px solid #222;">
            <td style="padding:10px;font-weight:bold;color:#ffb300;">{s.symbol}</td>
            <td style="padding:10px;">{s.company_name}</td>
            <td style="padding:10px;color:#aaa;">{s.sector}</td>
            <td style="padding:10px;font-weight:bold;">{s.price:,.0f}</td>
            <td style="padding:10px;text-align:center;font-weight:bold;color:#00e676;">{s.f_score}/9</td>
            <td style="padding:10px;text-align:center;">{s.earnings_quality_ratio:.2f}</td>
            <td style="padding:10px;text-align:center;">{badge}</td>
        </tr>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>Neiro-Stock-VN | Tactical Quantamental Terminal</title>
    <style>
        body {{
            background-color: #0b0e14;
            color: #d1d4dc;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 0;
            padding: 20px;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #1f2937;
            padding-bottom: 15px;
            margin-bottom: 20px;
        }}
        .title {{
            font-size: 24px;
            font-weight: 800;
            color: #ffb300;
            letter-spacing: 1px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }}
        .card {{
            background: #151a23;
            border: 1px solid #263238;
            border-radius: 8px;
            padding: 15px;
        }}
        .card-title {{
            font-size: 12px;
            color: #78909c;
            text-transform: uppercase;
            margin-bottom: 8px;
            font-weight: 600;
        }}
        .card-value {{
            font-size: 22px;
            font-weight: 800;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: #151a23;
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid #263238;
        }}
        th {{
            background: #1c2431;
            padding: 12px 10px;
            text-align: left;
            font-size: 12px;
            color: #90a4ae;
            text-transform: uppercase;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <div class="title">NEIRO-STOCK-VN TACTICAL TERMINAL</div>
            <div style="font-size:13px;color:#78909c;margin-top:4px;">Quantitative Microstructure & Fundamental Screener for Vietnam Equities</div>
        </div>
        <div style="text-align:right;">
            <span style="background:#1b5e20;color:#00e676;padding:5px 10px;border-radius:4px;font-size:12px;font-weight:bold;">LIVE ENGINE READY</span>
        </div>
    </div>

    <div class="grid">
        <div class="card">
            <div class="card-title">VN30F1M Basis Spread</div>
            <div class="card-value" style="color:{"#00e676" if basis.basis_points >= 0 else "#ff5252"};">{basis.basis_points:+.2f} pts</div>
            <div style="font-size:12px;color:#78909c;margin-top:5px;">Regime: {basis.regime}</div>
        </div>
        <div class="card">
            <div class="card-title">Institutional Smart Money Flow</div>
            <div class="card-value" style="color:#00e676;">+427.5 Tỷ VND</div>
            <div style="font-size:12px;color:#78909c;margin-top:5px;">Khối ngoại + Tự doanh mua ròng</div>
        </div>
        <div class="card">
            <div class="card-title">Market Breadth (VN30 > MA20)</div>
            <div class="card-value" style="color:#ffb300;">73.3%</div>
            <div style="font-size:12px;color:#78909c;margin-top:5px;">22/30 Cổ phiếu giữ xu hướng tăng</div>
        </div>
        <div class="card">
            <div class="card-title">Leading Sector (RRG Momentum)</div>
            <div class="card-value" style="color:#00e676;">CÔNG NGHỆ & THÉP</div>
            <div style="font-size:12px;color:#78909c;margin-top:5px;">FPT, HPG dẫn dắt dòng tiền</div>
        </div>
    </div>

    <h3 style="color:#cfd8dc;margin-bottom:12px;">Bảng Xếp Hạng Định Lượng Cơ Bản (Piotroski F-Score & Quality Ratio)</h3>
    <table>
        <thead>
            <tr>
                <th>Mã CP</th>
                <th>Tên Doanh Nghiệp</th>
                <th>Nhóm Ngành</th>
                <th>Giá Khớp (VND)</th>
                <th style="text-align:center;">F-Score</th>
                <th style="text-align:center;">CFO / NI</th>
                <th style="text-align:center;">Định Chế Xếp Hạng</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
</body>
</html>
"""
    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(html_content, encoding="utf-8")
    return str(dest)


if __name__ == "__main__":
    path = generate_terminal_html()
    print(f"Generated terminal at {path}")
