import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from . import analytics
from .config import (
    EMISSION_FACTOR_DEFAULT,
    EMISSION_FACTOR_SOURCE,
    EMISSION_FACTOR_UNIT,
    INDEX_WEIGHTS_DEFAULT,
    REPORTS_DIR,
)
from .models import Dataset, Locality, RooftopAnalysis

ACCENT = colors.HexColor("#0F766E")
DARK = colors.HexColor("#0B1F33")
LIGHT = colors.HexColor("#F1F5F9")
BAND_COLORS = {
    "81-100": colors.HexColor("#0F766E"),
    "61-80": colors.HexColor("#2563EB"),
    "41-60": colors.HexColor("#D97706"),
    "0-40": colors.HexColor("#B91C1C"),
}


def _styles():
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "title",
            parent=base["Title"],
            fontSize=20,
            textColor=DARK,
            spaceAfter=4,
            alignment=TA_CENTER,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            parent=base["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#475569"),
            alignment=TA_CENTER,
            spaceAfter=14,
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=base["Heading1"],
            fontSize=13,
            textColor=ACCENT,
            spaceBefore=14,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"], fontSize=9, leading=13, textColor=DARK
        ),
        "small": ParagraphStyle(
            "small", parent=base["Normal"], fontSize=8, leading=11, textColor=DARK
        ),
        "cell": ParagraphStyle(
            "cell", parent=base["Normal"], fontSize=7.5, leading=9.5, textColor=DARK
        ),
    }
    return styles


def _table(data, col_widths=None, header=True, styles=None):
    table = Table(data, colWidths=col_widths, repeatRows=1 if header else 0)
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT if header else LIGHT),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white if header else DARK),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    table.setStyle(TableStyle(commands))
    return table


def _fmt_inr(value: float) -> str:
    crore = 10_000_000
    if value >= crore:
        return f"Rs. {value / crore:.2f} crore"
    if value >= 100_000:
        return f"Rs. {value / 100_000:.2f} lakh"
    return f"Rs. {value:,.0f}"


def _map_drawing(records: List[RooftopAnalysis], width=16 * cm, height=10 * cm):
    from reportlab.graphics.shapes import Circle, Drawing, Line, Rect, String

    d = Drawing(width, height)

    d.add(Rect(0, 0, width, height, fillColor=colors.HexColor("#F8FAFC"), strokeColor=colors.HexColor("#CBD5E1")))
    if not records:
        d.add(String(10, height / 2, "No records", fontSize=10, fillColor=DARK))
        return d

    lats = [r.latitude for r in records]
    lons = [r.longitude for r in records]
    lat_min, lat_max = min(lats), max(lats)
    lon_min, lon_max = min(lons), max(lons)
    pad = 25
    span_lat = max(lat_max - lat_min, 1e-6)
    span_lon = max(lon_max - lon_min, 1e-6)

    def px(lon):
        return pad + (lon - lon_min) / span_lon * (width - 2 * pad)

    def py(lat):
        return pad + (lat - lat_min) / span_lat * (height - 2 * pad)

    for i in range(5):
        x = pad + i * (width - 2 * pad) / 4
        y = pad + i * (height - 2 * pad) / 4
        d.add(Line(x, pad, x, height - pad, strokeColor=colors.HexColor("#E2E8F0"), strokeWidth=0.4))
        d.add(Line(pad, y, width - pad, y, strokeColor=colors.HexColor("#E2E8F0"), strokeWidth=0.4))

    for rec in records:
        score = rec.spi or 0
        if score > 80:
            colour = BAND_COLORS["81-100"]
        elif score > 60:
            colour = BAND_COLORS["61-80"]
        elif score > 40:
            colour = BAND_COLORS["41-60"]
        else:
            colour = BAND_COLORS["0-40"]
        d.add(Circle(px(rec.longitude), py(rec.latitude), 3.2, fillColor=colour, strokeColor=colors.white, strokeWidth=0.5))

    d.add(String(pad, 6, f"Longitude {lon_min:.4f} to {lon_max:.4f}", fontSize=7, fillColor=DARK))
    d.add(String(width - 110, 6, f"Latitude {lat_min:.4f} to {lat_max:.4f}", fontSize=7, fillColor=DARK))
    legend_y = height - 12
    for i, (label, colour) in enumerate(
        [("SPI 81-100", BAND_COLORS["81-100"]), ("SPI 61-80", BAND_COLORS["61-80"]), ("SPI 41-60", BAND_COLORS["41-60"]), ("SPI 0-40", BAND_COLORS["0-40"])]
    ):
        x = pad + i * 88
        d.add(Circle(x, legend_y, 3.2, fillColor=colour, strokeColor=colors.white, strokeWidth=0.5))
        d.add(String(x + 7, legend_y - 2.5, label, fontSize=7, fillColor=DARK))
    return d


def build_report(
    db,
    title: str = "SolarSphere AI - Government Solar Planning Report",
    emission_factor: Optional[float] = None,
    budgets: Optional[List[float]] = None,
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    styles = _styles()
    factor = float(emission_factor or EMISSION_FACTOR_DEFAULT)
    budgets = budgets or [50_000_000, 100_000_000, 150_000_000, 200_000_000]
    weights = analytics.normalize_weights(weights)

    dataset = db.query(Dataset).filter(Dataset.is_active == 1).first()
    records = analytics.scoped_rooftops(db).all()
    localities = analytics.locality_analysis(db)
    summary = analytics.city_summary(db, {"emission_factor": factor})
    scenarios = analytics.compare_scenarios(db, budgets, emission_factor=factor)
    charts = analytics.chart_payloads(db)

    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"solar_planning_report_{stamp}.pdf"
    path = os.path.join(REPORTS_DIR, filename)

    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        rightMargin=1.6 * cm,
        leftMargin=1.6 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title=title,
    )
    story = []
    story.append(Paragraph(title, styles["title"]))
    story.append(
        Paragraph(
            "AI-assisted rooftop solar planning and decision support | Feature 3 of SolarSphere AI",
            styles["subtitle"],
        )
    )

    story.append(Paragraph("1. Project title", styles["h1"]))
    story.append(
        Paragraph(
            "SolarSphere AI - An Intelligent Community Solar Ecosystem Using AI and Blockchain. "
            "Feature 3: AI Government Solar Planning.",
            styles["body"],
        )
    )

    story.append(Paragraph("2. Study area", styles["h1"]))
    loc_names = ", ".join(l["name"] for l in localities)
    lats = [r.latitude for r in records]
    lons = [r.longitude for r in records]
    story.append(
        Paragraph(
            f"Localities covered: {loc_names}. Coordinate bounds: latitude "
            f"{min(lats):.4f} to {max(lats):.4f}, longitude {min(lons):.4f} to "
            f"{max(lons):.4f}. All records fall within the uploaded Feature 1 study area.",
            styles["body"],
        )
    )

    story.append(Paragraph("3. Dataset description", styles["h1"]))
    ds_name = dataset.filename if dataset else "not loaded"
    sheet = dataset.sheet_name if dataset else "-"
    story.append(
        Paragraph(
            f"Source workbook: <b>{ds_name}</b>, sheet <b>{sheet}</b>. "
            f"Rows read: {dataset.rows_total if dataset else 0}, valid: "
            f"{dataset.rows_valid if dataset else 0}, invalid: "
            f"{dataset.rows_invalid if dataset else 0}, missing values: "
            f"{dataset.missing_values if dataset else 0}, duplicates: "
            f"{dataset.duplicate_records if dataset else 0}. "
            f"Every source row carries Data_Type = SYNTHETIC_DEMO, therefore all Feature 1 "
            "fields in this report are demonstration values and not real-world measurements.",
            styles["body"],
        )
    )

    story.append(Paragraph("4. Dataset scope", styles["h1"]))
    scope = [
        ["Metric", "Value", "Classification"],
        ["Rooftop records", f"{summary['rooftop_records']}", "A - Feature 1 output"],
        ["Localities", f"{summary['locality_count']}", "A - Feature 1 output"],
        ["Total rooftop area", f"{summary['total_rooftop_area_m2']:,.0f} m2", "A - Feature 1 output"],
        ["Total usable rooftop area", f"{summary['total_usable_area_m2']:,.0f} m2", "A - Feature 1 output"],
        ["Total recommended panels", f"{summary['total_panels']:,}", "A - Feature 1 output"],
    ]
    story.append(_table(scope, col_widths=[5.2 * cm, 5.0 * cm, 6.4 * cm]))
    story.append(Spacer(1, 8))

    story.append(Paragraph("5. Solar capacity", styles["h1"]))
    story.append(
        Paragraph(
            f"Total potential capacity: <b>{summary['total_capacity_kw']:,.1f} kW "
            f"({summary['total_capacity_mw']:.3f} MW)</b>.",
            styles["body"],
        )
    )
    story.append(Paragraph("6. Annual generation", styles["h1"]))
    story.append(
        Paragraph(
            f"Total annual generation: <b>{summary['total_generation_kwh']:,.0f} kWh "
            f"({summary['total_generation_gwh']:.3f} GWh)</b>.",
            styles["body"],
        )
    )
    story.append(Paragraph("7. Estimated investment", styles["h1"]))
    story.append(
        Paragraph(
            f"Total estimated installation investment: <b>{_fmt_inr(summary['total_cost_inr'])}</b>.",
            styles["body"],
        )
    )
    story.append(Paragraph("8. Annual savings", styles["h1"]))
    story.append(
        Paragraph(
            f"Total estimated annual savings: <b>{_fmt_inr(summary['total_savings_inr'])}</b>.",
            styles["body"],
        )
    )

    story.append(Paragraph("9. Payback analysis", styles["h1"]))
    paybacks = [r.payback_period_years for r in records]
    story.append(
        Paragraph(
            f"Average payback {sum(paybacks) / len(paybacks):.2f} years, minimum "
            f"{min(paybacks):.2f} years, maximum {max(paybacks):.2f} years. "
            f"Distribution: "
            + ", ".join(
                f"{b['bucket']} = {b['count']}" for b in charts["payback_distribution"]
            )
            + ".",
            styles["body"],
        )
    )

    story.append(Paragraph("10. Locality-wise analysis", styles["h1"]))
    header = [
        "Locality", "Roof- tops", "Usable m2", "Capacity kW", "Generation kWh",
        "Investment", "Savings/yr", "Payback", "High/Med/Low", "SPI",
    ]
    rows = [header]
    for l in localities:
        rows.append(
            [
                l["name"],
                f"{l['rooftop_count']}",
                f"{l['total_usable_area_m2']:,.0f}",
                f"{l['total_capacity_kw']:,.1f}",
                f"{l['total_generation_kwh']:,.0f}",
                _fmt_inr(l["total_cost_inr"]),
                _fmt_inr(l["total_savings_inr"]),
                f"{l['avg_payback_years']:.2f} y",
                f"{l['high_count']}/{l['medium_count']}/{l['low_count']}",
                f"{l['spi']}",
            ]
        )
    story.append(
        _table(
            rows,
            col_widths=[2.1 * cm, 1.3 * cm, 1.7 * cm, 1.7 * cm, 2.1 * cm, 2.2 * cm,
                        2.0 * cm, 1.4 * cm, 1.7 * cm, 1.0 * cm],
        )
    )
    story.append(Spacer(1, 8))

    story.append(Paragraph("11. Solar Potential Index", styles["h1"]))
    story.append(
        Paragraph(
            f"City Solar Potential Index: <b>{summary['avg_spi']} / 100</b>. "
            "This is a project decision-support score, not an official government rating. "
            f"Weights used (percent): usable area {weights['usable_area']:.0f}, generation "
            f"{weights['generation']:.0f}, capacity {weights['capacity']:.0f}, economics "
            f"{weights['economics']:.0f}, payback {weights['payback']:.0f}, suitability "
            f"{weights['suitability']:.0f}. Factors are min-max normalized across the dataset; "
            "payback is inverted so shorter payback scores higher.",
            styles["body"],
        )
    )
    spi_rows = [["Locality", "SPI", "Main contributors"]]
    for l in sorted(localities, key=lambda x: x["spi"], reverse=True):
        breakdown = l["spi_breakdown"] or {}
        top = sorted(breakdown.items(), key=lambda kv: kv[1], reverse=True)[:3]
        spi_rows.append(
            [l["name"], f"{l['spi']}", ", ".join(f"{k} {v:.1f} pts" for k, v in top)]
        )
    story.append(_table(spi_rows, col_widths=[3.5 * cm, 1.6 * cm, 11.0 * cm]))
    story.append(Spacer(1, 8))

    story.append(Paragraph("12. GIS visualization", styles["h1"]))
    story.append(
        Paragraph(
            "Rooftop coordinates plotted from Feature 1 (Latitude/Longitude) and coloured by "
            "Solar Potential Index band. Basemap tiles in the live application are "
            "OpenStreetMap (classification C - real public data).",
            styles["small"],
        )
    )
    story.append(Spacer(1, 4))
    story.append(_map_drawing(records))
    story.append(Spacer(1, 8))

    story.append(Paragraph("13. Budget scenarios", styles["h1"]))
    scen_rows = [["Budget", "Rooftops", "Investment", "Capacity kW", "Generation kWh",
                  "Savings/yr", "CO2 t/yr", "Payback"]]
    for s in scenarios:
        scen_rows.append(
            [
                _fmt_inr(s["budget_inr"]),
                f"{s['rooftops_considered']}",
                _fmt_inr(s["investment_inr"]),
                f"{s['capacity_kw']:,.1f}",
                f"{s['generation_kwh']:,.0f}",
                _fmt_inr(s["annual_savings_inr"]),
                f"{s['co2_tonnes']:,.0f}",
                f"{s['avg_payback_years']:.2f} y",
            ]
        )
    story.append(_table(scen_rows, col_widths=[2.4 * cm, 1.5 * cm, 2.4 * cm, 2.0 * cm,
                                               2.4 * cm, 2.2 * cm, 1.6 * cm, 1.7 * cm]))
    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            "Scenarios are simulations only. No scenario is labelled as best. These results "
            "do not approve, award or select any government project.",
            styles["small"],
        )
    )
    story.append(Spacer(1, 8))

    story.append(Paragraph("14. Environmental impact", styles["h1"]))
    story.append(
        Paragraph(
            f"Annual generation {summary['total_generation_kwh']:,.0f} kWh x emission factor "
            f"{factor} {EMISSION_FACTOR_UNIT} = <b>{summary['co2_tonnes']:,.0f} tonnes CO2 "
            f"reduction per year</b>. Emission factor classification: E - user-configured "
            f"assumption. Basis: {EMISSION_FACTOR_SOURCE}",
            styles["body"],
        )
    )

    story.append(Paragraph("15. Methodology", styles["h1"]))
    story.append(
        Paragraph(
            "Feature 3 ingests the Feature 1 Excel output, validates and cleans it, groups "
            "records by Locality, aggregates rooftop results to locality and city level, "
            "computes an explainable weighted Solar Potential Index, visualizes the records "
            "on a GIS map, and runs budget simulations and scenario comparisons. Every number "
            "in this report is computed by the Feature 3 analytics engine from the uploaded "
            "dataset; no figure is generated randomly.",
            styles["body"],
        )
    )

    story.append(Paragraph("16. Assumptions", styles["h1"]))
    story.append(
        Paragraph(
            "One Excel row equals one analyzed rooftop. Locality is taken from the dataset and "
            "never randomly assigned. Feature 1 values for generation, cost, savings and "
            "payback are used as given. Index weights are configurable (default 25/25/20/15/10/5). "
            "The emission factor is configurable. Budget scenarios use a greedy "
            "Solar-Potential-Index-ranked selection within the budget.",
            styles["body"],
        )
    )

    story.append(Paragraph("17. Limitations", styles["h1"]))
    story.append(
        Paragraph(
            "The source rows are synthetic demonstration data and must be replaced with real "
            "Feature 1 outputs before any official use. Feature 3 performs no structural, "
            "shading, grid-connection or statutory assessment. The Solar Potential Index is a "
            "project aid, not an official government score. CO2 figures are indicative "
            "planning estimates, not verified carbon credits.",
            styles["body"],
        )
    )

    story.append(Paragraph("18. Data classification summary", styles["h1"]))
    class_rows = [
        ["Class", "Meaning", "Used for"],
        ["A", "Feature 1 output", "All uploaded Excel fields"],
        ["B", "Calculated by Feature 3", "Aggregates, Solar Potential Index, CO2, payback stats"],
        ["C", "Real public data", "OpenStreetMap basemap tiles in the live map"],
        ["D", "Simulated / demo data", "Source rows flagged SYNTHETIC_DEMO; budget scenarios"],
        ["E", "User-configured assumption", "Emission factor, index weights, budget and filters"],
    ]
    story.append(_table(class_rows, col_widths=[1.6 * cm, 5.2 * cm, 9.6 * cm]))

    doc.build(story)

    summary_payload = {
        "rooftop_records": summary["rooftop_records"],
        "capacity_kw": summary["total_capacity_kw"],
        "generation_kwh": summary["total_generation_kwh"],
        "investment_inr": summary["total_cost_inr"],
        "savings_inr": summary["total_savings_inr"],
        "co2_tonnes": summary["co2_tonnes"],
        "spi": summary["avg_spi"],
        "emission_factor": factor,
        "scenarios": [s["budget_inr"] for s in scenarios],
    }
    return {"filename": filename, "path": path, "title": title, "summary": summary_payload}
