from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./finance_agent.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.models.db_models import ReportORM, ReportCitationORM

    Base.metadata.create_all(bind=engine)

    # Seed one demo report for the report page route.
    with SessionLocal() as db:
        existing = db.get(ReportORM, "demo-report-001")
        if existing:
            return

        demo = ReportORM(
            report_id="demo-report-001",
            ticker="AAPL",
            summary="Revenue growth moderated year-over-year while operating margin remained resilient.",
            key_findings=[
                "Services revenue increased faster than hardware segments.",
                "Operating cash flow remained strong despite higher capex.",
                "Risk factors expanded language around supply chain concentration.",
            ],
            generated_at=datetime.now(timezone.utc),
        )
        db.add(demo)
        db.flush()

        db.add_all(
            [
                ReportCitationORM(
                    report_id=demo.report_id,
                    source_title="Form 10-K",
                    section="Item 7 - Management Discussion and Analysis",
                    excerpt="Net sales in Services grew compared to the prior fiscal year.",
                ),
                ReportCitationORM(
                    report_id=demo.report_id,
                    source_title="Form 10-K",
                    section="Item 1A - Risk Factors",
                    excerpt="Disruptions in global supply chains may adversely impact results.",
                ),
            ]
        )
        db.commit()
