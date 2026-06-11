export const apiBase = import.meta.env.VITE_API_BASE || "http://localhost:8765";

export function getSessionId() {
  let sessionId = localStorage.getItem("mw-session");
  if (!sessionId) {
    sessionId = crypto.randomUUID();
    localStorage.setItem("mw-session", sessionId);
  }
  return sessionId;
}

export async function fetchApi(endpoint: string, options?: RequestInit) {
  const url = new URL(`${apiBase}${endpoint}`);
  url.searchParams.set("session_id", getSessionId());
  
  const response = await fetch(url.toString(), {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  
  return response.json();
}
