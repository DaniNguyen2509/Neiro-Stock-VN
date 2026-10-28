import urllib.error
from unittest.mock import MagicMock, patch
from scripts.trigger_scan import dispatch_scan


class TestTriggerScan:
    def test_empty_token_fails(self):
        success, code, msg = dispatch_scan(token="")
        assert not success
        assert code == 400
        assert "không được để trống" in msg

    @patch("urllib.request.urlopen")
    def test_repository_dispatch_success_204(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 204
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        success, code, msg = dispatch_scan(
            token="ghp_mock_token_12345",
            repo="DaniNguyen2509/Neiro-Stock-VN",
            method="repository_dispatch",
            event_type="external_scan",
        )

        assert success
        assert code == 204
        assert "Kích hoạt thành công" in msg
        # Verify request parameters
        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "https://api.github.com/repos/DaniNguyen2509/Neiro-Stock-VN/dispatches"
        assert req.get_method() == "POST"
        assert req.get_header("Authorization") == "Bearer ghp_mock_token_12345"

    @patch("urllib.request.urlopen")
    def test_workflow_dispatch_success_204(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 204
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        success, code, msg = dispatch_scan(
            token="ghp_mock_token_12345",
            repo="DaniNguyen2509/Neiro-Stock-VN",
            method="workflow_dispatch",
            workflow_id="scanner_and_pages.yml",
            ref="main",
        )

        assert success
        assert code == 204
        assert "Kích hoạt thành công" in msg
        req = mock_urlopen.call_args[0][0]
        assert "actions/workflows/scanner_and_pages.yml/dispatches" in req.full_url

    @patch("urllib.request.urlopen")
    def test_http_error_handling(self, mock_urlopen):
        mock_err = urllib.error.HTTPError(
            url="https://api.github.com",
            code=401,
            msg="Bad credentials",
            hdrs={},
            fp=MagicMock(read=lambda: b'{"message": "Bad credentials"}'),
        )
        mock_urlopen.side_effect = mock_err

        success, code, msg = dispatch_scan(
            token="invalid_token",
            repo="DaniNguyen2509/Neiro-Stock-VN",
        )

        assert not success
        assert code == 401
        assert "401" in msg

    @patch("urllib.request.urlopen")
    def test_network_url_error_handling(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("Connection timed out")

        success, code, msg = dispatch_scan(
            token="ghp_mock_token",
            repo="DaniNguyen2509/Neiro-Stock-VN",
        )

        assert not success
        assert code == 500
        assert "Lỗi kết nối mạng" in msg
