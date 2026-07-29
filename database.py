from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from config import DB_URL

if not DB_URL:
    raise RuntimeError(
        "DATABASE_URL no está definida. "
        "Copiá .env.example a .env y completá la URL de conexión, o exportá la variable de entorno."
    )

# Creamos el motor. Al estar en su propio archivo, solo se crea una vez.
engine = create_engine(DB_URL)

# Configuramos el pool de sesiones
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para nuestros modelos
Base = declarative_base()

# Dependencia para FastAPI: Cada vez que un endpoint necesite la BD, 
# abrirá una sesión y la cerrará al terminar, devolviéndola al pool.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()