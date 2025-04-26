from utils import escuchar_comando, hablar, entrada_texto, obtener_modo_entrada, cambiar_modo_entrada, cargar_modo_entrada_usuario
from commands import (agregar_tarea, eliminar_tarea, mostrar_tareas, modificar_tarea,
                     agregar_recordatorio, cambiar_categoria, marcar_como_completada,
                     mostrar_tareas_por_categoria, mostrar_tareas_formato_calendario, # Se mantiene formato calendario local
                     mostrar_tareas_calendario_local, generar_reporte_mensual) # Importar función local y nueva función de reporte
from user_management import UserManager
import os
import re
from datetime import datetime

# Variable global para el gestor de usuarios
user_manager = UserManager()

def interpretar_comando(comando):
    """Interpreta comandos de manera más flexible"""
    comando = comando.lower().strip()

    # Comandos para registrarse o iniciar sesión
    if any(frase in comando for frase in ['registrar', 'registro', 'crear cuenta']):
        return 'registrar'

    if any(frase in comando for frase in ['iniciar sesion', 'login', 'ingresar', 'acceder']):
        return 'login'

    if any(frase in comando for frase in ['cerrar sesion', 'logout', 'salir cuenta']):
        return 'logout'

    # Comando para mostrar ayuda
    if any(frase in comando for frase in ['ayuda', 'comandos', 'que puedes hacer']):
        return 'ayuda'

    # Comandos relacionados con el modo silencioso
    if any(frase in comando for frase in ['modo silencioso', 'modo texto']):
        if 'activar' in comando or 'encender' in comando:
            return 'activar_silencioso'
        elif 'desactivar' in comando or 'apagar' in comando:
            return 'desactivar_silencioso'
        else:
            return 'toggle_silencioso'  # Por defecto conmuta

    # Comandos para mostrar tareas (incluyendo por categoría)
    if any(frase in comando for frase in ['muestra', 'muestrame', 'enseñame', 'dame', 'ver', 'lista', 'mostrar']):
        # Buscar si está solicitando tareas de una categoría específica
        match_categoria = re.search(r'(?:mostrar|ver|lista)\s+tareas\s+de\s+categoria\s+(\w+)', comando)
        if match_categoria:
             return ('mostrar_categoria', match_categoria.group(1))

        return 'mostrar' # Mostrar todas las tareas si no se especifica categoría

    # Comandos para agregar tareas
    if any(frase in comando for frase in ['agrega', 'añade', 'crear', 'nueva', 'agregar']):
        # Extraer la descripción de la tarea después del comando de agregar
        match_tarea = re.search(r'(?:agrega|añade|crear|nueva|agregar)\s+(.+)', comando)
        if match_tarea:
             tarea = match_tarea.group(1).strip()
             if tarea: # Asegurarse de que haya algo después del comando
                return ('agregar', tarea)
        return 'desconocido' # No se especificó tarea para agregar


    # Comandos para eliminar tareas
    if any(frase in comando for frase in ['elimina', 'borrar', 'quitar', 'remover', 'eliminar']):
        # Extraer la descripción de la tarea después del comando de eliminar
        match_tarea = re.search(r'(?:elimina|borrar|quitar|remover|eliminar)\s+(.+)', comando)
        if match_tarea:
            tarea = match_tarea.group(1).strip()
            if tarea: # Asegurarse de que haya algo después del comando
                return ('eliminar', tarea)
        return 'desconocido' # No se especificó tarea para eliminar

    # Comandos para modificar tareas
    if any(frase in comando for frase in ['modificar', 'cambiar', 'reemplazar', 'actualizar']):
        # Buscar el patrón "modificar [tarea vieja] por [tarea nueva]"
        match = re.search(r'(?:modificar|cambiar|reemplazar|actualizar)\s+(.+?)\s+por\s+(.+)', comando)
        if match:
            tarea_vieja = match.group(1).strip()
            tarea_nueva = match.group(2).strip()
            if tarea_vieja and tarea_nueva: # Asegurarse de que ambas partes existan
                 return ('modificar', tarea_vieja, tarea_nueva)
        return 'desconocido' # Formato de modificación incorrecto


    # Comandos para agregar recordatorios
    if any(frase in comando for frase in ['recordar', 'recordatorio', 'recordarme']):
        # Intentar extraer la tarea y la fecha/hora
        # Patrón más flexible para capturar la tarea y luego intentar encontrar la fecha/hora
        match_tarea_fecha = re.search(r'(?:recordar|recordatorio|recordarme)\s+(.+)', comando)

        if match_tarea_fecha:
            resto_comando = match_tarea_fecha.group(1).strip()

            # Buscar patrones comunes de fecha y hora dentro del resto del comando
            match_fecha_hora = re.search(r'(?:para\s+el|el)\s+(\d{1,2})\s+de\s+(\w+)(?:\s+(?:a\s+las|las)\s+(\d{1,2})(?:\:(\d{1,2}))?)?', resto_comando)
            match_solo_hora = re.search(r'(?:a\s+las|las)\s+(\d{1,2})(?:\:(\d{1,2}))?', resto_comando)
            match_fecha_iso = re.search(r'(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})', resto_comando) # YYYY-MM-DD HH:MM:SS


            tarea = resto_comando # Por defecto, todo después del comando es la tarea
            fecha_str = None

            if match_fecha_iso:
                 # Si encontramos formato ISO, usamos ese directamente
                 fecha_str = f"{match_fecha_iso.group(1)} {match_fecha_iso.group(2)}"
                 # Intentar extraer la tarea antes de la fecha ISO
                 tarea_part = resto_comando.split(match_fecha_iso.group(0))[0].strip()
                 if tarea_part:
                      tarea = tarea_part

            elif match_fecha_hora:
                 # Si encontramos el patrón "día de mes a las hora:minuto"
                 dia = int(match_fecha_hora.group(1))
                 mes_texto = match_fecha_hora.group(2).lower()
                 meses = {
                    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
                    'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
                }
                 mes = meses.get(mes_texto)
                 if mes:
                    # Usar el año actual, podrías añadir lógica para el año siguiente si la fecha ya pasó
                    año = datetime.now().year
                    hora = int(match_fecha_hora.group(3)) if match_fecha_hora.group(3) else 9 # Hora por defecto 9
                    minuto = int(match_fecha_hora.group(4)) if match_fecha_hora.group(4) else 0 # Minuto por defecto 0

                    try:
                        fecha = datetime(año, mes, dia, hora, minuto, 0)
                        fecha_str = fecha.strftime("%Y-%m-%d %H:%M:%S")

                        # Intentar extraer la tarea antes de la parte de fecha/hora
                        tarea_part = resto_comando.split(match_fecha_hora.group(0))[0].strip()
                        if tarea_part:
                            tarea = tarea_part

                    except ValueError:
                         # Fecha inválida (ej: día 31 en un mes de 30)
                         return 'desconocido' # O un mensaje de error más específico

            elif match_solo_hora:
                 # Si solo encontramos la hora, usar la fecha de hoy
                 hora = int(match_solo_hora.group(1))
                 minuto = int(match_solo_hora.group(2)) if match_solo_hora.group(2) else 0
                 fecha = datetime.now().replace(hour=hora, minute=minuto, second=0, microsecond=0)
                 # Si la hora ya pasó hoy, programar para mañana
                 if fecha <= datetime.now():
                      fecha += timedelta(days=1)
                 fecha_str = fecha.strftime("%Y-%m-%d %H:%M:%S")

                 # Intentar extraer la tarea antes de la parte de hora
                 tarea_part = resto_comando.split(match_solo_hora.group(0))[0].strip()
                 if tarea_part:
                     tarea = tarea_part


            if fecha_str and tarea:
                return ('recordatorio', tarea, fecha_str)
            elif tarea and not fecha_str:
                 # Si se menciona la tarea pero no se detecta fecha/hora válida
                 return 'desconocido' # O indicar que falta fecha/hora

        return 'desconocido' # No se detectó el patrón de recordatorio

    # Comandos para marcar como completada
    if any(frase in comando for frase in ['completar', 'completada', 'terminada', 'finalizar']):
        # Extraer la descripción de la tarea después del comando
        match_tarea = re.search(r'(?:completar|completada|terminada|finalizar)\s+(.+)', comando)
        if match_tarea:
            tarea = match_tarea.group(1).strip()
            if tarea: # Asegurarse de que haya algo después del comando
                return ('completar', tarea)
        return 'desconocido' # No se especificó tarea para completar

    # Comandos para cambiar categoría
    if 'categoria' in comando and any(frase in comando for frase in ['cambiar', 'modificar', 'actualizar']):
        # Buscar el patrón "cambiar categoria de [tarea] a [categoria]"
        match = re.search(r'(?:cambiar|modificar|actualizar)\s+categoria\s+de\s+(.+?)\s+a\s+(\w+)', comando)
        if match:
            tarea = match.group(1).strip()
            categoria = match.group(2).strip()
            if tarea and categoria: # Asegurarse de que ambas partes existan
                 return ('categoria', tarea, categoria)
        return 'desconocido' # Formato de cambio de categoría incorrecto

    # Comandos relacionados con el calendario (ahora local)
    if any(frase in comando for frase in ['calendario', 'agenda', 'eventos']):
        # Mantener 'formato calendario' que ya usa datos locales
        if any(frase in comando for frase in ['formato', 'visualizar']):
             return 'formato_calendario'
        # 'ver calendario' ahora mostrará las tareas con fecha límite del archivo local
        elif any(frase in comando for frase in ['mostrar', 'ver', 'listar']):
             return 'ver_calendario_local' # Nuevo nombre interno

        return 'ver_calendario_local'  # Por defecto muestra calendario local

    # Comando para generar reporte mensual
    # Ejemplo: "generar reporte de tareas de octubre de 2023"
    match_reporte = re.search(r'(?:generar|crear|mostrar)\s+reporte(?:\s+de\s+tareas)?\s+de\s+(\w+)\s+de\s+(\d{4})', comando)
    if match_reporte:
        mes_texto = match_reporte.group(1).lower()
        año_str = match_reporte.group(2)
        meses = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
            'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }
        mes = meses.get(mes_texto)
        try:
            año = int(año_str)
            if mes: # Asegurarse de que el nombre del mes sea válido
                 return ('generar_reporte', año, mes)
        except ValueError:
             pass # Año inválido

    # Si no se reconoce el comando
    return 'desconocido'

def mostrar_ayuda():
    """Muestra todos los comandos disponibles (actualizada)"""
    ayuda = """
    Comandos disponibles:

    -- Gestión de usuario --
    'registrar' - Crear una nueva cuenta
    'iniciar sesion' - Acceder a tu cuenta
    'cerrar sesion' - Salir de tu cuenta

    -- Modo de interacción --
    'modo silencioso' - Conmutar entre modo texto y voz
    'activar modo silencioso' - Usar solo texto (sin voz)
    'desactivar modo silencioso' - Volver al modo con voz

    -- Tareas --
    'mostrar tareas' - Ver todas tus tareas pendientes y completadas
    'agregar [descripción de la tarea]' - Añadir una nueva tarea
    'eliminar [descripción de la tarea]' - Eliminar una tarea existente (puedes usar palabras clave)
    'modificar [tarea vieja] por [tarea nueva]' - Cambiar la descripción de una tarea (puedes usar palabras clave para la tarea vieja)
    'completar [descripción de la tarea]' - Marcar una tarea como completada (puedes usar palabras clave)

    -- Categorías --
    'mostrar categoria [nombre]' - Ver tareas de una categoría específica
    'cambiar categoria de [tarea] a [categoria]' - Asignar una categoría a una tarea (puedes usar palabras clave para la tarea)

    -- Recordatorios (Locales) --
    'recordar [tarea] para el [día] de [mes] a las [hora:minutos]' - Programar una fecha y hora límite para una tarea
    'recordar [tarea] a las [hora:minutos]' - Programar una hora límite para hoy o mañana

    -- Calendario (Local) --
    'ver calendario' - Ver tus tareas con fecha límite próximas
    'formato calendario' - Ver tus tareas con fecha límite organizadas por día

    -- Reportes --
    'generar reporte de [mes] de [año]' - Genera un reporte mensual de tareas completadas y pendientes

    -- Sistema --
    'ayuda' - Mostrar este menú de ayuda
    'salir' - Cerrar el asistente
    """
    return ayuda

def main():
    """Función principal del asistente de tareas"""
    global user_manager

   

    print("Iniciando modo consola. Para usar la GUI, ejecuta gui.py")
    # Cargar preferencias de usuario si existe el archivo de usuarios
    if os.path.exists("usuarios.json"):
         # Intentar cargar un usuario por defecto o guiar al usuario a loguearse
         print("Por favor, inicia sesión o regístrate.")
        
         pass # No hace nada en modo consola por ahora

    # La lógica principal de la aplicación se ha trasladado a la clase MainWindow en gui.py
    # para ser ejecutada después de un inicio de sesión exitoso en la GUI.


# Si este script es el punto de entrada, ejecutar la función main (modo consola básico)
if __name__ == "__main__":
    main()
