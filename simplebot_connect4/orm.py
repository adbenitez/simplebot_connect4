from contextlib import contextmanager
from threading import Lock

from sqlalchemy import Column, ForeignKey, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import relationship, sessionmaker


class Base:
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()


Base = declarative_base(cls=Base)
_Session = sessionmaker()
_lock = Lock()


class Game(Base):
    p1 = Column(String(500), primary_key=True)
    p2 = Column(String(500), primary_key=True)
    chat_id = Column(Integer, nullable=False)
    board = Column(String(2000))
    black_player = Column(String(500))
    p1_wins = Column(Integer, default=0, nullable=False)
    p2_wins = Column(Integer, default=0, nullable=False)

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("p1_wins", 0)
        kwargs.setdefault("p2_wins", 0)
        super().__init__(**kwargs)


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    with _lock:
        session = _Session()
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()


def init(path: str, debug: bool = False) -> None:
    """Initialize engine."""
    engine = create_engine(path, echo=debug)
    Base.metadata.create_all(engine)
    _Session.configure(bind=engine)
