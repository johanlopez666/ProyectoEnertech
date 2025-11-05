import os
from flask import Flask
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Cargar variables de entorno
load_dotenv()

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY")

    # Guardar URI de PostgreSQL en config
    app.config['POSTGRES_URI'] = os.getenv("POSTGRES_URI")

    # Ejemplo de conexión inicial para probar
    try:
        conn = psycopg2.connect(app.config['POSTGRES_URI'], cursor_factory=RealDictCursor)
        conn.close()
        print("Conexión a PostgreSQL en Neon exitosa ✅")
    except Exception as e:
        print("Error al conectar a PostgreSQL:", e)

    # Registrar rutas (Blueprints)
    from app.routes import main
    app.register_blueprint(main)

    return app
