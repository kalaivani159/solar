import os
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from . import analytics, assistant, ingestion, report
from .config import (
    DEFAULT_DATASET,
    EMISSION_FACTOR_DEFAULT,
    EMISSION_FACTOR_SOURCE,
    EMISSION_FACTOR_UNIT,
    INDEX_WEIGHTS_DEFAULT,
    KNOWLEDGE_DIR,
)
from .database import Base, engine, get_db
from .models import AssistantQuery, DataSource, Dataset, Locality, Report, RooftopAnalysis
from .rag import kb
from .schemas import (
    AssistantRequest,
    CompareRequest,
    IndexWeightsRequest,
    ReportRequest,
    SimulateRequest,
)

app = FastAPI(
    title="SolarSphere AI - Feature 3: Government Solar Planning API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FILTER_PARAMS = [
    "locality",
    "suitability",
    "min_spi",
    "max_spi",
    "min_capacity",
    "max_capacity",
    "min_generation",
    "max_generation",
    "max_payback",
    "min_payback",
]


def _params(request: Request) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key in FILTER_PARAMS:
        raw = request.query_params.get(key)
        if raw is None or raw == "":
            continue
        if key in ("locality", "suitability"):
            out[key] = raw
        else:
            try:
                out[key] = float(raw)
            except ValueError:
                raise HTTPException(400, f"Invalid value for {key}: {raw}")
    return out


def _ensure_default(db: Session):
    active = db.query(Dataset).filter(Dataset.is_active == 1).first()
    if active is None and os.path.exists(DEFAULT_DATASET):
        stats = ingestion.load_default_dataset(db)
        analytics.rebuild_analytics(db)
        return stats
    return None


def _seed_sources(db: Session):
    if db.query(DataSource).count() > 0:
        return
    rows = [
        DataSource(
            dataset="SolarSphere_Feature3_Demo_Dataset_Location_Based.xlsx",
            source="Feature 1 (AI Rooftop Solar Potential Analysis) outputs, project team",
            purpose="Primary Feature 3 dataset: rooftop-level solar analysis records",
            fields_used="Location_Input, Latitude, Longitude, Locality, Rooftop_Area_m2, "
            "Usable_Rooftop_Area_m2, Recommended_Panels, System_Capacity_kW, "
            "Annual_Generation_kWh, Estimated_Installation_Cost_INR, "
            "Estimated_Annual_Savings_INR, Payback_Period_Years, Suitability, Data_Type",
            access_date="2026-09-27",
            license="Project-internal demonstration data",
            classification="D - synthetic demo (Data_Type = SYNTHETIC_DEMO)",
        ),
        DataSource(
            dataset="OpenStreetMap basemap tiles",
            source="OpenStreetMap (tile layer via Leaflet)",
            purpose="GIS visualization of rooftop points and locality centroids",
            fields_used="Map raster tiles only; no attribute data imported",
            access_date="2026-09-27",
            license="ODbL (data), OpenStreetMap tile usage policy (tiles)",
            classification="C - real public data",
        ),
        DataSource(
            dataset="Grid emission factor",
            source="Central Electricity Authority (CEA), CO2 Baseline Database for the "
            "Indian Power Sector (indicative weighted factor)",
            purpose="Estimated annual CO2 reduction calculation",
            fields_used="Emission factor (kg CO2/kWh), default 0.71",
            access_date="2026-09-27",
            license="Government of India publication (indicative use)",
            classification="E - user-configured assumption",
        ),
        DataSource(
            dataset="Project knowledge base",
            source="SolarSphere AI project documentation (backend/knowledge_base)",
            purpose="RAG grounding for the AI planning assistant",
            fields_used="methodology, solar_potential_index, budget_simulation, "
            "data_sources_assumptions, environmental_impact, feature1_workflow, dataset_description",
            access_date="2026-09-27",
            license="Project-internal",
            classification="B - project methodology",
        ),
    ]
    db.add_all(rows)
    db.commit()


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    try:
        _ensure_default(db)
        _seed_sources(db)
    finally:
        db.close()


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "solarsphere-feature3"}


@app.get("/api/dataset")
def get_dataset(db: Session = Depends(get_db)):
    ds = db.query(Dataset).filter(Dataset.is_active == 1).first()
    if not ds:
        return {"loaded": False}
    return {
        "loaded": True,
        "id": ds.id,
        "filename": ds.filename,
        "sheet_name": ds.sheet_name,
        "uploaded_at": ds.uploaded_at.isoformat() if ds.uploaded_at else None,
        "rows_total": ds.rows_total,
        "rows_valid": ds.rows_valid,
        "rows_invalid": ds.rows_invalid,
        "missing_values": ds.missing_values,
        "duplicate_records": ds.duplicate_records,
        "localities_count": ds.localities_count,
        "notes": ds.notes,
        "validation_log": ds.validation_log,
    }


@app.post("/api/upload/excel")
async def upload_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename:
        raise HTTPException(400, "No file provided")
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".xlsx", ".xlsm", ".xls"):
        raise HTTPException(400, "Only .xlsx / .xlsm workbooks are supported")
    from .config import UPLOAD_DIR

    dest = os.path.join(UPLOAD_DIR, os.path.basename(file.filename))
    with open(dest, "wb") as fh:
        fh.write(await file.read())
    try:
        stats = ingestion.load_file(db, dest, file.filename)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    except Exception as exc:
        raise HTTPException(422, f"Could not read workbook: {exc}")
    analytics.rebuild_analytics(db)
    return {"status": "ok", "stats": stats}


@app.post("/api/dataset/load-demo")
def load_demo(db: Session = Depends(get_db)):
    if not os.path.exists(DEFAULT_DATASET):
        raise HTTPException(404, "Bundled demo dataset not found")
    stats = ingestion.load_default_dataset(db)
    analytics.rebuild_analytics(db)
    return {"status": "ok", "stats": stats}


@app.get("/api/rooftops")
def list_rooftops(
    request: Request,
    limit: int = Query(50, le=500),
    offset: int = 0,
    sort: str = "spi",
    order: str = "desc",
    db: Session = Depends(get_db),
):
    q = analytics.filter_query(db, _params(request))
    total = q.count()
    column = {
        "spi": RooftopAnalysis.spi,
        "capacity": RooftopAnalysis.system_capacity_kw,
        "generation": RooftopAnalysis.annual_generation_kwh,
        "cost": RooftopAnalysis.installation_cost_inr,
        "savings": RooftopAnalysis.annual_savings_inr,
        "payback": RooftopAnalysis.payback_period_years,
        "usable": RooftopAnalysis.usable_rooftop_area_m2,
    }.get(sort, RooftopAnalysis.spi)
    q = q.order_by(column.asc() if order == "asc" else column.desc())
    rows = q.offset(offset).limit(limit).all()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": r.id,
                "location_input": r.location_input,
                "rooftop_selection": r.rooftop_selection,
                "latitude": r.latitude,
                "longitude": r.longitude,
                "locality": r.locality,
                "rooftop_area_m2": r.rooftop_area_m2,
                "usable_rooftop_area_m2": r.usable_rooftop_area_m2,
                "recommended_panels": r.recommended_panels,
                "system_capacity_kw": r.system_capacity_kw,
                "annual_generation_kwh": r.annual_generation_kwh,
                "installation_cost_inr": r.installation_cost_inr,
                "annual_savings_inr": r.annual_savings_inr,
                "payback_period_years": r.payback_period_years,
                "suitability": r.suitability,
                "data_type": r.data_type,
                "spi": r.spi,
                "spi_breakdown": r.spi_breakdown,
                "source_row": r.source_row,
            }
            for r in rows
        ],
    }


@app.get("/api/rooftops/{rooftop_id}")
def get_rooftop(rooftop_id: int, db: Session = Depends(get_db)):
    r = db.query(RooftopAnalysis).filter(RooftopAnalysis.id == rooftop_id).first()
    if not r:
        raise HTTPException(404, "Rooftop record not found")
    return {
        "id": r.id,
        "location_input": r.location_input,
        "rooftop_selection": r.rooftop_selection,
        "latitude": r.latitude,
        "longitude": r.longitude,
        "locality": r.locality,
        "rooftop_area_m2": r.rooftop_area_m2,
        "usable_rooftop_area_m2": r.usable_rooftop_area_m2,
        "recommended_panels": r.recommended_panels,
        "system_capacity_kw": r.system_capacity_kw,
        "annual_generation_kwh": r.annual_generation_kwh,
        "installation_cost_inr": r.installation_cost_inr,
        "annual_savings_inr": r.annual_savings_inr,
        "payback_period_years": r.payback_period_years,
        "suitability": r.suitability,
        "data_type": r.data_type,
        "spi": r.spi,
        "spi_breakdown": r.spi_breakdown,
        "source_row": r.source_row,
        "classification": "A - Feature 1 output, indexed by Feature 3 (SPI)",
    }


@app.get("/api/localities")
def list_localities(db: Session = Depends(get_db)):
    rows = analytics.locality_analysis(db)
    return {"total": len(rows), "items": rows}


@app.get("/api/localities/{name}")
def get_locality(name: str, db: Session = Depends(get_db)):
    rows = analytics.locality_analysis(db, {"locality": name})
    if not rows:
        raise HTTPException(404, f"Locality '{name}' not found")
    row = rows[0]
    rooftops = (
        analytics.scoped_rooftops(db)
        .filter(RooftopAnalysis.locality == name)
        .order_by(RooftopAnalysis.spi.desc())
        .all()
    )
    return {
        "locality": row,
        "rooftops": [
            {
                "id": r.id,
                "location_input": r.location_input,
                "locality": r.locality,
                "latitude": r.latitude,
                "longitude": r.longitude,
                "rooftop_area_m2": r.rooftop_area_m2,
                "usable_rooftop_area_m2": r.usable_rooftop_area_m2,
                "recommended_panels": r.recommended_panels,
                "system_capacity_kw": r.system_capacity_kw,
                "annual_generation_kwh": r.annual_generation_kwh,
                "installation_cost_inr": r.installation_cost_inr,
                "annual_savings_inr": r.annual_savings_inr,
                "payback_period_years": r.payback_period_years,
                "suitability": r.suitability,
                "data_type": r.data_type,
                "spi": r.spi,
                "spi_breakdown": r.spi_breakdown,
                "source_row": r.source_row,
            }
            for r in rooftops
        ],
    }


@app.get("/api/dashboard/summary")
def dashboard_summary(request: Request, db: Session = Depends(get_db)):
    _ensure_default(db)
    params = _params(request)
    params.setdefault("emission_factor", EMISSION_FACTOR_DEFAULT)
    summary = analytics.city_summary(db, params)
    summary["dataset"] = (
        {
            "filename": db.query(Dataset).filter(Dataset.is_active == 1).first().filename
        }
        if db.query(Dataset).filter(Dataset.is_active == 1).first()
        else None
    )
    return summary


@app.get("/api/dashboard/locality-analysis")
def dashboard_localities(request: Request, db: Session = Depends(get_db)):
    rows = analytics.locality_analysis(db, _params(request))
    return {"total": len(rows), "items": rows}


@app.get("/api/dashboard/charts")
def dashboard_charts(request: Request, db: Session = Depends(get_db)):
    return analytics.chart_payloads(db, _params(request))


@app.get("/api/map/rooftops")
def map_rooftops(request: Request, db: Session = Depends(get_db)):
    rows = analytics.filter_query(db, _params(request)).all()
    return {
        "total": len(rows),
        "points": [
            {
                "id": r.id,
                "latitude": r.latitude,
                "longitude": r.longitude,
                "locality": r.locality,
                "location_input": r.location_input,
                "system_capacity_kw": r.system_capacity_kw,
                "annual_generation_kwh": r.annual_generation_kwh,
                "payback_period_years": r.payback_period_years,
                "suitability": r.suitability,
                "spi": r.spi,
                "usable_rooftop_area_m2": r.usable_rooftop_area_m2,
                "installation_cost_inr": r.installation_cost_inr,
                "annual_savings_inr": r.annual_savings_inr,
            }
            for r in rows
        ],
    }


@app.get("/api/map/localities")
def map_localities(db: Session = Depends(get_db)):
    rows = analytics.locality_analysis(db)
    return {
        "total": len(rows),
        "points": [
            {
                "name": l["name"],
                "latitude": l["centroid_lat"],
                "longitude": l["centroid_lon"],
                "rooftop_count": l["rooftop_count"],
                "total_capacity_kw": l["total_capacity_kw"],
                "total_generation_kwh": l["total_generation_kwh"],
                "spi": l["spi"],
                "avg_payback_years": l["avg_payback_years"],
            }
            for l in rows
        ],
    }


@app.get("/api/solar-potential-index")
def solar_potential_index(db: Session = Depends(get_db)):
    rows = analytics.locality_analysis(db)
    rooftops = analytics.scoped_rooftops(db).all()
    city_spi = (
        round(sum(r.spi for r in rooftops) / len(rooftops), 1) if rooftops else 0
    )
    weights = analytics.applied_weights()
    return {
        "city_spi": city_spi,
        "weights": weights,
        "default_weights": INDEX_WEIGHTS_DEFAULT,
        "scale": "0-100 project decision-support score (not an official government score)",
        "method": "min-max normalization across the uploaded dataset; payback inverted",
        "localities": rows,
    }


@app.post("/api/solar-potential-index/recompute")
def recompute_index(body: IndexWeightsRequest, db: Session = Depends(get_db)):
    result = analytics.rebuild_analytics(db, body.weights)
    return {
        "status": "ok",
        "result": result,
        "weights": analytics.applied_weights(),
    }


@app.post("/api/planning/simulate")
def planning_simulate(body: SimulateRequest, db: Session = Depends(get_db)):
    return analytics.simulate_budget(
        db,
        budget_inr=body.budget_inr,
        min_spi=body.min_spi,
        max_payback=body.max_payback_years,
        min_capacity=body.min_capacity_kw,
        locality=body.locality,
        emission_factor=body.emission_factor,
    )


@app.post("/api/planning/compare")
def planning_compare(body: CompareRequest, db: Session = Depends(get_db)):
    scenarios = analytics.compare_scenarios(
        db,
        body.budgets_inr,
        min_spi=body.min_spi,
        max_payback=body.max_payback_years,
        min_capacity=body.min_capacity_kw,
        locality=body.locality,
        emission_factor=body.emission_factor,
    )
    return {"scenarios": scenarios}


@app.get("/api/environmental-impact")
def environmental_impact(
    request: Request,
    emission_factor: Optional[float] = None,
    db: Session = Depends(get_db),
):
    params = _params(request)
    factor = float(emission_factor or EMISSION_FACTOR_DEFAULT)
    params["emission_factor"] = factor
    summary = analytics.city_summary(db, params)
    return {
        "annual_generation_kwh": summary["total_generation_kwh"],
        "emission_factor": factor,
        "emission_factor_unit": EMISSION_FACTOR_UNIT,
        "emission_factor_source": EMISSION_FACTOR_SOURCE,
        "co2_tonnes": summary["co2_tonnes"],
        "classification": "generation = A; emission factor = E; CO2 result = B",
        "formula": "CO2 (t/yr) = annual generation (kWh) x factor (kg CO2/kWh) / 1000",
    }


@app.post("/api/assistant/query")
def assistant_query(body: AssistantRequest, db: Session = Depends(get_db)):
    _ensure_default(db)
    if not body.question.strip():
        raise HTTPException(400, "Question is empty")
    return assistant.answer_question(db, body.question, body.emission_factor)


@app.get("/api/assistant/knowledge")
def assistant_knowledge():
    return {
        "documents": kb.list_documents(),
        "knowledge_dir": os.path.basename(KNOWLEDGE_DIR),
        "answer_rule": (
            "Numeric answers are computed by the Feature 3 analytics engine first; the "
            "language layer only explains the computed result. Documentation questions are "
            "answered by retrieval over the project knowledge base."
        ),
    }


@app.get("/api/assistant/history")
def assistant_history(limit: int = 20, db: Session = Depends(get_db)):
    rows = (
        db.query(AssistantQuery)
        .order_by(AssistantQuery.created_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "items": [
            {
                "id": r.id,
                "question": r.question,
                "answer": r.answer,
                "mode": r.mode,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
    }


@app.post("/api/reports/generate")
def generate_report(body: ReportRequest, db: Session = Depends(get_db)):
    _ensure_default(db)
    result = report.build_report(
        db,
        title=body.title,
        emission_factor=body.emission_factor,
        budgets=body.budgets_inr,
        weights=body.weights,
    )
    db.add(
        Report(
            title=result["title"],
            filename=result["filename"],
            summary=result["summary"],
        )
    )
    db.commit()
    return {"status": "ok", "filename": result["filename"], "summary": result["summary"]}


@app.get("/api/reports")
def list_reports(db: Session = Depends(get_db)):
    rows = db.query(Report).order_by(Report.created_at.desc()).all()
    return {
        "items": [
            {
                "id": r.id,
                "title": r.title,
                "filename": r.filename,
                "summary": r.summary,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
    }


@app.get("/api/reports/{report_id}/download")
def download_report(report_id: int, db: Session = Depends(get_db)):
    row = db.query(Report).filter(Report.id == report_id).first()
    if not row:
        raise HTTPException(404, "Report not found")
    from .config import REPORTS_DIR

    path = os.path.join(REPORTS_DIR, row.filename)
    if not os.path.exists(path):
        raise HTTPException(404, "Report file missing on disk")
    return FileResponse(path, media_type="application/pdf", filename=row.filename)


@app.get("/api/meta/data-sources")
def data_sources(db: Session = Depends(get_db)):
    rows = db.query(DataSource).all()
    return {
        "items": [
            {
                "id": r.id,
                "dataset": r.dataset,
                "source": r.source,
                "purpose": r.purpose,
                "fields_used": r.fields_used,
                "access_date": r.access_date,
                "license": r.license,
                "classification": r.classification,
            }
            for r in rows
        ]
    }
