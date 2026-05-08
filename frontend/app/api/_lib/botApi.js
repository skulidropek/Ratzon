export function getBotApiUrl() {
  if (!process.env.BOT_API_URL && process.env.NODE_ENV === "production") {
    throw new Error("BOT_API_URL is not configured for this frontend service.");
  }

  return (process.env.BOT_API_URL || "http://localhost:8080").replace(/\/+$/, "");
}

export async function readJsonResponse(response) {
  const text = await response.text();
  if (!text) return null;

  try {
    return JSON.parse(text);
  } catch {
    return { error: text };
  }
}

export function proxyError(message, status = 503) {
  return Response.json({ error: message }, { status });
}
