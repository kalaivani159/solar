import { useFilters } from "../state/filters";
import type { Filters } from "../types";

export default function FilterBar({
  showLocality = true,
  localities,
  extra,
}: {
  showLocality?: boolean;
  localities?: string[];
  extra?: React.ReactNode;
}) {
  const { filters, setFilter, reset, activeCount } = useFilters();

  const input = (
    key: keyof Filters,
    label: string,
    placeholder: string,
    type = "text",
  ) => (
    <div className="field">
      <label>{label}</label>
      <input
        type={type}
        value={filters[key]}
        placeholder={placeholder}
        onChange={(e) => setFilter(key, e.target.value)}
      />
    </div>
  );

  return (
    <div className="filter-bar">
      {showLocality && (
        <div className="field">
          <label>Locality</label>
          <select
            value={filters.locality}
            onChange={(e) => setFilter("locality", e.target.value)}
          >
            <option value="all">All localities</option>
            {(localities ?? []).map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </div>
      )}
      <div className="field">
        <label>Suitability</label>
        <select
          value={filters.suitability}
          onChange={(e) => setFilter("suitability", e.target.value)}
        >
          <option value="all">All ratings</option>
          <option value="High">High</option>
          <option value="Medium">Medium</option>
          <option value="Low">Low</option>
        </select>
      </div>
      {input("min_spi", "Min index (0–100)", "e.g. 60")}
      {input("max_payback", "Max payback (years)", "e.g. 7")}
      {input("min_capacity", "Min capacity (kW)", "e.g. 50")}
      {input("min_generation", "Min generation (kWh)", "e.g. 50000")}
      {extra}
      <div className="filter-actions">
        <button className="btn btn-secondary" onClick={reset}>
          Reset {activeCount > 0 ? `(${activeCount})` : ""}
        </button>
      </div>
    </div>
  );
}
