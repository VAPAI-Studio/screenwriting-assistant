from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from .config import settings

# Create database engine
engine = create_engine(settings.DATABASE_URL)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize the database connection.

    Table creation is handled by the SQL migration at
    backend/migrations/init_db.sql, which is the single source of truth
    for the database schema. For future improvements, consider adopting
    Alembic for migration management.
    """
    with engine.connect() as conn:
        conn.execute(text("SELECT 1")) 