#!/usr/bin/env python3
"""Database initialization script."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import init_db, engine
from sqlalchemy import text

def main():
    print("Initializing database...")
    init_db()
    print("Database initialized successfully!")

if __name__ == "__main__":
    main()
