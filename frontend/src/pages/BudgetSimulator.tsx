import { useState } from "react";
import { api, formatINR, formatNumber } from "../api/client";
import PageHeader from "../components/PageHeader";
import { useFetch } from "../hooks/useFetch";
import { useFilters } from "../state/filters";
import type { Scenario } from "../types";

const PRESETS = [
  { label: "₹5 Crore", value: 5_000_000 },
  { label: "₹10 Crore", value: 10_000_000 },
  { label: "₹15 Crore", value: 15_000_000 },
  { label: "₹20 Crore", value: 20_000_000 },
];

export default function BudgetSimulator() {
  const { emissionFactor } = useFilters();
  const [budget, setBudget] = useState(10_000_000);
  const [custom, setCustom] = useState("10");
  const [minSpi, setMinSpi] = useState(0);
  const [maxPayback, setMaxPayback] = useState(12);
  const [minCapacity, setMinCapacity] = useState(0);
  const [locality, setLocality] = useState("all");
  const [result, setResult] = useState<Scenario | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const all = useFetch(() => api.localities(), []);

  const run = async (value = budget) => {
    setRunning(true);
    setError(null);
    try {
      const res = await api.simulate({
        budget_inr: value,
        min_spi: minSpi,
        max_payback_years: maxPayback,
        min_capacity_kw: minCapacity,
        locality: locality === "all" ? null : locality,
        emission_factor: emissionFactor,
      });
      setResult(res);
      setBudget(value);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  };

  return (
    <>
      <PageHeader
        title="Solar Planning Budget Simulator"
        subtitle="What-if planning simulation against the analyzed rooftop inventory"
        right={<span className="badge badge-blue">Simulation only — no approval or award</span>}
      />
      <div className="content">
        <div className="split">
          <div className="card">
            <div className="card-title">Planning inputs</div>
            <div className="card-sub">Choose a budget and optional eligibility thresholds</div>

            <div className="chip-row" style={{ marginBottom: 16 }}>
              {PRESETS.map((p) => (
                <button
                  key={p.value}
                  className={`chip ${budget === p.value ? "active" : ""}`}
                  onClick={() => {
                    setBudget(p.value);
                    run(p.value);
                  }}
                >
                  {p.label}
                </button>
              ))}
            </div>

            <div className="grid grid-2">
              <div className="field">
                <label>Custom budget (₹ Crore)</label>
                <div style={{ display: "flex", gap: 8 }}>
                  <input
                    type="number"
                    value={custom}
                    min={1}
                    onChange={(e) => setCustom(e.target.value)}
                  />
                  <button
                    className="btn"
                    onClick={() => run(Number(custom || 0) * 10_000_000)}
                  >
                    Apply
                  </button>
                </div>
              </div>
              <div className="field">
                <label>Locality filter</label>
                <select value={locality} onChange={(e) => setLocality(e.target.value)}>
                  <option value="all">All localities</option>
                  {(all.data?.items ?? []).map((l) => (
                    <option key={l.name} value={l.name}>
                      {l.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label>Minimum Solar Potential Index</label>
                <input
                  type="number"
                  value={minSpi}
                  min={0}
                  max={100}
                  onChange={(e) => setMinSpi(Number(e.target.value))}
                />
              </div>
              <div className="field">
                <label>Maximum payback (years)</label>
                <input
                  type="number"
                  value={maxPayback}
                  min={1}
                  step={0.5}
                  onChange={(e) => setMaxPayback(Number(e.target.value))}
                />
              </div>
              <div className="field">
                <label>Minimum capacity (kW)</label>
                <input
                  type="number"
                  value={minCapacity}
                  min={0}
                  step={5}
                  onChange={(e) => setMinCapacity(Number(e.target.value))}
                />
              </div>
              <div className="field" style={{ justifyContent: "flex-end" }}>
                <label>&nbsp;</label>
                <button className="btn" onClick={() => run()} disabled={running}>
                  {running ? <span className="spinner" /> : null}
                  {running ? "Simulating…" : "Run simulation"}
                </button>
              </div>
            </div>

            {error && (
              <div className="note warn" style={{ marginTop: 14 }}>
                {error}
              </div>
            )}

            <div className="note" style={{ marginTop: 16 }}>
              <b>Assumptions.</b> Eligible rooftop records are ranked by Solar Potential Index
              (then by annual generation) and selected greedily until the cumulative Feature 1
              installation cost reaches the budget. Emission factor applied:{" "}
              {emissionFactor} kg CO₂/kWh (user-configured). This is a planning simulation — it
              does not approve, award, shortlist or select any government project and creates
              no commitment of funds.
            </div>
          </div>

          <div className="card">
            <div className="card-title">Scenario result</div>
            <div className="card-sub">
              {result
                ? `Budget ${formatINR(result.budget_inr)} · ${result.locality ?? "all localities"}`
                : "Run a simulation to see the projected outcome"}
            </div>

            {!result ? (
              <div className="empty">
                <h3>No scenario computed yet</h3>
                <p>Select a budget above and run the simulation.</p>
              </div>
            ) : (
              <>
                <div className="stat-list">
                  <div className="stat-item">
                    <div className="s-label">Rooftops considered</div>
                    <div className="s-value">
                      {result.rooftops_considered}{" "}
                      <span className="muted small">
                        of {result.eligible_rooftops} eligible
                      </span>
                    </div>
                  </div>
                  <div className="stat-item">
                    <div className="s-label">Potential capacity</div>
                    <div className="s-value">{formatNumber(result.capacity_kw, 1)} kW</div>
                  </div>
                  <div className="stat-item">
                    <div className="s-label">Annual generation</div>
                    <div className="s-value">
                      {formatNumber(result.generation_kwh)} kWh
                    </div>
                  </div>
                  <div className="stat-item">
                    <div className="s-label">Estimated investment</div>
                    <div className="s-value">{formatINR(result.investment_inr)}</div>
                  </div>
                  <div className="stat-item">
                    <div className="s-label">Annual savings</div>
                    <div className="s-value">
                      {formatINR(result.annual_savings_inr)}
                    </div>
                  </div>
                  <div className="stat-item">
                    <div className="s-label">Estimated CO₂ reduction</div>
                    <div className="s-value">
                      {formatNumber(result.co2_tonnes)} t/yr
                    </div>
                  </div>
                  <div className="stat-item">
                    <div className="s-label">Average payback</div>
                    <div className="s-value">{result.avg_payback_years} years</div>
                  </div>
                  <div className="stat-item">
                    <div className="s-label">Unspent budget</div>
                    <div className="s-value">{formatINR(result.unspent_budget_inr)}</div>
                  </div>
                </div>

                <div style={{ marginTop: 14 }}>
                  <div className="classification">
                    Covered localities: {result.selected_localities.join(", ") || "none"}
                  </div>
                  <div className="classification">{result.selection_rule}</div>
                  <div className="classification">{result.classification}</div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
