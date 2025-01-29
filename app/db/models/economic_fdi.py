# app/db/models/economic_fdi.py
from sqlalchemy import (
    Column, Integer, Float, DateTime, String, UniqueConstraint, func, select
)
from app.db.base import Base

class EconomicSectorData(Base):
    __tablename__ = 'economic_sector_data'
    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False)
    quarter = Column(String(2), nullable=False)
    sector = Column(String(255), nullable=False)
    country = Column(String(255), nullable=False)
    value = Column(Float, nullable=True)

    ___table_args__ = (
    UniqueConstraint('year', 'quarter', 'sector', 'country', name='uq_economic_sector'),
)