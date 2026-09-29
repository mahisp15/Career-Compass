const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });

  let payload;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const detail = payload?.detail || payload?.message || `Request failed (${response.status})`;
    throw new Error(detail);
  }

  return payload;
}

export const api = {
  getRoles: () => request("/api/roles"),
  getCompanies: () => request("/api/companies"),
  getSkills: () => request("/api/skills"),
  getSkill: (skillName) => request(`/api/skills/${encodeURIComponent(skillName)}`),
  getTrends: () => request("/api/trends"),
  getTrend: (trendType) => request(`/api/trends/${encodeURIComponent(trendType)}`),
  getModelMetrics: () => request("/api/model/metrics"),
  analyze: (payload) => request("/api/analyze", { method: "POST", body: JSON.stringify(payload) }),
};

export { API_BASE_URL };
