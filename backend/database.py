import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# This finds the 'backend' folder regardless of where you run uvicorn from
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(BASE_DIR, ".env")

# Load it
load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv("DATABASE_URL")

# DEBUG PRINT: This will show up in your terminal
print(f"--- DEBUG: Looking for .env at: {env_path}")
print(f"--- DEBUG: DATABASE_URL found: {DATABASE_URL}")

if not DATABASE_URL:
    raise ValueError(f"Could not find DATABASE_URL. Is there a file at {env_path}?")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()