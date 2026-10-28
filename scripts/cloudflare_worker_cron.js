/**
 * Cloudflare Worker: Neiro-Stock-VN External Cron Dispatcher
 * 
 * Miễn phí 100% (100.000 requests/ngày trên Cloudflare Workers Free Tier).
 * Đảm bảo kích hoạt quét chính xác từng giây, không bao giờ bị nghẽn queue hoặc bị drop như GitHub Scheduler.
 * 
 * HƯỚNG DẪN CÀI ĐẶT TRÊN CLOUDFLARE DASHBOARD:
 * 1. Vào https://dash.cloudflare.com -> Workers & Pages -> Create Application -> Create Worker.
 * 2. Đặt tên worker (ví dụ: `neiro-stock-scanner-cron`).
 * 3. Dán toàn bộ nội dung file này vào editor của Worker và nhấn "Deploy".
 * 4. Vào Settings -> Variables and Secrets:
 *    - Thêm Secret: `GITHUB_PAT` = <Personal Access Token của bạn có quyền Actions: write>
 *    - (Tùy chọn) Thêm Variable: `GITHUB_REPO` = "DaniNguyen2509/Neiro-Stock-VN"
 * 5. Vào Settings -> Triggers -> Cron Triggers -> Add Cron Trigger:
 *    - Lịch quét trong phiên (Thứ 2 - Thứ 6):
 *      + Phiên sáng (09:18, 09:48, 10:18, 10:48, 11:18, 11:48 VN): `18,48 2,3,4 * * 1-5`
 *      + Phiên chiều (13:18, 13:48, 14:18, 14:48 VN): `18,48 6,7 * * 1-5`
 *      + Chốt phiên ATC (15:08 VN): `8 8 * * 1-5`
 *      + Chốt Tự doanh & Ngoại chiều (17:35 VN): `35 10 * * 1-5`
 *      + Chốt sổ tối (19:08 VN): `8 12 * * 1-5`
 */

export default {
  // 1. Kích hoạt tự động khi đến giờ Cron Trigger
  async scheduled(event, env, ctx) {
    console.log(`[Cron Trigger] Firing scheduled scan at ${new Date().toISOString()} (cron: ${event.cron})`);
    ctx.waitUntil(triggerGitHubScan(env, `cloudflare_cron:${event.cron}`));
  },

  // 2. Hỗ trợ kích hoạt thủ công khi gọi HTTP GET / POST vào Worker URL
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname === "/scan" || url.pathname === "/trigger") {
      const result = await triggerGitHubScan(env, "cloudflare_http_manual");
      return new Response(JSON.stringify(result, null, 2), {
        status: result.success ? 200 : 500,
        headers: { "Content-Type": "application/json" },
      });
    }

    return new Response(
      JSON.stringify({
        status: "Neiro-Stock-VN External Cron Worker is Active",
        endpoints: ["GET /scan để kích hoạt ngay", "POST /scan"],
        timestamp: new Date().toISOString(),
      }),
      { headers: { "Content-Type": "application/json" } }
    );
  },
};

async function triggerGitHubScan(env, source = "external") {
  const token = env.GITHUB_PAT;
  const repo = env.GITHUB_REPO || "DaniNguyen2509/Neiro-Stock-VN";

  if (!token) {
    const errMsg = "Missing GITHUB_PAT secret in Worker environment.";
    console.error(errMsg);
    return { success: false, error: errMsg };
  }

  const endpoint = `https://api.github.com/repos/${repo}/dispatches`;
  const body = JSON.stringify({
    event_type: "external_scan",
    client_payload: {
      source: source,
      triggered_at: new Date().toISOString(),
    },
  });

  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Accept": "application/vnd.github+json",
        "Authorization": `Bearer ${token}`,
        "User-Agent": "Neiro-Stock-VN-Cloudflare-Cron",
        "X-GitHub-Api-Version": "2022-11-28",
      },
      body: body,
    });

    if (res.status === 204 || res.status === 200) {
      console.log(`[Success] Dispatched scan to ${repo} via repository_dispatch (HTTP ${res.status}).`);
      return { success: true, status: res.status, message: "Scan triggered successfully on GitHub Actions." };
    } else {
      const errText = await res.text();
      console.error(`[Error] GitHub API returned ${res.status}: ${errText}`);
      return { success: false, status: res.status, error: errText };
    }
  } catch (err) {
    console.error(`[Fetch Exception]: ${err.message}`);
    return { success: false, error: err.message };
  }
}
