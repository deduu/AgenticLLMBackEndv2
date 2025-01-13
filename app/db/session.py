# app/db/session.py (updated)

import asyncio
import contextlib
import logging
from typing import AsyncIterator, Dict, Any, List
import pandas as pd
from sqlalchemy import (
    Column, Integer, Float, DateTime, String, UniqueConstraint, func, select
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from charset_normalizer import from_path
from dateutil.parser import parse
from app.db.base import Base

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
# Dictionary to hold multiple database sessions
database_sessions: Dict[str, Dict[str, Any]] = {}

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
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def setup_database_session(db_file_path: str, db_identifier: str):
    db_url = f"sqlite+aiosqlite:///{db_file_path}"
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    session_manager = DatabaseSessionManager(async_session, engine)

    # Store session manager
    database_sessions[db_identifier] = {
        'sessionmaker': async_session,
        'engine': engine,
        'session_manager': session_manager
    }
    logger.info(f"Database session for '{db_identifier}' set up.")
    return engine, async_session

async def init_db(engine, base=Base):
    try:
        async with engine.begin() as conn:
            logger.info("Creating tables...")
            await conn.run_sync(base.metadata.create_all)
            logger.info("Tables created successfully.")
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        raise e
    
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


async def import_csv_to_database(file_path: str, db: AsyncSession, engine, model):
    """
    Imports CSV data into the database for a given model, avoiding duplicates based on unique columns.
    """
    try:
        # Detect encoding
        encoding = detect_encoding(file_path)
        data = pd.read_csv(file_path, encoding=encoding)
        logger.info(f"DataFrame columns after reading CSV: {list(data.columns)}")
    except UnicodeDecodeError as ude:
        logger.error(f"Unicode decoding error with encoding '{encoding}': {ude}")
        # Attempt to read with 'latin1' as a fallback
        try:
            data = pd.read_csv(file_path, encoding='latin1')
            logger.info(f"Successfully read '{file_path}' with 'latin1' encoding as fallback.")
        except Exception as e:
            logger.error(f"Failed to read '{file_path}' with fallback encoding: {e}")
            await db.rollback()
            return
    except Exception as e:
        logger.error(f"Error reading CSV '{file_path}': {e}")
        await db.rollback()
        return

    try:
        # Parse date columns
        for col in data.columns:
            if 'date' in col.lower():
                data[col] = pd.to_datetime(data[col], errors='coerce')

        # Reflect the table by running metadata.create_all
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info(f"Database tables created/refreshed for '{model.__tablename__}'.")

        # Identify unique constraints
        unique_constraints = [constraint.columns.keys() for constraint in model.__table__.constraints if isinstance(constraint, UniqueConstraint)]
        if not unique_constraints:
            logger.warning(f"No unique constraints found for model '{model.__tablename__}'. Skipping duplicate check.")
            data_to_insert = data
        else:
            # Assuming single unique constraint for simplicity
            unique_columns = unique_constraints[0]
            query = select(*[getattr(model, col) for col in unique_columns])
            result = await db.execute(query)
            existing_unique = set(tuple(row) for row in result.fetchall())

            # Log existing unique records
            logger.info(f"Existing unique records in '{model.__tablename__}': {len(existing_unique)}")

            # Filter new records
            def is_new(row):
                key = tuple(row[col] for col in unique_columns)
                return key not in existing_unique

            data_to_insert = data[data.apply(is_new, axis=1)]

            # Log new records to insert
            logger.info(f"Number of new records to insert into '{model.__tablename__}': {len(data_to_insert)}")

        # Convert rows to model instances
        records = []
        for _, row in data_to_insert.iterrows():
            record_data = {}
            for column in data.columns:
                column_name = column.strip().replace(' ', '_').lower()
                value = row[column]
                if pd.isna(value):
                    value = None
                # Handle specific transformations
                if model.__tablename__ == 'employee_data_sample':
                    if column_name == 'retired':
                        value = str(value).strip().capitalize() if value is not None else None
                record_data[column_name] = value
            record = model(**record_data)
            records.append(record)

        # Bulk insert
        if records:
            db.add_all(records)
            await db.commit()
            logger.info(f"Inserted {len(records)} new records into '{model.__tablename__}' table.")
        else:
            logger.info(f"No new records to insert into '{model.__tablename__}' table.")

    except Exception as e:
        await db.rollback()
        logger.error(f"Error importing CSV '{file_path}': {e}")
# Dictionary to hold multiple database sessions
# database_sessions: Dict[str, DatabaseSessionManager] = {}
