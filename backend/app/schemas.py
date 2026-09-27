from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class SimulateRequest(BaseModel):
    budget_inr: float = Field(..., gt=0)
    min_spi: float = 0
    max_payback_years: float = 100
    min_capacity_kw: float = 0
    locality: Optional[str] = None
    emission_factor: Optional[float] = None


class CompareRequest(BaseModel):
    budgets_inr: List[float]
    min_spi: float = 0
    max_payback_years: float = 100
    min_capacity_kw: float = 0
    locality: Optional[str] = None
    emission_factor: Optional[float] = None


class IndexWeightsRequest(BaseModel):
    weights: Optional[Dict[str, float]] = None
    persist: bool = True


class AssistantRequest(BaseModel):
    question: str
    emission_factor: Optional[float] = None


class ReportRequest(BaseModel):
    title: str = "SolarSphere AI - Government Solar Planning Report"
    emission_factor: Optional[float] = None
    budgets_inr: Optional[List[float]] = None
    weights: Optional[Dict[str, float]] = None
