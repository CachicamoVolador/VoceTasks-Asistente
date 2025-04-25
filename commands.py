import json
import os
from datetime import datetime

def crear_archivo_tareas_si_no_existe(ruta_archivo):
    """Crea el archivo de tareas si no existe"""
    os.makedirs(os.path.dirname(ruta_archivo), exist_ok=True)
    if not os.path.exists(ruta_archivo):
        with open(ruta_archivo, "w") as file:
            json.dump({"tareas": []}, file, indent=4)

def agregar_tarea(tarea, email):
    """Agrega una nueva tarea a la lista"""
    ruta_archivo = f"usuarios/{email}/tareas.json"
    crear_archivo_tareas_si_no_existe(ruta_archivo)
    try:
        with open(ruta_archivo, "r+") as file:
            data = json.load(file)
            # Verifica si la tarea ya existe (sólo comparando descripción)
            tareas_desc = [t["descripcion"] for t in data["tareas"] if "descripcion" in t]
            if tarea in tareas_desc:
                return f"La tarea '{tarea}' ya existe en tu lista"
            
            # Agregar la tarea con información adicional
            nueva_tarea = {
                "descripcion": tarea,
                "fecha_creacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "fecha_limite": None,
                "completada": False,
                "categoria": "general",
                "sincronizado_calendario": False
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
            
            # Buscar la tarea por descripción
            tarea_encontrada = None
            for t in data["tareas"]:
                if t["descripcion"] == tarea:
                    tarea_encontrada = t
                    break
            
            if tarea_encontrada:
                data["tareas"].remove(tarea_encontrada)
                file.seek(0)
                json.dump(data, file, indent=4)
                file.truncate()
                return f"Tarea eliminada: {tarea}"
            else:
                # Buscar coincidencias parciales
                coincidencias = [t for t in data["tareas"] if tarea in t["descripcion"]]
                if len(coincidencias) == 1:
                    data["tareas"].remove(coincidencias[0])
                    file.seek(0)
                    json.dump(data, file, indent=4)
                    file.truncate()
                    return f"Tarea eliminada: {coincidencias[0]['descripcion']}"
                elif len(coincidencias) > 1:
                    return f"Encontré varias tareas similares. Por favor, sé más específico."
                else:
                    return "Tarea no encontrada."
    except Exception as e:
        print(f"Error al eliminar tarea: {e}")
        return "No se pudo eliminar la tarea"

def mostrar_tareas(email):
    """Muestra todas las tareas disponibles"""
    ruta_archivo = f"usuarios/{email}/tareas.json"
    crear_archivo_tareas_si_no_existe(ruta_archivo)
    try:
        with open(ruta_archivo, "r") as file:
            data = json.load(file)
            if data["tareas"]:
                tareas = [t["descripcion"] for t in data["tareas"]]
                return "Tareas pendientes: " + ", ".join(tareas)
            else:
                return "No hay tareas pendientes."
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
            
            # Buscar la tarea por descripción
            tarea_encontrada = None
            index = -1
            for i, t in enumerate(data["tareas"]):
                if t["descripcion"] == tarea_vieja:
                    tarea_encontrada = t
                    index = i
                    break
            
            if tarea_encontrada:
                # Mantener los otros datos de la tarea, solo cambiar descripción
                data["tareas"][index]["descripcion"] = tarea_nueva
                file.seek(0)
                json.dump(data, file, indent=4)
                file.truncate()
                return f"Tarea modificada: {tarea_vieja} -> {tarea_nueva}"
            else:
                # Buscar coincidencias parciales
                coincidencias = []
                indices = []
                for i, t in enumerate(data["tareas"]):
                    if tarea_vieja in t["descripcion"]:
                        coincidencias.append(t)
                        indices.append(i)
                
                if len(coincidencias) == 1:
                    # Mantener los otros datos de la tarea, solo cambiar descripción
                    data["tareas"][indices[0]]["descripcion"] = tarea_nueva
                    file.seek(0)
                    json.dump(data, file, indent=4)
                    file.truncate()
                    return f"Tarea modificada: {coincidencias[0]['descripcion']} -> {tarea_nueva}"
                elif len(coincidencias) > 1:
                    return f"Encontré varias tareas similares. Por favor, sé más específico."
                else:
                    return "Tarea no encontrada."
    except Exception as e:
        print(f"Error al modificar tarea: {e}")
        return "No se pudo modificar la tarea"

def agregar_recordatorio(tarea, fecha_limite, email):
    """Agrega una fecha límite a una tarea existente"""
    ruta_archivo = f"usuarios/{email}/tareas.json"
    crear_archivo_tareas_si_no_existe(ruta_archivo)
    try:
        # Importar aquí para evitar importación circular
        from calendar_integration import agregar_evento_calendario
        
        with open(ruta_archivo, "r+") as file:
            data = json.load(file)
            
            # Buscar la tarea por descripción
            tarea_encontrada = None
            index = -1
            for i, t in enumerate(data["tareas"]):
                if t["descripcion"] == tarea:
                    tarea_encontrada = t
                    index = i
                    break
            
            if tarea_encontrada:
                # Agregar fecha límite
                data["tareas"][index]["fecha_limite"] = fecha_limite
                
                # Agregar al calendario si está habilitado
                resultado_calendario = ""
                try:
                    resultado_calendario = agregar_evento_calendario(tarea, fecha_limite, email)
                    if "Evento creado" in resultado_calendario:
                        data["tareas"][index]["sincronizado_calendario"] = True
                except ImportError:
                    resultado_calendario = "\nPara sincronizar con el calendario, instala las dependencias necesarias."
                
                file.seek(0)
                json.dump(data, file, indent=4)
                file.truncate()
                
                return f"Recordatorio agregado para: {tarea} - Fecha: {fecha_limite}" + \
                       (f"\n{resultado_calendario}" if resultado_calendario else "")
            else:
                return "Tarea no encontrada."
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
            
            # Buscar la tarea por descripción
            tarea_encontrada = None
            index = -1
            for i, t in enumerate(data["tareas"]):
                if t["descripcion"] == tarea:
                    tarea_encontrada = t
                    index = i
                    break
            
            if tarea_encontrada:
                # Cambiar categoría
                data["tareas"][index]["categoria"] = categoria
                file.seek(0)
                json.dump(data, file, indent=4)
                file.truncate()
                return f"Categoría cambiada para: {tarea} - Nueva categoría: {categoria}"
            else:
                return "Tarea no encontrada."
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
            
            # Buscar la tarea por descripción
            tarea_encontrada = None
            index = -1
            for i, t in enumerate(data["tareas"]):
                if t["descripcion"] == tarea:
                    tarea_encontrada = t
                    index = i
                    break
            
            if tarea_encontrada:
                # Marcar como completada
                data["tareas"][index]["completada"] = True
                file.seek(0)
                json.dump(data, file, indent=4)
                file.truncate()
                return f"Tarea marcada como completada: {tarea}"
            else:
                return "Tarea no encontrada."
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
            tareas_categoria = [t["descripcion"] for t in data["tareas"] if t["categoria"] == categoria]
            if tareas_categoria:
                return f"Tareas de categoría '{categoria}': " + ", ".join(tareas_categoria)
            else:
                return f"No hay tareas en la categoría '{categoria}'."
    except Exception as e:
        print(f"Error al mostrar tareas por categoría: {e}")
        return "No se pudieron mostrar las tareas por categoría"

def mostrar_tareas_calendario(email, dias=7):
    """Muestra las tareas próximas en formato de calendario"""
    try:
        # Importar aquí para evitar importación circular
        from calendar_integration import listar_eventos_proximos
        return listar_eventos_proximos(email, dias)
    except ImportError:
        return "Para ver el calendario, instala las dependencias necesarias."
    except Exception as e:
        print(f"Error al mostrar tareas del calendario: {e}")
        return f"No se pudieron mostrar las tareas del calendario: {e}"

def sincronizar_todas_tareas_calendario(email):
    """Sincroniza todas las tareas con fecha al calendario"""
    try:
        # Importar aquí para evitar importación circular
        from calendar_integration import sincronizar_tareas_calendario
        return sincronizar_tareas_calendario(email)
    except ImportError:
        return "Para sincronizar con el calendario, instala las dependencias necesarias."
    except Exception as e:
        print(f"Error al sincronizar tareas: {e}")
        return f"No se pudieron sincronizar las tareas: {e}"

def enviar_recordatorios_email(email):
    """Envía recordatorios por email para tareas próximas"""
    try:
        # Importar aquí para evitar importación circular
        from calendar_integration import programar_recordatorios_automaticos
        return programar_recordatorios_automaticos(email)
    except ImportError:
        return "Para enviar recordatorios, instala las dependencias necesarias."
    except Exception as e:
        print(f"Error al enviar recordatorios: {e}")
        return f"No se pudieron enviar los recordatorios: {e}"

def mostrar_tareas_formato_calendario(email):
    """Muestra las tareas en formato de calendario"""
    ruta_archivo = f"usuarios/{email}/tareas.json"
    crear_archivo_tareas_si_no_existe(ruta_archivo)
    try:
        with open(ruta_archivo, "r") as file:
            data = json.load(file)
            
            # Filtrar tareas con fecha límite
            tareas_con_fecha = [t for t in data["tareas"] if t.get("fecha_limite")]
            
            if not tareas_con_fecha:
                return "No hay tareas con fecha límite para mostrar en formato calendario."
            
            # Organizar por fecha
            tareas_por_fecha = {}
            for tarea in tareas_con_fecha:
                fecha = tarea["fecha_limite"].split(" ")[0]  # Solo la parte de la fecha
                if fecha not in tareas_por_fecha:
                    tareas_por_fecha[fecha] = []
                tareas_por_fecha[fecha].append(tarea)
            
            # Crear visualización de calendario
            resultado = "Calendario de tareas:\n"
            for fecha in sorted(tareas_por_fecha.keys()):
                resultado += f"\n[{fecha}]\n"
                for tarea in tareas_por_fecha[fecha]:
                    hora = tarea["fecha_limite"].split(" ")[1][:5]  # HH:MM
                    estado = "[✓]" if tarea["completada"] else "[ ]"
                    resultado += f"  {hora} {estado} {tarea['descripcion']} ({tarea['categoria']})\n"
            
            return resultado
            
    except Exception as e:
        print(f"Error al mostrar tareas en formato calendario: {e}")
        return "No se pudieron mostrar las tareas en formato calendario"