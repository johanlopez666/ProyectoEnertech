from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import random
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import pytz

main = Blueprint('main', __name__)

def get_conn():
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise ValueError("No se encontró DATABASE_URL en la configuración")
    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)

def init_mensajes_table():
    """Crea la tabla de mensajes de la comunidad si no existe"""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS mensajes_comunidad (
                id SERIAL PRIMARY KEY,
                usuario_id INTEGER REFERENCES usuarios(id),
                nombre_usuario VARCHAR(255) NOT NULL,
                mensaje TEXT NOT NULL,
                color_avatar VARCHAR(7) NOT NULL,
                icono VARCHAR(50) DEFAULT 'person',
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error al crear tabla de mensajes: {e}")

# PÁGINA PRINCIPAL
@main.route('/')
def home():
    return render_template('index.html')

# DASHBOARD (requiere autenticación)
@main.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        flash('Por favor inicia sesión para acceder al dashboard.', 'error')
        return redirect(url_for('main.login'))
    return render_template('dashboard.html')

# LOGIN
@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form.get('correo')
        contrasena = request.form.get('contraseña')

        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("SELECT * FROM usuarios WHERE correo = %s", (correo,))
            usuario = cur.fetchone()
            cur.close()
            conn.close()

            if usuario and check_password_hash(usuario['contrasena'], contrasena):
                # Guardar info del usuario en session
                session['logged_in'] = True
                session['usuario'] = usuario['nombre']
                session['correo'] = usuario['correo']
                
                flash('Inicio de sesión exitoso.', 'success')
                return redirect(url_for('main.dashboard'))
            else:
                flash('Correo o contraseña incorrectos.', 'error')
                return render_template('login.html')

        except Exception as e:
            flash(f"Error al iniciar sesión: {str(e)}", "error")
            return render_template('login.html')

    # GET: renderizar login
    return render_template('login.html')

# LOGOUT
@main.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('Sesión cerrada exitosamente.', 'success')
    return redirect(url_for('main.home'))

# REGISTRO
@main.route('/registrarse', methods=['GET', 'POST'])
def registrarse():
    if request.method == 'POST':
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        telefono = request.form['telefono']
        direccion = request.form['direccion']
        correo = request.form['correo']
        contrasena = request.form['contrasena']
        ocupacion = request.form.get('ocupacion', '')
        num_personas = int(request.form['num_personas'])
        estrato = int(request.form['estrato'])

        # Hash de la contraseña
        contrasena_hash = generate_password_hash(contrasena)

        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO usuarios (nombre, apellido, telefono, direccion, correo, contrasena, ocupacion, num_personas, estrato)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (nombre, apellido, telefono, direccion, correo, contrasena_hash, ocupacion, num_personas, estrato))
            conn.commit()
            cur.close()
            conn.close()
            flash("Usuario registrado exitosamente", "success")
            return redirect(url_for('main.login'))  # Corregido: main.login
        except Exception as e:
            flash(f"Error al registrar usuario: {str(e)}", "error")
            return redirect(url_for('main.registrarse'))

    return render_template('Registrarse.html')

# ANEXAR FACTURA
@main.route('/anexar_factura')
def anexar_factura():
    if not session.get('logged_in'):
        flash('Por favor inicia sesión para acceder a esta página.', 'error')
        return redirect(url_for('main.login'))
    return render_template('anexar_factura.html')

# GUARDAR CONSUMO (para manejar el formulario de anexar_factura)
@main.route('/guardar_consumo', methods=['POST'])
def guardar_consumo():
    if not session.get('logged_in'):
        flash('Por favor inicia sesión para guardar información.', 'error')
        return redirect(url_for('main.login'))

    try:
        conn = get_conn()
        cur = conn.cursor()

        # 1️⃣ Obtener el id del usuario logueado
        cur.execute("SELECT id FROM usuarios WHERE correo = %s", (session['correo'],))
        usuario = cur.fetchone()
        usuario_id = usuario['id']

        # 2️⃣ Guardar los 3 meses
        for i in range(1, 4):
            mes = request.form.get(f'mes_{i}', '').strip()
            consumo_val = request.form.get(f'consumo_{i}', '').strip()
            promedio_val = request.form.get(f'promedio_{i}', '').strip()

            if mes and consumo_val and promedio_val:
                consumo_val = float(consumo_val)
                promedio_val = float(promedio_val)

                cur.execute("""
                    INSERT INTO consumos (usuario_id, mes, consumo, promedio, fecha)
                    VALUES (%s, %s, %s, %s, NOW())
                """, (usuario_id, mes, consumo_val, promedio_val))

        conn.commit()
        cur.close()
        conn.close()

        flash("Factura anexada con éxito. Por favor revise la sección Gráfico.", "success")
        return redirect(url_for('main.anexar_factura'))

    except Exception as e:
        flash(f"Error al guardar la información: {str(e)}", "error")
        return redirect(url_for('main.anexar_factura'))

@main.route('/grafico')
def grafico():
    if not session.get('logged_in'):
        flash('Por favor inicia sesión para acceder a esta página.', 'error')
        return redirect(url_for('main.login'))
    
    try:
        conn = get_conn()
        cur = conn.cursor()
        
        # Obtener id del usuario
        cur.execute("SELECT id FROM usuarios WHERE correo = %s", (session['correo'],))
        usuario = cur.fetchone()
        usuario_id = usuario['id']
        
        # Tomar consumos del usuario
        cur.execute(
            "SELECT mes, consumo, promedio, fecha FROM consumos "
            "WHERE usuario_id = %s ORDER BY fecha ASC LIMIT 7;", 
            (usuario_id,)
        )
        datos = cur.fetchall()
        cur.close()
        conn.close()
        
        # Convertir datos a tipos compatibles con JSON/JS
        labels = [str(d['mes']) for d in datos]        # meses como string
        consumos = [float(d['consumo']) for d in datos]  # consumo como float
        promedios = [float(d['promedio']) for d in datos] # promedio como float

        # Colores según relación con promedio
        colores = []
        for c, p in zip(consumos, promedios):
            if c < p:
                colores.append('#22c55e')   # verde
            elif c <= p + 1:
                colores.append('#eab308')   # amarillo
            else:
                colores.append('#ef4444')   # rojo

    except Exception as e:
        flash(f"Error al cargar datos: {str(e)}", "error")
        labels, consumos, promedios, colores = [], [], [], []

    return render_template(
        'grafico.html',
        labels=labels,
        consumos=consumos,
        promedios=promedios,
        colores=colores
    )


# REPORTES (requiere autenticación)
@main.route('/reportes')
def reportes():
    if not session.get('logged_in'):
        flash('Por favor inicia sesión para acceder a esta página.', 'error')
        return redirect(url_for('main.login'))
    
    try:
        conn = get_conn()
        cur = conn.cursor()
        
        # Obtener id del usuario
        cur.execute("SELECT id FROM usuarios WHERE correo = %s", (session['correo'],))
        usuario = cur.fetchone()
        usuario_id = usuario['id']
        
        # Obtener el último consumo registrado
        cur.execute(
            "SELECT mes, consumo, promedio, fecha FROM consumos "
            "WHERE usuario_id = %s ORDER BY fecha DESC LIMIT 1;", 
            (usuario_id,)
        )
        ultimo_consumo = cur.fetchone()
        
        # Obtener todos los consumos para calcular estadísticas
        cur.execute(
            "SELECT consumo, promedio FROM consumos "
            "WHERE usuario_id = %s ORDER BY fecha DESC LIMIT 7;", 
            (usuario_id,)
        )
        todos_consumos = cur.fetchall()
        
        cur.close()
        conn.close()
        
        # Procesar datos
        if ultimo_consumo:
            consumo_actual = float(ultimo_consumo['consumo'])
            promedio_actual = float(ultimo_consumo['promedio'])
            mes_actual = str(ultimo_consumo['mes'])
            
            # Calcular diferencia y porcentaje
            diferencia = consumo_actual - promedio_actual
            porcentaje = (consumo_actual / promedio_actual) * 100 if promedio_actual > 0 else 0
            
            # Determinar nivel de consumo
            if consumo_actual < promedio_actual:
                nivel = "Bajo (Verde)"
                nivel_color = "verde"
                posicion_indicator = 16.7  # centro de la franja verde
            elif consumo_actual <= promedio_actual + (promedio_actual * 0.1):
                nivel = "Moderado (Amarillo)"
                nivel_color = "amarillo"
                posicion_indicator = 50  # centro de la franja amarilla
            else:
                nivel = "Alto (Rojo)"
                nivel_color = "rojo"
                posicion_indicator = 83.3  # centro de la franja roja
            
            # Calcular costo aproximado (aproximadamente $868 COP por kWh)
            costo_adicional = float(abs(diferencia) * 868)
            
            # Generar reporte dinámico
            if nivel_color == "verde":
                reporte_texto = f"En {mes_actual}, tu nivel de consumo se ubicó en la zona verde, lo que indica un consumo eficiente y por debajo de tu promedio histórico. ¡Excelente trabajo!"
            elif nivel_color == "amarillo":
                reporte_texto = f"En {mes_actual}, tu nivel de consumo se ubicó en la zona amarilla, lo que indica un comportamiento moderado y estable respecto a tus registros anteriores."
            else:
                reporte_texto = f"En {mes_actual}, tu nivel de consumo se ubicó en la zona roja, lo que indica un consumo elevado respecto a tu promedio histórico. Te recomendamos revisar tus hábitos energéticos."
            
        else:
            # Sin datos
            consumo_actual = 0
            promedio_actual = 0
            mes_actual = "N/A"
            diferencia = 0
            porcentaje = 0
            nivel = "Sin datos"
            nivel_color = "amarillo"
            posicion_indicator = 50
            costo_adicional = 0
            reporte_texto = "Aún no has registrado consumos. Por favor, anexa una factura para ver tus reportes."
        
    except Exception as e:
        flash(f"Error al cargar datos: {str(e)}", "error")
        consumo_actual = 0
        promedio_actual = 0
        mes_actual = "N/A"
        diferencia = 0
        porcentaje = 0
        nivel = "Error"
        nivel_color = "amarillo"
        posicion_indicator = 50
        costo_adicional = 0
        reporte_texto = "Error al cargar los datos del reporte."
    
    return render_template(
        'reportes.html',
        consumo_actual=consumo_actual,
        promedio_actual=promedio_actual,
        mes_actual=mes_actual,
        diferencia=diferencia,
        porcentaje=porcentaje,
        nivel=nivel,
        nivel_color=nivel_color,
        posicion_indicator=posicion_indicator,
        costo_adicional=costo_adicional,
        reporte_texto=reporte_texto
    )

# QUIÉNES SOMOS (página pública)
@main.route('/quienes-somos')
def quienes_somos():
    return render_template('quienes_somos.html')

# COMUNIDAD (requiere autenticación)
@main.route('/comunidad', methods=['GET', 'POST'])
def comunidad():
    # Inicializar tabla si no existe
    init_mensajes_table()
    
    if not session.get('logged_in'):
        flash('Por favor inicia sesión para acceder a esta página.', 'error')
        return redirect(url_for('main.login'))
    
    try:
        conn = get_conn()
        cur = conn.cursor()
        
        if request.method == 'POST':
            mensaje_texto = request.form.get('mensaje', '').strip()
            
            if mensaje_texto:
                # Obtener id y nombre del usuario de la sesión
                correo_usuario = session.get('correo')
                nombre_usuario = session.get('usuario', 'Usuario')
                
                # Obtener usuario_id
                cur.execute("SELECT id FROM usuarios WHERE correo = %s", (correo_usuario,))
                usuario = cur.fetchone()
                usuario_id = usuario['id'] if usuario else None
                
                # Colores aleatorios para el avatar
                colores = ['#22c55e', '#3b82f6', '#f97316', '#8b5cf6', '#ec4899', '#06b6d4']
                color_avatar = random.choice(colores)
                
                # Guardar mensaje en la base de datos
                cur.execute("""
                    INSERT INTO mensajes_comunidad (usuario_id, nombre_usuario, mensaje, color_avatar, icono)
                    VALUES (%s, %s, %s, %s, %s)
                """, (usuario_id, nombre_usuario, mensaje_texto, color_avatar, 'person'))
                conn.commit()
                
                flash('Mensaje publicado exitosamente.', 'success')
                # No cerrar conexión aquí, se cerrará después de obtener mensajes
        
        # Obtener mensajes de la base de datos (últimos 50)
        cur.execute("""
            SELECT id, nombre_usuario, mensaje, color_avatar, icono, fecha
            FROM mensajes_comunidad
            ORDER BY fecha DESC
            LIMIT 50
        """)
        mensajes_db = cur.fetchall()
        
        cur.close()
        conn.close()
        
        # Formatear fecha y hora para los mensajes (zona horaria de Colombia)
        zona_colombia = pytz.timezone('America/Bogota')
        mensajes_con_tiempo = []
        for msg in mensajes_db:
            fecha_msg = msg['fecha']
            
            # Convertir la fecha a datetime si es string
            if isinstance(fecha_msg, str):
                try:
                    fecha_msg = datetime.fromisoformat(fecha_msg.replace('Z', '+00:00'))
                except:
                    fecha_msg = datetime.strptime(fecha_msg, '%Y-%m-%d %H:%M:%S')
            
            # Si la fecha no tiene zona horaria, asumir que está en UTC
            if fecha_msg.tzinfo is None:
                fecha_msg = pytz.UTC.localize(fecha_msg)
            
            # Convertir a zona horaria de Colombia
            fecha_colombia = fecha_msg.astimezone(zona_colombia)
            
            # Formatear fecha y hora en formato legible
            # Formato: "DD/MM/YYYY HH:MM"
            fecha_hora_str = fecha_colombia.strftime('%d/%m/%Y %H:%M')
            
            mensajes_con_tiempo.append({
                'usuario': msg['nombre_usuario'],
                'texto': msg['mensaje'],
                'tiempo': fecha_hora_str,
                'fecha': fecha_msg,
                'color_avatar': msg['color_avatar'],
                'icono': msg['icono']
            })
        
    except Exception as e:
        flash(f"Error al cargar mensajes: {str(e)}", "error")
        mensajes_con_tiempo = []
    
    # Lista completa de tips del mes
    todos_los_tips = [
        "Plancha tu ropa una sola vez a la semana para ahorrar energía",
        "Desconecta los cargadores cuando no los uses, siguen consumiendo energía",
        "Usa la luz natural durante el día y ahorra en iluminación artificial",
        "Lava la ropa con agua fría cuando sea posible para reducir el consumo",
        "Aprovecha el calor residual: apaga la estufa unos minutos antes de terminar",
        "Sella bien las ventanas y puertas para evitar pérdidas de temperatura",
        "Usa ventiladores en lugar de aire acondicionado cuando sea posible",
        "Descongela regularmente el refrigerador para mejorar su eficiencia",
        "Agrupa las comidas que requieren cocción para aprovechar el calor del horno",
        "Instala bombillas LED, consumen hasta 80% menos que las incandescentes",
        "Usa cortinas gruesas en invierno para mantener el calor dentro",
        "Limpia regularmente los filtros del aire acondicionado",
        "Aprovecha el sol para secar la ropa en lugar de usar secadora",
        "Desconecta los electrodomésticos en standby al final del día",
        "Usa el microondas en lugar del horno para calentar comidas pequeñas",
        "Configura tu termostato 2-3 grados más alto en verano",
        "Cocina con las ollas tapadas para usar menos energía",
        "Llena completamente la lavadora antes de usarla",
        "Instala sensores de movimiento para luces en áreas poco usadas",
        "Usa el modo eco en tus electrodomésticos cuando esté disponible",
        "Mantén el refrigerador a 3-5°C y el congelador a -18°C",
        "Revisa y reemplaza los sellos de puertas y ventanas si están dañados",
        "Usa timers para apagar automáticamente luces y aparatos",
        "Aprovecha el calor del sol para calentar agua en verano",
        "Cierra las cortinas en verano para mantener el calor fuera",
        "Limpia las bobinas del refrigerador para mejorar su eficiencia",
        "Usa ollas del tamaño adecuado para la estufa que estás usando",
        "Evita abrir el horno mientras cocinas, pierde mucho calor",
        "Usa la lavavajillas solo cuando esté llena",
        "Configura el modo de ahorro de energía en tus dispositivos"
    ]
    
    # Seleccionar 3 tips aleatorios
    tips_seleccionados = random.sample(todos_los_tips, min(3, len(todos_los_tips)))
    
    return render_template('comunidad.html', mensajes=mensajes_con_tiempo, tips=tips_seleccionados)