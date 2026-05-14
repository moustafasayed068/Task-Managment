import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.db.base_db import Base
from app.db.session_db import engine

print("Dropping all tables to clear dummy data...")
try:
    Base.metadata.drop_all(bind=engine)
    print("Tables dropped successfully.")
except Exception as e:
    print(f"Error dropping tables: {e}")

print("Recreating clean tables...")
try:
    Base.metadata.create_all(bind=engine)
    print("Tables recreated successfully.")
except Exception as e:
    print(f"Error creating tables: {e}")

print("Database reset complete! Please refresh the frontend.")
