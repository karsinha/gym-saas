"""
Configuración de SQLAlchemy: motor de conexión y sesión de base de datos.

- Si DATABASE_URL apunta a Postgres, se conecta a Postgres.
- Si no está definida, cae automáticamente en SQLite (archivo local gym.db),
  útil para arrancar rápido sin instalar nada.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import DATABASE_URL

# SQLite necesita este flag extra para funcionar bien con FastAPI (multithread)
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    Dependencia de FastAPI: abre una sesión de DB por request
    y la cierra automáticamente al terminar.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
