import { useState } from "react";
import { api, formatINR, formatNumber } from "../api/client";
import FilterBar from "../components/FilterBar";
import LocalityProfile from "../components/LocalityProfile";
import PageHeader from "../components/PageHeader";
import { useFetch } from "../hooks/useFetch";
import { useFilters } from "../state/filters";
import type { Locality, Rooftop } from "../types";

export default function LocalityAnalysis() {
  const { filters } = useFilters();
  const [selected, setSelected] = useState<string | null>(null);
  const [weights, setWeights] = useState<Record<string, number>>({});
  const [weightMsg, setWeightMsg] = useState<string | null>(null);
  const [savingWeights, setSavingWeights] = useState(false);

  const list = useFetch<{ items: Locality[] }>(
    () => api.localityAnalysis(filters),
    [JSON.stringify(filters)],
  );
  const all = useFetch(() => api.localities(), []);
  const indexMeta = useFetch(() => api.solarPotentialIndex(), []);
  const profile = useFetch<{ locality: Locality; rooftops: Rooftop[] }>(
    () => api.locality(selected as string),
    [selected],
    !!selected,
  );

  if (indexMeta.data && Object.keys(weights).length === 0) {
    setWeights(
      Object.fromEntries(
        Object.entries(indexMeta.data.weights).map(([k, v]) => [k, Math.round(v * 100) / 100]),
      ),
    );
  }

  const names = (all.data?.items ?? []).map((i) => i.name);
  const items = list.data?.items ?? [];

  const applyWeights = async () => {
    setSavingWeights(true);
    setWeightMsg(null);
    try {
      const res = await api.recomputeIndex(weights);
      setWeights(res.weights);
      setWeightMsg("Solar Potential Index recomputed with the updated weights.");
      list.reload();
      profile.reload();
      indexMeta.reload();
    } catch (e) {
      setWeightMsg(e instanceof Error ? e.message : String(e));
    } finally {
      setSavingWeights(false);
    }
  };

  const restoreDefaults = async () => {
    const defaults = indexMeta.data?.default_weights ?? {};
    setWeights(defaults);
    setSavingWeights(true);
    setWeightMsg(null);
    try {
      const res = await api.recomputeIndex(defaults);
      setWeights(res.weights);
      setWeightMsg("Default weights restored and the index recomputed.");
      list.reload();
      profile.reload();
      indexMeta.reload();
    } catch (e) {
      setWeightMsg(e instanceof Error ? e.message : String(e));
    } finally {
      setSavingWeights(false);
    }
  };

  const WEIGHT_LABELS: Record<string, string> = {
    usable_area: "Usable rooftop area",
    generation: "Generation potential",
    capacity: "Capacity potential",
    economics: "Economic feasibility",
    payback: "Payback feasibility",
    suitability: "Suitability",
  };

  return (
    <>
      <PageHeader
        title="Locality Analysis"
        subtitle="Locality-level aggregation of Feature 1 rooftop results"
        right={<span className="badge badge-teal">{items.length} localities</span>}
      />
      <div className="content">
        <FilterBar localities={names} />

        <div className="card">
          <div className="card-title">Locality aggregation</div>
          <div className="card-sub">
            Grouped by the Locality column of the uploaded workbook — no locality is randomly
            assigned
          </div>
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Locality</th>
                  <th className="num">Rooftops</th>
                  <th className="num">Rooftop m²</th>
                  <th className="num">Usable m²</th>
                  <th className="num">Panels</th>
                  <th className="num">Capacity kW</th>
                  <th className="num">Generation kWh</th>
                  <th className="num">Investment</th>
                  <th className="num">Savings/yr</th>
                  <th className="num">Avg payback</th>
                  <th className="num">Index</th>
                </tr>
              </thead>
              <tbody>
                {items.map((l) => (
                  <tr
                    key={l.name}
                    className="clickable"
                    onClick={() => setSelected(l.name)}
                    style={
                      selected === l.name ? { background: "#e6f3f1" } : undefined
                    }
                  >
                    <td>
                      <b>{l.name}</b>
                    </td>
                    <td className="num">{l.rooftop_count}</td>
                    <td className="num">{formatNumber(l.total_rooftop_area_m2)}</td>
                    <td className="num">{formatNumber(l.total_usable_area_m2)}</td>
                    <td className="num">{formatNumber(l.total_panels)}</td>
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
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {items.length === 0 && (
            <div className="empty">
              <h3>No localities match the current filters</h3>
              <p>Reset the filters to see all locality aggregations.</p>
            </div>
          )}
        </div>

        <div className="card" style={{ marginTop: 16 }}>
          <div className="card-title">Solar Potential Index weights</div>
          <div className="card-sub">
            {indexMeta.data?.method ?? "Min-max normalization across the uploaded dataset"} ·{" "}
            {indexMeta.data?.scale ?? "0–100 decision-support score"} · weights are rescaled to
            sum to 100
          </div>
          <div className="grid grid-3">
            {Object.entries(weights).map(([key, value]) => (
              <div className="field" key={key}>
                <label>{WEIGHT_LABELS[key] ?? key}</label>
                <input
                  type="number"
                  min={0}
                  value={value}
                  onChange={(e) =>
                    setWeights((prev) => ({ ...prev, [key]: Number(e.target.value) }))
                  }
                />
              </div>
            ))}
          </div>
          <div
            style={{
              display: "flex",
              gap: 10,
              alignItems: "center",
              marginTop: 14,
            }}
          >
            <button className="btn" onClick={applyWeights} disabled={savingWeights}>
              {savingWeights ? <span className="spinner" /> : null}
              {savingWeights ? "Recomputing…" : "Apply weights & recompute"}
            </button>
            <button
              className="btn btn-secondary"
              onClick={restoreDefaults}
              disabled={savingWeights}
            >
              Restore defaults
            </button>
            {weightMsg && <span className="small muted">{weightMsg}</span>}
          </div>
        </div>

        <div style={{ marginTop: 16 }}>
          <LocalityProfile
            locality={selected && profile.data ? profile.data.locality : null}
            rooftops={profile.data?.rooftops}
            loading={!!selected && profile.loading}
            onClose={() => {
              setSelected(null);
              profile.clear();
            }}
            weights={weights}
          />
        </div>
      </div>
    </>
  );
}
