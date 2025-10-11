import os
import json
import uuid
from datetime import datetime

# Directorio y archivos base
directorio_bloques = 'bloques_datos'
archivo_tabla_fat = 'tabla_fat.json'
tamaño_bloque = 20

# Crear carpeta y archivo inicial si no existen
os.makedirs(directorio_bloques, exist_ok=True)
if not os.path.exists(archivo_tabla_fat):
    with open(archivo_tabla_fat, 'w', encoding='utf-8') as f:
        json.dump([], f, indent=2, ensure_ascii=False)

# Cargar y guardar tabla FAT
def cargar_fat():
    with open(archivo_tabla_fat, 'r', encoding='utf-8') as f:
        return json.load(f)

def guardar_fat(tabla):
    with open(archivo_tabla_fat, 'w', encoding='utf-8') as f:
        json.dump(tabla, f, indent=2, ensure_ascii=False)

# Obtener fecha y hora actual
def ahora():
    return datetime.utcnow().isoformat() + 'Z'

# Crear bloque físico de datos
def crear_bloque(contenido, siguiente_ruta=None, fin_archivo=False):
    bloque_id = str(uuid.uuid4())
    ruta = os.path.join(directorio_bloques, f'bloque_{bloque_id}.json')
    bloque = {
        'datos': contenido,
        'siguiente': siguiente_ruta,
        'fin_archivo': fin_archivo
    }
    with open(ruta, 'w', encoding='utf-8') as f:
        json.dump(bloque, f, ensure_ascii=False, indent=2)
    return ruta

# Leer bloque desde archivo JSON
def leer_bloque(ruta):
    with open(ruta, 'r', encoding='utf-8') as f:
        return json.load(f)

# Eliminar archivo de bloque físico
def eliminar_bloque(ruta):
    try:
        os.remove(ruta)
    except FileNotFoundError:
        pass

# Dividir contenido en bloques de tamaño máximo
def dividir_en_bloques(contenido):
    return [contenido[i:i+tamaño_bloque] for i in range(0, len(contenido), tamaño_bloque)]

# Buscar archivo por nombre en la tabla FAT
def buscar_archivo(tabla, nombre):
    for entrada in tabla:
        if entrada['nombre'] == nombre:
            return entrada
    return None

# Crear nuevo archivo y sus bloques
def crear_archivo(tabla, nombre, contenido, propietario):
    if buscar_archivo(tabla, nombre):
        print('Ya existe un archivo con ese nombre.')
        return
    bloques = dividir_en_bloques(contenido)
    ruta_anterior = None
    ruta_inicial = None
    for i, parte in enumerate(bloques):
        fin = (i == len(bloques) - 1)
        ruta = crear_bloque(parte, None, fin)
        if ruta_anterior:
            bloque_prev = leer_bloque(ruta_anterior)
            bloque_prev['siguiente'] = ruta
            with open(ruta_anterior, 'w', encoding='utf-8') as f:
                json.dump(bloque_prev, f, ensure_ascii=False, indent=2)
        else:
            ruta_inicial = ruta
        ruta_anterior = ruta

    entrada = {
        'nombre': nombre,
        'ruta_datos': ruta_inicial,
        'en_papelera': False,
        'tamaño': len(contenido),
        'creado': ahora(),
        'modificado': ahora(),
        'eliminado': None,
        'propietario': propietario,
        'permisos': {propietario: {'lectura': True, 'escritura': True}}
    }
    tabla.append(entrada)
    guardar_fat(tabla)
    print(f'Archivo "{nombre}" creado con {len(bloques)} bloques.')

# Concatenar contenido de todos los bloques
def leer_contenido_archivo(entrada):
    ruta = entrada['ruta_datos']
    datos = []
    while ruta:
        bloque = leer_bloque(ruta)
        datos.append(bloque.get('datos', ''))
        ruta = bloque.get('siguiente')
    return ''.join(datos)

# Listar archivos activos
def listar_archivos(tabla):
    for e in tabla:
        if not e['en_papelera']:
            print(f"{e['nombre']} (propietario: {e['propietario']}) tamaño: {e['tamaño']} caracteres creado: {e['creado']}")

# Listar archivos en papelera
def listar_papelera(tabla):
    for e in tabla:
        if e['en_papelera']:
            print(f"{e['nombre']} (propietario: {e['propietario']}) eliminado: {e['eliminado']}")

# Verificar permisos
def tiene_permiso(entrada, usuario, permiso):
    if entrada['propietario'] == usuario:
        return True
    permisos_usuario = entrada.get('permisos', {}).get(usuario, {})
    return permisos_usuario.get(permiso, False)

# Abrir archivo y mostrar metadatos
def abrir_archivo(tabla, nombre, usuario):
    entrada = buscar_archivo(tabla, nombre)
    if not entrada:
        print('Archivo no encontrado.')
        return
    if entrada['en_papelera']:
        print('El archivo está en la papelera. Recupérelo primero.')
        return
    if not tiene_permiso(entrada, usuario, 'lectura'):
        print('No tiene permiso de lectura.')
        return
    contenido = leer_contenido_archivo(entrada)
    print('\n--- METADATOS ---')
    for k, v in entrada.items():
        if k != 'ruta_datos':
            print(f'{k}: {v}')
    print('\n--- CONTENIDO ---')
    print(contenido)

# Modificar archivo existente
def modificar_archivo(tabla, nombre, usuario):
    entrada = buscar_archivo(tabla, nombre)
    if not entrada:
        print('Archivo no encontrado.')
        return
    if entrada['en_papelera']:
        print('El archivo está en la papelera.')
        return
    if not tiene_permiso(entrada, usuario, 'escritura'):
        print('No tiene permiso de escritura.')
        return
    print('Contenido actual:\n')
    print(leer_contenido_archivo(entrada))
    print('\nIngrese nuevo contenido. Termine con ":wq"')
    lineas = []
    while True:
        linea = input()
        if linea.strip() == ':wq':
            break
        lineas.append(linea)
    nuevo_contenido = '\n'.join(lineas)
    bloques = dividir_en_bloques(nuevo_contenido)
    ruta_anterior = None
    ruta_inicial = None
    for i, parte in enumerate(bloques):
        fin = (i == len(bloques) - 1)
        ruta = crear_bloque(parte, None, fin)
        if ruta_anterior:
            bloque_prev = leer_bloque(ruta_anterior)
            bloque_prev['siguiente'] = ruta
            with open(ruta_anterior, 'w', encoding='utf-8') as f:
                json.dump(bloque_prev, f, ensure_ascii=False, indent=2)
        else:
            ruta_inicial = ruta
        ruta_anterior = ruta
    # Eliminar bloques antiguos
    ruta_vieja = entrada['ruta_datos']
    while ruta_vieja:
        try:
            bloque = leer_bloque(ruta_vieja)
        except FileNotFoundError:
            break
        siguiente = bloque.get('siguiente')
        eliminar_bloque(ruta_vieja)
        ruta_vieja = siguiente
    entrada['ruta_datos'] = ruta_inicial
    entrada['tamaño'] = len(nuevo_contenido)
    entrada['modificado'] = ahora()
    guardar_fat(tabla)
    print('Archivo modificado correctamente.')

# Mover archivo a papelera
def eliminar_archivo(tabla, nombre, usuario):
    entrada = buscar_archivo(tabla, nombre)
    if not entrada:
        print('Archivo no encontrado.')
        return
    if entrada['en_papelera']:
        print('El archivo ya está en la papelera.')
        return
    if entrada['propietario'] != usuario:
        print('Solo el propietario puede eliminar el archivo.')
        return
    entrada['en_papelera'] = True
    entrada['eliminado'] = ahora()
    guardar_fat(tabla)
    print('Archivo movido a la papelera.')

# Recuperar archivo desde la papelera
def recuperar_archivo(tabla, nombre, usuario):
    entrada = buscar_archivo(tabla, nombre)
    if not entrada:
        print('Archivo no encontrado.')
        return
    if not entrada['en_papelera']:
        print('El archivo no está en la papelera.')
        return
    if entrada['propietario'] != usuario:
        print('Solo el propietario puede recuperar el archivo.')
        return
    entrada['en_papelera'] = False
    entrada['eliminado'] = None
    entrada['modificado'] = ahora()
    guardar_fat(tabla)
    print('Archivo recuperado de la papelera.')

# Asignar permisos a otros usuarios
def asignar_permisos(tabla, nombre, usuario):
    entrada = buscar_archivo(tabla, nombre)
    if not entrada:
        print('Archivo no encontrado.')
        return
    if entrada['propietario'] != usuario:
        print('Solo el propietario puede asignar permisos.')
        return
    print('Ingrese el usuario al que desea asignar o revocar permisos:')
    otro = input().strip()
    print('Permitir lectura (s/n):')
    r = input().strip().lower() == 's'
    print('Permitir escritura (s/n):')
    w = input().strip().lower() == 's'
    if 'permisos' not in entrada:
        entrada['permisos'] = {}
    entrada['permisos'][otro] = {'lectura': r, 'escritura': w}
    guardar_fat(tabla)
    print('Permisos actualizados.')

# Mostrar ayuda de comandos
def mostrar_ayuda():
    print('''Comandos disponibles:
crear - Crear archivo
listar - Listar archivos activos
papelera - Mostrar archivos eliminados
abrir - Abrir y mostrar archivo
modificar - Modificar archivo (requiere permiso de escritura)
eliminar - Mover archivo a papelera
recuperar - Restaurar archivo desde papelera
permisos - Asignar permisos (solo propietario)
meta - Mostrar metadatos del archivo
salir - Salir del programa
ayuda - Mostrar esta ayuda\n''')

# Mostrar metadatos de un archivo
def mostrar_metadatos(tabla, nombre):
    entrada = buscar_archivo(tabla, nombre)
    if not entrada:
        print('Archivo no encontrado.')
        return
    for k, v in entrada.items():
        print(f'{k}: {v}')

# Función principal del sistema
def main():
    print('Simulador de sistema FAT')
    print('Ingrese su nombre de usuario ("admin" es el administrador):')
    usuario_actual = input().strip() or 'admin'
    print(f'Usuario activo: {usuario_actual}')
    tabla = cargar_fat()
    mostrar_ayuda()
    while True:
        comando = input('\n> ').strip().lower()
        if comando == 'crear':
            print('Nombre del archivo:')
            nombre = input().strip()
            print('Ingrese contenido. Termine con ":wq" en una nueva línea:')
            lineas = []
            while True:
                linea = input()
                if linea.strip() == ':wq':
                    break
                lineas.append(linea)
            contenido = '\n'.join(lineas)
            crear_archivo(tabla, nombre, contenido, usuario_actual)
        elif comando == 'listar':
            listar_archivos(tabla)
        elif comando == 'papelera':
            listar_papelera(tabla)
        elif comando == 'abrir':
            print('Nombre del archivo:')
            nombre = input().strip()
            abrir_archivo(tabla, nombre, usuario_actual)
        elif comando == 'modificar':
            print('Nombre del archivo:')
            nombre = input().strip()
            modificar_archivo(tabla, nombre, usuario_actual)
        elif comando == 'eliminar':
            print('Nombre del archivo:')
            nombre = input().strip()
            eliminar_archivo(tabla, nombre, usuario_actual)
        elif comando == 'recuperar':
            print('Nombre del archivo:')
            nombre = input().strip()
            recuperar_archivo(tabla, nombre, usuario_actual)
        elif comando == 'permisos':
            print('Nombre del archivo:')
            nombre = input().strip()
            asignar_permisos(tabla, nombre, usuario_actual)
        elif comando == 'meta':
            print('Nombre del archivo:')
            nombre = input().strip()
            mostrar_metadatos(tabla, nombre)
        elif comando == 'ayuda':
            mostrar_ayuda()
        elif comando == 'salir':
            break
        else:
            print('Comando no reconocido. Escriba "ayuda" para ver opciones.')


main()