import os
import re
from pathlib import Path
from src.hud.terminal import generate_terminal_html
from src.collector.fialda_scanner import FialdaCandidate


def test_generate_terminal_html_structure_and_auto_reload(tmp_path: Path):
    """Kiem thu toan dien cau truc HTML, co che Auto-Reload, Live Countdown va Cache-Busting."""
    output_file = tmp_path / "exports" / "test_terminal.html"
    
    mock_candidates = [
        FialdaCandidate(
            symbol="CTS",
            price=22.0,
            signal_type="CHO_MUA_CHAN_SONG",
            entry_low=21.5,
            entry_high=22.2,
            stop_loss=20.7,
            target_1m=28.5,
            rs_1m=88,
            composite_rating=85,
            acc_diss_rating="A",
            rrg_r=104.0,
            rrg_m=102.0,
            foreign_net_value_billion=12.5,
            ranking_score=89.5,
            catalyst="Chân sóng ngành Chứng khoán",
            adtv20_billion=25.0,
            liquidity_score=92.0,
            tp1=23.76,
            tp2=28.5,
            prev_rank=1,
            rank_change_delta=0,
        )
    ]
    
    result_path = generate_terminal_html(
        output_path=str(output_file),
        fialda_candidates=mock_candidates,
        top_n=5
    )
    
    assert os.path.exists(result_path), f"File {result_path} phai duoc tao thanh cong"
    content = Path(result_path).read_text(encoding="utf-8")
    
    # 1. Kiem tra the Meta Refresh du phong (5 phut = 300s)
    assert '<meta http-equiv="refresh" content="300">' in content
    
    # 2. Kiem tra Nhan thoi gian cap nhat (Gio Viet Nam)
    assert "🕒 Cập nhật:" in content
    assert re.search(r"\d{2}:\d{2}:\d{2} • \d{2}/\d{2}/\d{4}", content) is not None
    
    # 3. Kiem tra Bo dem nguoc Live Countdown UI (300s = 5 phut)
    assert '🔄 Tự làm mới: <b id="countdown" style="color:#00e676;">300</b>s' in content
    assert '<button onclick="reloadDashboard()"' in content
    assert 'id="live-status"' in content
    
    # 4. Kiem tra Script Cache-Busting, Live Ticker va setInterval
    assert "function reloadDashboard()" in content
    assert "url.searchParams.set('_t', Date.now().toString());" in content
    assert "async function fetchLivePrices()" in content
    assert "https://bgapidatafeed.vps.com.vn/getliststockdata/" in content
    assert "setInterval(function()" in content
    assert "countdownEl.innerText = secondsLeft > 0 ? secondsLeft : '0';" in content
    assert "reloadDashboard();" in content
    
    # 5. Kiem tra Du lieu co phieu mock xuat hien dung bang voi live-price data-sym
    assert "CTS" in content
    assert "22.00" in content
    assert 'class="live-price" data-sym="CTS"' in content
    assert "CHÂN SÓNG" in content
    assert "SIÊU TK" in content
