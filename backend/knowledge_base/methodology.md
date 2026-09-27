# SolarSphere AI — Feature 3 Methodology

Feature 3 is the AI Government Solar Planning module of SolarSphere AI. It takes the
rooftop-level outputs produced by Feature 1 (AI Rooftop Solar Potential Analysis) for many
locations and converts them into locality-level and city-level solar planning intelligence.

## Pipeline

Feature 1 Excel output -> Data ingestion -> Data validation -> Data cleaning ->
Geographic grouping -> Locality aggregation -> Solar Potential Index -> GIS visualization ->
Government dashboard -> Budget / what-if simulation -> Scenario comparison ->
Environmental impact -> AI planning assistant -> Solar planning report.

## Input

The primary input is the uploaded Excel workbook of Feature 1 outputs. The dataset contains
one row per analyzed rooftop. There is deliberately no Building_ID field: the geographic
identity of a record is Location_Input, Latitude, Longitude, Locality and the selected
rooftop/terrace.

## Grouping

Records are grouped by the Locality column of the Excel file. If the locality field were
missing but valid coordinates existed, Feature 3 derives the locality from the first token of
Location_Input or reports the record as Unassigned. Localities are never randomly assigned.

## Aggregation

For every locality Feature 3 computes: number of analyzed rooftops, total rooftop area, total
usable rooftop area, total recommended panels, total solar capacity, total annual generation,
total estimated installation investment, total annual savings, average payback period, and
the count of High / Medium / Low suitability rooftops. City-level totals aggregate all
localities.

## Classification of values

Every displayed value is classified as: (A) Feature 1 output, (B) calculated by Feature 3,
(C) real public data, (D) simulated or demo data, (E) user-configured assumption. Synthetic
source rows are flagged SYNTHETIC_DEMO in the Data_Type column and are always labelled as
demonstration data.
