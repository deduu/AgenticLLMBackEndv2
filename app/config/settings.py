# app/config/settings.py

import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    POSTGRES_DB_URL: str = os.getenv("POSTGRES_DB_URL")
    SQLITE_DB_URL: str = os.getenv("SQLITE_DB_URL")
    # Add other settings as needed

settings = Settings()
