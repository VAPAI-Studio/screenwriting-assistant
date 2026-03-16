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
    """Initialize the database connection and apply any pending migrations."""
    from .services.db_migrator import run_migrations
    run_migrations(engine)