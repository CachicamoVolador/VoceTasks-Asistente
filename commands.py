import json
import os
from datetime import datetime, timedelta # Importar timedelta para calcular fechas futuras

def crear_archivo_tareas_si_no_existe(ruta_archivo):
    """Crea el archivo de tareas si no existe"""
    os.makedirs(os.path.dirname(ruta_archivo), exist_ok=True)
    if not os.path.exists(ruta_archivo):
        with open(ruta_archivo, "w") as file:
            json.dump({"tareas": []}, file, indent=4)

# Modificar la función agregar_tarea para aceptar categoria y fecha_limite
def agregar_tarea(tarea, categoria, fecha_limite, email):
    """Agrega una nueva tarea a la lista con categoría y fecha límite"""
    ruta_archivo = f"usuarios/{email}/tareas.json"
    crear_archivo_tareas_si_no_existe(ruta_archivo)
    try:
        with open(ruta_archivo, "r+") as file:
            data = json.load(file)
            # Verifica si la tarea ya existe (sólo comparando descripción)
            tareas_desc = [t["descripcion"].lower() for t in data["tareas"] if "descripcion" in t] # Comparar en minúsculas
            if tarea.lower() in tareas_desc: # Comparar la nueva tarea en minúsculas
                return f"La tarea '{tarea}' ya existe en tu lista"

            # Validar formato de fecha límite si se proporciona
            fecha_limite_str = None
            if fecha_limite:
                try:
                    # Intentar parsear la fecha para asegurarse de que sea válida
                    datetime.strptime(fecha_limite, "%Y-%m-%d %H:%M:%S")
                    fecha_limite_str = fecha_limite
                except ValueError:
                    return f"Formato de fecha y hora inválido para la fecha límite. Usa %Y-%m-%d %H:%M:%S (Ej: 2023-10-27 10:30:00)."


            # Agregar la tarea con información adicional
            nueva_tarea = {
                "descripcion": tarea,
                "fecha_creacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "fecha_limite": fecha_limite_str, # Usar la fecha límite validada o None
                "completada": False,
                "categoria": categoria if categoria else "general", # Usar la categoría proporcionada o "general" por defecto
            }

            data["tareas"].append(nueva_tarea)
            file.seek(0)
            json.dump(data, file, indent=4)
            file.truncate()
        return f"Tarea agregada: {tarea}"
    except Exception as e:
        print(f"Error al agregar tarea: {e}")
        return "No se pudo agregar la tarea"

def eliminar_tarea(tarea, email):
    """Elimina una tarea de la lista"""
    ruta_archivo = f"usuarios/{email}/tareas.json"
    crear_archivo_tareas_si_no_existe(ruta_archivo)
    try:
        with open(ruta_archivo, "r+") as file:
            data = json.load(file)

            # Buscar la tarea por descripción (comparación parcial e insensible a mayúsculas)
            tarea_encontrada = None
            index = -1
            for i, t in enumerate(data["tareas"]):
                if tarea.lower() in t.get("descripcion", "").lower(): # Buscar parcial e insensible a mayúsculas
                    tarea_encontrada = t
                    index = i
                    break # Eliminar solo la primera coincidencia si hay varias

            if tarea_encontrada:
                data["tareas"].pop(index) # Usar pop con índice es más seguro después de encontrar
                file.seek(0)
                json.dump(data, file, indent=4)
                file.truncate()
                return f"Tarea eliminada: {tarea_encontrada['descripcion']}" # Usar la descripción exacta encontrada
            else:
                 # Si no se encontró por coincidencia parcial, buscar exacta (insensible a mayúsculas)
                 for i, t in enumerate(data["tareas"]):
                     if tarea.lower() == t.get("descripcion", "").lower():
                         tarea_encontrada = t
                         index = i
                         break

                 if tarea_encontrada:
                     data["tareas"].pop(index)
                     file.seek(0)
                     json.dump(data, file, indent=4)
                     file.truncate()
                     return f"Tarea eliminada: {tarea_encontrada['descripcion']}"
                 else:
                    return "Tarea no encontrada."
    except Exception as e:
        print(f"Error al eliminar tarea: {e}")
        return "No se pudo eliminar la tarea"


def mostrar_tareas(email):
    """Muestra todas las tareas pendientes y completadas"""
    ruta_archivo = f"usuarios/{email}/tareas.json"
    crear_archivo_tareas_si_no_existe(ruta_archivo)
    try:
        with open(ruta_archivo, "r") as file:
            data = json.load(file)
            if data["tareas"]:
                tareas_pendientes = [t["descripcion"] for t in data["tareas"] if not t.get("completada")]
                tareas_completadas = [t["descripcion"] for t in data["tareas"] if t.get("completada")]

                respuesta = ""
                if tareas_pendientes:
                    respuesta += "Tareas pendientes: " + ", ".join(tareas_pendientes)
                if tareas_completadas:
                    if respuesta:
                        respuesta += "\n" # Añadir salto de línea si hay tareas pendientes
                    respuesta += "Tareas completadas: " + ", ".join(tareas_completadas)

                if not respuesta:
                     respuesta = "No hay tareas en tu lista."

                return respuesta
            else:
                return "No hay tareas en tu lista."
    except Exception as e:
        print(f"Error al mostrar tareas: {e}")
        return "No se pudieron mostrar las tareas"


def modificar_tarea(tarea_vieja, tarea_nueva, email):
    """Modifica una tarea existente"""
    ruta_archivo = f"usuarios/{email}/tareas.json"
    crear_archivo_tareas_si_no_existe(ruta_archivo)
    try:
        with open(ruta_archivo, "r+") as file:
            data = json.load(file)

            # Buscar la tarea por descripción (insensible a mayúsculas y parcial)
            tarea_encontrada = None
            index = -1
            for i, t in enumerate(data["tareas"]):
                if tarea_vieja.lower() in t.get("descripcion", "").lower(): # Buscar parcial e insensible a mayúsculas
                    tarea_encontrada = t
                    index = i
                    break # Modificar solo la primera coincidencia

            if tarea_encontrada:
                # Mantener los otros datos de la tarea, solo cambiar descripción
                data["tareas"][index]["descripcion"] = tarea_nueva
                file.seek(0)
                json.dump(data, file, indent=4)
                file.truncate()
                return f"Tarea modificada: '{tarea_encontrada['descripcion']}' -> '{tarea_nueva}'"
            else:
                # Si no se encontró por coincidencia parcial, buscar exacta (insensible a mayúsculas)
                 for i, t in enumerate(data["tareas"]):
                     if tarea_vieja.lower() == t.get("descripcion", "").lower():
                         tarea_encontrada = t
                         index = i
                         break

                 if tarea_encontrada:
                     data["tareas"][index]["descripcion"] = tarea_nueva
                     file.seek(0)
                     json.dump(data, file, indent=4)
                     file.truncate()
                     return f"Tarea modificada: '{tarea_encontrada['descripcion']}' -> '{tarea_nueva}'"
                 else:
                    return "Tarea no encontrada para modificar."
    except Exception as e:
        print(f"Error al modificar tarea: {e}")
        return "No se pudo modificar la tarea"


def agregar_recordatorio(tarea, fecha_limite, email):
    """Agrega una fecha límite a una tarea existente (sin sincronización con Google)"""
    ruta_archivo = f"usuarios/{email}/tareas.json"
    crear_archivo_tareas_si_no_existe(ruta_archivo)
    try:
        with open(ruta_archivo, "r+") as file:
            data = json.load(file)

            # Buscar la tarea por descripción (insensible a mayúsculas y parcial)
            tarea_encontrada = None
            index = -1
            for i, t in enumerate(data["tareas"]):
                if tarea.lower() in t.get("descripcion", "").lower(): # Buscar parcial e insensible a mayúsculas
                    tarea_encontrada = t
                    index = i
                    break # Agregar recordatorio solo a la primera coincidencia

            if tarea_encontrada:
                # Validar y agregar fecha límite
                try:
                    # Intentar parsear la fecha para asegurarse de que sea válida
                    datetime.strptime(fecha_limite, "%Y-%m-%d %H:%M:%S")
                    data["tareas"][index]["fecha_limite"] = fecha_limite

                    # Eliminar la bandera de sincronización de Google si existía
                    if "sincronizado_calendario" in data["tareas"][index]:
                        del data["tareas"][index]["sincronizado_calendario"]

                    file.seek(0)
                    json.dump(data, file, indent=4)
                    file.truncate()

                    return f"Fecha límite agregada para: '{tarea_encontrada['descripcion']}' - Fecha: {fecha_limite}"
                except ValueError:
                    return f"Formato de fecha y hora inválido. Usa %Y-%m-%d %H:%M:%S (Ej: 2023-10-27 10:30:00)."

            else:
                # Si no se encontró por coincidencia parcial, buscar exacta (insensible a mayúsculas)
                 for i, t in enumerate(data["tareas"]):
                     if tarea.lower() == t.get("descripcion", "").lower():
                         tarea_encontrada = t
                         index = i
                         break
                 if tarea_encontrada:
                      try:
                         datetime.strptime(fecha_limite, "%Y-%m-%d %H:%M:%S")
                         data["tareas"][index]["fecha_limite"] = fecha_limite

                         if "sincronizado_calendario" in data["tareas"][index]:
                             del data["tareas"][index]["sincronizado_calendario"]

                         file.seek(0)
                         json.dump(data, file, indent=4)
                         file.truncate()
                         return f"Fecha límite agregada para: '{tarea_encontrada['descripcion']}' - Fecha: {fecha_limite}"
                      except ValueError:
                         return f"Formato de fecha y hora inválido. Usa %Y-%m-%d %H:%M:%S (Ej: 2023-10-27 10:30:00)."
                 else:
                     return "Tarea no encontrada para agregar recordatorio."
    except Exception as e:
        print(f"Error al agregar recordatorio: {e}")
        return "No se pudo agregar el recordatorio"


def cambiar_categoria(tarea, categoria, email):
    """Cambia la categoría de una tarea"""
    ruta_archivo = f"usuarios/{email}/tareas.json"
    crear_archivo_tareas_si_no_existe(ruta_archivo)
    try:
        with open(ruta_archivo, "r+") as file:
            data = json.load(file)

            # Buscar la tarea por descripción (insensible a mayúsculas y parcial)
            tarea_encontrada = None
            index = -1
            for i, t in enumerate(data["tareas"]):
                if tarea.lower() in t.get("descripcion", "").lower(): # Buscar parcial e insensible a mayúsculas
                    tarea_encontrada = t
                    index = i
                    break # Cambiar categoría solo a la primera coincidencia

            if tarea_encontrada:
                # Cambiar categoría
                data["tareas"][index]["categoria"] = categoria
                file.seek(0)
                json.dump(data, file, indent=4)
                file.truncate()
                return f"Categoría cambiada para: '{tarea_encontrada['descripcion']}' - Nueva categoría: {categoria}"
            else:
                 # Si no se encontró por coincidencia parcial, buscar exacta (insensible a mayúsculas)
                 for i, t in enumerate(data["tareas"]):
                     if tarea.lower() == t.get("descripcion", "").lower():
                         tarea_encontrada = t
                         index = i
                         break
                 if tarea_encontrada:
                     data["tareas"][index]["categoria"] = categoria
                     file.seek(0)
                     json.dump(data, file, indent=4)
                     file.truncate()
                     return f"Categoría cambiada para: '{tarea_encontrada['descripcion']}' - Nueva categoría: {categoria}"
                 else:
                     return "Tarea no encontrada para cambiar categoría."
    except Exception as e:
        print(f"Error al cambiar categoría: {e}")
        return "No se pudo cambiar la categoría"


def marcar_como_completada(tarea, email):
    """Marca una tarea como completada"""
    ruta_archivo = f"usuarios/{email}/tareas.json"
    crear_archivo_tareas_si_no_existe(ruta_archivo)
    try:
        with open(ruta_archivo, "r+") as file:
            data = json.load(file)

            # Buscar la tarea por descripción (insensible a mayúsculas y parcial)
            tarea_encontrada = None
            index = -1
            for i, t in enumerate(data["tareas"]):
                if tarea.lower() in t.get("descripcion", "").lower(): # Buscar parcial e insensible a mayúsculas
                    tarea_encontrada = t
                    index = i
                    break # Marcar como completada solo la primera coincidencia

            if tarea_encontrada:
                # Marcar como completada
                data["tareas"][index]["completada"] = True
                file.seek(0)
                json.dump(data, file, indent=4)
                file.truncate()
                return f"Tarea marcada como completada: '{tarea_encontrada['descripcion']}'"
            else:
                 # Si no se encontró por coincidencia parcial, buscar exacta (insensible a mayúsculas)
                 for i, t in enumerate(data["tareas"]):
                     if tarea.lower() == t.get("descripcion", "").lower():
                         tarea_encontrada = t
                         index = i
                         break
                 if tarea_encontrada:
                     data["tareas"][index]["completada"] = True
                     file.seek(0)
                     json.dump(data, file, indent=4)
                     file.truncate()
                     return f"Tarea marcada como completada: '{tarea_encontrada['descripcion']}'"
                 else:
                     return "Tarea no encontrada para marcar como completada."
    except Exception as e:
        print(f"Error al marcar tarea como completada: {e}")
        return "No se pudo marcar la tarea como completada"

def mostrar_tareas_por_categoria(categoria, email):
    """Muestra las tareas de una categoría específica"""
    ruta_archivo = f"usuarios/{email}/tareas.json"
    crear_archivo_tareas_si_no_existe(ruta_archivo)
    try:
        with open(ruta_archivo, "r") as file:
            data = json.load(file)
            # Filtrar por categoría (insensible a mayúsculas)
            tareas_categoria = [t for t in data["tareas"] if t.get("categoria", "").lower() == categoria.lower()]
            if tareas_categoria:
                respuesta = f"Tareas de categoría '{categoria}':\n"
                for tarea in tareas_categoria:
                     estado = "✓" if tarea.get("completada") else " "
                     fecha_limite = f" (Fecha límite: {tarea['fecha_limite']})" if tarea.get("fecha_limite") else ""
                     respuesta += f"- [{estado}] {tarea['descripcion']}{fecha_limite}\n"
                return respuesta.strip() # Eliminar el último salto de línea
            else:
                return f"No hay tareas en la categoría '{categoria}'."
    except Exception as e:
        print(f"Error al mostrar tareas por categoría: {e}")
        return "No se pudieron mostrar las tareas por categoría"

# Funciones relacionadas con calendario y recordatorios (adaptadas o eliminadas)

def mostrar_tareas_calendario_local(email):
    """Muestra las tareas con fecha límite en formato de lista por fecha (local)"""
    ruta_archivo = f"usuarios/{email}/tareas.json"
    crear_archivo_tareas_si_no_existe(ruta_archivo)
    try:
        with open(ruta_archivo, "r") as file:
            data = json.load(file)

            # Filtrar tareas con fecha límite
            tareas_con_fecha = [t for t in data["tareas"] if t.get("fecha_limite")]

            if not tareas_con_fecha:
                return "No hay tareas con fecha límite para mostrar en el calendario local."

            # Organizar por fecha y hora
            tareas_con_fecha.sort(key=lambda x: datetime.strptime(x["fecha_limite"], "%Y-%m-%d %H:%M:%S"))

            resultado = "Tareas con fecha límite:\n\n"
            fecha_actual = None
            for tarea in tareas_con_fecha:
                fecha_limite_dt = datetime.strptime(tarea["fecha_limite"], "%Y-%m-%d %H:%M:%S")
                fecha = fecha_limite_dt.strftime("%Y-%m-%d")
                hora = fecha_limite_dt.strftime("%H:%M")
                estado = "✓" if tarea.get("completada") else " "

                if fecha != fecha_actual:
                    resultado += f"--- {fecha} ---\n"
                    fecha_actual = fecha

                resultado += f"[{estado}] {hora} - {tarea['descripcion']} ({tarea['categoria']})\n"

            return resultado.strip()

    except Exception as e:
        print(f"Error al mostrar tareas en calendario local: {e}")
        return "No se pudieron mostrar las tareas en formato calendario local."

# La función mostrar_tareas_formato_calendario ya trabaja con datos locales, se mantiene igual

# Las funciones sincronizar_todas_tareas_calendario y enviar_recordatorios_email se eliminan
# ya que dependían de calendar_integration.py

# --- Nueva función para generar reporte mensual ---

def generar_reporte_mensual(email, año, mes):
    """Genera un reporte de tareas completadas y pendientes para un mes dado."""
    ruta_archivo = f"usuarios/{email}/tareas.json"
    crear_archivo_tareas_si_no_existe(ruta_archivo)

    try:
        with open(ruta_archivo, "r") as file:
            data = json.load(file)
            tareas = data.get("tareas", [])

            # Filtrar tareas por año y mes en la fecha de creación o fecha límite
            tareas_del_mes = []
            for tarea in tareas:
                # Considerar fecha de creación o fecha límite para el reporte mensual
                fecha_str = tarea.get("fecha_limite") or tarea.get("fecha_creacion")
                if fecha_str:
                    try:
                        # Asegurarse de que la cadena tenga el formato esperado antes de dividir
                        if " " in fecha_str and len(fecha_str.split(" ")[0]) == 10:
                            fecha_dt = datetime.strptime(fecha_str.split(" ")[0], "%Y-%m-%d")
                            if fecha_dt.year == año and fecha_dt.month == mes:
                                tareas_del_mes.append(tarea)
                        # Manejar casos donde solo hay fecha (sin hora) si es necesario
                        elif len(fecha_str) == 10: # %Y-%m-%d
                             fecha_dt = datetime.strptime(fecha_str, "%Y-%m-%d")
                             if fecha_dt.year == año and fecha_dt.month == mes:
                                tareas_del_mes.append(tarea)

                    except ValueError:
                        # Ignorar tareas con formatos de fecha inválidos
                        pass

            if not tareas_del_mes:
                return f"No hay tareas registradas o con fecha límite en el mes {mes} del año {año}."

            # Separar por estado
            tareas_completadas = [t for t in tareas_del_mes if t.get("completada")]
            tareas_pendientes = [t for t in tareas_del_mes if not t.get("completada")]

            # Generar reporte
            reporte = f"--- Reporte de Tareas - Mes {mes}/{año} ---\n\n"

            reporte += f"Tareas Completadas ({len(tareas_completadas)}):\n"
            if tareas_completadas:
                for tarea in tareas_completadas:
                    fecha_info = tarea.get("fecha_limite") or tarea.get("fecha_creacion", "Fecha no disponible")
                    reporte += f"- [✓] {tarea['descripcion']} (Categoría: {tarea.get('categoria', 'N/A')}, Fecha: {fecha_info})\n"
            else:
                reporte += "  Ninguna tarea completada en este mes.\n"

            reporte += f"\nTareas Pendientes ({len(tareas_pendientes)}):\n"
            if tareas_pendientes:
                for tarea in tareas_pendientes:
                     fecha_info = tarea.get("fecha_limite") or tarea.get("fecha_creacion", "Fecha no disponible")
                     reporte += f"- [ ] {tarea['descripcion']} (Categoría: {tarea.get('categoria', 'N/A')}, Fecha límite: {fecha_info})\n"
            else:
                reporte += "  Ninguna tarea pendiente en este mes.\n"

            reporte += "\n------------------------------\n"

            return reporte

    except FileNotFoundError:
        return "Aún no tienes tareas registradas."
    except Exception as e:
        print(f"Error al generar reporte mensual: {e}")
        return f"Hubo un error al generar el reporte: {e}"
