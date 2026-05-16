"""SQLAlchemy engine and session factory."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import SQLITE_DB_PATH
from db.models import Base
from pathlib import Path


def get_engine():
    Path(SQLITE_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{SQLITE_DB_PATH}",
        echo=False,
        connect_args={"timeout": 30},
    )
    return engine


def init_db():
    """Create all tables if they don't exist."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    return engine


def get_session():
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()
