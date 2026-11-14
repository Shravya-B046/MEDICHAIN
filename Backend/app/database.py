import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)

# Determine connect args depending on database dialect
connect_args = {}
database_url = settings.DATABASE_URL

if database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

# Create Synchronous SQLAlchemy 2.x Engine
try:
    engine = create_engine(
        database_url,
        connect_args=connect_args,
        pool_pre_ping=True,
    )
except Exception as e:
    logger.warning(
        f"Failed to connect to primary DATABASE_URL '{database_url}': {e}. "
        "Falling back to local SQLite demo database for offline testing."
    )
    fallback_url = "sqlite:///./medichain_demo.db"
    engine = create_engine(
        fallback_url,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )

# Synchronous SessionLocal factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Declarative Base for all ORM models
Base = declarative_base()


def get_db_session():
    """Context manager / direct getter for database sessions."""
    db = SessionLocal()
    try:
        return db
    finally:
        pass

