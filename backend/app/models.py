from datetime import datetime

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(300), nullable=False)
    sheet_name = Column(String(120))
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    rows_total = Column(Integer, default=0)
    rows_valid = Column(Integer, default=0)
    rows_invalid = Column(Integer, default=0)
    missing_values = Column(Integer, default=0)
    duplicate_records = Column(Integer, default=0)
    localities_count = Column(Integer, default=0)
    notes = Column(Text, default="")
    validation_log = Column(JSON, default=dict)
    is_active = Column(Integer, default=1)

    rooftops = relationship(
        "RooftopAnalysis", back_populates="dataset", cascade="all, delete-orphan"
    )


class RooftopAnalysis(Base):
    __tablename__ = "rooftop_analysis"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), index=True)
    source_row = Column(Integer)
    location_input = Column(String(300))
    rooftop_selection = Column(String(120))
    latitude = Column(Float)
    longitude = Column(Float)
    locality = Column(String(120), index=True)
    rooftop_area_m2 = Column(Float)
    usable_rooftop_area_m2 = Column(Float)
    recommended_panels = Column(Integer)
    system_capacity_kw = Column(Float)
    annual_generation_kwh = Column(Float)
    installation_cost_inr = Column(Float)
    annual_savings_inr = Column(Float)
    payback_period_years = Column(Float)
    suitability = Column(String(20), index=True)
    data_type = Column(String(40))
    spi = Column(Float)
    spi_breakdown = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    dataset = relationship("Dataset", back_populates="rooftops")


Index("ix_rooftop_analysis_latitude", RooftopAnalysis.latitude)
Index("ix_rooftop_analysis_longitude", RooftopAnalysis.longitude)


class Locality(Base):
    __tablename__ = "localities"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), index=True)
    name = Column(String(120), index=True)
    rooftop_count = Column(Integer, default=0)
    total_rooftop_area_m2 = Column(Float, default=0)
    total_usable_area_m2 = Column(Float, default=0)
    total_panels = Column(Integer, default=0)
    total_capacity_kw = Column(Float, default=0)
    total_generation_kwh = Column(Float, default=0)
    total_cost_inr = Column(Float, default=0)
    total_savings_inr = Column(Float, default=0)
    avg_payback_years = Column(Float, default=0)
    high_count = Column(Integer, default=0)
    medium_count = Column(Integer, default=0)
    low_count = Column(Integer, default=0)
    spi = Column(Float, default=0)
    spi_breakdown = Column(JSON, default=dict)
    centroid_lat = Column(Float)
    centroid_lon = Column(Float)
    why_text = Column(Text, default="")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PlanningScenario(Base):
    __tablename__ = "planning_scenarios"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120))
    budget_inr = Column(Float)
    min_spi = Column(Float, default=0)
    max_payback_years = Column(Float, default=100)
    min_capacity_kw = Column(Float, default=0)
    locality = Column(String(120))
    result = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class DataSource(Base):
    __tablename__ = "data_sources"

    id = Column(Integer, primary_key=True, index=True)
    dataset = Column(String(200))
    source = Column(String(300))
    purpose = Column(String(400))
    fields_used = Column(String(400))
    access_date = Column(String(40))
    license = Column(String(200))
    classification = Column(String(60))


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300))
    filename = Column(String(300))
    summary = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class AssistantQuery(Base):
    __tablename__ = "assistant_queries"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text)
    answer = Column(Text)
    mode = Column(String(40))
    sources = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
