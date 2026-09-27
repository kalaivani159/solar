import { useState } from "react";
import { api, filterQuery, formatINR, formatNumber } from "../api/client";
import FilterBar from "../components/FilterBar";
import PageHeader from "../components/PageHeader";
import RooftopDetail from "../components/RooftopDetail";
import { useFetch } from "../hooks/useFetch";
import { useFilters } from "../state/filters";
import type { Rooftop } from "../types";

const PAGE = 25;

export default function Rooftops() {
  const { filters } = useFilters();
  const [offset, setOffset] = useState(0);
  const [sort, setSort] = useState("spi");
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [selected, setSelected] = useState<number | null>(null);
  const [names, setNames] = useState<string[]>([]);

  useFetch(() => api.localities().then((r) => {
    setNames(r.items.map((i) => i.name));
    return r;
  }), []);

  const list = useFetch<{ total: number; items: Rooftop[] }>(
    () => api.rooftops(filters, PAGE + 1, sort, order),
    [JSON.stringify(filters), offset, sort, order],
  );
  const detail = useFetch<Rooftop>(
    () => api.rooftop(selected as number),
    [selected],
    selected !== null,
  );

  const total = list.data?.total ?? 0;
  const items = (list.data?.items ?? []).slice(0, PAGE);

  const sortBy = (key: string) => {
    if (key === sort) {
      setOrder(order === "desc" ? "asc" : "desc");
    } else {
      setSort(key);
      setOrder("desc");
    }
    setOffset(0);
  };

  const header = (label: string, key: string, numeric = true) => (
    <th
      key={key}
      className={numeric ? "num" : undefined}
      style={{ cursor: "pointer" }}
      onClick={() => sortBy(key)}
    >
      {label}
      {sort === key ? (order === "desc" ? " ↓" : " ↑") : ""}
    </th>
  );

  return (
    <>
      <PageHeader
        title="Rooftop Analysis Records"
        subtitle="Every analyzed rooftop record from the Feature 1 workbook"
        right={
          <>
            <span className="badge badge-slate">{total} records</span>
            <span className="badge badge-teal">click a row for full Feature 1 result</span>
          </>
        }
      />
      <div className="content">
        <FilterBar localities={names} />

        <div className="card">
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Location</th>
                  <th>Locality</th>
                  <th className="num">Lat</th>
                  <th className="num">Lon</th>
                  <th className="num">Rooftop m²</th>
                  <th className="num">Usable m²</th>
                  <th className="num">Panels</th>
                  {header("kW", "capacity")}
                  {header("kWh/yr", "generation")}
                  {header("Cost", "cost")}
                  {header("Savings", "savings")}
                  {header("Payback", "payback")}
                  <th>Suitability</th>
                  {header("Index", "spi")}
                </tr>
              </thead>
              <tbody>
                {items.map((r) => (
                  <tr key={r.id} className="clickable" onClick={() => setSelected(r.id)}>
                    <td title={r.location_input ?? ""}>
                      {(r.location_input ?? r.locality).slice(0, 34)}
                    </td>
                    <td>{r.locality}</td>
                    <td className="num">{r.latitude.toFixed(4)}</td>
                    <td className="num">{r.longitude.toFixed(4)}</td>
                    <td className="num">{formatNumber(r.rooftop_area_m2)}</td>
                    <td className="num">{formatNumber(r.usable_rooftop_area_m2)}</td>
                    <td className="num">{r.recommended_panels}</td>
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
                    <td className="num">
                      <span className="spi-pill">
                        {r.spi} <span>/100</span>
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="pager">
            <span>
              Showing {items.length} of {total} · {filterQuery(filters) || "no filters"}
            </span>
            <button
              className="btn btn-secondary"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE))}
            >
              Previous
            </button>
            <button
              className="btn btn-secondary"
              disabled={offset + PAGE >= total}
              onClick={() => setOffset(offset + PAGE)}
            >
              Next
            </button>
          </div>
        </div>
      </div>

      <RooftopDetail
        rooftop={selected !== null ? detail.data : null}
        onClose={() => {
          setSelected(null);
          detail.clear();
        }}
      />
    </>
  );
}
