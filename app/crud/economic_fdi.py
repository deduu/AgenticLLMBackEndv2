import pandas as pd
from sqlalchemy import (
    Column, Integer, Float, String, UniqueConstraint, select, func, insert
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import asyncio
import contextlib
import logging
from typing import AsyncIterator, Dict, List, Optional, Any

# ----------------------- Configuration ----------------------- #

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
Base = declarative_base()

db_identifier = "fdi"
csv_file_path = "fdi_new.csv"


# --------------------- Database Model --------------------- #

class EconomicSectorData(Base):
    __tablename__ = 'economic_sector_data'
    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False)
    quarter = Column(String(2), nullable=False)
    sector = Column(String(255), nullable=False)
    country = Column(String(255), nullable=False)
    value = Column(Float, nullable=True)

    __table_args__ = (
    UniqueConstraint('year', 'quarter', 'sector', 'country', name='uq_economic_sector'),
)


# --------------------- Database Management --------------------- #

class DatabaseSessionManager:
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
    db_url = f"sqlite+aiosqlite:///{db_file_path}"
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    session_manager = DatabaseSessionManager(async_session, engine)

    database_sessions[db_identifier] = {
        'sessionmaker': async_session,
        'engine': engine,
        'session_manager': session_manager
    }
    logger.info(f"Database session for '{db_identifier}' set up.")

async def initialize_fdi_database_sessions():
    """
    Initializes database sessions for all CSV files and imports their data.
    """
 

    db_file_path = f"{db_identifier}.db"  # SQLite database file
    await setup_database_session(db_file_path, db_identifier)

    # Import data
    session_info = database_sessions[db_identifier]
    session_manager: DatabaseSessionManager = session_info['session_manager']
    async with session_manager.create_session() as db:
        engine = session_info['engine']
        await import_csv_to_database(csv_file_path, db, engine)

from sqlalchemy.dialects.sqlite import insert

async def import_csv_to_database(file_path: str, db: AsyncSession, engine):
    try:
        # Load the CSV file
        data = pd.read_csv(file_path)
        logger.info(f"DataFrame columns after reading CSV: {list(data.columns)}")

        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created/refreshed.")

        # Rename and preprocess columns
        column_mapping = {
            'Year': 'year',
            'Quarter': 'quarter',
            'Sector': 'sector',
            'Country': 'country',
            'Value': 'value',
        }
        data.rename(columns=column_mapping, inplace=True)
        data['value'] = pd.to_numeric(data['value'], errors='coerce')

        # Convert the DataFrame to records
        new_records = data.to_dict(orient="records")

        # Insert records using on_conflict_do_nothing
        stmt = insert(EconomicSectorData).values(new_records)
        stmt = stmt.on_conflict_do_nothing(index_elements=['year', 'quarter', 'sector', 'country'])
        await db.execute(stmt)
        await db.commit()

        logger.info(f"Inserted {len(new_records)} records into the database (skipping duplicates).")
    except Exception as e:
        await db.rollback()
        logger.error(f"Error importing CSV '{file_path}': {e}")


@contextlib.asynccontextmanager
async def get_session(db_identifier: str) -> AsyncIterator[AsyncSession]:
    session_info = database_sessions.get(db_identifier)
    if session_info is None:
        raise ValueError(f"No session found for identifier '{db_identifier}'")
    session_manager: DatabaseSessionManager = session_info['session_manager']
    async with session_manager.create_session() as session:
        yield session

async def add_unit_to_values(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for record in results:
        # Add the unit to aggregated values
        if 'total_value' in record:
            record['total_value'] = f"{record['total_value']} Millions USD"
        # Add the unit to individual values
        if 'value' in record:
            record['value'] = f"{record['value']} Millions USD"
    return results

def add_unit_to_mappings(results: List[str]) ->List[Dict[str, Any]]:
    """
    Convert SQLAlchemy RowMapping results into dictionaries and add units to the 'total_value' field.

    Args:
        results (List[RowMapping]): The list of results returned by SQLAlchemy.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries with the modified 'total_value'.
    """
    return [
        {**dict(record), "total_value": f"{round(record['total_value'],2)} Millions USD"}
        for record in results
    ]
def convert_row_mapping_to_dict(rows):
    return [dict(row) for row in rows]


# --------------------- Query Functions --------------------- #
async def trends_in_fdi_value(
    db: AsyncSession, 
    start_year:int, 
    end_year: int, 
    countries: Optional[List[str]] = None
) ->List[Dict[str, Any]]:
    """
    Query total values grouped by sector, country, and year between start and end year.

    Args:
        db (AsyncSession): Database session.
        start_year (int): The start year for the query.
        end_year (int): The end year for the query.
        countries (Optional[List[str]]): List of countries to filter by (optional).

    Returns:
        List[Dict[str, Any]]: Query results with total values grouped by sector, country, and year.
    """
    stmt = (
        select(
            EconomicSectorData.sector,
            EconomicSectorData.country,
            EconomicSectorData.year,
            func.sum(EconomicSectorData.value).label("total_value")
        )
        .where(EconomicSectorData.year.between(start_year, end_year))
        .group_by(
            EconomicSectorData.sector,
            EconomicSectorData.country,
            EconomicSectorData.year
        )
        .order_by(EconomicSectorData.sector, EconomicSectorData.country, EconomicSectorData.year)
    )
    
    if countries:
        stmt = stmt.where(EconomicSectorData.country.in_(countries))

    results = await db.execute(stmt)
    response = add_unit_to_mappings(convert_row_mapping_to_dict(results.mappings().all()))
    logger.info(f"trends_in_fdi_value response: {response}")
    return response

async def trends_in_value_by_quarter(
    db: AsyncSession,
    year: Optional[int] = None,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
    quarter: Optional[str] = None,
    country: Optional[str] = None,
    sector: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve trends in value filtered by year(s), quarter, country, and sector.

    Args:
        db (AsyncSession): Database session.
        year (Optional[int]): Specific year to filter by (optional).
        start_year (Optional[int]): Start of the year range to filter by (optional).
        end_year (Optional[int]): End of the year range to filter by (optional).
        quarter (Optional[str]): Specific quarter to filter by (e.g., 'Q1') (optional).
        country (Optional[str]): Country name to filter by (optional).
        sector (Optional[str]): Sector name to filter by (optional).

    Returns:
        List[Dict[str, Any]]: Filtered trends in economic values.
    """
    stmt = (
        select(
            EconomicSectorData.sector,
            EconomicSectorData.year,
            EconomicSectorData.quarter,
            func.sum(EconomicSectorData.value).label("total_value")
        )
        .group_by(
            EconomicSectorData.sector,
            EconomicSectorData.year,
            EconomicSectorData.quarter
        )
        .order_by(EconomicSectorData.sector, EconomicSectorData.year, EconomicSectorData.quarter)
    )

    # Apply filters dynamically
    if year:
        stmt = stmt.where(EconomicSectorData.year == year)
    if start_year and end_year:
        stmt = stmt.where(EconomicSectorData.year.between(start_year, end_year))
    elif start_year:
        stmt = stmt.where(EconomicSectorData.year >= start_year)
    elif end_year:
        stmt = stmt.where(EconomicSectorData.year <= end_year)
    if quarter:
        stmt = stmt.where(EconomicSectorData.quarter == quarter)
    if country:
        stmt = stmt.where(EconomicSectorData.country == country)
    if sector:
        stmt = stmt.where(EconomicSectorData.sector == sector)

    results = await db.execute(stmt)
    return add_unit_to_mappings(convert_row_mapping_to_dict(results.mappings().all()))

# Query total value by country with quarterly breakdown
async def total_value_by_country_by_quarter(
    db: AsyncSession, 
    year: Optional[int] = None, 
    start_year: Optional[int] = None, 
    end_year: Optional[int] = None, 
    quarter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Calculate total value grouped by country and quarter.

    Args:
        db (AsyncSession): Database session.
        year (Optional[int]): Specific year to filter by (optional).
        start_year (Optional[int]): Start of the year range to filter by (optional).
        end_year (Optional[int]): End of the year range to filter by (optional).
        quarter (Optional[str]): Specific quarter to filter by (optional).

    Returns:
        List[Dict[str, Any]]: Total value grouped by country and quarter.
    """
    stmt = (
        select(
            EconomicSectorData.country,
            EconomicSectorData.year,
            EconomicSectorData.quarter,
            func.sum(EconomicSectorData.value).label("total_value")
        )
        .group_by(
            EconomicSectorData.country,
            EconomicSectorData.year,
            EconomicSectorData.quarter
        )
        .order_by(EconomicSectorData.country, EconomicSectorData.year, EconomicSectorData.quarter)
    )

    if year:
        stmt = stmt.where(EconomicSectorData.year == year)
    if start_year and end_year:
        stmt = stmt.where(EconomicSectorData.year.between(start_year, end_year))
    elif start_year:
        stmt = stmt.where(EconomicSectorData.year >= start_year)
    elif end_year:
        stmt = stmt.where(EconomicSectorData.year <= end_year)
    if quarter:
        stmt = stmt.where(EconomicSectorData.quarter == quarter)

    results = await db.execute(stmt)
    return add_unit_to_mappings(convert_row_mapping_to_dict(results.mappings().all()))

# Query total value by sector with quarterly breakdown
async def total_value_by_sector_by_quarter(
    db: AsyncSession, 
    year: Optional[int] = None, 
    start_year: Optional[int] = None, 
    end_year: Optional[int] = None, 
    quarter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Calculate total value grouped by sector and quarter.

    Args:
        db (AsyncSession): Database session.
        year (Optional[int]): Specific year to filter by (optional).
        start_year (Optional[int]): Start of the year range to filter by (optional).
        end_year (Optional[int]): End of the year range to filter by (optional).
        quarter (Optional[str]): Specific quarter to filter by (optional).

    Returns:
        List[Dict[str, Any]]: Total value grouped by sector and quarter.
    """
    stmt = (
        select(
            EconomicSectorData.sector,
            EconomicSectorData.year,
            EconomicSectorData.quarter,
            func.sum(EconomicSectorData.value).label("total_value")
        )
        .group_by(
            EconomicSectorData.sector,
            EconomicSectorData.year,
            EconomicSectorData.quarter
        )
        .order_by(EconomicSectorData.sector, EconomicSectorData.year, EconomicSectorData.quarter)
    )

    if year:
        stmt = stmt.where(EconomicSectorData.year == year)
    if start_year and end_year:
        stmt = stmt.where(EconomicSectorData.year.between(start_year, end_year))
    elif start_year:
        stmt = stmt.where(EconomicSectorData.year >= start_year)
    elif end_year:
        stmt = stmt.where(EconomicSectorData.year <= end_year)
    if quarter:
        stmt = stmt.where(EconomicSectorData.quarter == quarter)

    results = await db.execute(stmt)
    return add_unit_to_mappings(convert_row_mapping_to_dict(results.mappings().all()))

# async def total_fdi_value_by_country(db: AsyncSession, year: int) -> List[Dict[str, Any]]:
#     stmt = (
#         select(EconomicSectorData.country, func.sum(EconomicSectorData.value).label("total_value"))
#         .where(EconomicSectorData.year == year)
#         .group_by(EconomicSectorData.country)
#         .order_by(func.sum(EconomicSectorData.value).desc())
#     )
#     results = await db.execute(stmt)
#     return results.mappings().all()

async def total_fdi_value_by_country(
    db: AsyncSession, 
    start_year: Optional[int] = None, 
    end_year: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Calculate total FDI value grouped by country, filtered by a range of years.

    Args:
        db (AsyncSession): Database session.
        start_year (Optional[int]): Start of the year range to filter by (optional).
        end_year (Optional[int]): End of the year range to filter by (optional).

    Returns:
        List[Dict[str, Any]]: Total FDI value grouped by country.
    """
    stmt = (
        select(
            EconomicSectorData.country,
            func.sum(EconomicSectorData.value).label("total_value")
        )
        .group_by(EconomicSectorData.country)
        .order_by(func.sum(EconomicSectorData.value).desc())
    )

    # Apply year range filters
    if start_year and end_year:
        stmt = stmt.where(EconomicSectorData.year.between(start_year, end_year))
    elif start_year:
        stmt = stmt.where(EconomicSectorData.year >= start_year)
    elif end_year:
        stmt = stmt.where(EconomicSectorData.year <= end_year)

    results = await db.execute(stmt)
    response = add_unit_to_mappings(convert_row_mapping_to_dict(results.mappings().all()))
    print(f"total_fdi_value_by_country results: {response}")
    return response
    
async def total_fdi_value_by_sector(db: AsyncSession) -> List[Dict[str, Any]]:
    stmt = (
        select(EconomicSectorData.sector, func.sum(EconomicSectorData.value).label("total_value"))
        .group_by(EconomicSectorData.sector)
        .order_by(func.sum(EconomicSectorData.value).desc())
    )
    results = await db.execute(stmt)
    return add_unit_to_mappings(convert_row_mapping_to_dict(results.mappings().all()))

async def dynamic_query(db: AsyncSession, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    stmt = select(EconomicSectorData)
    for key, value in filters.items():
        stmt = stmt.where(getattr(EconomicSectorData, key) == value)
    results = await db.execute(stmt)
    return results.mappings().all()

# --------------------- Insertion Functions --------------------- #

from sqlalchemy.dialects.sqlite import insert

async def insert_economic_sector_record(db: AsyncSession, record: Dict[str, Any]) -> None:
    try:
        stmt = insert(EconomicSectorData).values(**record)
        stmt = stmt.on_conflict_do_update(
            index_elements=['year', 'quarter', 'sector', 'country'],  # Unique constraint fields
            set_={'value': stmt.excluded.value}  # Fields to update
        )
        await db.execute(stmt)
        await db.commit()
        logger.info(f"Inserted/Updated record: {record}")
    except Exception as e:
        await db.rollback()
        logger.error(f"Error inserting/updating record {record}: {e}")


async def insert_economic_sector_records(db: AsyncSession, records: List[Dict[str, Any]]) -> None:
    """
    Inserts multiple economic sector records into the database.
    If records with the same unique keys exist, it updates the 'value'.
    """
    try:
        stmt = insert(EconomicSectorData).values(records)
        stmt = stmt.on_conflict_do_update(
            index_elements=['year', 'quarter', 'sector', 'country'],
            set_={'value': stmt.excluded.value}
        )
        await db.execute(stmt)
        await db.commit()
        logger.info(f"Inserted/Updated {len(records)} records.")
    except Exception as e:
        await db.rollback()
        logger.error(f"Error inserting/updating records: {e}")

# --------------------- Main Execution --------------------- #

async def main():
    db_file_path = f"{db_identifier}.db"
    await setup_database_session(db_file_path, db_identifier)

    session_info = database_sessions[db_identifier]
    session_manager: DatabaseSessionManager = session_info['session_manager']
    async with session_manager.create_session() as db:
        engine = session_info['engine']
        await import_csv_to_database(csv_file_path, db, engine)

        # Example queries
        trends = await trends_in_value_by_quarter(db, start_year=2023, end_year=2023)
        logger.info(f"Trends in value: {trends}")

        total_value = await total_value_by_country(db, 2023)
        logger.info(f"Trends in value for Singapore: {total_value}")

        # sector_totals = await  trends_in_value_filtered(db, 2023, 2024, country="Singapura", sector="Pendidikan")
        # logger.info(f"Trendas in value for Singapore and Pendidikan: {sector_totals}")

        # # Example of inserting a single record
        # single_record = {
        #     'year': 2024,
        #     'quarter': 'Q1',
        #     'sector': 'Pendidikan',
        #     'country': 'Brunei Darussalam',
        #     'value': 5
        # }
        # await insert_economic_sector_record(db, single_record)

        # # Example of inserting multiple records
        # multiple_records = [
        #     {
        #         'year': 2023,
        #         'quarter': 'Q3',
        #         'sector': 'Pendidikan',
        #         'country': 'Kamboja',
        #         'value': -3
        #     },
        #     {
        #         'year': 2024,
        #         'quarter': 'Q2',
        #         'sector': 'Teknologi',
        #         'country': 'Singapore',
        #         'value': 10
        #     },
        #     # Add more records as needed
        # ]
        # await insert_economic_sector_records(db, multiple_records)

        # Verify insertions
        # all_records = await dynamic_query(db, {})
        # logger.info(f"All records in the database: {all_records}")

if __name__ == "__main__":
    asyncio.run(main())
