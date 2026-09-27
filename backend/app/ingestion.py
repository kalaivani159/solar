import os
from typing import Any, Dict, List, Tuple

import pandas as pd
from sqlalchemy.orm import Session

from .config import DEFAULT_DATASET
from .models import Dataset, Locality, RooftopAnalysis

CANONICAL_COLUMNS = {
    "location_input": "location_input",
    "rooftop_selection": "rooftop_selection",
    "latitude": "latitude",
    "longitude": "longitude",
    "locality": "locality",
    "rooftop_area_m2": "rooftop_area_m2",
    "usable_rooftop_area_m2": "usable_rooftop_area_m2",
    "recommended_panels": "recommended_panels",
    "system_capacity_kw": "system_capacity_kw",
    "annual_generation_kwh": "annual_generation_kwh",
    "estimated_installation_cost_inr": "installation_cost_inr",
    "estimated_annual_savings_inr": "annual_savings_inr",
    "payback_period_years": "payback_period_years",
    "suitability": "suitability",
    "data_type": "data_type",
}

REQUIRED = [
    "latitude",
    "longitude",
    "rooftop_area_m2",
    "usable_rooftop_area_m2",
    "recommended_panels",
    "system_capacity_kw",
    "annual_generation_kwh",
    "installation_cost_inr",
    "annual_savings_inr",
    "payback_period_years",
    "suitability",
]

OPTIONAL = ["location_input", "rooftop_selection", "locality", "data_type"]

NUMERIC_FIELDS = [
    "latitude",
    "longitude",
    "rooftop_area_m2",
    "usable_rooftop_area_m2",
    "recommended_panels",
    "system_capacity_kw",
    "annual_generation_kwh",
    "installation_cost_inr",
    "annual_savings_inr",
    "payback_period_years",
]

SUITABILITY_CANON = {"high": "High", "medium": "Medium", "low": "Low"}


def _normalize_name(name: str) -> str:
    cleaned = str(name).strip().lower()
    cleaned = cleaned.replace(" ", "_").replace("-", "_")
    cleaned = "".join(ch for ch in cleaned if ch.isalnum() or ch == "_")
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned


def map_columns(columns: List[str]) -> Tuple[Dict[str, str], List[str]]:
    mapping: Dict[str, str] = {}
    unmapped: List[str] = []
    for col in columns:
        key = _normalize_name(col)
        if key in CANONICAL_COLUMNS:
            mapping[col] = CANONICAL_COLUMNS[key]
        else:
            unmapped.append(col)
    return mapping, unmapped


def read_workbook(path: str) -> Tuple[pd.DataFrame, str, List[str]]:
    sheets = pd.ExcelFile(path).sheet_names
    preferred = None
    for name in sheets:
        if "readme" not in name.lower() and "metadata" not in name.lower():
            preferred = name
            break
    if preferred is None:
        preferred = sheets[0]
    df = pd.read_excel(path, sheet_name=preferred)
    other_sheets = [s for s in sheets if s != preferred]
    return df, preferred, other_sheets


def validate_and_clean(raw: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    mapping, unmapped = map_columns(list(raw.columns))
    missing_required = [
        CANONICAL_COLUMNS_inv(c) for c in REQUIRED if c not in mapping.values()
    ]

    df = raw.rename(columns=mapping)
    df = df.loc[:, ~df.columns.duplicated()]

    log: Dict[str, Any] = {
        "source_columns": list(raw.columns),
        "mapped_columns": mapping,
        "unmapped_columns": unmapped,
        "missing_required_columns": missing_required,
        "row_issues": [],
    }

    if missing_required:
        raise ValueError(
            "Missing required columns: " + ", ".join(missing_required)
        )

    for col in NUMERIC_FIELDS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in OPTIONAL:
        if col not in df.columns:
            df[col] = None

    df["locality"] = df["locality"].apply(
        lambda v: str(v).strip() if isinstance(v, str) and v.strip() else None
    )
    df["location_input"] = df["location_input"].apply(
        lambda v: str(v).strip() if isinstance(v, str) and v.strip() else None
    )
    df["data_type"] = df["data_type"].apply(
        lambda v: str(v).strip().upper() if isinstance(v, str) and v.strip() else "UNSPECIFIED"
    )
    df["suitability"] = df["suitability"].apply(
        lambda v: SUITABILITY_CANON.get(str(v).strip().lower()) if pd.notna(v) else None
    )

    total_rows = len(df)
    missing_cells = int(df[list(NUMERIC_FIELDS) + ["suitability", "locality"]].isna().sum().sum())

    duplicate_full = int(df.duplicated().sum())
    dup_coord_mask = df.duplicated(subset=["latitude", "longitude"], keep="first")
    duplicate_coords = int(dup_coord_mask.sum())

    reasons: List[str] = []
    invalid = pd.Series(False, index=df.index)

    invalid = invalid | df[REQUIRED].isna().any(axis=1)
    for idx in df.index[df[REQUIRED].isna().any(axis=1)]:
        reasons.append({"row": int(idx) + 2, "issue": "missing required value"})

    bad_lat = df["latitude"].notna() & ((df["latitude"] < -90) | (df["latitude"] > 90))
    bad_lon = df["longitude"].notna() & ((df["longitude"] < -180) | (df["longitude"] > 180))
    for idx in df.index[bad_lat]:
        reasons.append({"row": int(idx) + 2, "issue": "latitude out of range"})
    for idx in df.index[bad_lon]:
        reasons.append({"row": int(idx) + 2, "issue": "longitude out of range"})
    invalid = invalid | bad_lat | bad_lon

    negative_fields = [
        "rooftop_area_m2",
        "usable_rooftop_area_m2",
        "recommended_panels",
        "system_capacity_kw",
        "annual_generation_kwh",
        "installation_cost_inr",
        "annual_savings_inr",
        "payback_period_years",
    ]
    for field in negative_fields:
        mask = df[field].notna() & (df[field] < 0)
        for idx in df.index[mask]:
            reasons.append({"row": int(idx) + 2, "issue": f"negative value in {field}"})
        invalid = invalid | mask

    bad_usable = (
        df["usable_rooftop_area_m2"].notna()
        & df["rooftop_area_m2"].notna()
        & (df["usable_rooftop_area_m2"] > df["rooftop_area_m2"])
    )
    for idx in df.index[bad_usable]:
        reasons.append({"row": int(idx) + 2, "issue": "usable area greater than total area"})
    invalid = invalid | bad_usable

    dup_mask = dup_coord_mask | df.duplicated(keep="first")
    for idx in df.index[dup_mask]:
        reasons.append({"row": int(idx) + 2, "issue": "duplicate record"})
    invalid = invalid | dup_mask

    df["source_row"] = df.index + 2
    valid_df = df[~invalid].copy().reset_index(drop=True)
    invalid_df = df[invalid].copy().reset_index(drop=True)

    if valid_df["locality"].isna().any():
        valid_df["locality"] = valid_df.apply(_derive_locality, axis=1)

    valid_df["locality"] = valid_df["locality"].fillna("Unassigned")

    stats = {
        "total_rows": total_rows,
        "valid_rows": len(valid_df),
        "invalid_rows": len(invalid_df),
        "missing_values": missing_cells,
        "duplicate_records": duplicate_full + duplicate_coords,
        "localities": sorted(valid_df["locality"].dropna().unique().tolist()),
        "issues": reasons,
        "unmapped_columns": unmapped,
        "data_types": sorted(valid_df["data_type"].unique().tolist()),
        "suitability_counts": valid_df["suitability"].value_counts().to_dict(),
    }
    return valid_df, stats


def CANONICAL_COLUMNS_inv(key: str) -> str:
    for original, canonical in CANONICAL_COLUMNS.items():
        if canonical == key:
            return original
    return key


def _derive_locality(row) -> str:
    loc = row.get("location_input")
    if isinstance(loc, str) and "," in loc:
        return loc.split(",")[0].strip()
    return "Unassigned"


def store_dataset(
    db: Session, df: pd.DataFrame, stats: Dict[str, Any], filename: str, sheet: str
) -> Dataset:
    for ds in db.query(Dataset).all():
        db.delete(ds)
    db.flush()

    dataset = Dataset(
        filename=filename,
        sheet_name=sheet,
        rows_total=stats["total_rows"],
        rows_valid=stats["valid_rows"],
        rows_invalid=stats["invalid_rows"],
        missing_values=stats["missing_values"],
        duplicate_records=stats["duplicate_records"],
        localities_count=len(stats["localities"]),
        notes=f"Synthetic demo dataset flag: {', '.join(stats['data_types'])}",
        validation_log=stats,
        is_active=1,
    )
    db.add(dataset)
    db.flush()

    for _, row in df.iterrows():
        db.add(
            RooftopAnalysis(
                dataset_id=dataset.id,
                source_row=int(row["source_row"]),
                location_input=row.get("location_input"),
                rooftop_selection=row.get("rooftop_selection"),
                latitude=float(row["latitude"]),
                longitude=float(row["longitude"]),
                locality=row.get("locality"),
                rooftop_area_m2=float(row["rooftop_area_m2"]),
                usable_rooftop_area_m2=float(row["usable_rooftop_area_m2"]),
                recommended_panels=int(row["recommended_panels"]),
                system_capacity_kw=float(row["system_capacity_kw"]),
                annual_generation_kwh=float(row["annual_generation_kwh"]),
                installation_cost_inr=float(row["installation_cost_inr"]),
                annual_savings_inr=float(row["annual_savings_inr"]),
                payback_period_years=float(row["payback_period_years"]),
                suitability=row.get("suitability"),
                data_type=row.get("data_type"),
            )
        )
    db.commit()
    return dataset


def load_file(db: Session, path: str, filename: str = None) -> Dict[str, Any]:
    filename = filename or os.path.basename(path)
    raw, sheet, other = read_workbook(path)
    df, stats = validate_and_clean(raw)
    dataset = store_dataset(db, df, stats, filename, sheet)
    stats["dataset_id"] = dataset.id
    stats["sheet_name"] = sheet
    stats["other_sheets"] = other
    stats["filename"] = filename
    return stats


def load_default_dataset(db: Session) -> Dict[str, Any]:
    if not os.path.exists(DEFAULT_DATASET):
        raise FileNotFoundError(DEFAULT_DATASET)
    return load_file(db, DEFAULT_DATASET)
