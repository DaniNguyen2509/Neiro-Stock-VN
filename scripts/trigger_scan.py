import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Tuple


def dispatch_scan(
    token: str,
    repo: str = "DaniNguyen2509/Neiro-Stock-VN",
    method: str = "repository_dispatch",
    workflow_id: str = "scanner_and_pages.yml",
    event_type: str = "external_scan",
    ref: str = "main",
) -> Tuple[bool, int, str]:
    """
    Kích hoạt quét Fialda Scanner trên GitHub Actions từ xa qua GitHub REST API.

    Hỗ trợ 2 phương thức:
    1. repository_dispatch: POST /repos/{repo}/dispatches
       Payload: {"event_type": event_type}
    2. workflow_dispatch: POST /repos/{repo}/actions/workflows/{workflow_id}/dispatches
       Payload: {"ref": ref}

    Trả về: (success, status_code, message)
    """
    if not token or not token.strip():
        return False, 400, "Lỗi: GitHub Token không được để trống."

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token.strip()}",
        "User-Agent": "Neiro-Stock-VN-External-Cron/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    if method == "workflow_dispatch":
        url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_id}/dispatches"
        payload = json.dumps({"ref": ref}).encode("utf-8")
    else:
        url = f"https://api.github.com/repos/{repo}/dispatches"
        payload = json.dumps({"event_type": event_type}).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.status
            # GitHub API trả về 204 No Content khi dispatch thành công
            if status in (200, 204):
                return True, status, f"Kích hoạt thành công qua {method} (HTTP {status})."
            return False, status, f"Phản hồi bất thường: HTTP {status}."
    except urllib.error.HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode("utf-8")
        except Exception:
            pass
        return False, e.code, f"Lỗi HTTP {e.code}: {e.reason} - {error_body}"
    except urllib.error.URLError as e:
        return False, 500, f"Lỗi kết nối mạng: {e.reason}"
    except Exception as e:
        return False, 500, f"Lỗi không xác định: {str(e)}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CLI kích hoạt bot quét định lượng Neiro-Stock-VN từ xa qua GitHub API"
    )
    parser.add_argument(
        "--token",
        default=os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PAT"),
        help="GitHub Personal Access Token (PAT). Mặc định đọc từ biến môi trường GITHUB_TOKEN hoặc GITHUB_PAT",
    )
    parser.add_argument(
        "--repo",
        default="DaniNguyen2509/Neiro-Stock-VN",
        help="Repository định dạng 'owner/repo' (mặc định: DaniNguyen2509/Neiro-Stock-VN)",
    )
    parser.add_argument(
        "--method",
        choices=["repository_dispatch", "workflow_dispatch"],
        default="repository_dispatch",
        help="Phương thức dispatch (mặc định: repository_dispatch)",
    )
    parser.add_argument(
        "--workflow",
        default="scanner_and_pages.yml",
        help="Tên workflow khi dùng workflow_dispatch (mặc định: scanner_and_pages.yml)",
    )
    parser.add_argument(
        "--event-type",
        default="external_scan",
        help="Event type khi dùng repository_dispatch (mặc định: external_scan)",
    )
    parser.add_argument(
        "--ref",
        default="main",
        help="Nhánh mục tiêu (mặc định: main)",
    )

    args = parser.parse_args()

    if not args.token:
        print("❌ Lỗi: Chưa cung cấp GitHub Token.")
        print("💡 Hướng dẫn: Truyền qua tham số --token <YOUR_PAT> hoặc gán biến môi trường GITHUB_TOKEN.")
        sys.exit(1)

    print(f"🚀 Đang gửi yêu cầu kích hoạt quét đến {args.repo} qua {args.method}...")
    success, code, msg = dispatch_scan(
        token=args.token,
        repo=args.repo,
        method=args.method,
        workflow_id=args.workflow,
        event_type=args.event_type,
        ref=args.ref,
    )

    if success:
        print(f"✅ {msg}")
        sys.exit(0)
    else:
        print(f"❌ {msg}")
        sys.exit(1)


if __name__ == "__main__":
    main()
