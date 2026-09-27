import { useState } from "react";
import { api, formatNumber } from "../api/client";
import PageHeader from "../components/PageHeader";
import { useFetch } from "../hooks/useFetch";
import { useFilters } from "../state/filters";

const SECTIONS = [
  "Project title",
  "Study area",
  "Dataset description",
  "Number of rooftop records",
  "Total rooftop area",
  "Total usable rooftop area",
  "Total solar capacity",
  "Annual generation",
  "Estimated investment",
  "Annual savings",
  "Payback analysis",
  "Locality-wise analysis",
  "Solar Potential Index",
  "GIS visualization",
  "Budget scenarios",
  "Environmental impact",
  "Methodology",
  "Assumptions",
  "Limitations",
];

export default function Reports() {
  const { emissionFactor, setEmissionFactor } = useFilters();
  const [title, setTitle] = useState("SolarSphere AI - Government Solar Planning Report");
  const [budgets, setBudgets] = useState("5,10,15,20");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const reports = useFetch(() => api.reports(), []);
  const impact = useFetch(() => api.environmental(emissionFactor), [emissionFactor]);
  const summary = useFetch(() => api.summary({}, emissionFactor), [emissionFactor]);

  const generate = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const list = budgets
        .split(",")
        .map((b) => Number(b.trim()) * 10_000_000)
        .filter((b) => b > 0);
      const res = await api.generateReport({
        title,
        emission_factor: emissionFactor,
        budgets_inr: list.length ? list : undefined,
      });
      setMessage(`Generated: ${res.filename}`);
      reports.reload();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageHeader
        title="Solar Planning Reports"
        subtitle="Generate a professional PDF report with classification labels on every value"
        right={<span className="badge badge-teal">ReportLab PDF</span>}
      />
      <div className="content">
        <div className="split">
          <div className="card">
            <div className="card-title">Generate solar planning report</div>
            <div className="card-sub">
              The report contains all 19 required sections and labels Feature 1 outputs,
              calculated results, public data, user assumptions and simulated scenarios.
            </div>

            <div className="grid grid-2">
              <div className="field">
                <label>Report title</label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
              </div>
              <div className="field">
                <label>Budget scenarios (₹ Crore, comma separated)</label>
                <input
                  type="text"
                  value={budgets}
                  onChange={(e) => setBudgets(e.target.value)}
                />
              </div>
              <div className="field">
                <label>Emission factor (kg CO₂/kWh)</label>
                <input
                  type="number"
                  step="0.01"
                  value={emissionFactor}
                  onChange={(e) => setEmissionFactor(Number(e.target.value))}
                />
              </div>
              <div className="field" style={{ justifyContent: "flex-end" }}>
                <label>&nbsp;</label>
                <button className="btn" onClick={generate} disabled={busy}>
                  {busy ? <span className="spinner" /> : null}
                  {busy ? "Generating…" : "Generate PDF report"}
                </button>
              </div>
            </div>

            {message && <div className="note" style={{ marginTop: 14 }}>{message}</div>}

            <div className="card-title" style={{ marginTop: 20 }}>
              Report contents
            </div>
            <div className="grid grid-3">
              {SECTIONS.map((s, i) => (
                <div key={s} className="classification" style={{ fontSize: 12 }}>
                  {i + 1}. {s}
                </div>
              ))}
            </div>
          </div>

          <div>
            <div className="card">
              <div className="card-title">Environmental impact</div>
              <div className="card-sub">
                Estimated annual CO₂ reduction from the filtered dataset
              </div>
              <div className="stat-list">
                <div className="stat-item">
                  <div className="s-label">Annual generation</div>
                  <div className="s-value">
                    {impact.data ? `${formatNumber(impact.data.annual_generation_kwh)} kWh` : "—"}
                  </div>
                </div>
                <div className="stat-item">
                  <div className="s-label">Emission factor</div>
                  <div className="s-value">
                    {impact.data ? `${impact.data.emission_factor} kg/kWh` : "—"}
                  </div>
                </div>
                <div className="stat-item">
                  <div className="s-label">CO₂ reduction</div>
                  <div className="s-value">
                    {impact.data ? `${formatNumber(impact.data.co2_tonnes)} t/yr` : "—"}
                  </div>
                </div>
                <div className="stat-item">
                  <div className="s-label">City index</div>
                  <div className="s-value">
                    {summary.data ? `${summary.data.avg_spi} / 100` : "—"}
                  </div>
                </div>
              </div>
              <div className="note" style={{ marginTop: 12 }}>
                {impact.data?.formula}
                <br />
                <span className="classification">
                  {impact.data?.classification} · Source: {impact.data?.emission_factor_source}
                </span>
              </div>
            </div>

            <div className="card">
              <div className="card-title">Generated reports</div>
              <div className="card-sub">Stored in backend/generated_reports</div>
              {(reports.data?.items ?? []).length === 0 ? (
                <div className="empty">
                  <h3>No reports yet</h3>
                  <p>Generate the first planning report with the form.</p>
                </div>
              ) : (
                <div className="table-wrap">
                  <table className="data">
                    <thead>
                      <tr>
                        <th>Title</th>
                        <th>File</th>
                        <th>Created</th>
                        <th>Download</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(reports.data?.items ?? []).map((r) => (
                        <tr key={r.id}>
                          <td>{r.title}</td>
                          <td>{r.filename}</td>
                          <td>{new Date(r.created_at).toLocaleString()}</td>
                          <td>
                            <a
                              className="btn btn-secondary"
                              href={api.reportUrl(r.id)}
                              target="_blank"
                              rel="noreferrer"
                            >
                              Open PDF
                            </a>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
