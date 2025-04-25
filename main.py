from utils import escuchar_comando, hablar, entrada_texto, obtener_modo_entrada, cambiar_modo_entrada, cargar_modo_entrada_usuario
from commands import (agregar_tarea, eliminar_tarea, mostrar_tareas, modificar_tarea, 
                     agregar_recordatorio, cambiar_categoria, marcar_como_completada, 
                     mostrar_tareas_por_categoria, mostrar_tareas_calendario,
                     sincronizar_todas_tareas_calendario, enviar_recordatorios_email,
                     mostrar_tareas_formato_calendario)
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
    
    # Comandos relacionados con el calendario
    if any(frase in comando for frase in ['calendario', 'agenda', 'eventos']):
        if any(frase in comando for frase in ['sincronizar', 'conectar']):
            return 'sincronizar_calendario'
        elif any(frase in comando for frase in ['mostrar', 'ver', 'listar']):
            return 'ver_calendario'
        elif any(frase in comando for frase in ['formato', 'visualizar']):
            return 'formato_calendario'
        else:
            return 'ver_calendario'  # Por defecto
    
    # Comandos para enviar recordatorios
    if any(frase in comando for frase in ['enviar recordatorios', 'notificar', 'alertas']):
        return 'enviar_recordatorios'
    
    # Comandos para mostrar tareas
    if any(frase in comando for frase in ['muestra', 'muestrame', 'enseñame', 'dame', 'ver', 'lista', 'mostrar']):
        # Buscar si está solicitando tareas de una categoría específica
        if 'categoria' in comando:
            palabras = comando.split()
            for i, palabra in enumerate(palabras):
                if palabra == 'categoria' and i+1 < len(palabras):
                    return ('mostrar_categoria', palabras[i+1])
        return 'mostrar'
    
    # Comandos para agregar tareas
    if any(frase in comando for frase in ['agrega', 'añade', 'crear', 'nueva', 'agregar']):
        partes = comando.split()
        index_comando = -1
        for i, palabra in enumerate(partes):
            if palabra in ['agrega', 'añade', 'crear', 'nueva', 'agregar']:
                index_comando = i
                break
        
        if index_comando != -1:
            tarea = ' '.join(partes[index_comando+1:])
            return ('agregar', tarea)
    
    # Comandos para eliminar tareas
    if any(frase in comando for frase in ['elimina', 'borrar', 'quitar', 'remover', 'eliminar']):
        partes = comando.split()
        index_comando = -1
        for i, palabra in enumerate(partes):
            if palabra in ['elimina', 'borrar', 'quitar', 'remover', 'eliminar']:
                index_comando = i
                break
        
        if index_comando != -1:
            tarea = ' '.join(partes[index_comando+1:])
            return ('eliminar', tarea)
    
    # Comandos para modificar tareas
    if any(frase in comando for frase in ['modificar', 'cambiar', 'reemplazar', 'actualizar']):
        if ' por ' in comando:
            partes = comando.split(' por ')
            primera_parte = partes[0]
            for palabra in ['modificar', 'cambiar', 'reemplazar', 'actualizar']:
                primera_parte = primera_parte.replace(palabra, '')
            tarea_vieja = primera_parte.strip()
            tarea_nueva = partes[1].strip()
            return ('modificar', tarea_vieja, tarea_nueva)
    
    # Comandos para agregar recordatorios
    if any(frase in comando for frase in ['recordar', 'recordatorio', 'recordarme']):
        # Intentar extraer la tarea y la fecha
        match_tarea = re.search(r'(?:recordar|recordatorio|recordarme)\s+(.+?)(?:\s+para\s+el|\s+el\s+|\s+a\s+las|\s+para|\s+en)', comando)
        match_fecha = re.search(r'(?:para\s+el|el)\s+(\d{1,2})\s+de\s+(\w+)', comando)
        match_hora = re.search(r'(?:a\s+las|las)\s+(\d{1,2})(?:\:(\d{1,2}))?', comando)
        
        if match_tarea:
            tarea = match_tarea.group(1).strip()
            
            # Construir fecha y hora
            fecha = datetime.now()
            if match_fecha:
                dia = int(match_fecha.group(1))
                mes_texto = match_fecha.group(2).lower()
                meses = {
                    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
                    'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
                }
                if mes_texto in meses:
                    mes = meses[mes_texto]
                    fecha = fecha.replace(day=dia, month=mes)
            
            hora, minuto = 9, 0  # Por defecto a las 9:00
            if match_hora:
                hora = int(match_hora.group(1))
                if match_hora.group(2):
                    minuto = int(match_hora.group(2))
            
            fecha = fecha.replace(hour=hora, minute=minuto, second=0)
            fecha_str = fecha.strftime("%Y-%m-%d %H:%M:%S")
            
            return ('recordatorio', tarea, fecha_str)
    
    # Comandos para marcar como completada
    if any(frase in comando for frase in ['completar', 'completada', 'terminada', 'finalizar']):
        partes = comando.split()
        index_comando = -1
        for i, palabra in enumerate(partes):
            if palabra in ['completar', 'completada', 'terminada', 'finalizar']:
                index_comando = i
                break
        
        if index_comando != -1:
            tarea = ' '.join(partes[index_comando+1:])
            return ('completar', tarea)
    
    # Comandos para cambiar categoría
    if 'categoria' in comando and any(frase in comando for frase in ['cambiar', 'modificar', 'actualizar']):
        match = re.search(r'(?:cambiar|modificar|actualizar)\s+categoria\s+de\s+(.+?)\s+a\s+(\w+)', comando)
        if match:
            tarea = match.group(1).strip()
            categoria = match.group(2).strip()
            return ('categoria', tarea, categoria)
    
    # Si no se reconoce el comando
    return 'desconocido'

def mostrar_ayuda():
    """Muestra todos los comandos disponibles"""
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
    'mostrar tareas' - Ver todas tus tareas pendientes
    'agregar [tarea]' - Añadir una nueva tarea
    'eliminar [tarea]' - Eliminar una tarea existente
    'modificar [tarea vieja] por [tarea nueva]' - Cambiar una tarea
    'completar [tarea]' - Marcar una tarea como completada
    
    -- Categorías --
    'mostrar categoria [nombre]' - Ver tareas de una categoría
    'cambiar categoria de [tarea] a [categoria]' - Asignar categoría
    
    -- Recordatorios --
    'recordar [tarea] para el [día] de [mes] a las [hora]' - Programar recordatorio
    'enviar recordatorios' - Enviar recordatorios por email
    
    -- Calendario --
    'ver calendario' - Ver próximos eventos
    'sincronizar calendario' - Sincronizar tareas con Google Calendar
    'formato calendario' - Ver tareas en formato calendario
    
    -- Sistema --
    'ayuda' - Mostrar este menú de ayuda
    'salir' - Cerrar el asistente
    """
    return ayuda

def main():
    """Función principal del asistente de tareas"""
    global user_manager
    
    hablar("Bienvenido a tu Asistente de Tareas. ¿Cómo puedo ayudarte hoy?")
    
    while True:
        # Obtener comando del usuario
        if obtener_modo_entrada() == 'voz':
            comando = escuchar_comando()
        else:
            comando = entrada_texto("Tú: ")
        
        # Salir del programa
        if comando in ['salir', 'adios', 'hasta luego', 'cerrar']:
            hablar("Hasta pronto. Que tengas un buen día.")
            break
        
        # Interpretar el comando
        accion = interpretar_comando(comando)
        
        # Comandos que no requieren inicio de sesión
        if accion == 'registrar':
            nombre = entrada_texto("Nombre: ")
            email = entrada_texto("Email: ")
            password = entrada_texto("Contraseña: ", ocultar=True)
            success, mensaje = user_manager.register_user(email, password, nombre)
            hablar(mensaje)
            continue
        
        elif accion == 'login':
            email = entrada_texto("Email: ")
            password = entrada_texto("Contraseña: ", ocultar=True)
            success, mensaje = user_manager.login(email, password)
            hablar(mensaje)
            if success:
                # Cargar preferencias de usuario
                silent_mode = user_manager.get_silent_mode()
                modo = 'texto' if silent_mode else 'voz'
                cambiar_modo_entrada(modo)
                hablar(f"Modo de interacción: {modo}")
            continue
        
        elif accion == 'logout':
            success, mensaje = user_manager.logout()
            hablar(mensaje)
            continue
        
        elif accion == 'ayuda':
            hablar(mostrar_ayuda())
            continue
        
        # Verificar si el usuario ha iniciado sesión
        if not user_manager.current_user:
            hablar("Por favor, inicia sesión primero")
            continue
        
        # Comandos de configuración de modo
        if accion == 'activar_silencioso':
            user_manager.update_user_preference('silent_mode', True)
            cambiar_modo_entrada('texto')
            hablar("Modo silencioso activado")
        
        elif accion == 'desactivar_silencioso':
            user_manager.update_user_preference('silent_mode', False)
            cambiar_modo_entrada('voz')
            hablar("Modo silencioso desactivado")
        
        elif accion == 'toggle_silencioso':
            success, mensaje = user_manager.toggle_silent_mode()
            if success:
                nuevo_modo = 'texto' if user_manager.get_silent_mode() else 'voz'
                cambiar_modo_entrada(nuevo_modo)
                hablar(mensaje)
            else:
                hablar(mensaje)
        
        # Comandos que requieren inicio de sesión
        elif accion == 'mostrar':
            respuesta = mostrar_tareas(user_manager.current_user)
            hablar(respuesta)
        
        elif isinstance(accion, tuple) and accion[0] == 'agregar':
            respuesta = agregar_tarea(accion[1], user_manager.current_user)
            hablar(respuesta)
        
        elif isinstance(accion, tuple) and accion[0] == 'eliminar':
            respuesta = eliminar_tarea(accion[1], user_manager.current_user)
            hablar(respuesta)
        
        elif isinstance(accion, tuple) and accion[0] == 'modificar':
            respuesta = modificar_tarea(accion[1], accion[2], user_manager.current_user)
            hablar(respuesta)
        
        elif isinstance(accion, tuple) and accion[0] == 'recordatorio':
            respuesta = agregar_recordatorio(accion[1], accion[2], user_manager.current_user)
            hablar(respuesta)
        
        elif isinstance(accion, tuple) and accion[0] == 'completar':
            respuesta = marcar_como_completada(accion[1], user_manager.current_user)
            hablar(respuesta)
        
        elif isinstance(accion, tuple) and accion[0] == 'categoria':
            respuesta = cambiar_categoria(accion[1], accion[2], user_manager.current_user)
            hablar(respuesta)
        
        elif isinstance(accion, tuple) and accion[0] == 'mostrar_categoria':
            respuesta = mostrar_tareas_por_categoria(accion[1], user_manager.current_user)
            hablar(respuesta)
        
        # Comandos de calendario
        elif accion == 'ver_calendario':
            respuesta = mostrar_tareas_calendario(user_manager.current_user)
            hablar(respuesta)
        
        elif accion == 'sincronizar_calendario':
            respuesta = sincronizar_todas_tareas_calendario(user_manager.current_user)
            hablar(respuesta)
        
        elif accion == 'formato_calendario':
            respuesta = mostrar_tareas_formato_calendario(user_manager.current_user)
            hablar(respuesta)
        
        elif accion == 'enviar_recordatorios':
            respuesta = enviar_recordatorios_email(user_manager.current_user)
            hablar(respuesta)
        
        else:
            hablar("No entendí el comando. Puedes decir 'ayuda' para ver las opciones disponibles.")

if __name__ == "__main__":
    main()