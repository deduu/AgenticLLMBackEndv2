# app/services/data_importer.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import asyncio
import contextlib
from typing import AsyncIterator, Dict, Any, List, Tuple
import pandas as pd
from sqlalchemy import (
    Column, Integer, Float, DateTime, String, UniqueConstraint, func, select
)

async def import_csv_to_database(file_path: str, db: AsyncSession, model_class):
    """
    Generic function to import CSV data into a specified database table, avoiding duplicates based on primary key.

    Args:
        file_path: Path to the CSV file.
        db: The async database session.
        model_class: The ORM model class representing the database table.

    Returns:
        None
    """
    try:
        # Read CSV data
        data = pd.read_csv(file_path)

        # Retrieve existing primary key values to avoid duplicates
        primary_key_column = model_class.__table__.primary_key.columns.values()[0]
        existing_ids_result = await db.execute(select(getattr(model_class, primary_key_column.name)))
        existing_ids = set(row[0] for row in existing_ids_result.fetchall())

        # Filter out existing records
        data_to_insert = data[~data[primary_key_column.name].isin(existing_ids)]

        # Prepare ORM records
        records = [
            model_class(**row.to_dict())
            for _, row in data_to_insert.iterrows()
        ]

        # Bulk insert new records into the database
        db.add_all(records)
        await db.commit()
        print(f"Successfully inserted {len(records)} new records into the database.")

    except Exception as e:
        await db.rollback()
        print(f"Error inserting data: {e}")
