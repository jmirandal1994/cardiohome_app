from flask import Flask, render_template, request, redirect, session, url_for, flash
import os
from werkzeug.utils import secure_filename
import smtplib
from email.message import EmailMessage

# --- Configuración inicial ---
app = Flask(__name__)
app.secret_key = 'clave_super_segura'
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'docx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- Simulación de usuarios con establecimientos asignados ---
USUARIOS = {
    'admin': {
        'password': 'admin123',
        'establecimientos': []
    },
    'doctora1': {
        'password': '1234',
        'establecimientos': ['Escuela A', 'Liceo B']
    },
    'doctora2': {
        'password': 'abcd',
        'establecimientos': []
    }
}

# Eventos calendario (podría ir en un archivo externo si se desea)
EVENTOS = [
    {'fecha': '20/05/2025', 'horario': '09:00 - 10:30', 'establecimiento': 'Escuela A', 'obs': 'Evaluación inicial'},
    {'fecha': '21/05/2025', 'horario': '11:00 - 12:30', 'establecimiento': 'Liceo B', 'obs': 'Entrega de informes'}
]

# --- Verifica tipo de archivo permitido ---
def permitido(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Rutas ---
@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    usuario = request.form['username']
    clave = request.form['password']
    if usuario in USUARIOS and USUARIOS[usuario]['password'] == clave:
        session['usuario'] = usuario
        return redirect(url_for('dashboard'))
    flash('Usuario o contraseña incorrecta')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session:
        return redirect(url_for('index'))
    usuario = session['usuario']
    establecimientos = USUARIOS[usuario]['establecimientos']
    return render_template('dashboard.html', usuario=usuario, establecimientos=establecimientos, eventos=EVENTOS)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/admin/agregar', methods=['POST'])
def admin_agregar():
    nombre = request.form['nombre']
    fecha = request.form['fecha']
    horario = request.form['horario']
    obs = request.form['obs']
    doctora = request.form['doctora']
    archivo = request.files['formulario']

    if archivo and permitido(archivo.filename):
        filename = secure_filename(f'{nombre}.pdf')
        archivo.save(os.path.join('static/formularios', filename))

        # Agregar el colegio al perfil de la doctora
        if doctora in USUARIOS:
            if nombre not in USUARIOS[doctora]['establecimientos']:
                USUARIOS[doctora]['establecimientos'].append(nombre)

        # Agregar al calendario
        EVENTOS.append({
            'fecha': fecha,
            'horario': horario,
            'establecimiento': nombre,
            'obs': obs
        })

        print(f'NUEVO: {nombre}, {fecha}, {horario}, {obs}, asignado a {doctora}')

    return redirect(url_for('dashboard'))

@app.route('/subir/<establecimiento>', methods=['POST'])
def subir(establecimiento):
    if 'usuario' not in session:
        return redirect(url_for('index'))

    archivos = request.files.getlist('archivo')
    if not archivos or archivos[0].filename == '':
        return 'No se seleccionó ningún archivo.', 400

    mensajes = []
    for archivo in archivos:
        if permitido(archivo.filename):
            filename = secure_filename(f"{session['usuario']}_{establecimiento}_{archivo.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            archivo.save(filepath)
            mensajes.append(f'✔ {archivo.filename}')
        else:
            mensajes.append(f'✖ {archivo.filename} (no permitido)')

    return "Archivos procesados:<br>" + "<br>".join(mensajes)

@app.route('/evaluados/<establecimiento>', methods=['POST'])
def evaluados(establecimiento):
    if 'usuario' not in session:
        return redirect(url_for('index'))

    cantidad = request.form.get('alumnos')
    usuario = session['usuario']
    enviar_correo(
        asunto=f'Alumnos evaluados - {establecimiento}',
        cuerpo=f'Doctora: {usuario}\nEstablecimiento: {establecimiento}\nCantidad evaluada: {cantidad}'
    )
    return f'Datos enviados correctamente: {cantidad} alumnos evaluados.'

# --- Función de envío de correo ---
def enviar_correo(asunto, cuerpo):
    EMAIL_REMITENTE = 'noreply@cardiohome.cl'
    EMAIL_RECEPTOR = 'jmiraandal@gmail.com'
    CONTRASEÑA = 'Estafa123'

    mensaje = EmailMessage()
    mensaje['Subject'] = asunto
    mensaje['From'] = EMAIL_REMITENTE
    mensaje['To'] = EMAIL_RECEPTOR
    mensaje.set_content(cuerpo)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_REMITENTE, CONTRASEÑA)
            smtp.send_message(mensaje)
    except Exception as e:
        print(f"Error al enviar correo: {e}")

# --- Crear carpeta de subida si no existe ---
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- Ejecutar la app ---
if __name__ == '__main__':
    app.run(debug=True)
