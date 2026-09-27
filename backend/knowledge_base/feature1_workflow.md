# Feature 1 Workflow (input producer for Feature 3)

Feature 1 is AI Rooftop Solar Potential Analysis. Its workflow:

User -> enters or selects a LOCATION -> map/GIS displays the location -> user selects the
required ROOFTOP/TERRACE -> satellite/aerial image of the selected rooftop -> AI rooftop
segmentation using U-Net -> rooftop area calculation -> usable rooftop area -> solar panel
arrangement -> recommended panel count -> system capacity -> solar generation estimation ->
installation cost -> annual savings -> payback period -> Feature 1 output.

Feature 1 does NOT start with a Building ID. The primary geographic identity of a result is
Location + Latitude + Longitude + Locality + selected rooftop.

Feature 3 therefore does not require or invent Building_ID values. It receives rooftop-level
results from many Feature 1 analyses and answers a different question:

- Feature 1: "How much solar potential does this selected rooftop have?"
- Feature 3: "Across multiple analyzed rooftops and localities, what is the overall solar
  potential and how can it be used for government-level solar planning?"

Feature 1 outputs consumed by Feature 3: Location_Input, Rooftop_Selection, Latitude,
Longitude, Locality, Rooftop_Area_m2, Usable_Rooftop_Area_m2, Recommended_Panels,
System_Capacity_kW, Annual_Generation_kWh, Estimated_Installation_Cost_INR,
Estimated_Annual_Savings_INR, Payback_Period_Years, Suitability.
