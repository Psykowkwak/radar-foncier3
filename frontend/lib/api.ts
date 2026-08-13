// Client fetch vers le backend -- voir app/api/routes/*.py cote backend.
import type {
  AnalysisJob,
  AnalysisJobLaunched,
  Filters,
  Municipality,
  MunicipalitySearchResult,
  Opportunity,
  ParcelDetail,
} from "./types";

// Toujours en meme origine : le navigateur n'appelle jamais le backend
// directement. Voir app/api/backend/[...path]/route.ts (proxy server-side qui
// ajoute la cle interne) et middleware.ts (Basic Auth du site).
const API_URL = "/api/backend";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`Erreur API ${response.status} sur ${path} : ${text}`);
  }
  return response.json() as Promise<T>;
}

export function searchMunicipalities(query: string): Promise<MunicipalitySearchResult[]> {
  if (!query.trim()) return Promise.resolve([]);
  return request(`/api/municipalities/search?q=${encodeURIComponent(query)}`);
}

export function getMunicipality(insee: string): Promise<Municipality> {
  return request(`/api/municipalities/${insee}`);
}

export function launchAnalysis(insee: string): Promise<AnalysisJobLaunched> {
  return request(`/api/municipalities/${insee}/analyze`, { method: "POST" });
}

export function getAnalysisJob(jobId: string): Promise<AnalysisJob> {
  return request(`/api/analysis-jobs/${jobId}`);
}

export function getOpportunities(insee: string, filters: Partial<Filters> = {}): Promise<Opportunity[]> {
  const params = new URLSearchParams();
  if (filters.min_score != null) params.set("min_score", String(filters.min_score));
  if (filters.min_area != null) params.set("min_area", String(filters.min_area));
  if (filters.max_area != null) params.set("max_area", String(filters.max_area));
  if (filters.operation_type) params.set("operation_type", filters.operation_type);
  if (filters.vacant_only) params.set("vacant_only", "true");
  const qs = params.toString();
  return request(`/api/municipalities/${insee}/opportunities${qs ? `?${qs}` : ""}`);
}

export function getTopOpportunities(insee: string, limit = 50): Promise<Opportunity[]> {
  return request(`/api/municipalities/${insee}/top-opportunities?limit=${limit}`);
}

export function getParcel(parcelId: string): Promise<ParcelDetail> {
  return request(`/api/parcels/${parcelId}`);
}

export { API_URL };
