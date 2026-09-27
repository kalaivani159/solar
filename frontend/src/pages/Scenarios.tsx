import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, formatINR, formatNumber } from "../api/client";
import PageHeader from "../components/PageHeader";
import { useFetch } from "../hooks/useFetch";
import { useFilters } from "../state/filters";
import type { Scenario } from "../types";

const DEFAULT_BUDGETS = [
  { label: "₹5 Cr", value: 5_000_000 },
  { label: "₹10 Cr", value: 10_000_000 },
  { label: "₹15 Cr", value: 15_000_000 },
  { label: "₹20 Cr", value: 20_000_000 },
];

export default function Scenarios() {
  const { emissionFactor } = useFilters();
  const [minSpi, setMinSpi] = useState(0);
  const [maxPayback, setMaxPayback] = useState(12);
  const [budgets, setBudgets] = useState<number[]>(
    DEFAULT_BUDGETS.map((b) => b.value),
  );
  const [custom, setCustom] = useState("");

  const data = useFetch<{ scenarios: Scenario[] }>(
    () =>
      api.compare({
        budgets_inr: budgets,
        min_spi: minSpi,
        max_payback_years: maxPayback,
        emission_factor: emissionFactor,
      }),
    [JSON.stringify(budgets), minSpi, maxPayback, emissionFactor],
  );

  const scenarios = data.data?.scenarios ?? [];
  const chart = scenarios.map((s) => ({
    label: `₹${(s.budget_inr / 10_000_000).toFixed(0)} Cr`,
    investment: s.investment_inr,
    capacity: s.capacity_kw,
    generation: s.generation_gwh * 1000,
    savings: s.annual_savings_inr,
    rooftops: s.rooftops_considered,
    co2: s.co2_tonnes,
  }));

  const toggleBudget = (value: number) => {
    setBudgets((prev) =>
      prev.includes(value)
        ? prev.filter((v) => v !== value)
        : [...prev, value].sort((a, b) => a - b),
    );
  };

  return (
    <>
      <PageHeader
        title="Scenario Comparison"
        subtitle="Consequences of different planning budgets under the same assumptions"
        right={<span className="badge badge-blue">No scenario is labelled “best”</span>}
      />
      <div className="content">
        <div className="filter-bar">
          <div className="field">
            <label>Budgets in comparison</label>
            <div className="chip-row">
              {DEFAULT_BUDGETS.map((b) => (
                <button
                  key={b.value}
                  className={`chip ${budgets.includes(b.value) ? "active" : ""}`}
                  onClick={() => toggleBudget(b.value)}
                >
                  {b.label}
                </button>
              ))}
            </div>
          </div>
          <div className="field" style={{ minWidth: 180 }}>
            <label>Add custom budget (₹ Crore)</label>
            <div style={{ display: "flex", gap: 8 }}>
              <input
                type="number"
                value={custom}
                placeholder="e.g. 12"
                onChange={(e) => setCustom(e.target.value)}
              />
              <button
                className="btn"
                onClick={() => {
                  const v = Number(custom);
                  if (v > 0) {
                    toggleBudget(v * 10_000_000);
                    setCustom("");
                  }
                }}
              >
                Add
              </button>
            </div>
          </div>
          <div className="field">
            <label>Min index</label>
            <input
              type="number"
              value={minSpi}
              onChange={(e) => setMinSpi(Number(e.target.value))}
            />
          </div>
          <div className="field">
            <label>Max payback (yrs)</label>
            <input
              type="number"
              value={maxPayback}
              onChange={(e) => setMaxPayback(Number(e.target.value))}
            />
          </div>
        </div>

        <div className="card">
          <div className="card-title">Comparison table</div>
          <div className="card-sub">
            Same eligibility rules applied to each budget · emission factor {emissionFactor} kg
            CO₂/kWh
          </div>
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Budget</th>
                  <th className="num">Rooftops</th>
                  <th className="num">Investment</th>
                  <th className="num">Capacity kW</th>
                  <th className="num">Generation kWh</th>
                  <th className="num">Savings/yr</th>
                  <th className="num">CO₂ t/yr</th>
                  <th className="num">Avg payback</th>
                  <th className="num">Unspent</th>
                </tr>
              </thead>
              <tbody>
                {scenarios.map((s) => (
                  <tr key={s.budget_inr}>
                    <td>
                      <b>{formatINR(s.budget_inr)}</b>
                    </td>
                    <td className="num">{s.rooftops_considered}</td>
                    <td className="num">{formatINR(s.investment_inr)}</td>
                    <td className="num">{formatNumber(s.capacity_kw, 1)}</td>
                    <td className="num">{formatNumber(s.generation_kwh)}</td>
                    <td className="num">{formatINR(s.annual_savings_inr)}</td>
                    <td className="num">{formatNumber(s.co2_tonnes)}</td>
                    <td className="num">{s.avg_payback_years} y</td>
                    <td className="num">{formatINR(s.unspent_budget_inr)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {scenarios.length === 0 && (
            <div className="empty">
              <h3>Select at least one budget</h3>
              <p>Use the budget chips above to build the comparison.</p>
            </div>
          )}
        </div>

        <div className="two-col" style={{ marginTop: 16 }}>
          <div className="card">
            <div className="card-title">Investment vs annual savings</div>
            <div className="card-sub">Rupees deployed against yearly return per budget</div>
            <div className="chart-box">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chart}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#64748b" }} />
                  <YAxis tick={{ fontSize: 11, fill: "#64748b" }} />
                  <Tooltip formatter={(v) => formatINR(Number(v))} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="investment" name="Investment" fill="#0b1f33" radius={[3, 3, 0, 0]} />
                  <Bar dataKey="savings" name="Annual savings" fill="#0f766e" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="card">
            <div className="card-title">Capacity and rooftops covered</div>
            <div className="card-sub">Planned capacity (kW) and number of rooftop records</div>
            <div className="chart-box">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chart}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#64748b" }} />
                  <YAxis tick={{ fontSize: 11, fill: "#64748b" }} />
                  <Tooltip formatter={(v) => formatNumber(Number(v), 1)} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="capacity" name="Capacity (kW)" fill="#2563eb" radius={[3, 3, 0, 0]} />
                  <Bar dataKey="rooftops" name="Rooftops" fill="#d97706" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="card">
            <div className="card-title">Annual generation</div>
            <div className="card-sub">Projected generation (MWh/yr) per budget scenario</div>
            <div className="chart-box">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chart}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#64748b" }} />
                  <YAxis tick={{ fontSize: 11, fill: "#64748b" }} />
                  <Tooltip formatter={(v) => `${formatNumber(Number(v))} MWh`} />
                  <Bar dataKey="generation" name="Generation (MWh)" fill="#0f766e" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="card">
            <div className="card-title">Estimated CO₂ reduction</div>
            <div className="card-sub">Tonnes CO₂ per year at the configured emission factor</div>
            <div className="chart-box">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chart}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#64748b" }} />
                  <YAxis tick={{ fontSize: 11, fill: "#64748b" }} />
                  <Tooltip formatter={(v) => `${formatNumber(Number(v))} tonnes`} />
                  <Bar dataKey="co2" name="CO₂ t/yr" fill="#15803d" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        <div className="note" style={{ marginTop: 16 }}>
          {scenarios[0]?.disclaimer ??
            "Scenarios are simulations computed from the uploaded dataset and do not represent approvals."}
        </div>
      </div>
    </>
  );
}
