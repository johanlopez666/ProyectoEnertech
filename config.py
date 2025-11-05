import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Configuración de PostgreSQL
    POSTGRES_URI = os.getenv("POSTGRES_URI") or os.getenv("DATABASE_URL")
    DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URI")
    
    # Configuración de seguridad
    SECRET_KEY = os.getenv("SECRET_KEY") or "clave_por_defecto_segura"
