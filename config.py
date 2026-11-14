"""Load machine-specific settings from .env."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent
LIBRARY_ROOT = Path(os.environ["LIBRARY_PATH"]) if os.getenv("LIBRARY_PATH") else None
DB_PATH = PROJECT_ROOT / "data" / "library.duckdb"
SQL_REPORTS_DIR = PROJECT_ROOT / "sql" / "reports"
