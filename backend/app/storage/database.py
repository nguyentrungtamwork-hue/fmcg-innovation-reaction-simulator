"""SQLAlchemy engine, session, and Base."""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=_connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables + lightweight column migrations. MVP-only; production should use Alembic."""
    from app.models import project as _p  # noqa: F401
    from app.models import brief as _b  # noqa: F401
    from app.models import ontology as _o  # noqa: F401
    from app.models import agent as _a  # noqa: F401
    from app.models import event as _e  # noqa: F401
    from app.models import report as _r  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_columns()


def _ensure_columns() -> None:
    """SQLite-friendly additive column migrations for older local DBs (Phase 30+).

    Generic: for every mapped table that already exists, compare the ORM columns to
    the on-disk columns and ``ALTER TABLE ADD COLUMN`` for any that are missing.
    New columns are added as nullable (existing rows get NULL); the ORM supplies
    defaults on future inserts. This keeps an older `fmcg_sim.db` usable after the
    schema grows, without Alembic. No data is dropped or rewritten.
    """
    if not settings.database_url.startswith("sqlite"):
        return
    from sqlalchemy import text

    with engine.connect() as conn:
        for table in Base.metadata.sorted_tables:
            try:
                rows = list(conn.execute(text(f"PRAGMA table_info({table.name})")))
            except Exception:  # noqa: BLE001
                continue
            if not rows:  # table doesn't exist yet (create_all handles those)
                continue
            existing = {row[1] for row in rows}
            for col in table.columns:
                if col.name in existing:
                    continue
                try:
                    ddl_type = col.type.compile(dialect=engine.dialect)
                except Exception:  # noqa: BLE001
                    ddl_type = "TEXT"
                try:
                    conn.execute(text(f'ALTER TABLE {table.name} ADD COLUMN "{col.name}" {ddl_type}'))
                except Exception:  # noqa: BLE001
                    pass
        conn.commit()
