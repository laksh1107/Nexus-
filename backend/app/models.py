from sqlalchemy import String, Text, Integer, Float, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from .database import Base
class Job(Base):
    __tablename__="jobs"
    id: Mapped[int]=mapped_column(primary_key=True)
    name: Mapped[str]=mapped_column(String(240),default="Uploaded log")
    source: Mapped[str]=mapped_column(String(40),default="upload")
    status: Mapped[str]=mapped_column(String(30),default="queued")
    total_logs: Mapped[int]=mapped_column(Integer,default=0)
    anomaly_count: Mapped[int]=mapped_column(Integer,default=0)
    incident_count: Mapped[int]=mapped_column(Integer,default=0)
    model_name: Mapped[str]=mapped_column(String(120),default="TF-IDF + Isolation Forest")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
    raw_text: Mapped[str]=mapped_column(Text,default="")
    result: Mapped[dict]=mapped_column(JSON,default=dict)
class Incident(Base):
    __tablename__="incidents"
    id: Mapped[int]=mapped_column(primary_key=True)
    job_id: Mapped[int]=mapped_column(Integer,index=True)
    title: Mapped[str]=mapped_column(String(240))
    severity: Mapped[str]=mapped_column(String(30))
    root_service: Mapped[str]=mapped_column(String(120))
    confidence_score: Mapped[float]=mapped_column(Float)
    evidence: Mapped[dict]=mapped_column(JSON,default=dict)
    recommendation: Mapped[str]=mapped_column(Text,default="")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
