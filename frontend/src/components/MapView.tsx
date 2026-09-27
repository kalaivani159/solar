import { CircleMarker, MapContainer, Popup, TileLayer, Tooltip } from "react-leaflet";
import { spiColor } from "../lib/colors";
import type { Locality, MapPoint } from "../types";

function fmt(v: number) {
  if (!Number.isFinite(Number(v))) return "—";
  return Number(v).toLocaleString("en-IN", { maximumFractionDigits: 1 });
}

export default function MapView({
  points,
  localities,
  height,
  onLocalityClick,
  onRooftopClick,
  legend = true,
}: {
  points: MapPoint[];
  localities?: Locality[];
  height?: number;
  onLocalityClick?: (name: string) => void;
  onRooftopClick?: (id: number) => void;
  legend?: boolean;
}) {
  const center: [number, number] = points.length
    ? [
        points.reduce((s, p) => s + p.latitude, 0) / points.length,
        points.reduce((s, p) => s + p.longitude, 0) / points.length,
      ]
    : [13.03, 80.2];

  return (
    <div className="map-outer" style={height ? { height } : undefined}>
      <div className="map-shell" style={height ? { height } : undefined}>
        <MapContainer center={center} zoom={12} scrollWheelZoom>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {points.map((p) => (
            <CircleMarker
              key={p.id}
              center={[p.latitude, p.longitude]}
              radius={6}
              pathOptions={{
                color: "#ffffff",
                weight: 1.4,
                fillColor: spiColor(p.spi),
                fillOpacity: 0.92,
              }}
              eventHandlers={{
                click: () => onRooftopClick?.(p.id),
              }}
            >
              <Tooltip direction="top" opacity={0.95}>
                <div style={{ fontSize: 12, lineHeight: 1.5 }}>
                  <b>{p.locality}</b>
                  <br />
                  Index {p.spi}/100 · {p.suitability}
                  <br />
                  {fmt(p.system_capacity_kw)} kW · {fmt(p.annual_generation_kwh)} kWh/yr
                  <br />
                  Payback {fmt(p.payback_period_years)} yrs
                </div>
              </Tooltip>
              <Popup>
                <div style={{ fontSize: 12.5, lineHeight: 1.6 }}>
                  <b>{p.location_input ?? p.locality}</b>
                  <br />
                  <span className="classification">
                    {p.latitude.toFixed(5)}, {p.longitude.toFixed(5)}
                  </span>
                  <hr style={{ margin: "7px 0", border: "none", borderTop: "1px solid #e2e8f0" }} />
                  Solar Potential Index: <b>{p.spi}/100</b>
                  <br />
                  Suitability: <b>{p.suitability}</b>
                  <br />
                  Usable rooftop: {fmt(p.usable_rooftop_area_m2)} m²
                  <br />
                  Capacity: {fmt(p.system_capacity_kw)} kW
                  <br />
                  Generation: {fmt(p.annual_generation_kwh)} kWh/yr
                  <br />
                  Investment: ₹{fmt(p.installation_cost_inr)}
                  <br />
                  Savings: ₹{fmt(p.annual_savings_inr)}/yr
                  <br />
                  Payback: {fmt(p.payback_period_years)} years
                  <div className="classification" style={{ marginTop: 6 }}>
                    Feature 1 output · index by Feature 3
                  </div>
                </div>
              </Popup>
            </CircleMarker>
          ))}

          {(localities ?? []).map((l) => (
            <CircleMarker
              key={`loc-${l.name}`}
              center={[l.centroid_lat, l.centroid_lon]}
              radius={13}
              pathOptions={{
                color: spiColor(l.spi),
                weight: 2.5,
                fillColor: "#0b1f33",
                fillOpacity: 0.12,
              }}
              eventHandlers={{
                click: () => onLocalityClick?.(l.name),
              }}
            >
              <Tooltip direction="top" opacity={0.95}>
                <div style={{ fontSize: 12, lineHeight: 1.5 }}>
                  <b>{l.name}</b> (locality centroid)
                  <br />
                  {l.rooftop_count} rooftops · Index {l.spi}/100
                  <br />
                  {fmt(l.total_capacity_kw)} kW · {fmt(l.total_generation_kwh)} kWh/yr
                </div>
              </Tooltip>
            </CircleMarker>
          ))}
        </MapContainer>
      </div>
      {legend && (
        <div className="legend">
          <b>Solar Potential Index</b>
          <div>
            <span className="dot" style={{ background: "#0f766e" }} />
            81–100 · very high
          </div>
          <div>
            <span className="dot" style={{ background: "#2563eb" }} />
            61–80 · high
          </div>
          <div>
            <span className="dot" style={{ background: "#d97706" }} />
            41–60 · moderate
          </div>
          <div>
            <span className="dot" style={{ background: "#b91c1c" }} />
            0–40 · limited
          </div>
          <div style={{ marginTop: 5, color: "#64748b" }}>
            ○ locality centroid · basemap © OpenStreetMap
          </div>
        </div>
      )}
    </div>
  );
}
