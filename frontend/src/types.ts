export interface SpiBreakdown {
  [key: string]: number;
}

export interface Rooftop {
  id: number;
  location_input: string | null;
  rooftop_selection: string | null;
  latitude: number;
  longitude: number;
  locality: string;
  rooftop_area_m2: number;
  usable_rooftop_area_m2: number;
  recommended_panels: number;
  system_capacity_kw: number;
  annual_generation_kwh: number;
  installation_cost_inr: number;
  annual_savings_inr: number;
  payback_period_years: number;
  suitability: string;
  data_type: string;
  spi: number;
  spi_breakdown: SpiBreakdown | null;
  source_row?: number;
}

export interface Locality {
  name: string;
  rooftop_count: number;
  total_rooftop_area_m2: number;
  total_usable_area_m2: number;
  total_panels: number;
  total_capacity_kw: number;
  total_generation_kwh: number;
  total_cost_inr: number;
  total_savings_inr: number;
  avg_payback_years: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  spi: number;
  spi_breakdown: SpiBreakdown | null;
  centroid_lat: number;
  centroid_lon: number;
  why_text: string;
}

export interface CitySummary {
  rooftop_records: number;
  total_rooftop_area_m2: number;
  total_usable_area_m2: number;
  total_panels: number;
  total_capacity_kw: number;
  total_capacity_mw: number;
  total_generation_kwh: number;
  total_generation_gwh: number;
  total_cost_inr: number;
  total_savings_inr: number;
  avg_payback_years: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  avg_spi: number;
  locality_count: number;
  co2_tonnes: number;
  emission_factor: number;
  emission_factor_unit: string;
  emission_factor_source: string;
  data_classification: Record<string, string>;
  dataset?: { filename: string } | null;
}

export interface DatasetInfo {
  loaded: boolean;
  id?: number;
  filename?: string;
  sheet_name?: string;
  uploaded_at?: string;
  rows_total?: number;
  rows_valid?: number;
  rows_invalid?: number;
  missing_values?: number;
  duplicate_records?: number;
  localities_count?: number;
  notes?: string;
  validation_log?: Record<string, unknown>;
}

export interface Scenario {
  budget_inr: number;
  min_spi: number;
  max_payback_years: number;
  min_capacity_kw: number;
  locality: string | null;
  eligible_rooftops: number;
  rooftops_considered: number;
  investment_inr: number;
  unspent_budget_inr: number;
  capacity_kw: number;
  capacity_mw: number;
  generation_kwh: number;
  generation_gwh: number;
  annual_savings_inr: number;
  co2_tonnes: number;
  avg_payback_years: number;
  emission_factor: number;
  selection_rule: string;
  disclaimer: string;
  classification: string;
  selected_localities: string[];
}

export interface MapPoint {
  id: number;
  latitude: number;
  longitude: number;
  locality: string;
  location_input: string | null;
  system_capacity_kw: number;
  annual_generation_kwh: number;
  payback_period_years: number;
  suitability: string;
  spi: number;
  usable_rooftop_area_m2: number;
  installation_cost_inr: number;
  annual_savings_inr: number;
}

export interface ChartsPayload {
  capacity_by_locality: { locality: string; capacity_kw: number }[];
  generation_by_locality: { locality: string; generation_kwh: number }[];
  investment_vs_savings: {
    locality: string;
    investment_inr: number;
    annual_savings_inr: number;
  }[];
  payback_distribution: { bucket: string; count: number }[];
  spi_distribution: { bucket: string; count: number }[];
  suitability_distribution: { name: string; count: number }[];
  index_by_locality: { locality: string; spi: number }[];
}

export interface AssistantResponse {
  question: string;
  answer: string;
  mode: string;
  data: Record<string, unknown>;
  sources: string[];
  llm: boolean;
}

export interface Filters {
  locality: string;
  suitability: string;
  min_spi: string;
  max_payback: string;
  min_capacity: string;
  min_generation: string;
}
