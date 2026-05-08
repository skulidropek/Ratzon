import { getBotApiUrl, proxyError, readJsonResponse } from "../_lib/botApi";

export async function POST(request) {
  try {
    const body = await request.json();
    const { message, wallet } = body;

    if (!message || !wallet) {
      return Response.json({ error: "message and wallet are required" }, { status: 400 });
    }

    const botApiUrl = getBotApiUrl();
    const res = await fetch(`${botApiUrl}/swap`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, wallet }),
      cache: "no-store",
    });

    const data = await readJsonResponse(res);

    if (!res.ok) {
      return proxyError(data?.error || "Failed to prepare swap", res.status);
    }

    return Response.json(data);
  } catch (error) {
    console.error("Swap API error:", error);
    return proxyError(
      error?.message || "Bot API is unavailable. Check BOT_API_URL and bot service logs.",
    );
  }
}
