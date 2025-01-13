# app/db/models/employee_data.py
from sqlalchemy import (
    Column, Integer, Float, DateTime, String, UniqueConstraint, func, select
)
from app.db.base import Base

class EmployeeData(Base):
    __tablename__ = 'employee_data_sample'
    id = Column(Integer, primary_key=True, index=True)
    employeeid = Column(Integer, nullable=False, unique=True)
    age = Column(Integer, nullable=True)
    lengthofservice = Column(Float, nullable=True)
    retired = Column(String(10), nullable=True)  # Stored as 'True'/'False'
    distancefromhome = Column(Float, nullable=True)
    engagementscore = Column(Float, nullable=True)
    satisfactionscore = Column(Float, nullable=True)
    salarylastyear = Column(Float, nullable=True)
    salarythisyear = Column(Float, nullable=True)
    salaryhikesincelastyear = Column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint('employeeid', name='uq_employeeid'),
    )