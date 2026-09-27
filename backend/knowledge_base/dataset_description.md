# Dataset Description — Feature 3 Input Workbook

Workbook: SolarSphere_Feature3_Demo_Dataset_Location_Based.xlsx.

Sheets:
1. "Feature 1 Outputs" — the analysis records.
2. "README" — dataset metadata stating that the file is a synthetic demonstration of the
   outputs passed from Feature 1 into Feature 3, that Building ID is not used, and that the
   primary grouping for Feature 3 is Location / Locality.

Columns of the "Feature 1 Outputs" sheet:
Location_Input, Rooftop_Selection, Latitude, Longitude, Locality, Rooftop_Area_m2,
Usable_Rooftop_Area_m2, Recommended_Panels, System_Capacity_kW, Annual_Generation_kWh,
Estimated_Installation_Cost_INR, Estimated_Annual_Savings_INR, Payback_Period_Years,
Suitability, Data_Type.

Observed quality (inspection on 2026-09-27): 120 rows, 15 columns, zero missing values, zero
duplicate records, zero invalid coordinates, no negative numbers, usable area never exceeds
total rooftop area. Eight localities are present with 15 rooftop records each: Anna Nagar,
T. Nagar, Velachery, Porur, Mogappair, Adyar, Tambaram, Ambattur. Coordinates fall inside
Chennai (latitude 12.917 to 13.121, longitude 80.093 to 80.265). All rows are flagged
SYNTHETIC_DEMO in the Data_Type column.

Fields NOT present in the workbook and therefore calculated by Feature 3: Solar Potential
Index, locality aggregates, city summary, estimated CO2 reduction, budget scenarios.
