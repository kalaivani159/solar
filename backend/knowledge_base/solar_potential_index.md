# Solar Potential Index — Project Decision-Support Score

The Solar Potential Index (SPI) is a project decision-support score, NOT an official
government score and NOT a statutory or regulatory rating. Range: 0 to 100.

## Formula

SPI = weighted combination of six normalized factors:

| Factor | Default weight | Direction | Source field |
|---|---|---|---|
| Usable rooftop area | 25 | higher is better | Usable_Rooftop_Area_m2 |
| Generation potential | 25 | higher is better | Annual_Generation_kWh |
| Capacity potential | 20 | higher is better | System_Capacity_kW |
| Economic feasibility | 15 | higher is better | Estimated_Annual_Savings_INR |
| Payback feasibility | 10 | lower payback is better (inverted) | Payback_Period_Years |
| Suitability | 5 | High = 1.0, Medium = 0.5, Low = 0.1 | Suitability |

## Normalization

Numeric factors are min-max normalized across the whole uploaded dataset:
normalized = (value - min) / (max - min), clipped to [0, 1].
The payback factor uses 1 - normalized so that a shorter payback period contributes
positively. Weights are configurable at runtime; if the user supplies weights they are
rescaled to sum to 100.

## Aggregation to locality and city

Each rooftop receives its own SPI and a breakdown of points per factor. A locality SPI is
the arithmetic mean of the SPI values of its analyzed rooftops. The city SPI is the mean of
all rooftop SPI values. The breakdown shown under "Why this score?" is the mean point
contribution of each factor for that locality.

## Explainability

Because every factor contributes a known number of points, the score is fully explainable:
the system lists which factors contributed strongly (>= 70 percent of their weight) and
which contributed weakly (<= 35 percent of their weight). No random or black-box scoring is
used anywhere in Feature 3.
