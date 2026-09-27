import type {
  AssistantResponse,
  ChartsPayload,
  CitySummary,
  DatasetInfo,
  Filters,
  Locality,
  MapPoint,
  Rooftop,
  Scenario,
} from "../types";

export const API_BASE =
  (import.meta.env.VITE_API_BASE as string | undefined) ??
  (import.meta.env.DEV ? "http://127.0.0.1:8000/api" : "/api");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export function filterQuery(filters: Partial<Filters>): string {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "" && value !== "all") {
      params.set(key, String(value));
    }
  });
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export const api = {
  dataset: () => request<DatasetInfo>("/dataset"),
  loadDemo: () =>
    request<{ status: string }>("/dataset/load-demo", { method: "POST" }),
  uploadExcel: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<{ status: string; stats: Record<string, unknown> }>(
      "/upload/excel",
      { method: "POST", body: form },
    );
  },
  summary: (filters: Partial<Filters>, emissionFactor?: number) => {
    const qs = filterQuery(filters);
    const suffix = emissionFactor ? `${qs ? "&" : "?"}emission_factor=${emissionFactor}` : "";
    return request<CitySummary>(`/dashboard/summary${qs}${suffix}`);
  },
  localityAnalysis: (filters: Partial<Filters>) =>
    request<{ total: number; items: Locality[] }>(
      `/dashboard/locality-analysis${filterQuery(filters)}`,
    ),
  charts: (filters: Partial<Filters>) =>
    request<ChartsPayload>(`/dashboard/charts${filterQuery(filters)}`),
  localities: () => request<{ total: number; items: Locality[] }>("/localities"),
  locality: (name: string) =>
    request<{ locality: Locality; rooftops: Rooftop[] }>(
      `/localities/${encodeURIComponent(name)}`,
    ),
  rooftops: (filters: Partial<Filters>, limit = 200, sort = "spi", order = "desc") => {
    const qs = filterQuery(filters);
    return request<{ total: number; items: Rooftop[] }>(
      `/rooftops${qs}${qs ? "&" : "?"}limit=${limit}&sort=${sort}&order=${order}`,
    );
  },
  rooftop: (id: number) => request<Rooftop>(`/rooftops/${id}`),
  mapRooftops: (filters: Partial<Filters>) =>
    request<{ total: number; points: MapPoint[] }>(
      `/map/rooftops${filterQuery(filters)}`,
    ),
  mapLocalities: () =>
    request<{
      total: number;
      points: {
        name: string;
        latitude: number;
        longitude: number;
        rooftop_count: number;
        total_capacity_kw: number;
        total_generation_kwh: number;
        spi: number;
        avg_payback_years: number;
      }[];
    }>("/map/localities"),
  solarPotentialIndex: () =>
    request<{
      city_spi: number;
      weights: Record<string, number>;
      default_weights: Record<string, number>;
      method: string;
      scale: string;
      localities: Locality[];
    }>("/solar-potential-index"),
  recomputeIndex: (weights: Record<string, number>) =>
    request<{ status: string; weights: Record<string, number> }>(
      "/solar-potential-index/recompute",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ weights, persist: true }),
      },
    ),
  simulate: (body: {
    budget_inr: number;
    min_spi?: number;
    max_payback_years?: number;
    min_capacity_kw?: number;
    locality?: string | null;
    emission_factor?: number;
  }) =>
    request<Scenario>("/planning/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  compare: (body: Record<string, unknown>) =>
    request<{ scenarios: Scenario[] }>("/planning/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  environmental: (emissionFactor?: number) =>
    request<{
      annual_generation_kwh: number;
      emission_factor: number;
      emission_factor_unit: string;
      emission_factor_source: string;
      co2_tonnes: number;
      classification: string;
      formula: string;
    }>(
      `/environmental-impact${emissionFactor ? `?emission_factor=${emissionFactor}` : ""}`,
    ),
  ask: (question: string, emissionFactor?: number) =>
    request<AssistantResponse>("/assistant/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, emission_factor: emissionFactor }),
    }),
  knowledge: () =>
    request<{
      documents: { filename: string; title: string; chunks: number }[];
      answer_rule: string;
    }>("/assistant/knowledge"),
  reports: () =>
    request<{
      items: {
        id: number;
        title: string;
        filename: string;
        summary: Record<string, number>;
        created_at: string;
      }[];
    }>("/reports"),
  generateReport: (body: {
    title?: string;
    emission_factor?: number;
    budgets_inr?: number[];
  }) =>
    request<{ status: string; filename: string; summary: Record<string, number> }>(
      "/reports/generate",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      },
    ),
  reportUrl: (id: number) => `${API_BASE}/reports/${id}/download`,
  dataSources: () =>
    request<{
      items: {
        id: number;
        dataset: string;
        source: string;
        purpose: string;
        fields_used: string;
        access_date: string;
        license: string;
        classification: string;
      }[];
    }>("/meta/data-sources"),
};

export function formatINR(value: number): string {
  if (!Number.isFinite(Number(value))) return "—";
  const v = Number(value);
  if (v >= 10_000_000) return `₹${(v / 10_000_000).toFixed(2)} Cr`;
  if (v >= 100_000) return `₹${(v / 100_000).toFixed(2)} L`;
  return `₹${Math.round(v).toLocaleString("en-IN")}`;
}

export function formatNumber(value: number, digits = 0): string {
  if (!Number.isFinite(Number(value))) return "—";
  return Number(value).toLocaleString("en-IN", {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
  });
}
