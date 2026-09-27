import { useState } from "react";
import { api } from "../api/client";
import FilterBar from "../components/FilterBar";
import LocalityProfile from "../components/LocalityProfile";
import MapView from "../components/MapView";
import PageHeader from "../components/PageHeader";
import RooftopDetail from "../components/RooftopDetail";
import { useFetch } from "../hooks/useFetch";
import { useFilters } from "../state/filters";
import type { Locality, MapPoint, Rooftop } from "../types";

export default function SolarMap() {
  const { filters } = useFilters();
  const [localities, setLocalities] = useState<string[]>([]);
  const [selectedLocality, setSelectedLocality] = useState<string | null>(null);
  const [rooftopId, setRooftopId] = useState<number | null>(null);

  const map = useFetch<{ points: MapPoint[] }>(
    () => api.mapRooftops(filters),
    [JSON.stringify(filters)],
  );
  const localityList = useFetch(() => api.localities(), []);
  const profile = useFetch<{ locality: Locality; rooftops: Rooftop[] }>(
    () => api.locality(selectedLocality as string),
    [selectedLocality],
    !!selectedLocality,
  );
  const rooftop = useFetch<Rooftop>(
    () => api.rooftop(rooftopId as number),
    [rooftopId],
    rooftopId !== null,
  );

  if (localityList.data && localities.length === 0) {
    setLocalities(localityList.data.items.map((i) => i.name));
  }

  return (
    <>
      <PageHeader
        title="Solar Potential Map"
        subtitle="GIS view of analyzed rooftops and locality solar profiles"
        right={
          <>
            <span className="badge badge-slate">{map.data?.points.length ?? 0} points</span>
            <span className="badge badge-teal">Index-coloured</span>
          </>
        }
      />
      <div className="content">
        <FilterBar localities={localities} />
        <div className="split">
          <MapView
            points={map.data?.points ?? []}
            localities={localityList.data?.items}
            onLocalityClick={(name) => setSelectedLocality(name)}
            onRooftopClick={(id) => setRooftopId(id)}
          />
          <div>
            <LocalityProfile
              locality={
                selectedLocality && profile.data ? profile.data.locality : null
              }
              rooftops={profile.data?.rooftops}
              loading={!!selectedLocality && profile.loading}
              onClose={() => {
                setSelectedLocality(null);
                profile.clear();
              }}
              onSelectRooftop={(id) => setRooftopId(id)}
            />
            <div className="note" style={{ marginTop: 14 }}>
              <b>Interactions:</b> click a coloured marker to open the complete Feature 1
              rooftop analysis; click a locality ring (or a locality in Locality Analysis) to
              open the locality solar profile. Filters above update the map, dashboard, tables
              and charts together.
            </div>
          </div>
        </div>
      </div>
      <RooftopDetail
        rooftop={rooftopId !== null ? rooftop.data : null}
        onClose={() => {
          setRooftopId(null);
          rooftop.clear();
        }}
      />
    </>
  );
}
