import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

USER = os.getenv("POSTGRES_USER")
PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_NAME = os.getenv("POSTGRES_DB")
PORT = os.getenv("POSTGRES_PORT", "5432")

if not USER or not PASSWORD or not DB_NAME:
    raise ValueError(
        "ERROR DE SEGURIDAD: Faltan variables de entorno para la base de datos. "
        "Asegúrate de tener un archivo .env configurado correctamente."
    )

DATABASE_URL = f"postgresql://{USER}:{PASSWORD}@localhost:{PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()