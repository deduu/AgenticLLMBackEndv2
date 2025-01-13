import pandas as pd
from sqlalchemy import (
    Column, Integer, Float, DateTime, String, UniqueConstraint, func, select
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import asyncio
import contextlib
from typing import AsyncIterator, Dict, Any, List, Tuple, Optional
import os
import logging
from dateutil.parser import parse
from charset_normalizer import from_path

# ----------------------- Configuration ----------------------- #

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the base for declarative models
Base = declarative_base()

# --------------------- Database Model --------------------- #

class EmployeeData(Base):
    __tablename__ = 'employee_data'
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, nullable=False, unique=True)
    age = Column(Float, nullable=False)
    length_of_service = Column(Float, nullable=True)
    retired = Column(String(5), nullable=True)
    distance_from_home = Column(Float, nullable=True)
    engagement_score = Column(Float, nullable=True)
    satisfaction_score = Column(Float, nullable=True)
    salary_last_year = Column(Float, nullable=True)
    salary_this_year = Column(Float, nullable=True)
    salary_hike_since_last_year = Column(Float, nullable=True)

# --------------------- Utility Functions --------------------- #

def detect_encoding(file_path: str) -> str:
    """
    Detect the encoding of a file using charset-normalizer.
    """
    try:
        result = from_path(file_path).best()
        if result:
            encoding = result.encoding
            logger.info(f"Detected encoding '{encoding}' for file '{file_path}'.")
            return encoding
    except Exception as e:
        logger.error(f"Failed to detect encoding for file '{file_path}': {e}")
    return 'utf-8'

# --------------------- Database Management --------------------- #

class DatabaseSessionManager:
    """
    Manages asynchronous database sessions.
    """
    def __init__(self, sessionmaker, engine):
        self.sessionmaker = sessionmaker
        self.engine = engine

    async def close(self):
        if self.engine:
            await self.engine.dispose()

    @contextlib.asynccontextmanager
    async def create_session(self) -> AsyncIterator[AsyncSession]:
        session = self.sessionmaker()
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Session rollback due to error: {e}")
            raise
        finally:
            await session.close()

database_sessions: Dict[str, Dict[str, Any]] = {}

async def setup_database_session(db_file_path: str, db_identifier: str):
    """
    Sets up the asynchronous SQLite database session.
    """
    db_url = f"sqlite+aiosqlite:///{db_file_path}"
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    session_manager = DatabaseSessionManager(async_session, engine)

    # Store session manager
    database_sessions[db_identifier] = {
        'sessionmaker': async_session,
        'engine': engine,
        'session_manager': session_manager
    }
    logger.info(f"Database session for '{db_identifier}' set up.")

async def import_csv_to_database(file_path: str, db: AsyncSession, engine):
    """
    Imports CSV data into the database, ensuring unique records for employee_id.
    """
    try:
        # Detect encoding
        encoding = detect_encoding(file_path)
        data = pd.read_csv(file_path, encoding=encoding)
        logger.info(f"DataFrame columns after reading CSV: {list(data.columns)}")

        # Parse date columns if any
        for col in data.columns:
            if 'date' in col.lower():
                data[col] = pd.to_datetime(data[col], errors='coerce')

        # Reflect the table by running metadata.create_all
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info(f"Database tables created/refreshed.")

        # Map CSV columns to model fields
        column_mapping = {
            'EmployeeID': 'employee_id',
            'Age': 'age',
            'LengthOfService': 'length_of_service',
            'Retired': 'retired',
            'DistanceFromHome': 'distance_from_home',
            'EngagementScore': 'engagement_score',
            'SatisfactionScore': 'satisfaction_score',
            'SalaryLastYear': 'salary_last_year',
            'SalaryThisYear': 'salary_this_year',
            'SalaryHikeSinceLastYear': 'salary_hike_since_last_year',
        }

        # Rename columns to match model fields
        data.rename(columns=column_mapping, inplace=True)

        # Filter out duplicates based on employee_id
       # Filter out duplicates based on employee_id
        existing_ids = set((await db.execute(select(EmployeeData.employee_id))).scalars())
        new_records = data[~data['employee_id'].isin(existing_ids)].to_dict(orient="records")


        # Bulk insert new records
        objects = [EmployeeData(**row) for row in new_records]
        db.add_all(objects)
        await db.commit()
        logger.info(f"Inserted {len(objects)} records into the database.")
    except Exception as e:
        await db.rollback()
        logger.error(f"Error importing CSV '{file_path}': {e}")



@contextlib.asynccontextmanager
async def get_session(db_identifier: str) -> AsyncIterator[AsyncSession]:
    """
    Async context manager to get a session for a specific database identifier.
    """
    session_info = database_sessions.get(db_identifier)
    if session_info is None:
        raise ValueError(f"No session found for identifier '{db_identifier}'")
    session_manager: DatabaseSessionManager = session_info['session_manager']
    async with session_manager.create_session() as session:
        yield session

# --------------------- Query Functions --------------------- #

async def compute_metrics(db: AsyncSession) -> Dict[str, Any]:
    """
    Compute required metrics.
    """
    results = {}
    try:
        # Average age
        avg_age = (await db.execute(select(func.avg(EmployeeData.age)))).scalar()
        results['Average Age'] = avg_age

        # Average length of service
        avg_length_of_service = (await db.execute(select(func.avg(EmployeeData.length_of_service)))).scalar()
        results['Average Length of Service'] = avg_length_of_service

        # Retirement rate
        total_employees = (await db.execute(select(func.count(EmployeeData.id)))).scalar()
        retired_employees = (await db.execute(select(func.count(EmployeeData.id)).where(EmployeeData.retired == 'True'))).scalar()
        results['Retirement Rate'] = (retired_employees / total_employees) if total_employees else 0

        # Average distance from home
        avg_distance = (await db.execute(select(func.avg(EmployeeData.distance_from_home)))).scalar()
        results['Average Distance from Home'] = avg_distance

        # Engagement rate
        engagement_norm = 3.0  # Example norm value
        engaged_employees = (await db.execute(select(func.count(EmployeeData.id)).where(EmployeeData.engagement_score > engagement_norm))).scalar()
        results['Engagement Rate'] = (engaged_employees / total_employees) if total_employees else 0

        # Satisfaction rate
        satisfied_employees = (await db.execute(select(func.count(EmployeeData.id)).where(EmployeeData.satisfaction_score > 3.0))).scalar()
        results['Satisfaction Rate'] = (satisfied_employees / total_employees) if total_employees else 0

        # Salary hike since last year
        avg_salary_hike = (await db.execute(select(func.avg(EmployeeData.salary_hike_since_last_year)))).scalar()
        results['Average Salary Hike'] = avg_salary_hike

    except Exception as e:
        logger.error(f"Error computing metrics: {e}")

    return results


# --------------------- Query Functions --------------------- #

from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Optional, Any

# --------------------- Query Functions --------------------- #

async def average_metrics(column, db: AsyncSession, variable:str, unit: str) -> Dict[str, Optional[Any]]:
    """
    General helper function to calculate average, median, min, and max for a given column.
    Compatible with SQLite.
    
    Args:
        column: The column to perform calculations on.
        db: The database session.
        unit: The unit of the metric.
        
    Returns:
        A dictionary containing the unit and calculated statistics.
    """
    try:
        # Calculate average, min, and max
        stats_query = select(
            func.avg(column).label("average"),
            func.min(column).label("minimum"),
            func.max(column).label("maximum"),
        )
        stats_result = await db.execute(stats_query)
        stats = stats_result.mappings().first()

        # Calculate median
        count_query = select(func.count(column))
        total_count = (await db.execute(count_query)).scalar()

        if total_count == 0:
            median = None
        else:
            median_offset = (total_count - 1) // 2
            median_query = (
                select(column)
                .order_by(column)
                .limit(1)
                .offset(median_offset)
            )
            median_result = await db.execute(median_query)
            median = median_result.scalar()

        return {
            "metric": variable,
            "unit": unit,
            "average": stats["average"],
            "median": median,
            "min": stats["minimum"],
            "max": stats["maximum"],
        }
    except Exception as e:
        logger.error(f"Error calculating metrics for column {column}: {e}")
        return {"metric": variable, "unit": unit, "average": None, "median": None, "min": None, "max": None}


async def average_age(db: AsyncSession) -> Dict[str, Optional[Any]]:
    """
    Calculates average, median, min, and max for the age of employees.
    """
    return await average_metrics(EmployeeData.age, db, "Age","years")


async def average_length_of_service(db: AsyncSession) -> Dict[str, Optional[Any]]:
    """
    Calculates average, median, min, and max for the length of service of employees.
    """
    return await average_metrics(EmployeeData.length_of_service, db, "Length of Service", "years")


async def average_distance_from_home(db: AsyncSession) -> Dict[str, Optional[Any]]:
    """
    Calculates average, median, min, and max for the distance from home of employees.
    """
    return await average_metrics(EmployeeData.distance_from_home, db, "Distance from Home", "km")


async def average_salary_hike_since_last_year(db: AsyncSession) -> Dict[str, Optional[Any]]:
    """
    Calculates average, median, min, and max for the salary hike since last year.
    """
    return await average_metrics(EmployeeData.salary_hike_since_last_year, db, "Salary Hike since last year", "percentage")


async def retirement_rate(db: AsyncSession) -> Dict[str, Optional[Any]]:
    """
    Calculates retirement rate (percentage of employees retired).
    """
    try:
        total_employees = (await db.execute(select(func.count(EmployeeData.id)))).scalar()
        retired_employees = (await db.execute(
            select(func.count(EmployeeData.id)).where(EmployeeData.retired == 'True')
        )).scalar()

        rate = (retired_employees / total_employees) * 100 if total_employees else 0

        return {
            "metric": "Retirement Rate",
            "unit": "%",
            "rate": rate,
            "total_employees": total_employees,
            "retired_employees": retired_employees,
        }
    except Exception as e:
        logger.error(f"Error calculating retirement rate: {e}")
        return {"metric": "Retirement Rate", "unit": "%", "rate": None, "total_employees": None, "retired_employees": None}


async def engagement_rate(db: AsyncSession, engagement_norm: float = 3.0) -> Dict[str, Optional[Any]]:
    """
    Calculates engagement rate (percentage of employees above the engagement threshold).
    """
    try:
        total_employees = (await db.execute(select(func.count(EmployeeData.id)))).scalar()
        engaged_employees = (await db.execute(
            select(func.count(EmployeeData.id)).where(EmployeeData.engagement_score > engagement_norm)
        )).scalar()

        rate = (engaged_employees / total_employees) * 100 if total_employees else 0

        return {
            "metric": "Engagement Rate",
            "unit": "%",
            "rate": rate,
            "total_employees": total_employees,
            "engaged_employees": engaged_employees,
        }
    except Exception as e:
        logger.error(f"Error calculating engagement rate: {e}")
        return {"metric": "Engagement Rate", "unit": "%", "rate": None, "total_employees": None, "engaged_employees": None}


async def satisfaction_rate(db: AsyncSession, satisfaction_threshold: float = 3.0) -> Dict[str, Optional[Any]]:
    """
    Calculates satisfaction rate (percentage of employees above the satisfaction threshold).
    """
    try:
        total_employees = (await db.execute(select(func.count(EmployeeData.id)))).scalar()
        satisfied_employees = (await db.execute(
            select(func.count(EmployeeData.id)).where(EmployeeData.satisfaction_score > satisfaction_threshold)
        )).scalar()

        rate = round((satisfied_employees / total_employees) * 100, 2) if total_employees else 0

        return {
            "metric": "Satisfaction Rate",
            "unit": "%",
            "rate": rate,
            "total_employees": total_employees,
            "satisfied_employees": satisfied_employees,
        }
    except Exception as e:
        logger.error(f"Error calculating satisfaction rate: {e}")
        return {"metric": "Satisfaction Rate", "unit": "%", "rate": None, "total_employees": None, "satisfied_employees": None}



# --------------------- Main Execution --------------------- #
db_identifier = "employee_db"
async def main():
    csv_file_path = "synthetic_data.csv"
    db_file_path = f"{db_identifier}.db"

    # Set up database session
    await setup_database_session(db_file_path, db_identifier)

    # Import data
    session_info = database_sessions[db_identifier]
    session_manager: DatabaseSessionManager = session_info['session_manager']
    async with session_manager.create_session() as db:
        engine = session_info['engine']
        await import_csv_to_database(csv_file_path, db, engine)

        # Compute metrics
        metrics = await compute_all_metrics(db)
        for key, value in metrics.items():
            logger.info(f"{key}: {value}")
async def compute_all_metrics(db: AsyncSession) -> Dict[str, Any]:
    """
    Computes and combines all employee metrics into a single dictionary.
    """
    metrics = {}
    try:
        metrics["Age"] = await average_age(db)
        metrics["Length of Service"] = await average_length_of_service(db)
        metrics["Distance from Home"] = await average_distance_from_home(db)
        metrics["Salary Hike"] = await average_salary_hike_since_last_year(db)
        metrics["Retirement Rate"] = await retirement_rate(db)
        metrics["Engagement Rate"] = await engagement_rate(db)
        metrics["Satisfaction Rate"] = await satisfaction_rate(db)
    except Exception as e:
        logger.error(f"Error computing all metrics: {e}")
    return metrics


if __name__ == "__main__":
    asyncio.run(main())
