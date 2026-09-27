from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from .config import (
    EMISSION_FACTOR_DEFAULT,
    EMISSION_FACTOR_SOURCE,
    EMISSION_FACTOR_UNIT,
    INDEX_WEIGHTS_DEFAULT,
)
from .models import Locality, RooftopAnalysis

SUITABILITY_SCORE = {"High": 1.0, "Medium": 0.5, "Low": 0.1}

_applied_weights: Optional[Dict[str, float]] = None


def applied_weights() -> Dict[str, float]:
    return dict(_applied_weights) if _applied_weights else normalize_weights()


def _minmax(value: float, lo: float, hi: float, invert: bool = False) -> float:
    if hi - lo <= 1e-9:
        return 1.0
    ratio = (value - lo) / (hi - lo)
    ratio = max(0.0, min(1.0, ratio))
    return 1.0 - ratio if invert else ratio


def normalize_weights(weights: Optional[Dict[str, float]] = None) -> Dict[str, float]:
    merged = dict(INDEX_WEIGHTS_DEFAULT)
    if weights:
        for key, val in weights.items():
            if key in merged and val is not None:
                merged[key] = max(0.0, float(val))
    total = sum(merged.values())
    if total <= 0:
        return dict(INDEX_WEIGHTS_DEFAULT)
    return {k: round(v * 100.0 / total, 2) for k, v in merged.items()}


def compute_rooftop_index(records: List[RooftopAnalysis], weights=None) -> Dict[str, float]:
    if not records:
        return {}
    w = normalize_weights(weights)
    usable = [r.usable_rooftop_area_m2 for r in records]
    gen = [r.annual_generation_kwh for r in records]
    cap = [r.system_capacity_kw for r in records]
    sav = [r.annual_savings_inr for r in records]
    pay = [r.payback_period_years for r in records]

    ranges = {
        "usable_area": (min(usable), max(usable)),
        "generation": (min(gen), max(gen)),
        "capacity": (min(cap), max(cap)),
        "economics": (min(sav), max(sav)),
        "payback": (min(pay), max(pay)),
    }

    for rec in records:
        raw = {
            "usable_area": _minmax(rec.usable_rooftop_area_m2, *ranges["usable_area"]),
            "generation": _minmax(rec.annual_generation_kwh, *ranges["generation"]),
            "capacity": _minmax(rec.system_capacity_kw, *ranges["capacity"]),
            "economics": _minmax(rec.annual_savings_inr, *ranges["economics"]),
            "payback": _minmax(
                rec.payback_period_years, ranges["payback"][0], ranges["payback"][1], invert=True
            ),
            "suitability": SUITABILITY_SCORE.get(rec.suitability, 0.3),
        }
        breakdown = {
            key: round(raw[key] * w[key], 2) for key in w
        }
        rec.spi_breakdown = breakdown
        rec.spi = round(sum(breakdown.values()), 1)
    return w


def why_score(breakdown: Dict[str, float], weights: Dict[str, float]) -> str:
    labels = {
        "usable_area": "usable rooftop area",
        "generation": "annual generation potential",
        "capacity": "system capacity potential",
        "economics": "economic value (annual savings)",
        "payback": "payback feasibility",
        "suitability": "Feature 1 suitability rating",
    }
    strengths, weaknesses = [], []
    for key, points in breakdown.items():
        share = points / weights.get(key, 1) if weights.get(key) else 0
        if share >= 0.7:
            strengths.append(labels.get(key, key))
        elif share <= 0.35:
            weaknesses.append(labels.get(key, key))
    parts = []
    if strengths:
        parts.append(
            "strong " + ", ".join(strengths)
        )
    if weaknesses:
        parts.append("weaker " + ", ".join(weaknesses))
    if not parts:
        parts.append("a balanced profile across all measured factors")
    return (
        "The score is driven by " + " and ".join(parts) + ". "
        "Each factor is min-max normalized across the uploaded dataset and multiplied by its "
        "configured weight; payback is inverted so a shorter payback adds points."
    )


def rebuild_analytics(db: Session, weights=None) -> Dict[str, Any]:
    global _applied_weights
    records = scoped_rooftops(db).all()
    if not records:
        return {"rooftops": 0}
    w = compute_rooftop_index(records, weights)
    _applied_weights = dict(w)
    by_locality: Dict[str, List[RooftopAnalysis]] = {}
    for rec in records:
        by_locality.setdefault(rec.locality, []).append(rec)

    db.query(Locality).delete()
    for name, recs in by_locality.items():
        breakdown_acc: Dict[str, float] = {}
        for rec in recs:
            for key, val in (rec.spi_breakdown or {}).items():
                breakdown_acc[key] = breakdown_acc.get(key, 0) + val
        avg_breakdown = {k: round(v / len(recs), 2) for k, v in breakdown_acc.items()}
        avg_spi = round(sum(r.spi for r in recs) / len(recs), 1)
        why = why_score(avg_breakdown, w)
        db.add(
            Locality(
                name=name,
                rooftop_count=len(recs),
                total_rooftop_area_m2=round(sum(r.rooftop_area_m2 for r in recs), 2),
                total_usable_area_m2=round(sum(r.usable_rooftop_area_m2 for r in recs), 2),
                total_panels=sum(r.recommended_panels for r in recs),
                total_capacity_kw=round(sum(r.system_capacity_kw for r in recs), 2),
                total_generation_kwh=round(sum(r.annual_generation_kwh for r in recs), 2),
                total_cost_inr=round(sum(r.installation_cost_inr for r in recs), 2),
                total_savings_inr=round(sum(r.annual_savings_inr for r in recs), 2),
                avg_payback_years=round(
                    sum(r.payback_period_years for r in recs) / len(recs), 2
                ),
                high_count=sum(1 for r in recs if r.suitability == "High"),
                medium_count=sum(1 for r in recs if r.suitability == "Medium"),
                low_count=sum(1 for r in recs if r.suitability == "Low"),
                spi=avg_spi,
                spi_breakdown=avg_breakdown,
                centroid_lat=round(sum(r.latitude for r in recs) / len(recs), 6),
                centroid_lon=round(sum(r.longitude for r in recs) / len(recs), 6),
                why_text=why,
            )
        )
    db.commit()
    return {"rooftops": len(records), "localities": len(by_locality), "weights": w}


def active_dataset_id(db: Session) -> Optional[int]:
    from .models import Dataset

    ds = db.query(Dataset).filter(Dataset.is_active == 1).first()
    return ds.id if ds else None


def scoped_rooftops(db: Session):
    from .models import Dataset

    q = db.query(RooftopAnalysis)
    active = db.query(Dataset).filter(Dataset.is_active == 1).first()
    if active is not None:
        q = q.filter(RooftopAnalysis.dataset_id == active.id)
    return q


def filter_query(db: Session, params: Dict[str, Any]):
    q = scoped_rooftops(db)
    if params.get("locality"):
        q = q.filter(RooftopAnalysis.locality == params["locality"])
    if params.get("suitability"):
        q = q.filter(RooftopAnalysis.suitability == params["suitability"])
    if params.get("min_spi") is not None:
        q = q.filter(RooftopAnalysis.spi >= float(params["min_spi"]))
    if params.get("max_spi") is not None:
        q = q.filter(RooftopAnalysis.spi <= float(params["max_spi"]))
    if params.get("min_capacity") is not None:
        q = q.filter(RooftopAnalysis.system_capacity_kw >= float(params["min_capacity"]))
    if params.get("max_capacity") is not None:
        q = q.filter(RooftopAnalysis.system_capacity_kw <= float(params["max_capacity"]))
    if params.get("min_generation") is not None:
        q = q.filter(RooftopAnalysis.annual_generation_kwh >= float(params["min_generation"]))
    if params.get("max_payback") is not None:
        q = q.filter(RooftopAnalysis.payback_period_years <= float(params["max_payback"]))
    if params.get("min_payback") is not None:
        q = q.filter(RooftopAnalysis.payback_period_years >= float(params["min_payback"]))
    return q


def co2_tonnes(generation_kwh: float, factor: float) -> float:
    return round(generation_kwh * factor / 1000.0, 2)


def city_summary(db: Session, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    params = params or {}
    records = filter_query(db, params).all()
    factor = float(params.get("emission_factor") or EMISSION_FACTOR_DEFAULT)
    localities = db.query(Locality).all()
    if params.get("locality"):
        localities = [l for l in localities if l.name == params["locality"]]

    total_gen = sum(r.annual_generation_kwh for r in records)
    summary = {
        "rooftop_records": len(records),
        "total_rooftop_area_m2": round(sum(r.rooftop_area_m2 for r in records), 2),
        "total_usable_area_m2": round(sum(r.usable_rooftop_area_m2 for r in records), 2),
        "total_panels": sum(r.recommended_panels for r in records),
        "total_capacity_kw": round(sum(r.system_capacity_kw for r in records), 2),
        "total_capacity_mw": round(sum(r.system_capacity_kw for r in records) / 1000, 3),
        "total_generation_kwh": round(total_gen, 2),
        "total_generation_gwh": round(total_gen / 1e6, 3),
        "total_cost_inr": round(sum(r.installation_cost_inr for r in records), 2),
        "total_savings_inr": round(sum(r.annual_savings_inr for r in records), 2),
        "avg_payback_years": round(
            sum(r.payback_period_years for r in records) / len(records), 2
        )
        if records
        else 0,
        "high_count": sum(1 for r in records if r.suitability == "High"),
        "medium_count": sum(1 for r in records if r.suitability == "Medium"),
        "low_count": sum(1 for r in records if r.suitability == "Low"),
        "avg_spi": round(sum(r.spi for r in records) / len(records), 1) if records else 0,
        "locality_count": len({r.locality for r in records}),
        "co2_tonnes": co2_tonnes(total_gen, factor),
        "emission_factor": factor,
        "emission_factor_unit": EMISSION_FACTOR_UNIT,
        "emission_factor_source": EMISSION_FACTOR_SOURCE,
        "data_classification": {
            "rooftop_fields": "A - Feature 1 output",
            "aggregates_and_index": "B - calculated by Feature 3",
            "emission_factor": "E - user-configured assumption",
            "source_rows": "D - synthetic demo rows flagged SYNTHETIC_DEMO in the Excel",
        },
    }
    return summary


def locality_analysis(db: Session, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    params = params or {}
    rows = db.query(Locality).all()
    if params.get("locality"):
        rows = [r for r in rows if r.name == params["locality"]]
    out = []
    for r in sorted(rows, key=lambda x: x.total_capacity_kw, reverse=True):
        out.append(
            {
                "name": r.name,
                "rooftop_count": r.rooftop_count,
                "total_rooftop_area_m2": r.total_rooftop_area_m2,
                "total_usable_area_m2": r.total_usable_area_m2,
                "total_panels": r.total_panels,
                "total_capacity_kw": r.total_capacity_kw,
                "total_generation_kwh": r.total_generation_kwh,
                "total_cost_inr": r.total_cost_inr,
                "total_savings_inr": r.total_savings_inr,
                "avg_payback_years": r.avg_payback_years,
                "high_count": r.high_count,
                "medium_count": r.medium_count,
                "low_count": r.low_count,
                "spi": r.spi,
                "spi_breakdown": r.spi_breakdown,
                "centroid_lat": r.centroid_lat,
                "centroid_lon": r.centroid_lon,
                "why_text": r.why_text,
            }
        )
    return out


def chart_payloads(db: Session, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    params = params or {}
    locs = locality_analysis(db, params)
    records = filter_query(db, params).all()

    payback_buckets = [
        {"bucket": "< 5 yrs", "count": 0},
        {"bucket": "5 - 6 yrs", "count": 0},
        {"bucket": "6 - 7 yrs", "count": 0},
        {"bucket": "7 - 8 yrs", "count": 0},
        {"bucket": "> 8 yrs", "count": 0},
    ]
    for r in records:
        p = r.payback_period_years
        if p < 5:
            payback_buckets[0]["count"] += 1
        elif p < 6:
            payback_buckets[1]["count"] += 1
        elif p < 7:
            payback_buckets[2]["count"] += 1
        elif p < 8:
            payback_buckets[3]["count"] += 1
        else:
            payback_buckets[4]["count"] += 1

    spi_buckets = [
        {"bucket": "0 - 20", "count": 0},
        {"bucket": "21 - 40", "count": 0},
        {"bucket": "41 - 60", "count": 0},
        {"bucket": "61 - 80", "count": 0},
        {"bucket": "81 - 100", "count": 0},
    ]
    for r in records:
        score = r.spi or 0
        if score <= 20:
            idx = 0
        elif score <= 40:
            idx = 1
        elif score <= 60:
            idx = 2
        elif score <= 80:
            idx = 3
        else:
            idx = 4
        spi_buckets[idx]["count"] += 1

    suitability = [
        {"name": "High", "count": sum(1 for r in records if r.suitability == "High")},
        {"name": "Medium", "count": sum(1 for r in records if r.suitability == "Medium")},
        {"name": "Low", "count": sum(1 for r in records if r.suitability == "Low")},
    ]

    return {
        "capacity_by_locality": [
            {"locality": l["name"], "capacity_kw": l["total_capacity_kw"]} for l in locs
        ],
        "generation_by_locality": [
            {"locality": l["name"], "generation_kwh": l["total_generation_kwh"]} for l in locs
        ],
        "investment_vs_savings": [
            {
                "locality": l["name"],
                "investment_inr": l["total_cost_inr"],
                "annual_savings_inr": l["total_savings_inr"],
            }
            for l in locs
        ],
        "payback_distribution": payback_buckets,
        "spi_distribution": spi_buckets,
        "suitability_distribution": suitability,
        "index_by_locality": [
            {"locality": l["name"], "spi": l["spi"]} for l in locs
        ],
    }


def simulate_budget(
    db: Session,
    budget_inr: float,
    min_spi: float = 0,
    max_payback: float = 100,
    min_capacity: float = 0,
    locality: Optional[str] = None,
    emission_factor: Optional[float] = None,
) -> Dict[str, Any]:
    factor = float(emission_factor or EMISSION_FACTOR_DEFAULT)
    eligible = (
        filter_query(
            db,
            {
                "min_spi": min_spi,
                "max_payback": max_payback,
                "min_capacity": min_capacity,
                "locality": locality,
            },
        )
        .all()
    )
    eligible_sorted = sorted(
        eligible, key=lambda r: (r.spi or 0, r.annual_generation_kwh), reverse=True
    )

    selected, running = [], 0.0
    for rec in eligible_sorted:
        if running + rec.installation_cost_inr <= budget_inr:
            selected.append(rec)
            running += rec.installation_cost_inr

    gen = sum(r.annual_generation_kwh for r in selected)
    savings = sum(r.annual_savings_inr for r in selected)
    capacity = sum(r.system_capacity_kw for r in selected)
    avg_payback = (
        sum(r.payback_period_years for r in selected) / len(selected) if selected else 0
    )

    return {
        "budget_inr": budget_inr,
        "min_spi": min_spi,
        "max_payback_years": max_payback,
        "min_capacity_kw": min_capacity,
        "locality": locality,
        "eligible_rooftops": len(eligible),
        "rooftops_considered": len(selected),
        "investment_inr": round(running, 2),
        "unspent_budget_inr": round(budget_inr - running, 2),
        "capacity_kw": round(capacity, 2),
        "capacity_mw": round(capacity / 1000, 3),
        "generation_kwh": round(gen, 2),
        "generation_gwh": round(gen / 1e6, 3),
        "annual_savings_inr": round(savings, 2),
        "co2_tonnes": co2_tonnes(gen, factor),
        "avg_payback_years": round(avg_payback, 2),
        "emission_factor": factor,
        "selection_rule": (
            "Eligible rooftop records are ranked by Solar Potential Index (then by annual "
            "generation) and selected greedily until the cumulative installation cost reaches "
            "the planning budget."
        ),
        "disclaimer": (
            "Planning simulation only. It does not approve, award, shortlist or select any "
            "government project, and it creates no commitment of funds."
        ),
        "classification": "D - simulated scenario output computed from A (Feature 1) inputs",
        "selected_localities": sorted({r.locality for r in selected}),
    }


def compare_scenarios(db: Session, budgets: List[float], **kwargs) -> List[Dict[str, Any]]:
    return [simulate_budget(db, b, **kwargs) for b in budgets]
