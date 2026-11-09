const BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message, status, code, field) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.field = field;
  }
}

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${BASE_URL}${path}`, options);
  } catch (error) {
    throw new ApiError(
      "Could not reach the BankSense API. Is the backend running?",
      0,
      "NETWORK_ERROR",
    );
  }

  const isJson = (response.headers.get("content-type") || "").includes(
    "application/json",
  );
  const body = isJson ? await response.json() : null;

  if (!response.ok) {
    const detail = body?.error ?? {};
    throw new ApiError(
      detail.message || `Request failed with status ${response.status}`,
      response.status,
      detail.code || "HTTP_ERROR",
      detail.field,
    );
  }

  return body;
}

export function analyzeComplaint(text, model) {
  return request("/api/complaints/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, model }),
  });
}

export function getComplaints(limit = 20, offset = 0) {
  return request(`/api/complaints?limit=${limit}&offset=${offset}`);
}

export function getAnalytics() {
  return request("/api/analytics");
}

export function getHealth() {
  return request("/api/health");
}
