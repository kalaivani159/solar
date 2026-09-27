# Budget Simulator and Scenario Comparison Methodology

## Purpose

The Solar Planning Budget Simulator lets a government user explore what a hypothetical
planning budget could cover using the analyzed rooftop records. It is a planning aid only.

## Inputs

- Government planning budget in INR (for example 5 crore, 10 crore, 15 crore, 20 crore, or custom).
- Minimum Solar Potential Index (0-100).
- Maximum payback period in years.
- Minimum system capacity in kW.
- Optional locality filter.
- Optional grid emission factor for the CO2 estimate.

## Selection rule

1. Filter all rooftop records by the threshold constraints (min SPI, max payback, min
   capacity, locality).
2. Rank the eligible records by Solar Potential Index descending, breaking ties by annual
   generation descending.
3. Select records greedily while the cumulative estimated installation cost stays within the
   budget.

## Outputs

Rooftops considered, eligible rooftops, investment used, unspent budget, potential capacity,
annual generation, annual savings, estimated CO2 reduction, average payback, and the list of
localities covered.

## Scenario comparison

Multiple budgets can be run through the same rule and compared side by side in a table and
charts. Feature 3 deliberately does NOT label any scenario as best, optimal or recommended;
it only shows the consequences of different budgets and assumptions.

## Important limitation

This is a planning simulation. It does not approve, award, shortlist or select government
projects, does not create any financial commitment, and does not replace statutory
sanctioning processes.
