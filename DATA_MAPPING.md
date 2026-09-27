# DATA MAPPING — Feature 3 (AI Government Solar Planning)

Primary dataset: `data/SolarSphere_Feature3_Demo_Dataset_Location_Based.xlsx`
Inspected on: 2026-09-27 (actual file inspection, no assumptions).

---

## 1. Workbook structure (as inspected)

| Property | Value |
|---|---|
| Workbook name | SolarSphere_Feature3_Demo_Dataset_Location_Based.xlsx |
| Sheet 1 | `Feature 1 Outputs` — 120 data rows × 15 columns |
| Sheet 2 | `README` — 6 rows of dataset metadata (key/value) |
| Building ID | **Not present** (explicitly excluded per README sheet) |
| Data_Type column | every row = `SYNTHETIC_DEMO` |

### README sheet contents
- Dataset purpose: Synthetic demonstration of the outputs passed from Feature 1 into Feature 3.
- Feature 1 workflow: user enters/selects location → selects rooftop/terrace → Feature 1 generates rooftop solar analysis.
- Building ID: not used.
- Primary grouping for Feature 3: Location / Locality.
- Important: synthetic demo data; replace with actual Feature 1 outputs later.

---

## 2. Column-by-column mapping

| # | Excel column | Type | Observed values / range | Classification | Feature 3 purpose |
|---|---|---|---|---|---|
| 1 | `Location_Input` | text | 8 unique, e.g. `Anna Nagar, Chennai, Tamil Nadu` | A — Feature 1 output | Geographic identity of the analysis; city/region filter, map label |
| 2 | `Rooftop_Selection` | text | constant `Selected rooftop/terrace` | A — Feature 1 output | Confirms record = one selected rooftop; shown in rooftop detail view |
| 3 | `Latitude` | float | 12.917047 – 13.121344, 0 invalid, 0 missing | A — Feature 1 output | GIS map position, geographic grouping, coordinate validation |
| 4 | `Longitude` | float | 80.093459 – 80.264745, 0 invalid, 0 missing | A — Feature 1 output | GIS map position, geographic grouping, coordinate validation |
| 5 | `Locality` | text | 8 values × 15 rows: Anna Nagar, T. Nagar, Velachery, Porur, Mogappair, Adyar, Tambaram, Ambattur | A — Feature 1 output | **Primary aggregation key** → locality profile, locality index, map clusters |
| 6 | `Rooftop_Area_m2` | float | 58.29 – 649.83 | A — Feature 1 output | Total rooftop area (locality + city totals) |
| 7 | `Usable_Rooftop_Area_m2` | float | 40.18 – 558.33; never > total area | A — Feature 1 output | Locality solar potential, usable-area factor of the index |
| 8 | `Recommended_Panels` | int | 19 – 300 | A — Feature 1 output | Panel totals per locality/city |
| 9 | `System_Capacity_kW` | float | 10.45 – 165.00 (city total 9,254.85 kW) | A — Feature 1 output | Capacity potential factor of the index; KPI; budget simulator |
| 10 | `Annual_Generation_kWh` | float | 15,056 – 251,832 (city total 13,084,232.66 kWh) | A — Feature 1 output | Generation factor of the index; KPI; CO₂ calculation input |
| 11 | `Estimated_Installation_Cost_INR` | float | 655,773 – 11,163,590 (city total ₹566,235,604) | A — Feature 1 output | Investment totals; budget simulator constraint |
| 12 | `Estimated_Annual_Savings_INR` | float | 86,039 – 1,782,842 (city total ₹85,372,559) | A — Feature 1 output | Economic feasibility factor of the index; investment-vs-savings chart |
| 13 | `Payback_Period_Years` | float | 4.46 – 10.63 years (mean 6.81) | A — Feature 1 output | Payback feasibility factor (lower is better); simulator filter |
| 14 | `Suitability` | text | High 66 / Medium 41 / Low 13 | A — Feature 1 output | Suitability factor of the index; distribution charts; map legend |
| 15 | `Data_Type` | text | `SYNTHETIC_DEMO` (120/120) | D — synthetic flag carried from source | Honesty label shown on dashboard, map, report, assistant answers |

### Fields NOT in the Excel (must be produced by Feature 3)

| Missing field | Produced by | Classification |
|---|---|---|
| Solar Potential Index (0–100) | Feature 3 index engine (normalized, weighted, configurable) | B — calculated by Feature 3 |
| Locality-level aggregates (counts, totals, averages) | Feature 3 aggregation engine | B — calculated by Feature 3 |
| City-level summary / KPIs | Feature 3 aggregation engine | B — calculated by Feature 3 |
| Estimated CO₂ reduction | Annual generation × configurable emission factor | B + E (emission factor is user-configured) |
| Budget / what-if scenarios, scenario comparison | Feature 3 simulation engine | D — simulated scenario output |
| AI explanations, RAG answers | Feature 3 assistant (grounded in calculated results) | B — calculated, then explained |
| Emission factor (kg CO₂/kWh) | User-configured assumption (default 0.71 kg CO₂/kWh, India grid, documented) | E — user-configured assumption |

---

## 3. Data quality findings (actual inspection results)

| Check | Result |
|---|---|
| Missing values | **0** across all 15 columns |
| Duplicate records (full row) | **0** |
| Duplicate coordinates | **0** |
| Invalid latitude | **0** (all within −90…90) |
| Invalid longitude | **0** (all within −180…180) |
| Negative numeric values | **0** |
| Usable area > total area | **0** |
| Geographic coverage | Chennai: lat 12.917–13.121, lon 80.093–80.265 |
| Localities | 8 (15 rooftop records each) |
| Directly usable fields | all 15 |
| Calculatable fields | aggregates, index, CO₂, scenarios |
| Missing fields | CO₂, index, aggregates, scenarios (see above) |
| Additional external datasets needed? | **No.** The uploaded Excel is sufficient as the primary dataset. Only external inputs used: OpenStreetMap tiles (basemap), a documented grid emission factor (configurable), and static methodology documents for RAG. |

---

## 4. Data classification legend (used across the project)

- **A — Feature 1 output**: value comes directly from the uploaded Excel.
- **B — Calculated by Feature 3**: derived deterministically from A.
- **C — Real public data**: e.g. OpenStreetMap basemap tiles.
- **D — Simulated / demo data**: source file rows are flagged `SYNTHETIC_DEMO`; budget scenarios are simulated outputs.
- **E — User-configured assumption**: emission factor, index weights, budget, filter thresholds.

Every UI surface and the PDF report label values with these classes. Synthetic data is never presented as a real-world measurement.
