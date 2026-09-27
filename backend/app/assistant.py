import json
import os
import re
import urllib.request
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from . import analytics
from .config import EMISSION_FACTOR_DEFAULT, EMISSION_FACTOR_SOURCE, EMISSION_FACTOR_UNIT
from .models import AssistantQuery, Locality, RooftopAnalysis
from .rag import kb

CRORE = 10_000_000
LAKH = 100_000


def _fmt_inr(value: float) -> str:
    value = float(value)
    if value >= CRORE:
        return f"₹{value / CRORE:.2f} crore"
    if value >= LAKH:
        return f"₹{value / LAKH:.2f} lakh"
    return f"₹{value:,.0f}"


def _fmt_num(value: float, unit: str = "") -> str:
    value = float(value)
    if abs(value) >= 1_000_000:
        text = f"{value / 1_000_000:.2f} million"
    elif abs(value) >= 1000:
        text = f"{value:,.0f}"
    else:
        text = f"{value:,.2f}".rstrip("0").rstrip(".")
    return f"{text}{(' ' + unit) if unit else ''}"


def _localities(db: Session) -> List[Locality]:
    return db.query(Locality).order_by(Locality.total_capacity_kw.desc()).all()


def _find_locality(db: Session, question: str) -> Optional[Locality]:
    q = question.lower()
    matches = []
    for loc in _localities(db):
        name = loc.name.lower()
        if name in q:
            matches.append(loc)
    if not matches:
        return None
    matches.sort(key=lambda l: len(l.name), reverse=True)
    return matches[0]


def _parse_money(text: str) -> Optional[float]:
    patterns = [
        (r"(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:crore|cr\b)", CRORE),
        (r"(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:lakh|lac|lakhs|k\b)", LAKH),
    ]
    for pattern, multiplier in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            return float(match.group(1)) * multiplier
    match = re.search(r"(?:₹|rs\.?|inr)\s*(\d+(?:,\d+)*(?:\.\d+)?)", text, flags=re.I)
    if match:
        return float(match.group(1).replace(",", ""))
    return None


def _dataset_facts(db: Session) -> Dict[str, Any]:
    summary = analytics.city_summary(db)
    locs = analytics.locality_analysis(db)
    return {"summary": summary, "localities": locs}


def _answer_locality_rank(
    db: Session, metric: str, question: str, descending: bool = True
) -> Dict[str, Any]:
    locs = analytics.locality_analysis(db)
    labels = {
        "capacity": ("total_capacity_kw", "total solar capacity", "kW"),
        "generation": ("total_generation_kwh", "annual generation", "kWh"),
        "savings": ("total_savings_inr", "annual savings", "INR"),
        "investment": ("total_cost_inr", "installation investment", "INR"),
        "usable": ("total_usable_area_m2", "usable rooftop area", "m2"),
        "spi": ("spi", "Solar Potential Index", "points"),
        "payback": ("avg_payback_years", "average payback", "years"),
    }
    field, label, unit = labels[metric]
    reverse = descending
    superlative = "highest" if descending else "lowest"
    ranked = sorted(locs, key=lambda l: l[field], reverse=reverse)
    top = ranked[0]
    value = top[field]

    def fmt(v):
        if metric in ("savings", "investment"):
            return _fmt_inr(v)
        return _fmt_num(v, unit)

    if len(ranked) > 1:
        next_part = f" Next: {ranked[1]['name']} at {fmt(ranked[1][field])}."
    else:
        next_part = ""
    answer = (
        f"{top['name']} has the {superlative} {label} among the {len(locs)} analyzed "
        f"localities: {fmt(value)} across {top['rooftop_count']} analyzed rooftops "
        f"(Solar Potential Index {top['spi']}/100, average payback "
        f"{top['avg_payback_years']} years).{next_part} "
        "Values are calculated by Feature 3 from the uploaded Feature 1 records."
    )
    return {
        "mode": "analytics",
        "answer": answer,
        "data": {
            "locality": top["name"],
            "metric": label,
            "value": value,
            "ranking": [
                {"locality": l["name"], "value": l[field]} for l in ranked[:5]
            ],
        },
        "sources": ["Feature 3 locality aggregation engine"],
    }


def _answer_locality_profile(db: Session, loc: Locality) -> Dict[str, Any]:
    answer = (
        f"{loc.name}: {loc.rooftop_count} analyzed rooftops, total rooftop area "
        f"{loc.total_rooftop_area_m2:,.0f} m2, usable rooftop area "
        f"{loc.total_usable_area_m2:,.0f} m2, potential capacity "
        f"{loc.total_capacity_kw:,.1f} kW, annual generation "
        f"{loc.total_generation_kwh:,.0f} kWh, estimated investment "
        f"{_fmt_inr(loc.total_cost_inr)}, annual savings {_fmt_inr(loc.total_savings_inr)}, "
        f"average payback {loc.avg_payback_years} years, Solar Potential Index {loc.spi}/100. "
        f"Suitability split: {loc.high_count} High, {loc.medium_count} Medium, "
        f"{loc.low_count} Low. Why this score: {loc.why_text}"
    )
    return {
        "mode": "analytics",
        "answer": answer,
        "data": {
            "locality": loc.name,
            "rooftops": loc.rooftop_count,
            "capacity_kw": loc.total_capacity_kw,
            "generation_kwh": loc.total_generation_kwh,
            "investment_inr": loc.total_cost_inr,
            "annual_savings_inr": loc.total_savings_inr,
            "avg_payback_years": loc.avg_payback_years,
            "spi": loc.spi,
            "spi_breakdown": loc.spi_breakdown,
            "why": loc.why_text,
        },
        "sources": ["Feature 3 locality aggregation engine", "Solar Potential Index engine"],
    }


def _answer_payback_count(db: Session, question: str) -> Dict[str, Any]:
    match = re.search(r"(\d+(?:\.\d+)?)\s*year", question, flags=re.I)
    if not match:
        return {"mode": "analytics", "answer": None}
    threshold = float(match.group(1))
    rows = (
        analytics.scoped_rooftops(db)
        .filter(RooftopAnalysis.payback_period_years < threshold)
        .all()
    )
    total = analytics.scoped_rooftops(db).count()
    answer = (
        f"{len(rows)} of {total} analyzed rooftop records have a payback period below "
        f"{threshold:g} years ({len(rows) / total * 100:.1f}%). Together they represent "
        f"{sum(r.system_capacity_kw for r in rows):,.1f} kW of capacity and "
        f"{sum(r.annual_generation_kwh for r in rows):,.0f} kWh of annual generation."
    )
    return {
        "mode": "analytics",
        "answer": answer,
        "data": {
            "threshold_years": threshold,
            "matching_rooftops": len(rows),
            "total_rooftops": total,
            "capacity_kw": round(sum(r.system_capacity_kw for r in rows), 2),
        },
        "sources": ["Feature 1 records filtered by Feature 3"],
    }


def _answer_budget_change(db: Session, question: str, emission_factor: float) -> Optional[Dict[str, Any]]:
    numbers = [float(n.replace(",", "")) for n in re.findall(r"(\d+(?:\.\d+)?)", question)]
    crore_values = [
        float(m.group(1)) * CRORE
        for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(?:crore|cr\b)", question, flags=re.I)
    ]
    if len(crore_values) >= 2:
        first, second = crore_values[0], crore_values[1]
    elif len(crore_values) == 1 and len(numbers) >= 2:
        first, second = crore_values[0], None
        for n in numbers:
            candidate = n * CRORE
            if candidate != first:
                second = candidate
                break
    else:
        return None
    if second is None:
        return None

    low = analytics.simulate_budget(db, min(first, second), emission_factor=emission_factor)
    high = analytics.simulate_budget(db, max(first, second), emission_factor=emission_factor)
    delta_cap = high["capacity_kw"] - low["capacity_kw"]
    delta_gen = high["generation_kwh"] - low["generation_kwh"]
    answer = (
        f"Planning simulation: raising the budget from {_fmt_inr(low['budget_inr'])} to "
        f"{_fmt_inr(high['budget_inr'])} increases the rooftops considered from "
        f"{low['rooftops_considered']} to {high['rooftops_considered']}, capacity from "
        f"{low['capacity_kw']:,.1f} kW to {high['capacity_kw']:,.1f} kW "
        f"(+{delta_cap:,.1f} kW), annual generation from {low['generation_gwh']:,.3f} GWh to "
        f"{high['generation_gwh']:,.3f} GWh (+{delta_gen:,.0f} kWh), annual savings from "
        f"{_fmt_inr(low['annual_savings_inr'])} to {_fmt_inr(high['annual_savings_inr'])}, "
        f"and estimated CO2 reduction from {low['co2_tonnes']:,.0f} to "
        f"{high['co2_tonnes']:,.0f} tonnes/year at an emission factor of "
        f"{low['emission_factor']} {EMISSION_FACTOR_UNIT}. {high['disclaimer']}"
    )
    return {
        "mode": "analytics",
        "answer": answer,
        "data": {"scenarios": [low, high]},
        "sources": ["Feature 3 budget simulation engine"],
    }


def _answer_simulate(db: Session, question: str, emission_factor: float) -> Optional[Dict[str, Any]]:
    budget = _parse_money(question)
    if budget is None:
        return None
    result = analytics.simulate_budget(db, budget, emission_factor=emission_factor)
    answer = (
        f"With a planning budget of {_fmt_inr(budget)}, the simulation considers "
        f"{result['rooftops_considered']} of {result['eligible_rooftops']} eligible rooftop "
        f"records, investing {_fmt_inr(result['investment_inr'])} for "
        f"{result['capacity_kw']:,.1f} kW of capacity and "
        f"{result['generation_kwh']:,.0f} kWh of annual generation, giving annual savings of "
        f"{_fmt_inr(result['annual_savings_inr'])}, an estimated "
        f"{result['co2_tonnes']:,.0f} tonnes CO2 reduction per year, and an average payback "
        f"of {result['avg_payback_years']} years. {result['disclaimer']}"
    )
    return {
        "mode": "analytics",
        "answer": answer,
        "data": {"scenario": result},
        "sources": ["Feature 3 budget simulation engine"],
    }


def _answer_city_metric(db: Session, question: str, emission_factor: float) -> Optional[Dict[str, Any]]:
    q = question.lower()
    summary = analytics.city_summary(db, {"emission_factor": emission_factor})
    if "co2" in q or "carbon" in q or "emission" in q:
        answer = (
            f"Estimated annual CO2 reduction: {summary['co2_tonnes']:,.0f} tonnes, from "
            f"{summary['total_generation_gwh']:,.3f} GWh of annual generation multiplied by "
            f"the configured emission factor of {summary['emission_factor']} "
            f"{EMISSION_FACTOR_UNIT} (classification E - user-configured assumption; basis: "
            f"{EMISSION_FACTOR_SOURCE})."
        )
        key = "co2_tonnes"
    elif "capacity" in q or "potential" in q:
        answer = (
            f"Total potential capacity across all analyzed localities: "
            f"{summary['total_capacity_kw']:,.1f} kW ({summary['total_capacity_mw']:.3f} MW) "
            f"from {summary['rooftop_records']} rooftop records in "
            f"{summary['locality_count']} localities."
        )
        key = "total_capacity_kw"
    elif "generation" in q or "generate" in q:
        answer = (
            f"Total annual generation: {summary['total_generation_kwh']:,.0f} kWh "
            f"({summary['total_generation_gwh']:.3f} GWh) across "
            f"{summary['rooftop_records']} analyzed rooftops."
        )
        key = "total_generation_kwh"
    elif "invest" in q or "cost" in q:
        answer = (
            f"Total estimated installation investment: {_fmt_inr(summary['total_cost_inr'])} "
            f"across {summary['rooftop_records']} rooftop records."
        )
        key = "total_cost_inr"
    elif "saving" in q or "economic" in q:
        answer = (
            f"Total estimated annual savings: {_fmt_inr(summary['total_savings_inr'])}; "
            f"average payback across all records is {summary['avg_payback_years']} years."
        )
        key = "total_savings_inr"
    elif "payback" in q:
        answer = (
            f"Average payback period across all analyzed rooftops: "
            f"{summary['avg_payback_years']} years (Feature 1 values aggregated by Feature 3)."
        )
        key = "avg_payback_years"
    elif "index" in q or "spi" in q:
        answer = (
            f"City Solar Potential Index: {summary['avg_spi']}/100, the mean of the "
            f"per-rooftop index values. It is a project decision-support score, not an "
            "official government rating."
        )
        key = "avg_spi"
    else:
        return None
    return {
        "mode": "analytics",
        "answer": answer,
        "data": {"city_summary": summary, "focus": key},
        "sources": ["Feature 3 city aggregation engine"],
    }


def _answer_count(db: Session, question: str) -> Optional[Dict[str, Any]]:
    q = question.lower()
    loc = _find_locality(db, question)
    if "suitability" in q or "high" in q or "medium" in q or "low" in q:
        rows = db.query(RooftopAnalysis)
        if loc:
            rows = rows.filter(RooftopAnalysis.locality == loc.name)
        recs = rows.all()
        high = sum(1 for r in recs if r.suitability == "High")
        medium = sum(1 for r in recs if r.suitability == "Medium")
        low = sum(1 for r in recs if r.suitability == "Low")
        scope = f"{loc.name}" if loc else "the city"
        answer = (
            f"In {scope}: {high} High, {medium} Medium and {low} Low suitability rooftop "
            f"records out of {len(recs)} analyzed rooftops."
        )
        return {
            "mode": "analytics",
            "answer": answer,
            "data": {"high": high, "medium": medium, "low": low, "total": len(recs)},
            "sources": ["Feature 1 Suitability field aggregated by Feature 3"],
        }
    if "rooftop" in q:
        if loc:
            answer = (
                f"{loc.name} has {loc.rooftop_count} analyzed rooftop records in the "
                "uploaded Feature 1 dataset."
            )
            count = loc.rooftop_count
        else:
            count = analytics.scoped_rooftops(db).count()
            answer = (
                f"The dataset contains {count} analyzed rooftop records across "
                f"{len(_localities(db))} localities."
            )
        return {
            "mode": "analytics",
            "answer": answer,
            "data": {"count": count},
            "sources": ["Uploaded Feature 1 Excel dataset"],
        }
    return None


def _answer_list_localities(db: Session) -> Dict[str, Any]:
    locs = analytics.locality_analysis(db)
    lines = [
        f"{i}. {l['name']} - {l['rooftop_count']} rooftops, "
        f"{l['total_capacity_kw']:,.1f} kW, {l['total_generation_kwh']:,.0f} kWh/yr, "
        f"SPI {l['spi']}/100, payback {l['avg_payback_years']} yrs"
        for i, l in enumerate(locs, 1)
    ]
    return {
        "mode": "analytics",
        "answer": "Localities ranked by total capacity:\n" + "\n".join(lines),
        "data": {"localities": locs},
        "sources": ["Feature 3 locality aggregation engine"],
    }


def _rag_answer(question: str) -> Dict[str, Any]:
    results = kb.search(question, top_k=3)
    if not results:
        return {
            "mode": "rag",
            "answer": (
                "I could not find a matching calculation or a matching passage in the "
                "project knowledge base. Try asking about a locality, a total, the Solar "
                "Potential Index, budget simulation, CO2 impact, or the methodology."
            ),
            "data": {},
            "sources": [],
        }
    blocks = []
    for r in results:
        blocks.append(f"[{r['source']} :: {r['heading']}]\n{r['text']}")
    answer = (
        "Based on the project documentation:\n\n" + "\n\n".join(blocks)
    )
    return {
        "mode": "rag",
        "answer": answer,
        "data": {"retrieved": results},
        "sources": [r["source"] for r in results],
    }


def _llm_polish(question: str, draft: str) -> Optional[str]:
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    if not api_key:
        return None
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are the SolarSphere AI government planning assistant. Rewrite the "
                    "provided grounded answer into clear, professional prose. Do not invent, "
                    "change or omit any number. Keep every figure exactly as given."
                ),
            },
            {"role": "user", "content": f"Question: {question}\n\nGrounded answer:\n{draft}"},
        ],
        "temperature": 0.2,
    }
    try:
        req = urllib.request.Request(
            f"{base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]
    except Exception:
        return None


def answer_question(
    db: Session, question: str, emission_factor: Optional[float] = None
) -> Dict[str, Any]:
    factor = float(emission_factor or EMISSION_FACTOR_DEFAULT)
    q = question.strip()
    lower = q.lower()
    result: Optional[Dict[str, Any]] = None

    if re.search(r"budget.*from.*to", lower) or (
        "budget" in lower and len(re.findall(r"(\d+(?:\.\d+)?)\s*(?:crore|cr\b)", lower)) >= 2
    ):
        result = _answer_budget_change(db, q, factor)

    if result is None and "budget" in lower:
        result = _answer_simulate(db, q, factor)

    if result is None:
        loc = _find_locality(db, q)
        if loc and re.search(r"why|explain|reason", lower):
            result = _answer_locality_profile(db, loc)

    if result is None:
        rank = re.search(
            r"(highest|maximum|most|lowest|least|best)\s+"
            r"((?:total\s+|average\s+|solar\s+|annual\s+)*)"
            r"(capacity|generation|savings|investment|usable|index|payback)",
            lower,
        )
        if rank:
            word = rank.group(3)
            metric = {
                "capacity": "capacity",
                "generation": "generation",
                "savings": "savings",
                "investment": "investment",
                "usable": "usable",
                "index": "spi",
                "payback": "payback",
            }[word]
            descending = rank.group(1) not in ("lowest", "least")
            result = _answer_locality_rank(db, metric, q, descending=descending)

    if result is None:
        loc = _find_locality(db, q)
        if loc and ("generation" in lower or "generate" in lower or "available in" in lower):
            answer = (
                f"{loc.name} has an annual generation potential of "
                f"{loc.total_generation_kwh:,.0f} kWh ({loc.total_generation_kwh / 1000:,.0f} MWh) "
                f"from {loc.rooftop_count} analyzed rooftops with a combined capacity of "
                f"{loc.total_capacity_kw:,.1f} kW. "
                f"Estimated investment {_fmt_inr(loc.total_cost_inr)}, annual savings "
                f"{_fmt_inr(loc.total_savings_inr)}, Solar Potential Index {loc.spi}/100."
            )
            result = {
                "mode": "analytics",
                "answer": answer,
                "data": {"locality": loc.name, "generation_kwh": loc.total_generation_kwh},
                "sources": ["Feature 3 locality aggregation engine"],
            }

    if result is None and "payback" in lower and re.search(r"\d+(?:\.\d+)?\s*year", lower):
        result = _answer_payback_count(db, q)

    if result is None:
        loc = _find_locality(db, q)
        if loc and ("explain" in lower or "solar potential" in lower or "profile" in lower):
            result = _answer_locality_profile(db, loc)

    if result is None and re.search(
        r"methodolog|formula|how is|how are|how do|weight|assumption|limitation|"
        r"data source|classification|define|definition|what does feature 3",
        lower,
    ):
        result = _rag_answer(q)

    if result is None:
        result = _answer_city_metric(db, q, factor)

    if result is None and ("localit" in lower or "area" in lower or "list" in lower):
        result = _answer_list_localities(db)

    if result is None:
        result = _answer_count(db, q)

    if result is None or result.get("answer") is None:
        result = _rag_answer(q)

    answer_text = result["answer"]
    polished = _llm_polish(q, answer_text)
    if polished:
        answer_text = polished
        result["llm"] = True
    else:
        result["llm"] = False

    result["question"] = q
    result["emission_factor"] = factor

    db.add(
        AssistantQuery(
            question=q,
            answer=answer_text,
            mode=result["mode"],
            sources=result.get("sources", []),
        )
    )
    db.commit()
    return result
