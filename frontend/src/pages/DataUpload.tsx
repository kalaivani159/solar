import { useRef, useState } from "react";
import { api, formatINR, formatNumber } from "../api/client";
import PageHeader from "../components/PageHeader";
import { useFetch } from "../hooks/useFetch";
import type { DatasetInfo, Rooftop } from "../types";

const CLASSES = [
  { code: "A", label: "Feature 1 output", desc: "Values read directly from the uploaded workbook" },
  { code: "B", label: "Calculated by Feature 3", desc: "Aggregates, index, CO₂, distributions" },
  { code: "C", label: "Real public data", desc: "OpenStreetMap basemap tiles" },
  { code: "D", label: "Simulated / demo data", desc: "SYNTHETIC_DEMO source rows and budget scenarios" },
  { code: "E", label: "User-configured assumption", desc: "Emission factor, index weights, thresholds" },
];

export default function DataUpload() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const dataset = useFetch<DatasetInfo>(() => api.dataset(), []);
  const preview = useFetch<{ items: Rooftop[] }>(() => api.rooftops({}, 10), []);
  const sources = useFetch(() => api.dataSources(), []);

  const handleFile = async (file: File | undefined) => {
    if (!file) return;
    setUploading(true);
    setMessage(null);
    try {
      const res = await api.uploadExcel(file);
      const stats = res.stats as Record<string, unknown>;
      setMessage(
        `Imported ${stats.valid_rows} valid rooftop records from ${
          stats.total_rows
        } rows (${stats.invalid_rows} invalid, ${stats.duplicate_records} duplicates).`,
      );
      dataset.reload();
      preview.reload();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : String(e));
    } finally {
      setUploading(false);
    }
  };

  const loadDemo = async () => {
    setUploading(true);
    setMessage(null);
    try {
      await api.loadDemo();
      setMessage("Bundled Feature 1 demo dataset loaded.");
      dataset.reload();
      preview.reload();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : String(e));
    } finally {
      setUploading(false);
    }
  };

  const d = dataset.data;
  const log = (d?.validation_log ?? {}) as Record<string, unknown>;
  const issues = (log.issues as { row: number; issue: string }[]) ?? [];
  const suitability = (log.suitability_counts ?? {}) as Record<string, number>;

  return (
    <>
      <PageHeader
        title="Data Management"
        subtitle="Import Feature 1 Excel outputs, validate, clean and inspect the dataset"
        right={
          d?.loaded ? (
            <span className="badge badge-teal">Active dataset · {d.rows_valid} records</span>
          ) : (
            <span className="badge badge-slate">No dataset</span>
          )
        }
      />
      <div className="content">
        <div className="card">
          <div className="card-title">Excel data upload</div>
          <div className="card-sub">
            Accepts .xlsx workbooks containing Feature 1 outputs. The system identifies the
            data sheet (README/metadata sheets are skipped), maps and normalizes columns,
            validates coordinates and numeric ranges, removes duplicates and cleans values.
          </div>

          <div
            className={`dropzone ${drag ? "drag" : ""}`}
            onClick={() => fileRef.current?.click()}
            onDragOver={(e) => {
              e.preventDefault();
              setDrag(true);
            }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDrag(false);
              handleFile(e.dataTransfer.files[0]);
            }}
          >
            <div style={{ fontSize: 26, color: "#0f766e" }}>⬆</div>
            <h3>{uploading ? "Importing workbook…" : "Drop the Feature 1 Excel file here"}</h3>
            <p>or click to browse · .xlsx only</p>
            <input
              ref={fileRef}
              type="file"
              accept=".xlsx,.xlsm"
              style={{ display: "none" }}
              onChange={(e) => handleFile(e.target.files?.[0])}
            />
          </div>

          <div style={{ display: "flex", gap: 10, marginTop: 14, alignItems: "center" }}>
            <button className="btn btn-secondary" onClick={loadDemo} disabled={uploading}>
              Reload bundled demo dataset
            </button>
            {message && <span className="small muted">{message}</span>}
          </div>
        </div>

        {d?.loaded && (
          <div className="card">
            <div className="card-title">Data quality report</div>
            <div className="card-sub">
              {d.filename} · sheet {d.sheet_name} · imported{" "}
              {d.uploaded_at ? new Date(d.uploaded_at).toLocaleString() : ""}
            </div>
            <div className="quality-grid">
              <div className="quality-item">
                <div className="q-value">{d.rows_total}</div>
                <div className="q-label">Total rooftop records</div>
              </div>
              <div className="quality-item">
                <div className="q-value">{d.rows_valid}</div>
                <div className="q-label">Valid records</div>
              </div>
              <div className="quality-item">
                <div className="q-value">{d.rows_invalid}</div>
                <div className="q-label">Invalid records</div>
              </div>
              <div className="quality-item">
                <div className="q-value">{d.missing_values}</div>
                <div className="q-label">Missing values</div>
              </div>
              <div className="quality-item">
                <div className="q-value">{d.duplicate_records}</div>
                <div className="q-label">Duplicate records</div>
              </div>
              <div className="quality-item">
                <div className="q-value">{d.localities_count}</div>
                <div className="q-label">Localities found</div>
              </div>
            </div>

            <div className="grid grid-2" style={{ marginTop: 16 }}>
              <div className="note">
                <b>Column mapping.</b>{" "}
                {Object.entries(
                  (log.mapped_columns as Record<string, string>) ?? {},
                )
                  .map(([orig, canon]) => `${orig} → ${canon}`)
                  .join(" · ")}
              </div>
              <div className="note">
                <b>Suitability mix.</b>{" "}
                {Object.entries(suitability)
                  .map(([k, v]) => `${k}: ${v}`)
                  .join(" · ")}{" "}
                · {d.notes}
              </div>
            </div>

            {issues.length > 0 ? (
              <>
                <div className="card-title" style={{ marginTop: 16 }}>
                  Validation issues
                </div>
                <div className="table-wrap">
                  <table className="data">
                    <thead>
                      <tr>
                        <th>Source row</th>
                        <th>Issue</th>
                      </tr>
                    </thead>
                    <tbody>
                      {issues.slice(0, 50).map((i, idx) => (
                        <tr key={idx}>
                          <td>{i.row}</td>
                          <td>{i.issue}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            ) : (
              <div className="note" style={{ marginTop: 16 }}>
                <b>No validation issues found.</b> All rows passed coordinate range checks,
                numeric range checks, usable-area consistency, missing-value checks and
                duplicate detection.
              </div>
            )}
          </div>
        )}

        <div className="card">
          <div className="card-title">Dataset preview</div>
          <div className="card-sub">First 10 stored rooftop records</div>
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Location</th>
                  <th>Locality</th>
                  <th className="num">Lat</th>
                  <th className="num">Lon</th>
                  <th className="num">Usable m²</th>
                  <th className="num">kW</th>
                  <th className="num">kWh/yr</th>
                  <th className="num">Cost</th>
                  <th className="num">Savings</th>
                  <th className="num">Payback</th>
                  <th>Suitability</th>
                  <th>Data type</th>
                </tr>
              </thead>
              <tbody>
                {(preview.data?.items ?? []).map((r) => (
                  <tr key={r.id}>
                    <td>{(r.location_input ?? "").slice(0, 30)}</td>
                    <td>{r.locality}</td>
                    <td className="num">{r.latitude.toFixed(4)}</td>
                    <td className="num">{r.longitude.toFixed(4)}</td>
                    <td className="num">{formatNumber(r.usable_rooftop_area_m2)}</td>
                    <td className="num">{formatNumber(r.system_capacity_kw, 1)}</td>
                    <td className="num">{formatNumber(r.annual_generation_kwh)}</td>
                    <td className="num">{formatINR(r.installation_cost_inr)}</td>
                    <td className="num">{formatINR(r.annual_savings_inr)}</td>
                    <td className="num">{r.payback_period_years}</td>
                    <td>
                      <span className={`badge badge-${r.suitability.toLowerCase()}`}>
                        {r.suitability}
                      </span>
                    </td>
                    <td>
                      <span className="badge badge-slate">{r.data_type}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card">
          <div className="card-title">Data classification legend</div>
          <div className="card-sub">
            Every value in Feature 3 is labelled with one of these classes
          </div>
          <div className="grid grid-3">
            {CLASSES.map((c) => (
              <div key={c.code} className="stat-item">
                <div className="s-label">
                  {c.code} · {c.label}
                </div>
                <div className="small muted" style={{ marginTop: 6 }}>
                  {c.desc}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="card-title">Data sources</div>
          <div className="card-sub">
            Only sources genuinely used by Feature 3 are registered
          </div>
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Dataset</th>
                  <th>Source</th>
                  <th>Purpose</th>
                  <th>Fields used</th>
                  <th>Accessed</th>
                  <th>License</th>
                  <th>Class</th>
                </tr>
              </thead>
              <tbody>
                {(sources.data?.items ?? []).map((s) => (
                  <tr key={s.id}>
                    <td>{s.dataset}</td>
                    <td>{s.source}</td>
                    <td>{s.purpose}</td>
                    <td style={{ whiteSpace: "normal", maxWidth: 320 }}>{s.fields_used}</td>
                    <td>{s.access_date}</td>
                    <td>{s.license}</td>
                    <td>
                      <span className="badge badge-teal">{s.classification.split(" - ")[0]}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  );
}
