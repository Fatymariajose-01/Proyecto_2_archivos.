import sys
import json
import os
import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QInputDialog, QMessageBox, QTextEdit, QLineEdit
)

USERS_FILE = "usuarios.json"
PERMISSIONS_FILE = "permisos.json"
FAT_FILE = "fat.json"
LOG_FILE = "bitacora.txt"
BLOQUES_DIR = "bloques"

# -------------------- FUNCIONES AUXILIARES --------------------

def cargar_json(ruta, defecto):
    if not os.path.exists(ruta):
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(defecto, f, indent=4)
        return defecto
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_json(ruta, datos):
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4)

def registrar_en_bitacora(usuario, accion, archivo, resultado):
    fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{fecha}] Usuario: {usuario} | Acción: {accion} | Archivo: {archivo} | Resultado: {resultado}\n")

def crear_bloques(texto):
    if not os.path.exists(BLOQUES_DIR):
        os.makedirs(BLOQUES_DIR)

    bloques = []
    partes = [texto[i:i + 20] for i in range(0, len(texto), 20)]
    for i, parte in enumerate(partes):
        bloque_nombre = f"{BLOQUES_DIR}/bloque_{datetime.datetime.now().timestamp()}_{i}.json"
        bloque = {
            "datos": parte,
            "siguiente": None,
            "eof": i == len(partes) - 1
        }
        if i > 0:
            bloques[-1]["contenido"]["siguiente"] = bloque_nombre
            guardar_json(bloques[-1]["ruta"], bloques[-1]["contenido"])
        bloques.append({"ruta": bloque_nombre, "contenido": bloque})
    guardar_json(bloques[-1]["ruta"], bloques[-1]["contenido"])
    return bloques[0]["ruta"]

def leer_contenido_bloques(ruta_inicial):
    contenido = ""
    actual = ruta_inicial
    while actual and os.path.exists(actual):
        bloque = cargar_json(actual, {})
        contenido += bloque.get("datos", "")
        actual = bloque.get("siguiente")
    return contenido


# -------------------- CLASE PRINCIPAL --------------------

class MainWindow(QMainWindow):
    def __init__(self, usuario, login_window):
        super().__init__()
        self.usuario = usuario
        self.login_window = login_window
        self.setWindowTitle(f"Gestor FAT - Sesión: {usuario}")
        self.setGeometry(400, 200, 700, 450)

        self.setStyleSheet("""
            QMainWindow { background-color: #0e1a2b; color: white; }
            QPushButton {
                background-color: #0078d7;
                border: none;
                padding: 8px;
                border-radius: 6px;
                color: white;
                font-weight: bold;
            }
            QPushButton:disabled {
                background-color: #444;
                color: #aaa;
            }
            QPushButton:hover:!disabled { background-color: #3399ff; }
            QListWidget { background-color: #1a273d; color: white; border-radius: 6px; padding: 4px; }
        """)

        layout = QVBoxLayout()
        label = QLabel(f"Bienvenido, {usuario}")
        label.setStyleSheet("font-size: 18px; font-weight: bold; margin: 6px;")
        layout.addWidget(label)

        self.lista = QListWidget()
        layout.addWidget(self.lista)

        botones_layout = QHBoxLayout()
        self.btn_crear = QPushButton("Crear archivo")
        self.btn_abrir = QPushButton("Abrir archivo")
        self.btn_modificar = QPushButton("Modificar archivo")
        self.btn_eliminar = QPushButton("Eliminar archivo")
        self.btn_recuperar = QPushButton("Recuperar archivo")
        self.btn_permisos = QPushButton("Permisos")
        self.btn_cerrar = QPushButton("Cerrar sesión")

        self.btn_crear.clicked.connect(self.crear_archivo)
        self.btn_abrir.clicked.connect(self.abrir_archivo)
        self.btn_modificar.clicked.connect(self.modificar_archivo)
        self.btn_eliminar.clicked.connect(self.eliminar_archivo)
        self.btn_recuperar.clicked.connect(self.recuperar_archivo)
        self.btn_permisos.clicked.connect(self.gestionar_permisos)
        self.btn_cerrar.clicked.connect(self.cerrar_sesion)

        botones = [
            self.btn_crear, self.btn_abrir, self.btn_modificar,
            self.btn_eliminar, self.btn_recuperar, self.btn_permisos, self.btn_cerrar
        ]
        for b in botones:
            botones_layout.addWidget(b)

        layout.addLayout(botones_layout)

        # Deshabilitar botón de permisos si no es admin
        if self.usuario != "admin":
            self.btn_permisos.setDisabled(True)

        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

        self.actualizar_lista()
        self.ventanas_abiertas = []  # para evitar que se cierren QTextEdit

    # -------------------- FUNCIONES DE ARCHIVO --------------------

    def actualizar_lista(self):
        fat = cargar_json(FAT_FILE, {"archivos": {}})
        self.lista.clear()
        for nombre, info in fat["archivos"].items():
            if not info.get("eliminado", False):
                self.lista.addItem(nombre)

    def crear_archivo(self):
        nombre, ok = QInputDialog.getText(self, "Nuevo archivo", "Ingrese nombre del archivo:")
        if not ok or not nombre:
            return
        contenido, ok = QInputDialog.getMultiLineText(self, "Contenido", "Ingrese el contenido:")
        if not ok:
            return
        ruta_bloque = crear_bloques(contenido)
        fat = cargar_json(FAT_FILE, {"archivos": {}})
        fat["archivos"][nombre] = {
            "nombre": nombre,
            "ruta_inicial": ruta_bloque,
            "eliminado": False,
            "caracteres": len(contenido),
            "fecha_creacion": str(datetime.datetime.now()),
            "fecha_modificacion": str(datetime.datetime.now()),
            "fecha_eliminacion": None,
            "owner": self.usuario
        }
        guardar_json(FAT_FILE, fat)

        permisos = cargar_json(PERMISSIONS_FILE, {"archivos": {}})
        permisos["archivos"][nombre] = {"owner": self.usuario, "permisos": {self.usuario: ["lectura", "escritura"]}}
        guardar_json(PERMISSIONS_FILE, permisos)

        registrar_en_bitacora(self.usuario, "crear", nombre, "Éxito")
        self.actualizar_lista()
        QMessageBox.information(self, "Éxito", "Archivo creado correctamente.")

    def abrir_archivo(self):
        archivo = self.lista.currentItem()
        if not archivo:
            QMessageBox.warning(self, "Error", "Seleccione un archivo.")
            return
        archivo = archivo.text()

        permisos = cargar_json(PERMISSIONS_FILE, {"archivos": {}})
        datos = permisos["archivos"].get(archivo, {})
        if self.usuario not in datos.get("permisos", {}) or "lectura" not in datos["permisos"][self.usuario]:
            QMessageBox.warning(self, "Permiso denegado", "No tiene permiso de lectura.")
            registrar_en_bitacora(self.usuario, "abrir", archivo, "Permiso denegado")
            return

        fat = cargar_json(FAT_FILE, {"archivos": {}})
        info = fat["archivos"].get(archivo)
        if not info:
            QMessageBox.warning(self, "Error", "Archivo no encontrado.")
            return

        contenido = leer_contenido_bloques(info["ruta_inicial"])
        ventana = QTextEdit()
        ventana.setReadOnly(True)
        ventana.setText(contenido)
        ventana.setWindowTitle(f"Lectura - {archivo}")
        ventana.resize(500, 400)
        ventana.show()

        # Guardar referencia para evitar que se cierre
        self.ventanas_abiertas.append(ventana)

        registrar_en_bitacora(self.usuario, "abrir", archivo, "Éxito")

    def modificar_archivo(self):
        archivo = self.lista.currentItem()
        if not archivo:
            QMessageBox.warning(self, "Error", "Seleccione un archivo.")
            return
        archivo = archivo.text()

        permisos = cargar_json(PERMISSIONS_FILE, {"archivos": {}})
        datos = permisos["archivos"].get(archivo, {})
        if self.usuario not in datos.get("permisos", {}) or "escritura" not in datos["permisos"][self.usuario]:
            QMessageBox.warning(self, "Permiso denegado", "No tiene permiso de escritura.")
            registrar_en_bitacora(self.usuario, "modificar", archivo, "Permiso denegado")
            return

        fat = cargar_json(FAT_FILE, {"archivos": {}})
        info = fat["archivos"].get(archivo)
        contenido_actual = leer_contenido_bloques(info["ruta_inicial"])

        nuevo, ok = QInputDialog.getMultiLineText(self, "Modificar archivo", "Contenido actual:\n" + contenido_actual)
        if not ok:
            return

        ruta_bloque = crear_bloques(nuevo)
        info["ruta_inicial"] = ruta_bloque
        info["caracteres"] = len(nuevo)
        info["fecha_modificacion"] = str(datetime.datetime.now())
        fat["archivos"][archivo] = info
        guardar_json(FAT_FILE, fat)

        registrar_en_bitacora(self.usuario, "modificar", archivo, "Éxito")
        QMessageBox.information(self, "Éxito", "Archivo modificado correctamente.")

    def eliminar_archivo(self):
        archivo = self.lista.currentItem()
        if not archivo:
            QMessageBox.warning(self, "Error", "Seleccione un archivo.")
            return
        archivo = archivo.text()
        fat = cargar_json(FAT_FILE, {"archivos": {}})
        if archivo not in fat["archivos"]:
            return
        fat["archivos"][archivo]["eliminado"] = True
        fat["archivos"][archivo]["fecha_eliminacion"] = str(datetime.datetime.now())
        guardar_json(FAT_FILE, fat)
        self.actualizar_lista()
        registrar_en_bitacora(self.usuario, "eliminar", archivo, "Éxito")
        QMessageBox.information(self, "Éxito", "Archivo enviado a la papelera.")

    def recuperar_archivo(self):
        fat = cargar_json(FAT_FILE, {"archivos": {}})
        papelera = [n for n, i in fat["archivos"].items() if i.get("eliminado", False)]
        if not papelera:
            QMessageBox.information(self, "Papelera", "No hay archivos en papelera.")
            return
        archivo, ok = QInputDialog.getItem(self, "Recuperar archivo", "Seleccione:", papelera, 0, False)
        if ok:
            fat["archivos"][archivo]["eliminado"] = False
            guardar_json(FAT_FILE, fat)
            registrar_en_bitacora(self.usuario, "recuperar", archivo, "Éxito")
            self.actualizar_lista()
            QMessageBox.information(self, "Éxito", "Archivo recuperado.")

    def gestionar_permisos(self):
        if self.usuario != "admin":
            QMessageBox.warning(self, "Acceso denegado", "Solo el administrador puede gestionar permisos.")
            registrar_en_bitacora(self.usuario, "permiso", "-", "Intento no autorizado")
            return

        permisos = cargar_json(PERMISSIONS_FILE, {"archivos": {}})
        archivo = self.lista.currentItem()
        if not archivo:
            QMessageBox.warning(self, "Error", "Seleccione un archivo.")
            return
        archivo = archivo.text()

        usuarios = list(cargar_json(USERS_FILE, {}).keys())
        usuario_sel, ok = QInputDialog.getItem(self, "Asignar permisos", "Seleccione usuario:", usuarios, 0, False)
        if not ok:
            return
        permisos_disp = ["lectura", "escritura"]
        perm, ok = QInputDialog.getItem(self, "Permiso", "Seleccione permiso:", permisos_disp, 0, False)
        if not ok:
            return

        datos = permisos["archivos"].get(archivo, {"permisos": {}})
        if "permisos" not in datos:
            datos["permisos"] = {}
        if usuario_sel not in datos["permisos"]:
            datos["permisos"][usuario_sel] = []
        if perm not in datos["permisos"][usuario_sel]:
            datos["permisos"][usuario_sel].append(perm)
        permisos["archivos"][archivo] = datos
        guardar_json(PERMISSIONS_FILE, permisos)

        registrar_en_bitacora(self.usuario, "permiso", archivo, f"Concedido {perm} a {usuario_sel}")
        QMessageBox.information(self, "Éxito", "Permiso asignado correctamente.")

    def cerrar_sesion(self):
        self.close()
        self.login_window.show()


# -------------------- LOGIN --------------------

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestor FAT - Login")
        self.setGeometry(700, 400, 400, 250)
        self.setStyleSheet("""
            QWidget { background-color: #0e1a2b; color: white; font-family: 'Segoe UI'; }
            QLineEdit { background-color: #1a273d; border: 1px solid #2b3a57; padding: 6px; color: white; border-radius: 6px; }
            QPushButton { background-color: #0078d7; border: none; padding: 8px; border-radius: 6px; color: white; font-weight: bold; }
            QPushButton:hover { background-color: #3399ff; }
        """)

        layout = QVBoxLayout()
        self.usuario = QLineEdit()
        self.usuario.setPlaceholderText("Usuario")
        self.password = QLineEdit()
        self.password.setPlaceholderText("Contraseña")
        self.password.setEchoMode(QLineEdit.Password)
        self.btn_login = QPushButton("Iniciar sesión")
        self.btn_login.clicked.connect(self.iniciar_sesion)
        self.btn_crear = QPushButton("Crear usuario")
        self.btn_crear.clicked.connect(self.crear_usuario)
        layout.addWidget(QLabel("Gestor FAT - Iniciar sesión"))
        layout.addWidget(self.usuario)
        layout.addWidget(self.password)
        layout.addWidget(self.btn_login)
        layout.addWidget(self.btn_crear)
        self.setLayout(layout)

    def iniciar_sesion(self):
        usuario = self.usuario.text().strip()
        clave = self.password.text().strip()
        usuarios = cargar_json(USERS_FILE, {"admin": "admin123"})
        if usuario in usuarios and usuarios[usuario] == clave:
            registrar_en_bitacora(usuario, "login", "-", "Éxito")
            self.hide()
            self.main_window = MainWindow(usuario, self)
            self.main_window.show()
        else:
            QMessageBox.warning(self, "Error", "Usuario o contraseña incorrectos.")
            registrar_en_bitacora(usuario, "login", "-", "Fallido")

    def crear_usuario(self):
        usuario, ok = QInputDialog.getText(self, "Nuevo usuario", "Ingrese nombre de usuario:")
        if not ok or not usuario:
            return
        password, ok = QInputDialog.getText(self, "Nueva contraseña", "Ingrese contraseña:")
        if not ok or not password:
            return
        usuarios = cargar_json(USERS_FILE, {"admin": "admin123"})
        if usuario in usuarios:
            QMessageBox.warning(self, "Error", "El usuario ya existe.")
        else:
            usuarios[usuario] = password
            guardar_json(USERS_FILE, usuarios)
            QMessageBox.information(self, "Éxito", f"Usuario '{usuario}' creado correctamente.")


# -------------------- EJECUCIÓN PRINCIPAL --------------------

if __name__ == "__main__":
    app = QApplication(sys.argv)
    login = LoginWindow()
    login.show()
    sys.exit(app.exec_())
