import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, filterQuery, formatINR, formatNumber } from "../api/client";
import FilterBar from "../components/FilterBar";
import MapView from "../components/MapView";
import PageHeader from "../components/PageHeader";
import { useFetch } from "../hooks/useFetch";
import { useFilters } from "../state/filters";
import type { ChartsPayload, CitySummary, Locality, MapPoint } from "../types";

const AXIS = { fontSize: 11, fill: "#64748b" };

function Kpi({
  label,
  value,
  note,
}: {
  label: string;
  value: string;
  note?: string;
}) {
  return (
    <div className="kpi">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
      {note && <div className="kpi-note">{note}</div>}
    </div>
  );
}

export default function Dashboard() {
  const { filters, emissionFactor, setEmissionFactor } = useFilters();
  const [localities, setLocalities] = useState<string[]>([]);

  const summary = useFetch<CitySummary>(
    () => api.summary(filters, emissionFactor),
    [JSON.stringify(filters), emissionFactor],
  );
  const localityData = useFetch<{ items: Locality[] }>(
    () => api.localityAnalysis(filters),
    [JSON.stringify(filters)],
  );
  const charts = useFetch<ChartsPayload>(
    () => api.charts(filters),
    [JSON.stringify(filters)],
  );
  const map = useFetch<{ points: MapPoint[] }>(
    () => api.mapRooftops(filters),
    [JSON.stringify(filters)],
  );
  useFetch(() => api.localities().then((r) => {
    setLocalities(r.items.map((i) => i.name));
    return r;
  }), []);

  const s = summary.data;
  const c = charts.data;

  return (
    <>
      <PageHeader
        title="Solar Planning Intelligence"
        subtitle="AI-assisted rooftop solar planning and decision support"
        right={
          <>
            <div className="field" style={{ minWidth: 170 }}>
              <label>Emission factor (kg CO₂/kWh)</label>
              <input
                type="number"
                step="0.01"
                value={emissionFactor}
                onChange={(e) => setEmissionFactor(Number(e.target.value))}
              />
            </div>
            <span className="badge badge-teal">Demo dataset</span>
          </>
        }
      />
      <div className="content">
        <FilterBar localities={localities} />

        {summary.error && (
          <div className="note warn">Could not reach API: {summary.error}</div>
        )}

        <div className="grid grid-4" style={{ marginBottom: 16 }}>
          <Kpi
            label="Analyzed rooftops"
            value={s ? formatNumber(s.rooftop_records) : "—"}
            note={s ? `${s.locality_count} localities in scope` : ""}
          />
          <Kpi
            label="Total potential capacity"
            value={s ? `${formatNumber(s.total_capacity_kw, 1)} kW` : "—"}
            note={s ? `${s.total_capacity_mw.toFixed(3)} MW` : ""}
          />
          <Kpi
            label="Annual solar generation"
            value={s ? `${formatNumber(s.total_generation_kwh)} kWh` : "—"}
            note={s ? `${s.total_generation_gwh.toFixed(3)} GWh per year` : ""}
          />
          <Kpi
            label="Estimated investment"
            value={s ? formatINR(s.total_cost_inr) : "—"}
            note="Feature 1 installation cost totals"
          />
          <Kpi
            label="Annual savings"
            value={s ? formatINR(s.total_savings_inr) : "—"}
            note={s ? `Payback avg ${s.avg_payback_years} years` : ""}
          />
          <Kpi
            label="Estimated CO₂ reduction"
            value={s ? `${formatNumber(s.co2_tonnes)} t/yr` : "—"}
            note={s ? `Factor ${s.emission_factor} ${s.emission_factor_unit}` : ""}
          />
          <Kpi
            label="City Solar Potential Index"
            value={s ? `${s.avg_spi} / 100` : "—"}
            note="Project decision-support score"
          />
          <Kpi
            label="Suitability split"
            value={
              s ? `${s.high_count} / ${s.medium_count} / ${s.low_count}` : "—"
            }
            note="High / Medium / Low"
          />
        </div>

        <div className="card">
          <div className="card-title">Solar potential map</div>
          <div className="card-sub">
            Rooftop locations from Feature 1 coordinates, coloured by Solar Potential Index ·
            basemap © OpenStreetMap (public data)
          </div>
          <MapView
            points={map.data?.points ?? []}
            localities={localityData.data?.items}
            height={430}
          />
        </div>

        <div className="section-title">Locality analysis</div>
        <div className="card">
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Locality</th>
                  <th className="num">Rooftops</th>
                  <th className="num">Usable m²</th>
                  <th className="num">Capacity kW</th>
                  <th className="num">Generation kWh</th>
                  <th className="num">Investment</th>
                  <th className="num">Savings/yr</th>
                  <th className="num">Payback</th>
                  <th className="num">Index</th>
                  <th>Suitability</th>
                </tr>
              </thead>
              <tbody>
                {(localityData.data?.items ?? []).map((l) => (
                  <tr key={l.name}>
                    <td>
                      <b>{l.name}</b>
                    </td>
                    <td className="num">{l.rooftop_count}</td>
                    <td className="num">{formatNumber(l.total_usable_area_m2)}</td>
                    <td className="num">{formatNumber(l.total_capacity_kw, 1)}</td>
                    <td className="num">{formatNumber(l.total_generation_kwh)}</td>
                    <td className="num">{formatINR(l.total_cost_inr)}</td>
                    <td className="num">{formatINR(l.total_savings_inr)}</td>
                    <td className="num">{l.avg_payback_years} y</td>
                    <td className="num">
                      <span className="spi-pill">
                        {l.spi} <span>/100</span>
                      </span>
                    </td>
                    <td>
                      <span className="badge badge-high">{l.high_count} High</span>{" "}
                      <span className="badge badge-medium">{l.medium_count} Med</span>{" "}
                      <span className="badge badge-low">{l.low_count} Low</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="two-col" style={{ marginTop: 16 }}>
          <div className="card">
            <div className="card-title">Capacity by locality</div>
            <div className="card-sub">Total system capacity (kW) per locality</div>
            <div className="chart-box">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={c?.capacity_by_locality ?? []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="locality" tick={AXIS} interval={0} angle={-18} textAnchor="end" height={55} />
                  <YAxis tick={AXIS} />
                  <Tooltip formatter={(v) => formatNumber(Number(v), 1)} />
                  <Bar dataKey="capacity_kw" name="Capacity (kW)" fill="#0f766e" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="card">
            <div className="card-title">Generation by locality</div>
            <div className="card-sub">Estimated annual generation (kWh) per locality</div>
            <div className="chart-box">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={c?.generation_by_locality ?? []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="locality" tick={AXIS} interval={0} angle={-18} textAnchor="end" height={55} />
                  <YAxis tick={AXIS} />
                  <Tooltip formatter={(v) => formatNumber(Number(v))} />
                  <Bar dataKey="generation_kwh" name="Generation (kWh)" fill="#2563eb" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="card">
            <div className="card-title">Investment vs savings</div>
            <div className="card-sub">One-time installation investment against annual savings</div>
            <div className="chart-box">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={c?.investment_vs_savings ?? []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="locality" tick={AXIS} interval={0} angle={-18} textAnchor="end" height={55} />
                  <YAxis tick={AXIS} />
                  <Tooltip formatter={(v) => formatINR(Number(v))} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="investment_inr" name="Investment" fill="#0b1f33" radius={[3, 3, 0, 0]} />
                  <Bar dataKey="annual_savings_inr" name="Annual savings" fill="#0f766e" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="card">
            <div className="card-title">Payback distribution</div>
            <div className="card-sub">Rooftop records grouped by payback period</div>
            <div className="chart-box">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={c?.payback_distribution ?? []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="bucket" tick={AXIS} />
                  <YAxis tick={AXIS} allowDecimals={false} />
                  <Tooltip formatter={(v) => `${v} rooftops`} />
                  <Bar dataKey="count" name="Rooftops" fill="#d97706" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="card">
            <div className="card-title">Solar Potential Index</div>
            <div className="card-sub">Index score by locality (0–100 decision-support score)</div>
            <div className="chart-box">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={c?.index_by_locality ?? []} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis type="number" domain={[0, 100]} tick={AXIS} />
                  <YAxis type="category" dataKey="locality" tick={AXIS} width={92} />
                  <Tooltip formatter={(v) => `${v} / 100`} />
                  <Bar dataKey="spi" name="Index" radius={[0, 3, 3, 0]}>
                    {(c?.index_by_locality ?? []).map((entry) => (
                      <Cell
                        key={entry.locality}
                        fill={
                          entry.spi >= 61
                            ? "#2563eb"
                            : entry.spi >= 41
                              ? "#d97706"
                              : "#b91c1c"
                        }
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="card">
            <div className="card-title">Suitability distribution</div>
            <div className="card-sub">Feature 1 suitability ratings across filtered records</div>
            <div className="chart-box">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={c?.suitability_distribution ?? []}
                    dataKey="count"
                    nameKey="name"
                    innerRadius={58}
                    outerRadius={95}
                    paddingAngle={2}
                  >
                    {(c?.suitability_distribution ?? []).map((entry) => (
                      <Cell
                        key={entry.name}
                        fill={
                          entry.name === "High"
                            ? "#15803d"
                            : entry.name === "Medium"
                              ? "#d97706"
                              : "#b91c1c"
                        }
                      />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v, n) => `${v} ${n}`} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        <div className="note" style={{ marginTop: 16 }}>
          <b>Data classification.</b>{" "}
          {s
            ? Object.entries(s.data_classification)
                .map(([k, v]) => `${k}: ${v}`)
                .join(" · ")
            : "Loading..."}{" "}
          · Source workbook rows are flagged SYNTHETIC_DEMO and are demonstration values,
          not real-world measurements. Filter query:{" "}
          <code>{filterQuery(filters) || "? (no filters)"}</code>
        </div>
      </div>
    </>
  );
}
