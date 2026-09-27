import { formatINR, formatNumber } from "../api/client";
import { FactorBreakdown } from "./LocalityProfile";
import type { Rooftop } from "../types";

export default function RooftopDetail({
  rooftop,
  onClose,
}: {
  rooftop: Rooftop | null;
  onClose: () => void;
}) {
  if (!rooftop) return null;
  const r = rooftop;
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(11,31,51,0.55)",
        zIndex: 900,
        display: "flex",
        justifyContent: "flex-end",
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: "min(560px, 94vw)",
          height: "100%",
          background: "#fff",
          padding: 24,
          overflowY: "auto",
          boxShadow: "-8px 0 24px rgba(0,0,0,0.18)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
          <div>
            <div className="card-title">Feature 1 rooftop analysis</div>
            <div className="card-sub">
              {r.location_input ?? r.locality} · {r.rooftop_selection ?? "Selected rooftop"}
            </div>
          </div>
          <button className="btn btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>

        <div className="note">
          <b>Geographic identity:</b> {r.locality} · {r.latitude.toFixed(6)},{" "}
          {r.longitude.toFixed(6)} · no Building_ID is used in this project.
          <br />
          <span className="classification">
            Source row {r.source_row} · Data_Type {r.data_type} · classification A (Feature 1
            output), index B (Feature 3)
          </span>
        </div>

        <div className="stat-list" style={{ marginTop: 14 }}>
          <div className="stat-item">
            <div className="s-label">Rooftop area</div>
            <div className="s-value">{formatNumber(r.rooftop_area_m2)} m²</div>
          </div>
          <div className="stat-item">
            <div className="s-label">Usable rooftop area</div>
            <div className="s-value">{formatNumber(r.usable_rooftop_area_m2)} m²</div>
          </div>
          <div className="stat-item">
            <div className="s-label">Recommended panels</div>
            <div className="s-value">{r.recommended_panels}</div>
          </div>
          <div className="stat-item">
            <div className="s-label">System capacity</div>
            <div className="s-value">{formatNumber(r.system_capacity_kw, 2)} kW</div>
          </div>
          <div className="stat-item">
            <div className="s-label">Annual generation</div>
            <div className="s-value">{formatNumber(r.annual_generation_kwh)} kWh</div>
          </div>
          <div className="stat-item">
            <div className="s-label">Installation cost</div>
            <div className="s-value">{formatINR(r.installation_cost_inr)}</div>
          </div>
          <div className="stat-item">
            <div className="s-label">Annual savings</div>
            <div className="s-value">{formatINR(r.annual_savings_inr)}</div>
          </div>
          <div className="stat-item">
            <div className="s-label">Payback period</div>
            <div className="s-value">{r.payback_period_years} years</div>
          </div>
        </div>

        <div style={{ marginTop: 16 }}>
          <span className={`badge badge-${r.suitability.toLowerCase()}`}>
            Suitability: {r.suitability}
          </span>{" "}
          <span className="badge badge-teal">
            Solar Potential Index {r.spi} / 100
          </span>
        </div>

        <div className="card-title" style={{ marginTop: 20 }}>
          Index breakdown
        </div>
        <FactorBreakdown breakdown={r.spi_breakdown} total={r.spi} />
      </div>
    </div>
  );
}
