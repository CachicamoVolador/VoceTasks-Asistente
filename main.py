from utils import escuchar_comando, hablar, entrada_texto, obtener_modo_entrada, cambiar_modo_entrada, cargar_modo_entrada_usuario
from commands import (
    agregar_tarea,
    eliminar_tarea,
    mostrar_tareas,
    modificar_tarea,
    marcar_como_completada,
    generar_reporte
)
from user_management import UserManager
import os
import re
from datetime import datetime, timedelta
import parsedatetime as pdt
from parsedatetime import Calendar, Constants

user_manager = UserManager()

def limpiar_conectores_fecha(texto):
    """Elimina conectores de fecha comunes del final del texto."""
    conectores = ["para el", "para la", "para en", "para", "el", "en", "cuando sea el", "cuando sea", "a las", "a la"]
    texto_lower = texto.lower()
    for conector in sorted(conectores, key=len, reverse=True): 
        if texto_lower.endswith(f" {conector}"):
            return texto[:-len(f" {conector}")].strip()
    return texto

def interpretar_comando(comando):
    """Interpreta comandos de manera más flexible"""
    ahora_inicio_interprete = datetime.now()
    print(f"DEBUG main.py - datetime.now() al inicio de interpretar_comando: {ahora_inicio_interprete}") 
    comando = comando.lower().strip()
    comando = re.sub(r'\s+', ' ', comando) # <-- MEJORA: Normalizar espacios

    cal_pdt_en = Calendar(Constants("en_US", usePyICU=False))

    # Gestión de Usuario
    if any(frase in comando for frase in ['registrar', 'registro', 'crear cuenta', 'nueva cuenta']): # Añadido sinónimo
        return 'registrar'
    if any(frase in comando for frase in ['iniciar sesion', 'login', 'ingresar', 'acceder', 'entrar']): # Añadido sinónimo
        return 'login'
    if any(frase in comando for frase in ['cerrar sesion', 'logout', 'salir cuenta', 'desconectar']): # Añadido sinónimo
        return 'logout'
    
    # Ayuda y Manual
    if any(frase in comando for frase in ['ayuda', 'comandos', 'que puedes hacer', 'manual', 'tutorial', 'instrucciones']): # Añadido sinónimos
        return 'ayuda'

    # Modo Silencioso
    if any(frase in comando for frase in ['modo silencioso', 'modo texto', 'silencio']): # Añadido sinónimo
        if 'activar' in comando or 'encender' in comando or 'pon' in comando and 'silencio' in comando :
            return 'activar_silencioso'
        elif 'desactivar' in comando or 'apagar' in comando or 'quita' in comando and 'silencio' in comando:
            return 'desactivar_silencioso'
        else:
            return 'toggle_silencioso'

    # Mostrar Tareas
    if any(frase in comando for frase in ['muestra', 'muestrame', 'enseñame', 'dame', 'ver', 'lista', 'listar', 'mostrar', 'dime mis', 'que tareas tengo', 'cuales son mis tareas']): # Añadido sinónimos
        match_categoria = re.search(r'(?:mostrar|ver|lista|listar)\s+tareas\s+de\s+categor[ií]a\s+([\w\s]+)', comando, re.IGNORECASE)
        if match_categoria:
             return ('mostrar_categoria', match_categoria.group(1).strip())
        return 'mostrar'

    # Agregar Tareas
    if any(frase in comando for frase in ['agrega', 'añade', 'anota', 'crear', 'nueva', 'nuevo', 'agregar', 'apunta', 'registrar tarea']): # Añadido sinónimos
        texto_payload = ""
        # Primero el patrón más específico que incluye "tarea"
        match_cmd_tarea = re.match(r'(?:agrega|añade|anota|crear|nueva|nuevo|agregar|apunta|registrar tarea)\s+tarea\s+(.+)', comando, re.IGNORECASE)
        if match_cmd_tarea:
            texto_payload = match_cmd_tarea.group(1).strip()
        else: # Luego el patrón más general
            match_cmd_simple = re.match(r'(?:agrega|añade|anota|crear|nueva|nuevo|agregar|apunta|registrar tarea)\s+(.+)', comando, re.IGNORECASE)
            if match_cmd_simple:
                texto_payload = match_cmd_simple.group(1).strip()
            else:
                return ('agregar_sin_info', None, None, None)

        if not texto_payload:
            return ('agregar_sin_info', None, None, None)

        descripcion_final = texto_payload
        fecha_extraida_str = None
        categoria_extraida_str = None
        texto_para_procesar_fecha_y_desc = texto_payload
        
        match_cat = re.search(r'(.*?)\s*(?:en\s+categor[ií]a|categor[ií]a)\s+([\w\s]+?)(?:\s+(?:para|el|en|cuando)|$)', texto_para_procesar_fecha_y_desc, re.IGNORECASE)
        
        if match_cat:
            parte_antes_cat_keyword = match_cat.group(1).strip()
            categoria_potencial = match_cat.group(2).strip()
            texto_despues_nombre_cat = texto_para_procesar_fecha_y_desc[match_cat.end(2):].strip() 
            
            ahora_ref_cat_check = datetime.now()
            _, cat_is_date_flag = cal_pdt_en.parseDT(categoria_potencial.replace("mañana", "tomorrow"), ahora_ref_cat_check)

            es_fecha_mas_explicita_despues = False
            if texto_despues_nombre_cat:
                 texto_despues_para_check = texto_despues_nombre_cat.replace("mañana", "tomorrow")
                 _, es_fecha_mas_explicita_despues_flag = cal_pdt_en.parseDT(texto_despues_para_check, ahora_ref_cat_check)
                 if es_fecha_mas_explicita_despues_flag > 0 and (texto_despues_nombre_cat.lower().startswith("para") or texto_despues_nombre_cat.lower().startswith("el")):
                     es_fecha_mas_explicita_despues = True

            if categoria_potencial and not (cat_is_date_flag > 0 and es_fecha_mas_explicita_despues):
                categoria_extraida_str = categoria_potencial
                texto_para_procesar_fecha_y_desc = (parte_antes_cat_keyword + " " + texto_despues_nombre_cat).strip()
                descripcion_final = texto_para_procesar_fecha_y_desc
        
        palabras_para_fecha = texto_para_procesar_fecha_y_desc.split()
        descripcion_final = texto_para_procesar_fecha_y_desc

        if palabras_para_fecha:
            for i in range(min(5, len(palabras_para_fecha)), 0, -1): 
                posible_fecha_texto_original = " ".join(palabras_para_fecha[len(palabras_para_fecha)-i:])
                posible_fecha_texto_para_pdt = posible_fecha_texto_original.replace("mañana", "tomorrow")
                
                ahora_ref_fecha = datetime.now()
                print(f"DEBUG main.py - Usando en_US. Ref: {ahora_ref_fecha}. Parseando: '{posible_fecha_texto_para_pdt}'")
                fecha_dt_obj, parse_status = cal_pdt_en.parseDT(posible_fecha_texto_para_pdt, ahora_ref_fecha)

                if parse_status > 0:
                    desc_candidata = " ".join(palabras_para_fecha[:len(palabras_para_fecha)-i]).strip()
                    desc_candidata = limpiar_conectores_fecha(desc_candidata)
                    if desc_candidata: 
                        descripcion_final = desc_candidata
                        fecha_extraida_str = fecha_dt_obj.strftime("%Y-%m-%d %H:%M:%S")
                        break 
                    else: 
                        if categoria_extraida_str:
                            return ('agregar_sin_descripcion_con_fecha_cat', fecha_dt_obj.strftime("%Y-%m-%d %H:%M:%S"), categoria_extraida_str)
                        else:
                            return ('agregar_sin_descripcion_con_fecha', fecha_dt_obj.strftime("%Y-%m-%d %H:%M:%S"), None)
            
        if not fecha_extraida_str : 
            descripcion_final = limpiar_conectores_fecha(descripcion_final)

        if not descripcion_final.strip():
            if fecha_extraida_str and categoria_extraida_str:
                return ('agregar_sin_descripcion_con_fecha_cat', fecha_extraida_str, categoria_extraida_str)
            elif fecha_extraida_str:
                return ('agregar_sin_descripcion_con_fecha', fecha_extraida_str, None)
            elif categoria_extraida_str:
                return ('agregar_sin_descripcion_con_cat', None, categoria_extraida_str)
            else:
                return ('agregar_sin_info', None, None, None)

        if not fecha_extraida_str and not categoria_extraida_str:
            ahora_ref_desc_check = datetime.now()
            texto_desc_para_check_fecha = descripcion_final.replace("mañana", "tomorrow")
            dt_obj_desc_check, ps_desc_check = cal_pdt_en.parseDT(texto_desc_para_check_fecha, ahora_ref_desc_check)
            if ps_desc_check > 0 and len(descripcion_final.split()) <= 3: 
                return ('agregar_sin_descripcion_con_fecha', dt_obj_desc_check.strftime("%Y-%m-%d %H:%M:%S"), None)

        return ('agregar', descripcion_final.strip(), fecha_extraida_str, categoria_extraida_str)

    # Eliminar Tareas
    if any(frase in comando for frase in ['elimina', 'borrar', 'quitar', 'remover', 'descartar', 'eliminar']): # Añadido sinónimos
        match_tarea = re.search(r'(?:elimina|borrar|quitar|remover|descartar|eliminar)\s+(.+)', comando, re.IGNORECASE)
        if match_tarea:
            tarea = match_tarea.group(1).strip()
            if tarea: return ('eliminar', tarea)
        return 'desconocido'

    # Modificar Tareas
    if any(frase in comando for frase in ['modificar', 'cambiar', 'reemplazar', 'actualizar', 'editar']): # Añadido sinónimo
        ahora_ref_mod = datetime.now()
        cal_pdt_en_mod = Calendar(Constants("en_US", usePyICU=False))

        match_desc = re.search(r'(?:modificar|editar|cambiar)\s+descripci[oó]n\s+de\s+(.+?)\s+a\s+(.+)', comando, re.IGNORECASE) # Añadido 'editar', 'cambiar'
        if match_desc: return ('modificar_descripcion', match_desc.group(1).strip(), match_desc.group(2).strip())
        
        match_fecha = re.search(r'(?:modificar|editar|cambiar)\s+fecha\s+de\s+(.+?)\s+a\s+(.+)', comando, re.IGNORECASE) # Añadido 'editar', 'cambiar'
        if match_fecha:
            tarea_orig_fecha = match_fecha.group(1).strip()
            nueva_fecha_texto_orig = match_fecha.group(2).strip()
            nueva_fecha_texto_pdt = nueva_fecha_texto_orig.replace("mañana", "tomorrow")
            print(f"DEBUG main.py - Modificar fecha. Ref: {ahora_ref_mod}. Parseando: '{nueva_fecha_texto_pdt}'")
            dt_obj_fecha, ps_fecha = cal_pdt_en_mod.parseDT(nueva_fecha_texto_pdt, ahora_ref_mod)
            if ps_fecha > 0: return ('modificar_fecha', tarea_orig_fecha, dt_obj_fecha.strftime("%Y-%m-%d %H:%M:%S"))
            else: return ('modificar_fecha_invalida', tarea_orig_fecha, nueva_fecha_texto_orig)
        
        match_cat_mod = re.search(r'(?:modificar|editar|cambiar)\s+categor[ií]a\s+de\s+(.+?)\s+a\s+([\w\s]+)', comando, re.IGNORECASE) # Añadido 'editar', 'cambiar'
        if match_cat_mod: return ('modificar_categoria', match_cat_mod.group(1).strip(), match_cat_mod.group(2).strip())
        
        match_general = re.search(r'(?:modificar|cambiar|reemplazar|actualizar|editar)\s+(.+?)\s+por\s+(.+)', comando, re.IGNORECASE) # Añadido 'editar'
        if match_general: return ('modificar_descripcion', match_general.group(1).strip(), match_general.group(2).strip())
        return 'desconocido_modificar'

    # Recordatorios (revisar si esta lógica sigue siendo necesaria o si 'agregar' la cubre)
    if any(frase in comando for frase in ['recordar', 'recordatorio', 'recordarme', 'poner fecha limite', 'establecer limite', 'fijar fecha']): # Añadido sinónimo
        ahora_ref_rec = datetime.now()
        cal_pdt_en_rec = Calendar(Constants("en_US", usePyICU=False))
        # ... (resto de la lógica de recordatorio, usando cal_pdt_en_rec y reemplazo de "mañana")
        match_rec_conector = re.search(r'(?:recordar|recordatorio|recordarme|poner fecha limite a|establecer limite para|fijar fecha para)\s+(.+?)\s+(?:para el|el|para|con limite|para cuando sea el|cuando sea el|cuando sea|para cuando)\s+(.+)', comando, re.IGNORECASE)
        if match_rec_conector:
            desc_rec = match_rec_conector.group(1).strip()
            fecha_texto_rec_orig = match_rec_conector.group(2).strip()
            fecha_texto_rec_pdt = fecha_texto_rec_orig.replace("mañana", "tomorrow")
            print(f"DEBUG main.py - Recordar conector. Ref: {ahora_ref_rec}. Parseando: '{fecha_texto_rec_pdt}'")
            dt_obj_rec, ps_rec = cal_pdt_en_rec.parseDT(fecha_texto_rec_pdt, ahora_ref_rec)
            if ps_rec > 0: return ('agregar', limpiar_conectores_fecha(desc_rec), dt_obj_rec.strftime("%Y-%m-%d %H:%M:%S"), None) 
            else: return ('recordatorio_sin_fecha_clara', desc_rec, fecha_texto_rec_orig)
        
        match_rec_simple = re.search(r'(?:recordar|recordatorio|recordarme|poner fecha limite|establecer limite|fijar fecha)\s+(.+)', comando, re.IGNORECASE)
        if match_rec_simple:
            texto_completo_rec = match_rec_simple.group(1).strip()
            palabras_rec = texto_completo_rec.split()
            if palabras_rec:
                for i in range(min(len(palabras_rec), 5), 0, -1):
                    segmento_fecha_candidato_rec_orig = " ".join(palabras_rec[len(palabras_rec)-i:])
                    segmento_fecha_candidato_rec_pdt = segmento_fecha_candidato_rec_orig.replace("mañana", "tomorrow")
                    print(f"DEBUG main.py - Recordar simple. Ref: {ahora_ref_rec}. Parseando: '{segmento_fecha_candidato_rec_pdt}'")
                    dt_obj_rec_seg, ps_rec_seg = cal_pdt_en_rec.parseDT(segmento_fecha_candidato_rec_pdt, ahora_ref_rec)
                    if ps_rec_seg > 0:
                        desc_rec_seg = " ".join(palabras_rec[:len(palabras_rec)-i]).strip()
                        desc_rec_seg = limpiar_conectores_fecha(desc_rec_seg)
                        if desc_rec_seg: return ('agregar', desc_rec_seg, dt_obj_rec_seg.strftime("%Y-%m-%d %H:%M:%S"), None)
                        else: return ('recordatorio_sin_tarea_clara', dt_obj_rec_seg.strftime("%Y-%m-%d %H:%M:%S"))
                return ('agregar', limpiar_conectores_fecha(texto_completo_rec), None, None) 
        return 'desconocido_recordatorio'


    # Completar Tareas
    if any(frase in comando for frase in ['completar', 'completada', 'terminada', 'finalizar', 'marcar como completada', 'hecho con', 'lista']): # Añadido sinónimos
        match_tarea = re.search(r'(?:completar|completada|terminada|finalizar|marcar como completada|hecho con|lista)\s+(.+)', comando, re.IGNORECASE)
        if match_tarea:
            tarea = match_tarea.group(1).strip()
            # Evitar que "lista de tareas" se confunda con completar "de tareas"
            if tarea.lower() not in ["de tareas", "tareas"]:
                return ('completar', tarea)
        return 'desconocido'

    # Categorías (asignar/poner en)
    if 'categor[ií]a' in comando and any(frase in comando for frase in ['asignar', 'poner en', 'cambiar categoria a']): # Añadido 'cambiar categoria a'
        # "asignar categoría Y a tarea X"
        match_asignar_cat_tarea = re.search(r'asignar\s+categor[ií]a\s+([\w\s]+?)\s+a\s+(?:tarea\s+)?(.+)', comando, re.IGNORECASE)
        if match_asignar_cat_tarea: return ('modificar_categoria', limpiar_conectores_fecha(match_asignar_cat_tarea.group(2).strip()), match_asignar_cat_tarea.group(1).strip())
        
        # "poner tarea X en categoría Y"
        match_poner_tarea_cat = re.search(r'poner\s+(?:tarea\s+)?(.+?)\s+en\s+categor[ií]a\s+([\w\s]+)', comando, re.IGNORECASE)
        if match_poner_tarea_cat: return ('modificar_categoria', limpiar_conectores_fecha(match_poner_tarea_cat.group(1).strip()), match_poner_tarea_cat.group(2).strip())

        # "cambiar categoria a Y para tarea X" o "cambiar categoria de tarea X a Y" (ya cubierto por 'modificar')
        return 'desconocido_categoria'


    if any(frase in comando for frase in ['calendario', 'agenda', 'eventos', 'ver agenda']): # Añadido sinónimo
        return 'ver_calendario_local'

    match_reporte = re.search(r'(?:generar|crear|mostrar|dame el)\s+reporte(?:\s+de\s+tareas)?\s+de\s+(\w+)\s+de\s+(\d{4})', comando, re.IGNORECASE) # Añadido 'dame el'
    if match_reporte:
        mes_texto = match_reporte.group(1).lower()
        año_str = match_reporte.group(2)
        meses_map = {'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12}
        mes = meses_map.get(mes_texto)
        try:
            año = int(año_str)
            if mes and 1900 < año < 2200: return ('generar_reporte', año, mes)
        except ValueError: pass
             
    return 'desconocido'


def mostrar_ayuda(): # Sin cambios, ya contiene el manual
    manual = """
**Bienvenido a VoceTasks - Tu Asistente de Tareas Inteligente**

VoceTasks es una aplicación para ayudarte a gestionar tus tareas de forma sencilla, 
ya sea a través de comandos de voz o texto. A continuación, encontrarás una 
guía rápida para empezar:

**Gestión de Usuario:**
* **Registrarse:** Para crear una nueva cuenta, di o escribe: `registrar` o `crear cuenta`. 
    Se te pedirá un email, nombre y contraseña.
* **Iniciar Sesión:** Para acceder a tu cuenta, di o escribe: `iniciar sesion`, `login`, `ingresar` o `acceder`. 
    Se te pedirá tu email y contraseña.
* **Cerrar Sesión:** Para salir de tu cuenta, di o escribe: `cerrar sesion`, `logout` o `salir cuenta`.

**Modo de Interacción (Principalmente para CLI):**
* Puedes alternar entre el modo de **voz** y **texto**.
* Para cambiar al modo de texto, di o escribe: `modo silencioso`, `activar modo silencioso` o `modo texto`.
* Para volver al modo de voz, di o escribe: `desactivar modo silencioso`.
    (En la GUI, usas el botón del micrófono para activar la escucha por voz).

**Gestión de Tareas:**
* **Mostrar Tareas:** Para ver tu lista de tareas, di o escribe: 
    `mostrar tareas`, `muestrame mis tareas` o `lista de tareas`.
* **Agregar una Tarea:** Usa el comando `agregar` seguido de la descripción. 
    Puedes incluir opcionalmente una categoría y una fecha límite.
    * Ejemplos:
        * `agregar Comprar pan`
        * `agregar Reunión con el equipo para mañana a las 10 am en categoría Trabajo`
        * `agregar Llamar al cliente para el viernes` 
            (Nota: "mañana" por voz se traduce internamente a "tomorrow" para mejorar la precisión)
        * `agregar Idea para el proyecto en categoría Ideas`
* **Eliminar una Tarea:** `eliminar [descripción de la tarea]`
    * Ejemplo: `eliminar Comprar pan`
* **Completar una Tarea:** `completar [descripción de la tarea]`
    * Ejemplo: `completar Reunión con el equipo`

**Modificar Tareas:**
* **Modificar Descripción:** `modificar descripción de [tarea antigua] a [nueva descripción]`
    * Ejemplo: `modificar descripción de Llamar al cliente a Llamar a Juan Pérez`
* **Modificar Fecha:** `modificar fecha de [tarea] a [nueva fecha]`
    * Ejemplo: `modificar fecha de Llamar a Juan Pérez a tomorrow 2 pm`
* **Modificar Categoría:** `modificar categoría de [tarea] a [nueva categoría]`
    * También: `asignar categoría [categoría] a [tarea]` o `poner [tarea] en categoría [categoría]`
    * Ejemplo: `modificar categoría de Comprar pan a Compras`

**Categorías:**
* **Mostrar Tareas por Categoría:** `mostrar tareas de categoria [nombre de la categoría]`
    * Ejemplo: `mostrar tareas de categoria Trabajo`

**Calendario (en la GUI):**
* La pestaña "Calendario" te permite ver tus tareas organizadas por fecha. 
    Puedes hacer clic en una fecha para ver las tareas, y doble clic para agregar una nueva tarea en esa fecha.

**Reportes (en la GUI):**
* La pestaña "Reportes" te permite generar resúmenes de tus tareas (diarios, semanales, mensuales) 
    y exportarlos como archivos HTML.

**Sincronización con Google Drive (en la GUI):**
* Usa los botones "Descargar" y "Subir" en la barra de herramientas para sincronizar 
    tus tareas con tu cuenta de Google Drive. Se creará una carpeta llamada 'VoceTasks_Sync'.

**Ayuda:**
* Para ver esta guía de comandos (en CLI) o acceder al manual (en GUI), 
    di o escribe: `ayuda`, `manual` o `tutorial`.

¡Esperamos que disfrutes usando VoceTasks!
    """
    return manual

def main():
    global user_manager
    if not os.path.exists("usuarios"):
        os.makedirs("usuarios", exist_ok=True)
    if not os.path.exists(user_manager.users_file):
         with open(user_manager.users_file, "w", encoding='utf-8') as file:
             json.dump({"usuarios": []}, file, indent=4)

    print("Iniciando VoceTasks en modo consola.")
    print("Para usar la interfaz gráfica, ejecuta: python gui.py")
    print("----------------------------------------------------")

    while not user_manager.current_user:
        print("\nDebes iniciar sesión o registrarte.")
        opcion = input("Escribe 'login', 'registrar' o 'salir': ").lower()
        if opcion == 'login':
            email = input("Email: ")
            password = entrada_texto("Contraseña: ", ocultar=True) if 'entrada_texto' in globals() and callable(globals()['entrada_texto']) else input("Contraseña: ") 
            success, message = user_manager.login(email, password)
            print(message)
            if success:
                if 'cargar_modo_entrada_usuario' in globals() and callable(globals()['cargar_modo_entrada_usuario']): cargar_modo_entrada_usuario(email)
                if 'obtener_modo_entrada' in globals() and callable(globals()['obtener_modo_entrada']): print(f"Modo de interacción actual: {obtener_modo_entrada()}")
        elif opcion == 'registrar':
            email = input("Email para registrar: ")
            name = input("Nombre: ")
            password = entrada_texto("Contraseña para registrar: ", ocultar=True) if 'entrada_texto' in globals() and callable(globals()['entrada_texto']) else input("Contraseña para registrar: ")
            confirm_password = entrada_texto("Confirmar contraseña: ", ocultar=True) if 'entrada_texto' in globals() and callable(globals()['entrada_texto']) else input("Confirmar contraseña: ")
            if password != confirm_password:
                print("Las contraseñas no coinciden.")
                continue
            success, message = user_manager.register_user(email, name, password)
            print(message)
        elif opcion == 'salir':
            print("Saliendo de VoceTasks.")
            return
        else:
            print("Opción no válida.")

    print(f"\nBienvenido de nuevo, {user_manager.get_user_name()}!")
    print("Escribe 'ayuda' para ver los comandos o 'salir' para terminar.")

    while True:
        comando_entrada_original = ""
        if 'obtener_modo_entrada' in globals() and callable(globals()['obtener_modo_entrada']) and obtener_modo_entrada() == 'voz':
            print("Di un comando...")
            comando_entrada_original = escuchar_comando() if 'escuchar_comando' in globals() and callable(globals()['escuchar_comando']) else input(f"{user_manager.get_user_name()} (voz simulada)> ")
            print(f"Escuchado: '{comando_entrada_original}'")
            if comando_entrada_original in ["error de conexión", "no entendí"]:
                if 'hablar' in globals() and callable(globals()['hablar']): hablar(f"Lo siento, {comando_entrada_original}. Por favor, intenta de nuevo o escribe el comando.")
                else: print(f"Lo siento, {comando_entrada_original}. Por favor, intenta de nuevo o escribe el comando.")
                comando_entrada_original = entrada_texto(f"{user_manager.get_user_name()}> ") if 'entrada_texto' in globals() and callable(globals()['entrada_texto']) else input(f"{user_manager.get_user_name()}> ")
        else:
            comando_entrada_original = entrada_texto(f"{user_manager.get_user_name()}> ") if 'entrada_texto' in globals() and callable(globals()['entrada_texto']) else input(f"{user_manager.get_user_name()}> ")


        if not comando_entrada_original:
            continue
        if comando_entrada_original.lower() == 'salir':
            if 'hablar' in globals() and callable(globals()['hablar']): hablar("Hasta luego. Cerrando sesión y saliendo.")
            else: print("Hasta luego. Cerrando sesión y saliendo.")
            user_manager.logout()
            break

        accion = interpretar_comando(comando_entrada_original)
        respuesta_para_hablar = f"Comando '{comando_entrada_original}' no reconocido o acción no implementada en CLI."
        print(f"Acción interpretada: {accion}") 

        try:
            if isinstance(accion, tuple):
                clave_accion = accion[0]
                if clave_accion == 'agregar':
                    if len(accion) == 4:
                        desc_tarea, fecha_lim_detectada, cat_detectada = accion[1], accion[2], accion[3]
                        cat_para_agregar_cli = cat_detectada if cat_detectada else (entrada_texto(f"Categoría para '{desc_tarea}' (default: General): ") if 'entrada_texto' in globals() and callable(globals()['entrada_texto']) else input(f"Categoría para '{desc_tarea}' (default: General): ") or "General")
                        success, msg = agregar_tarea(desc_tarea, cat_para_agregar_cli, fecha_lim_detectada, user_manager.current_user)
                        respuesta_para_hablar = msg
                        if success:
                            respuesta_para_hablar += f" en categoría '{cat_para_agregar_cli}'"
                            if fecha_lim_detectada: respuesta_para_hablar += f" con fecha límite {fecha_lim_detectada}."
                            else: respuesta_para_hablar += " sin fecha límite específica."
                    else:
                        respuesta_para_hablar = "Error: datos incompletos para agregar tarea."
                elif clave_accion == 'agregar_sin_info':
                    respuesta_para_hablar = "No entendí qué tarea agregar. Por favor, especifica la descripción."
                elif clave_accion == 'agregar_sin_descripcion_con_fecha':
                    fecha_detectada_error = accion[1]
                    respuesta_para_hablar = f"Entendí una fecha ({fecha_detectada_error}) pero no la descripción de la tarea."
                elif clave_accion == 'agregar_sin_descripcion_con_cat':
                    cat_detectada_error = accion[2]
                    respuesta_para_hablar = f"Entendí una categoría ({cat_detectada_error}) pero no la descripción."
                elif clave_accion == 'agregar_sin_descripcion_con_fecha_cat':
                    fecha_detectada_error, cat_detectada_error = accion[1], accion[2]
                    respuesta_para_hablar = f"Entendí fecha ({fecha_detectada_error}) y categoría ({cat_detectada_error}) pero no la descripción."
                elif clave_accion == 'eliminar':
                    success, msg = eliminar_tarea(accion[1], user_manager.current_user)
                    respuesta_para_hablar = msg
                elif clave_accion in ['modificar_descripcion', 'modificar_fecha', 'modificar_categoria']:
                    tarea_original = accion[1]
                    nuevos_datos_mod = {}
                    if clave_accion == 'modificar_descripcion':
                        nuevos_datos_mod["descripcion"] = accion[2]
                    elif clave_accion == 'modificar_fecha':
                        nuevos_datos_mod["fecha_limite"] = accion[2]
                    elif clave_accion == 'modificar_categoria':
                        nuevos_datos_mod["categoria"] = accion[2]
                    success, msg = modificar_tarea(tarea_original, nuevos_datos_mod, user_manager.current_user)
                    respuesta_para_hablar = msg
                elif clave_accion == 'modificar_fecha_invalida':
                    tarea_orig_f_inv, fecha_texto_inv = accion[1], accion[2]
                    respuesta_para_hablar = f"No se pudo entender la fecha '{fecha_texto_inv}' para la tarea '{tarea_orig_f_inv}'."
                elif clave_accion == 'completar':
                    success, msg = marcar_como_completada(accion[1], user_manager.current_user)
                    respuesta_para_hablar = msg
                elif clave_accion == 'mostrar_categoria':
                    categoria_a_mostrar = accion[1]
                    datos_tareas = mostrar_tareas(user_manager.current_user)
                    tareas_filtradas = [t for t in datos_tareas.get('tareas', []) if t.get('categoria', '').lower() == categoria_a_mostrar.lower()] 
                    if tareas_filtradas:
                        respuesta_para_hablar = f"Tareas en categoría '{categoria_a_mostrar}':"
                        print(respuesta_para_hablar)
                        for t_item in tareas_filtradas:
                            estado = "Completada" if t_item.get('completada') else "Pendiente"
                            fecha_lim_str_disp = f" Límite: {t_item.get('fecha_limite', 'N/A')}" if t_item.get('fecha_limite') else ""
                            print(f"  - {t_item['descripcion']} ({estado}){fecha_lim_str_disp}")
                        if len(tareas_filtradas) > 3: respuesta_para_hablar = f"Se mostraron {len(tareas_filtradas)} tareas de {categoria_a_mostrar}."
                    else:
                        respuesta_para_hablar = f"No hay tareas en la categoría '{categoria_a_mostrar}'."
                elif clave_accion == 'recordatorio_sin_fecha_clara':
                    t_desc_sf, f_texto_sf = accion[1], accion[2]
                    respuesta_para_hablar = f"No pude entender la fecha '{f_texto_sf}' para la tarea '{t_desc_sf}'."
                elif clave_accion == 'recordatorio_sin_tarea_clara':
                    f_texto_st = accion[1]
                    respuesta_para_hablar = f"Entendí la fecha '{f_texto_st}', pero no la descripción de la tarea."
                elif clave_accion == 'generar_reporte':
                    año_rep, mes_rep = accion[1], accion[2]
                    try:
                        fecha_inicio_obj = datetime(año_rep, mes_rep, 1)
                        fecha_fin_obj = datetime(año_rep, mes_rep + 1, 1) - timedelta(days=1) if mes_rep < 12 else datetime(año_rep, 12, 31)
                        reporte_html_cli = generar_reporte('mensual', fecha_inicio_obj.date(), fecha_fin_obj.date(), user_manager.current_user)
                        nombre_archivo_reporte = f"reporte_{user_manager.current_user.split('@')[0]}_{año_rep}_{mes_rep:02d}.html" 
                        with open(nombre_archivo_reporte, "w", encoding="utf-8") as f_rep:
                            f_rep.write(reporte_html_cli)
                        respuesta_para_hablar = f"Reporte mensual para {mes_rep}/{año_rep} guardado como '{nombre_archivo_reporte}'."
                        print(respuesta_para_hablar)
                    except Exception as e_rep:
                        respuesta_para_hablar = f"Error al generar reporte: {e_rep}"

            elif isinstance(accion, str):
                if accion == 'mostrar':
                    datos_tareas_cli = mostrar_tareas(user_manager.current_user)
                    lista_tareas_cli = datos_tareas_cli.get('tareas', []) 
                    if not lista_tareas_cli:
                        respuesta_para_hablar = "No tienes tareas registradas."
                    else:
                        print("\nTus tareas:")
                        pendientes_cli_list = []
                        for t_cli in lista_tareas_cli:
                            estado_cli = "Completada" if t_cli.get('completada') else "Pendiente"
                            fecha_lim_str_cli = f" Límite: {t_cli.get('fecha_limite', 'N/A')}" if t_cli.get('fecha_limite') else ""
                            cat_str_cli = f" Cat: {t_cli.get('categoria', 'General')}"
                            print(f"  - {t_cli['descripcion']}{cat_str_cli} ({estado_cli}){fecha_lim_str_cli}")
                            if not t_cli.get('completada'):
                                pendientes_cli_list.append(t_cli['descripcion'])
                        if pendientes_cli_list:
                             respuesta_para_hablar = f"Tienes {len(pendientes_cli_list)} tareas pendientes. La primera es: {pendientes_cli_list[0]}" if pendientes_cli_list else "¡Todas tus tareas están completadas!"
                        else:
                             respuesta_para_hablar = "¡Todas tus tareas están completadas!"
                        if len(lista_tareas_cli) > 3 :
                            respuesta_para_hablar += " Se han listado todas en la consola."
                elif accion == 'ayuda':
                    print(mostrar_ayuda()) 
                    respuesta_para_hablar = "Manual de ayuda mostrado en la consola."
                elif accion in ['activar_silencioso', 'desactivar_silencioso', 'toggle_silencioso']:
                    modo_actual = obtener_modo_entrada() if 'obtener_modo_entrada' in globals() and callable(globals()['obtener_modo_entrada']) else 'texto'
                    nuevo_modo = ""
                    if accion == 'activar_silencioso': nuevo_modo = 'texto'
                    elif accion == 'desactivar_silencioso': nuevo_modo = 'voz'
                    elif accion == 'toggle_silencioso': nuevo_modo = 'texto' if modo_actual == 'voz' else 'voz'
                    if 'cambiar_modo_entrada' in globals() and callable(globals()['cambiar_modo_entrada']):
                        success, msg = cambiar_modo_entrada(nuevo_modo, user_manager.current_user)
                        respuesta_para_hablar = msg
                        if nuevo_modo == 'texto': print(respuesta_para_hablar)
                    else:
                        respuesta_para_hablar = "Función de cambio de modo no disponible."
                elif accion == 'ver_calendario_local':
                    datos_tareas_cal_cli = mostrar_tareas(user_manager.current_user)
                    tareas_con_fecha_cli = sorted([t_cal for t_cal in datos_tareas_cal_cli.get('tareas', []) if t_cal.get('fecha_limite')],key=lambda x: x['fecha_limite']) 
                    if tareas_con_fecha_cli:
                        respuesta_para_hablar = "Próximas tareas con fecha límite:"
                        print("\n" + respuesta_para_hablar)
                        for t_cal_item in tareas_con_fecha_cli[:5]:
                             estado_cal_cli = "Completada" if t_cal_item.get('completada') else "Pendiente"
                             print(f"  - {t_cal_item['descripcion']} para el {t_cal_item['fecha_limite']} ({estado_cal_cli})")
                        if len(tareas_con_fecha_cli) > 5: print(f"  ...y {len(tareas_con_fecha_cli)-5} más.")
                        respuesta_para_hablar = f"Se listaron {len(tareas_con_fecha_cli)} tareas con fecha." if len(tareas_con_fecha_cli) >= 1 else "No tienes tareas con fecha."
                    else:
                        respuesta_para_hablar = "No tienes tareas con fecha límite asignada."
                elif accion == 'logout':
                    if 'hablar' in globals() and callable(globals()['hablar']): hablar("Cerrando sesión.")
                    else: print("Cerrando sesión.")
                    user_manager.logout()
                    print("Sesión cerrada.")
                    return 
                elif accion in ['desconocido_modificar', 'desconocido_recordatorio', 'desconocido_categoria', 'desconocido']:
                    respuesta_para_hablar = f"No entendí el comando '{comando_entrada_original}'. Intenta de nuevo o escribe 'ayuda'."
        except Exception as e_cli_loop:
            print(f"Error procesando comando en CLI: {e_cli_loop}")
            import traceback
            traceback.print_exc() 
            respuesta_para_hablar = "Ocurrió un error inesperado."

        print(f"Respuesta: {respuesta_para_hablar}")
        if 'hablar' in globals() and callable(globals()['hablar']): hablar(respuesta_para_hablar)
        else: print(respuesta_para_hablar)

if __name__ == "__main__":
    while True:
        if user_manager: user_manager.logout() 
        main() 
        if user_manager and not user_manager.current_user: 
            continuar = input("¿Deseas salir completamente de VoceTasks (s/n)? ").lower()
            if continuar == 's':
                print("Saliendo de VoceTasks. ¡Hasta pronto!")
                break
        else: 
            print("Saliendo de VoceTasks (estado inesperado). ¡Hasta pronto!")
            break
