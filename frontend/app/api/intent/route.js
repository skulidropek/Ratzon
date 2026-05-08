// frontend/src/app/api/intent/route.js
/**
 * API route — прокси между фронтендом и Python ботом.
 * Фронтенд → Next.js API → Python бот → Jupiter → Response
 */

import { getBotApiUrl, proxyError, readJsonResponse } from "../_lib/botApi";

export async function POST(request) {
  try {
    const body = await request.json();
    const { message } = body;

    if (!message) {
      return Response.json({ error: "message required" }, { status: 400 });
    }

    const botApiUrl = getBotApiUrl();

    // Прокси к Python боту
    const res = await fetch(`${botApiUrl}/intent`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
      cache: "no-store",
    });

    const data = await readJsonResponse(res);

    if (!res.ok) {
      return proxyError(data?.error || `Bot API error (${res.status})`, res.status);
    }

    return Response.json(data);

  } catch (error) {
    console.error("Intent API error:", error);
    return proxyError(
      error?.message || "Bot API is unavailable. Check BOT_API_URL and bot service logs.",
    );
  }
}
