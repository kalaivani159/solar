# Environmental Impact Methodology

## Formula

Estimated annual CO2 reduction = Annual renewable generation (kWh) x emission factor
(kg CO2 / kWh) / 1000, expressed in tonnes of CO2 per year.

## Emission factor

Default value: 0.71 kg CO2/kWh. Basis: indicative weighted grid emission factor for the
Indian power sector (Central Electricity Authority CO2 Baseline Database). Classification:
E - user-configured assumption. The factor is configurable in the dashboard and in the
report generator; the applied value, unit and source are always shown next to the result.

## What is shown

Annual generation (A - Feature 1 output), emission factor (E - user-configured), and the
resulting estimated CO2 reduction (B - calculated by Feature 3).

## Caveat

The result is an order-of-magnitude planning estimate. It assumes grid-connected
displacement of average grid electricity, no battery storage losses, and no lifecycle
emissions of the solar equipment. It is not a verified carbon-credit calculation.
