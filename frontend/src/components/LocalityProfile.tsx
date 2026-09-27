import { formatINR, formatNumber } from "../api/client";
import type { Locality, Rooftop } from "../types";

const FACTOR_LABELS: Record<string, string> = {
  usable_area: "Usable rooftop area",
  generation: "Generation potential",
  capacity: "Capacity potential",
  economics: "Economic feasibility",
  payback: "Payback feasibility",
  suitability: "Suitability",
};

const FACTOR_WEIGHTS: Record<string, number> = {
  usable_area: 25,
  generation: 25,
  capacity: 20,
  economics: 15,
  payback: 10,
  suitability: 5,
};

export function FactorBreakdown({
  breakdown,
  total,
  weights,
}: {
  breakdown: Record<string, number> | null;
  total: number;
  weights?: Record<string, number>;
}) {
  if (!breakdown) return <div className="muted small">No index breakdown available.</div>;
  return (
    <div>
      {Object.entries(breakdown).map(([key, points]) => {
        const max = weights?.[key] ?? FACTOR_WEIGHTS[key] ?? 25;
        return (
          <div className="factor-row" key={key}>
            <span className="f-name">{FACTOR_LABELS[key] ?? key}</span>
            <span className="f-bar">
              <i style={{ width: `${Math.min(100, (points / max) * 100)}%` }} />
            </span>
            <span className="f-val">
              {points.toFixed(1)} / {max}
            </span>
          </div>
        );
      })}
      <div className="classification" style={{ marginTop: 8 }}>
        Weighted total: {total.toFixed(1)} / 100 · weights are configurable
      </div>
    </div>
  );
}

export default function LocalityProfile({
  locality,
  rooftops,
  loading,
  onClose,
  onSelectRooftop,
  weights,
}: {
  locality: Locality | null;
  rooftops?: Rooftop[];
  loading?: boolean;
  onClose?: () => void;
  onSelectRooftop?: (id: number) => void;
  weights?: Record<string, number>;
}) {
  if (loading) return <div className="card">Loading locality profile…</div>;
  if (!locality)
    return (
      <div className="card">
        <div className="empty">
          <h3>Select a locality</h3>
          <p>
            Click a locality on the map or in the table to open its complete solar profile and
            the “Why this score?” explanation.
          </p>
        </div>
      </div>
    );

  const l = locality;
  return (
    <div className="card">
      <div className="card-title" style={{ display: "flex", justifyContent: "space-between" }}>
        <span>Locality solar profile · {l.name}</span>
        {onClose && (
          <button className="btn btn-ghost" onClick={onClose}>
            Close
          </button>
        )}
      </div>
      <div className="card-sub">
        Aggregated by Feature 3 from {l.rooftop_count} analyzed Feature 1 rooftop records
      </div>

      <div className="stat-list">
        <div className="stat-item">
          <div className="s-label">Analyzed rooftops</div>
          <div className="s-value">{l.rooftop_count}</div>
        </div>
        <div className="stat-item">
          <div className="s-label">Total rooftop area</div>
          <div className="s-value">{formatNumber(l.total_rooftop_area_m2)} m²</div>
        </div>
        <div className="stat-item">
          <div className="s-label">Usable rooftop area</div>
          <div className="s-value">{formatNumber(l.total_usable_area_m2)} m²</div>
        </div>
        <div className="stat-item">
          <div className="s-label">Potential capacity</div>
          <div className="s-value">{formatNumber(l.total_capacity_kw, 1)} kW</div>
        </div>
        <div className="stat-item">
          <div className="s-label">Annual generation</div>
          <div className="s-value">{formatNumber(l.total_generation_kwh)} kWh</div>
        </div>
        <div className="stat-item">
          <div className="s-label">Estimated investment</div>
          <div className="s-value">{formatINR(l.total_cost_inr)}</div>
        </div>
        <div className="stat-item">
          <div className="s-label">Annual savings</div>
          <div className="s-value">{formatINR(l.total_savings_inr)}</div>
        </div>
        <div className="stat-item">
          <div className="s-label">Average payback</div>
          <div className="s-value">{l.avg_payback_years} years</div>
        </div>
      </div>

      <div className="split" style={{ marginTop: 16 }}>
        <div>
          <div className="card-title">Solar Potential Index · {l.spi} / 100</div>
          <div className="card-sub">Contribution of each measurable factor</div>
          <FactorBreakdown breakdown={l.spi_breakdown} total={l.spi} weights={weights} />
        </div>
        <div>
          <div className="card-title">Why this score?</div>
          <div className="note">{l.why_text}</div>
          <div style={{ marginTop: 10 }}>
            <span className="badge badge-high">{l.high_count} High</span>{" "}
            <span className="badge badge-medium">{l.medium_count} Medium</span>{" "}
            <span className="badge badge-low">{l.low_count} Low</span>
          </div>
        </div>
      </div>

      {rooftops && rooftops.length > 0 && (
        <>
          <div className="card-title" style={{ marginTop: 18 }}>
            Rooftop records in {l.name}
          </div>
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Location</th>
                  <th className="num">Lat</th>
                  <th className="num">Lon</th>
                  <th className="num">Usable m²</th>
                  <th className="num">kW</th>
                  <th className="num">kWh/yr</th>
                  <th className="num">Payback</th>
                  <th className="num">Index</th>
                  <th>Suitability</th>
                </tr>
              </thead>
              <tbody>
                {rooftops.map((r) => (
                  <tr
                    key={r.id}
                    className="clickable"
                    onClick={() => onSelectRooftop?.(r.id)}
                  >
                    <td>{r.location_input ?? r.locality}</td>
                    <td className="num">{r.latitude.toFixed(4)}</td>
                    <td className="num">{r.longitude.toFixed(4)}</td>
                    <td className="num">{formatNumber(r.usable_rooftop_area_m2)}</td>
                    <td className="num">{formatNumber(r.system_capacity_kw, 1)}</td>
                    <td className="num">{formatNumber(r.annual_generation_kwh)}</td>
                    <td className="num">{r.payback_period_years} y</td>
                    <td className="num">{r.spi}</td>
                    <td>
                      <span className={`badge badge-${r.suitability.toLowerCase()}`}>
                        {r.suitability}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
