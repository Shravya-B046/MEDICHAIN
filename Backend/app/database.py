import json
import logging
import socket
import urllib.request
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)

# Fallback DNS resolver for networks where local Wi-Fi router refuses cloud DNS queries
_orig_getaddrinfo = socket.getaddrinfo


def _fallback_getaddrinfo(host, port, *args, **kwargs):
    try:
        return _orig_getaddrinfo(host, port, *args, **kwargs)
    except socket.gaierror:
        # If local router DNS failed, resolve via Google DNS-over-HTTPS
        try:
            req = urllib.request.Request(
                f"https://dns.google/resolve?name={host}&type=A",
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=5) as res:
                data = json.loads(res.read().decode())
                answers = data.get("Answer", [])
                for ans in answers:
                    if ans.get("type") == 1 and ans.get("data"):
                        return _orig_getaddrinfo(ans["data"], port, *args, **kwargs)
        except Exception:
            pass
        raise


socket.getaddrinfo = _fallback_getaddrinfo

# Determine database engine and connection fallback
database_url = settings.DATABASE_URL
active_db_type = "postgresql" if database_url.startswith("postgresql") else "sqlite"
active_db_url = database_url

connect_args = {}
if database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = None

# Attempt primary connection and verify connectivity
try:
    if database_url.startswith("postgresql"):
        try:
            import psycopg

            def _create_pg_conn():
                return psycopg.connect(database_url)

            candidate_engine = create_engine(
                "postgresql+psycopg://",
                creator=_create_pg_conn,
                pool_pre_ping=True,
            )
        except ImportError:
            import psycopg2
            pg_url = database_url
            if pg_url.startswith("postgresql://"):
                pg_url = pg_url.replace("postgresql://", "postgresql+psycopg2://", 1)
            candidate_engine = create_engine(
                pg_url,
                pool_pre_ping=True,
            )
    else:
        candidate_engine = create_engine(
            database_url,
            connect_args=connect_args,
            pool_pre_ping=True,
        )

    # Test connection immediately
    with candidate_engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    engine = candidate_engine
    active_db_type = "postgresql" if database_url.startswith("postgresql") else "sqlite"
    logger.info(f"Connected to primary database ({active_db_type}) successfully!")
except Exception as e:
    logger.warning(
        f"Unable to connect to primary DATABASE_URL '{database_url}': {e}. "
        "Falling back to local SQLite demo database (sqlite:///./medichain_demo.db) for demonstration."
    )
    from pathlib import Path as _Path
    _db_file = _Path(__file__).resolve().parent.parent / "medichain_demo.db"
    fallback_url = f"sqlite:///{_db_file.as_posix()}"
    active_db_type = "sqlite"
    active_db_url = fallback_url
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


def get_active_database_info() -> dict:
    """Returns honest metadata regarding current database connection."""
    return {
        "engine": active_db_type,
        "is_fallback_sqlite": active_db_type == "sqlite",
        "url_masked": (
            "postgresql://neondb_owner:***@ep-orange-cloud-b37154fa-pooler.../neondb"
            if active_db_type == "postgresql"
            else "sqlite:///./medichain_demo.db"
        ),
    }
