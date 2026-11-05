"""
SQLite persistence for OI snapshots and historical data.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from core.logger import logger
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    create_engine,
    Index,
    text,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from config.settings import DB_PATH, HISTORY_RETENTION_DAYS

Base = declarative_base()


class OISnapshotRow(Base):
    __tablename__ = "oi_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    stock = Column(String(32), nullable=False, index=True)
    security_id = Column(String(32), nullable=False, index=True)
    expiry = Column(String(16), nullable=False)
    strike = Column(Float, nullable=False)
    option_type = Column(String(4), nullable=False)
    ltp = Column(Float)
    oi = Column(Integer)
    volume = Column(Integer)
    turnover = Column(Float)

    __table_args__ = (
        Index("ix_sec_ts", "security_id", "timestamp"),
    )


class DatabaseManager:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def insert_snapshot(
        self,
        timestamp: datetime,
        stock: str,
        security_id: str,
        expiry: str,
        strike: float,
        option_type: str,
        ltp: float,
        oi: int,
        volume: int = 0,
        turnover: float = 0.0,
    ) -> None:
        session = self.Session()
        try:
            row = OISnapshotRow(
                timestamp=timestamp,
                stock=stock,
                security_id=str(security_id),
                expiry=expiry,
                strike=strike,
                option_type=option_type,
                ltp=ltp,
                oi=oi,
                volume=volume,
                turnover=turnover,
            )
            session.add(row)
            session.commit()
        except Exception as exc:
            session.rollback()
            logger.error(f"DB insert failed: {exc}")
        finally:
            session.close()

    def get_latest_oi(self, security_id: str) -> Optional[int]:
        session = self.Session()
        try:
            row = (
                session.query(OISnapshotRow)
                .filter(OISnapshotRow.security_id == str(security_id))
                .order_by(OISnapshotRow.timestamp.desc())
                .first()
            )
            return row.oi if row else None
        finally:
            session.close()

    def get_previous_day_close_oi(self, security_id: str) -> Optional[int]:
        """Best-effort previous trading day last snapshot."""
        session = self.Session()
        try:
            cutoff = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            row = (
                session.query(OISnapshotRow)
                .filter(
                    OISnapshotRow.security_id == str(security_id),
                    OISnapshotRow.timestamp < cutoff,
                )
                .order_by(OISnapshotRow.timestamp.desc())
                .first()
            )
            return row.oi if row else None
        finally:
            session.close()

    def purge_old(self, days: int = HISTORY_RETENTION_DAYS) -> int:
        session = self.Session()
        try:
            cutoff = datetime.now() - timedelta(days=days)
            deleted = (
                session.query(OISnapshotRow)
                .filter(OISnapshotRow.timestamp < cutoff)
                .delete()
            )
            session.commit()
            logger.info(f"Purged {deleted} old snapshot rows")
            return deleted
        except Exception as exc:
            session.rollback()
            logger.error(f"Purge failed: {exc}")
            return 0
        finally:
            session.close()
