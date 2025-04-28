# commands.py (Modificado para reportes diarios/semanales/mensuales)

import json
import os
from datetime import datetime, timedelta # Asegurarse de que timedelta esté importado
import html

# --- Funciones de Manejo de Archivos y Tareas (sin cambios) ---
# ... (mantener las funciones existentes: crear_archivo_tareas_si_no_existe, agregar_tarea, etc.)

def crear_archivo_tareas_si_no_existe(ruta_archivo):
    """Crea el archivo de tareas si no existe, incluyendo el directorio del usuario."""
    user_dir = os.path.dirname(ruta_archivo)
    os.makedirs(user_dir, exist_ok=True) # Crea el directorio si no existe
    if not os.path.exists(ruta_archivo):
        try:
            with open(ruta_archivo, "w", encoding='utf-8') as file:
                json.dump({"tareas": []}, file, indent=4, ensure_ascii=False)
            print(f"Archivo de tareas creado en: {ruta_archivo}")
        except IOError as e:
            print(f"Error al crear el archivo de tareas {ruta_archivo}: {e}")

def agregar_tarea(tarea, categoria, fecha_limite, email, completada=False):
    """Agrega una nueva tarea a la lista del usuario."""
    ruta_archivo = f"usuarios/{email}/tareas.json"
    crear_archivo_tareas_si_no_existe(ruta_archivo) # Asegura que el archivo y directorio existan

    try:
        # Leer el archivo actual
        try:
            with open(ruta_archivo, "r", encoding='utf-8') as file:
                data = json.load(file)
                # Asegurar que 'tareas' exista y sea una lista
                if "tareas" not in data or not isinstance(data["tareas"], list):
                    data["tareas"] = []
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error al leer {ruta_archivo} o archivo corrupto ({e}). Reiniciando.")
            data = {"tareas": []} # Reiniciar si hay error

        # Verificar si la tarea ya existe (insensible a mayúsculas/minúsculas y espacios)
        tareas_desc = [t["descripcion"].strip().lower() for t in data.get("tareas", []) if "descripcion" in t]
        if tarea.strip().lower() in tareas_desc:
            return False, f"La tarea '{tarea}' ya existe en tu lista."

        # Validar y formatear fecha límite si existe
        fecha_limite_str = None
        if fecha_limite:
             try:
                 # Intentar parsear la fecha y hora
                 dt_obj = datetime.strptime(fecha_limite, '%Y-%m-%d %H:%M:%S')
                 fecha_limite_str = dt_obj.strftime('%Y-%m-%d %H:%M:%S') # Reformatear por si acaso
             except ValueError:
                 print(f"Advertencia: Formato de fecha límite inválido: {fecha_limite}. No se guardará la fecha.")
                 fecha_limite_str = None # Ignorar fecha inválida

        # Crear la nueva tarea
        nueva_tarea = {
            "descripcion": tarea.strip(),
            "categoria": categoria.strip() if categoria else "General", # Categoría por defecto
            "fecha_creacion": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "fecha_limite": fecha_limite_str,
            "completada": completada # Estado inicial
        }

        # Añadir la nueva tarea a la lista
        data["tareas"].append(nueva_tarea)

        # Guardar los datos actualizados en el archivo
        with open(ruta_archivo, "w", encoding='utf-8') as file:
            json.dump(data, file, indent=4, ensure_ascii=False)

        return True, f"Tarea '{tarea}' agregada correctamente."

    except IOError as e:
        print(f"Error de E/S al agregar tarea en {ruta_archivo}: {e}")
        return False, "Error interno al guardar la tarea (IOError)."
    except Exception as e:
        print(f"Error inesperado al agregar tarea para {email}: {e}")
        return False, "Error interno inesperado al agregar la tarea."


def eliminar_tarea(tarea_a_eliminar, email):
    """Elimina una tarea de la lista del usuario."""
    ruta_archivo = f"usuarios/{email}/tareas.json"
    if not os.path.exists(ruta_archivo):
        return False, "No se encontraron tareas para este usuario."

    try:
        # Leer el archivo
        with open(ruta_archivo, "r", encoding='utf-8') as file:
            data = json.load(file)
            if "tareas" not in data or not isinstance(data["tareas"], list):
                print(f"Advertencia: Formato inválido en {ruta_archivo}. Reiniciando.")
                data = {"tareas": []}

        tareas_originales = data.get("tareas", [])
        tarea_encontrada = False
        # Crear nueva lista sin la tarea a eliminar (insensible a mayúsculas/minúsculas)
        nuevas_tareas = []
        for t in tareas_originales:
            if "descripcion" in t and t["descripcion"].strip().lower() == tarea_a_eliminar.strip().lower():
                tarea_encontrada = True
                print(f"Tarea '{tarea_a_eliminar}' encontrada para eliminar.")
            else:
                nuevas_tareas.append(t)

        if tarea_encontrada:
            data["tareas"] = nuevas_tareas
            # Guardar la lista actualizada
            with open(ruta_archivo, "w", encoding='utf-8') as file:
                json.dump(data, file, indent=4, ensure_ascii=False)
            return True, f"Tarea '{tarea_a_eliminar}' eliminada correctamente."
        else:
            return False, f"La tarea '{tarea_a_eliminar}' no se encontró en tu lista."

    except (json.JSONDecodeError, IOError) as e:
        print(f"Error al leer/escribir o archivo corrupto {ruta_archivo} al eliminar: {e}")
        return False, "Error interno al eliminar (archivo corrupto o problema de I/O)."
    except Exception as e:
        print(f"Error inesperado al eliminar tarea: {e}")
        return False, "Error interno inesperado al eliminar la tarea."


def mostrar_tareas(email):
    """Muestra todas las tareas del usuario, devolviendo dict {tareas: []} o vacío si falla."""
    ruta_archivo = f"usuarios/{email}/tareas.json"
    try:
        with open(ruta_archivo, "r", encoding='utf-8') as file:
            data = json.load(file)
            # Validar estructura básica
            if not isinstance(data, dict) or "tareas" not in data or not isinstance(data["tareas"], list):
                print(f"Advertencia: Formato inesperado en {ruta_archivo} para {email}. Devolviendo vacío.")
                return {"tareas": []}
            return data # Devuelve el diccionario completo {"tareas": [...]}
    except FileNotFoundError:
        print(f"Archivo de tareas no encontrado para {email}. Devolviendo lista vacía.")
        # Devolver estructura esperada aunque esté vacía
        return {"tareas": []}
    except json.JSONDecodeError:
        print(f"Error: Archivo de tareas corrupto para {email}. Devolviendo lista vacía.")
        return {"tareas": []}
    except Exception as e:
        print(f"Error inesperado al cargar tareas para {email}: {e}")
        return {"tareas": []}


def modificar_tarea(nombre_tarea_original, nuevos_datos_tarea, email):
    """Modifica una tarea existente con nuevos datos."""
    ruta_archivo = f"usuarios/{email}/tareas.json"
    if not os.path.exists(ruta_archivo):
        return False, "No se encontraron tareas para este usuario."

    try:
        # Leer archivo
        with open(ruta_archivo, "r", encoding='utf-8') as file:
            data = json.load(file)
            if "tareas" not in data or not isinstance(data["tareas"], list):
                 print(f"Advertencia: Formato inválido en {ruta_archivo} al modificar. Reiniciando.")
                 data = {"tareas": []}

        tareas = data.get("tareas", [])
        tarea_encontrada_index = -1
        # Buscar la tarea por descripción original (insensible a mayúsculas/minúsculas)
        nombre_original_lower = nombre_tarea_original.strip().lower()
        for i, t in enumerate(tareas):
            if "descripcion" in t and t["descripcion"].strip().lower() == nombre_original_lower:
                tarea_encontrada_index = i
                break

        if tarea_encontrada_index != -1:
            tarea_a_modificar = tareas[tarea_encontrada_index]
            print(f"Modificando tarea: {tarea_a_modificar}")

            # Actualizar campos si están presentes en nuevos_datos_tarea
            if "descripcion" in nuevos_datos_tarea:
                 nueva_desc = nuevos_datos_tarea["descripcion"].strip()
                 if nueva_desc: # No permitir descripción vacía
                     tarea_a_modificar["descripcion"] = nueva_desc
                 else:
                     return False, "La nueva descripción no puede estar vacía."

            if "categoria" in nuevos_datos_tarea:
                tarea_a_modificar["categoria"] = nuevos_datos_tarea["categoria"].strip() if nuevos_datos_tarea["categoria"] else "General"

            if "fecha_limite" in nuevos_datos_tarea:
                nueva_fecha_limite_str = nuevos_datos_tarea["fecha_limite"]
                if nueva_fecha_limite_str:
                     try:
                         # Validar y reformatear la nueva fecha
                         dt_obj = datetime.strptime(nueva_fecha_limite_str, '%Y-%m-%d %H:%M:%S')
                         tarea_a_modificar["fecha_limite"] = dt_obj.strftime('%Y-%m-%d %H:%M:%S')
                     except ValueError:
                         print(f"Advertencia: Formato de nueva fecha inválido: {nueva_fecha_limite_str}. No se actualiza la fecha.")
                         # Decidir si mantener la anterior o ponerla a None
                         # Mantengamos la anterior por ahora si la nueva es inválida
                         pass
                else:
                     # Si se pasa una cadena vacía o None, quitar la fecha límite
                     tarea_a_modificar["fecha_limite"] = None

            if "completada" in nuevos_datos_tarea:
                # Asegurarse de que sea un booleano
                tarea_a_modificar["completada"] = bool(nuevos_datos_tarea["completada"])

            print(f"Tarea después de modificar: {tarea_a_modificar}")

            # Guardar los cambios
            with open(ruta_archivo, "w", encoding='utf-8') as file:
                json.dump(data, file, indent=4, ensure_ascii=False)

            return True, f"Tarea '{nombre_tarea_original}' modificada correctamente."
        else:
            return False, f"La tarea '{nombre_tarea_original}' no se encontró para modificar."

    except (json.JSONDecodeError, IOError) as e:
        print(f"Error al leer/escribir o archivo corrupto {ruta_archivo} al modificar: {e}")
        return False, "Error interno al modificar (archivo corrupto o problema de I/O)."
    except Exception as e:
        print(f"Error inesperado al modificar tarea: {e}")
        return False, "Error interno inesperado al modificar la tarea."


def marcar_como_completada(tarea_a_completar, email):
    """Marca una tarea como completada en la lista."""
    ruta_archivo = f"usuarios/{email}/tareas.json"
    if not os.path.exists(ruta_archivo):
        return False, "No se encontraron tareas para este usuario."

    try:
        with open(ruta_archivo, "r+", encoding='utf-8') as file: # Abrir en modo lectura/escritura
            data = json.load(file)
            if "tareas" not in data or not isinstance(data["tareas"], list):
                 print(f"Advertencia: Formato inválido en {ruta_archivo} al completar. Reiniciando.")
                 data = {"tareas": []}

            tareas = data.get("tareas", [])
            tarea_encontrada = False
            tarea_a_completar_lower = tarea_a_completar.strip().lower()

            for t in tareas:
                 if "descripcion" in t and t["descripcion"].strip().lower() == tarea_a_completar_lower:
                     if not t.get("completada", False): # Marcar solo si no estaba ya completada
                         t["completada"] = True
                         tarea_encontrada = True
                         print(f"Marcando como completada: {t}")
                         break # Terminar bucle una vez encontrada y marcada
                     else:
                         # Si ya estaba completada, considerarlo éxito pero informar
                         return True, f"La tarea '{tarea_a_completar}' ya estaba marcada como completada."

            if tarea_encontrada:
                # Rebobinar y escribir todo el archivo actualizado
                file.seek(0)
                json.dump(data, file, indent=4, ensure_ascii=False)
                file.truncate() # Asegurar que no queden restos del archivo viejo
                return True, f"Tarea '{tarea_a_completar}' marcada como completada."
            else:
                return False, f"La tarea '{tarea_a_completar}' no se encontró en tu lista."

    except (json.JSONDecodeError, IOError) as e:
        print(f"Error al leer/escribir o archivo corrupto {ruta_archivo} al completar: {e}")
        return False, "Error interno al marcar completada (archivo corrupto o problema de I/O)."
    except Exception as e:
        print(f"Error inesperado al marcar como completada: {e}")
        return False, "Error interno inesperado al marcar la tarea como completada."

# --- Nueva Función de Reporte Genérica ---
def generar_reporte(periodo_tipo, fecha_inicio, fecha_fin, email):
    """
    Genera un reporte HTML de tareas para un período específico.
    Args:
        periodo_tipo (str): 'diario', 'semanal', o 'mensual'.
        fecha_inicio (datetime.date): Fecha de inicio del período.
        fecha_fin (datetime.date): Fecha de fin del período (inclusive).
        email (str): Email del usuario.
    Returns:
        str: Contenido HTML del reporte o mensaje de error.
    """
    ruta_archivo = f"usuarios/{email}/tareas.json"

    # Determinar el título del reporte basado en el tipo y fechas
    titulo_periodo = ""
    if periodo_tipo == 'diario':
        titulo_periodo = fecha_inicio.strftime('%d de %B de %Y')
    elif periodo_tipo == 'semanal':
        titulo_periodo = f"Semana del {fecha_inicio.strftime('%d/%m/%Y')} al {fecha_fin.strftime('%d/%m/%Y')}"
    elif periodo_tipo == 'mensual':
        titulo_periodo = fecha_inicio.strftime('%B de %Y')
    else:
        titulo_periodo = f"Período del {fecha_inicio.strftime('%d/%m/%Y')} al {fecha_fin.strftime('%d/%m/%Y')}"

    try:
        # Leer datos de tareas
        tareas_data = mostrar_tareas(email) # Reutilizar función de carga segura
        tareas = tareas_data.get("tareas", [])

        tareas_del_periodo = []
        # Convertir fechas de inicio/fin a datetime para comparación completa (incluyendo hora 00:00 y 23:59:59)
        inicio_dt = datetime.combine(fecha_inicio, datetime.min.time())
        fin_dt = datetime.combine(fecha_fin, datetime.max.time())

        for tarea in tareas:
            fecha_ref_str = tarea.get("fecha_limite") or tarea.get("fecha_creacion")
            if fecha_ref_str:
                try:
                    fecha_obj = datetime.strptime(fecha_ref_str, '%Y-%m-%d %H:%M:%S')
                    # Filtrar si la fecha de la tarea está dentro del rango [inicio_dt, fin_dt]
                    if inicio_dt <= fecha_obj <= fin_dt:
                        tareas_del_periodo.append(tarea)
                except ValueError:
                    # Podríamos intentar parsear solo la fecha si la hora falla
                    try:
                       fecha_obj_date = datetime.strptime(fecha_ref_str.split(" ")[0], '%Y-%m-%d').date()
                       if fecha_inicio <= fecha_obj_date <= fecha_fin:
                           tareas_del_periodo.append(tarea)
                    except ValueError:
                        pass # Ignorar tareas con formato de fecha inválido

        # Ordenar tareas del período
        tareas_del_periodo.sort(key=lambda t: (
            t.get("completada", False), # Pendientes (False=0) antes que completadas (True=1)
            t.get("fecha_limite") or t.get("fecha_creacion") or "9999", # Sin fecha al final
            t.get("descripcion", "").lower() # Orden alfabético como último criterio
        ))

        tareas_completadas = [t for t in tareas_del_periodo if t.get("completada")]
        tareas_pendientes = [t for t in tareas_del_periodo if not t.get("completada")]
        total_tareas = len(tareas_del_periodo)
        tasa_completitud = (len(tareas_completadas) / total_tareas * 100) if total_tareas > 0 else 0

        # --- INICIO: Generar reporte HTML (similar al anterior, pero con título dinámico) ---
        reporte_html = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <title>Reporte de Tareas - {titulo_periodo}</title>
            <style>
                /* --- Estilos CSS (los mismos que en generar_reporte_mensual) --- */
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    margin: 20px;
                    background-color: #f9f9f9;
                    color: #333;
                }}
                .report-container {{
                    background-color: #fff;
                    padding: 25px;
                    border-radius: 8px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                    max-width: 800px; /* Ancho máximo para legibilidad */
                    margin: auto; /* Centrar contenedor */
                }}
                h1, h2, h3 {{
                    color: #005a9e; /* Un azul oscuro */
                    border-bottom: 2px solid #e0e0e0;
                    padding-bottom: 5px;
                    margin-top: 25px;
                    margin-bottom: 15px;
                }}
                h1 {{ font-size: 1.8em; text-align: center; border-bottom: none; margin-bottom: 5px; }}
                h2 {{ font-size: 1.4em; text-align: center; margin-top: 0; padding-bottom: 10px; margin-bottom: 25px;}}
                h3 {{ font-size: 1.2em; color: #333; border-bottom: 1px dashed #ccc; }}
                ul {{
                    list-style-type: none;
                    padding-left: 0;
                }}
                li {{
                    margin-bottom: 12px;
                    border-bottom: 1px solid #f0f0f0;
                    padding: 10px 5px;
                    display: flex;
                    align-items: flex-start;
                    transition: background-color 0.2s ease; /* Suave hover */
                }}
                 li:hover {{
                    background-color: #f5f5f5; /* Ligero fondo al pasar el ratón */
                }}
                li:last-child {{
                    border-bottom: none;
                }}
                .task-icon {{
                    margin-right: 12px;
                    font-size: 1.2em; /* Icono un poco más grande */
                    width: 25px; /* Ancho fijo */
                    text-align: center;
                    line-height: 1.2; /* Alinear mejor verticalmente */
                    flex-shrink: 0; /* Evitar que el icono se encoja */
                }}
                .task-content {{
                    flex-grow: 1;
                }}
                .task-desc {{
                    font-weight: 600;
                    display: block;
                    margin-bottom: 4px;
                    color: #222; /* Descripción un poco más oscura */
                }}
                .task-details {{
                    font-size: 0.85em;
                    color: #555; /* Detalles más grises */
                    display: flex; /* Alinear detalles horizontalmente */
                    flex-wrap: wrap; /* Permitir que pasen a línea nueva si no caben */
                    gap: 5px 15px; /* Espacio vertical y horizontal entre elementos */
                }}
                .category-tag {{
                    background-color: #e7f3ff;
                    color: #005a9e;
                    padding: 2px 8px; /* Un poco más de padding */
                    border-radius: 10px; /* Más redondeado */
                    font-size: 0.8em;
                    white-space: nowrap; /* Evitar que se parta la etiqueta */
                }}
                .date-info {{
                     white-space: nowrap;
                }}
                .status-completed .task-icon {{ color: #28a745; }} /* Verde */
                .status-completed .task-desc {{ text-decoration: line-through; color: #888; }}
                .status-pending .task-icon {{ color: #ffc107; }} /* Ámbar */
                .status-overdue .task-icon {{ color: #dc3545; }} /* Rojo */
                .status-overdue .task-desc {{ color: #b82e3b; }}
                .status-overdue .date-info {{ color: #dc3545; font-weight: bold; }}
                .summary {{
                    background-color: #f0f4f8; /* Azul/gris muy pálido */
                    border: 1px solid #d6dde5;
                    padding: 15px 20px;
                    margin-bottom: 30px;
                    border-radius: 6px;
                }}
                .summary h3 {{ margin-top: 0; border: none; }}
                .summary p {{ margin: 6px 0; font-size: 0.95em; }}
                .summary strong {{ color: #1a4a73; }} /* Resaltar números */
                .no-tasks {{ font-style: italic; color: #888; padding: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="report-container">
                <h1>Reporte de Tareas</h1>
                <h2>{titulo_periodo}</h2>

                <div class="summary">
                    <h3>Resumen del Período</h3>
                    <p><strong>Total de tareas en el período:</strong> {total_tareas}</p>
                    <p><strong>Tareas completadas:</strong> {len(tareas_completadas)}</p>
                    <p><strong>Tareas pendientes:</strong> {len(tareas_pendientes)}</p>
                    <p><strong>Tasa de completitud:</strong> {tasa_completitud:.1f}%</p>
                </div>

                <h3>Tareas Pendientes ({len(tareas_pendientes)})</h3>
        """

        if tareas_pendientes:
            reporte_html += "<ul>"
            now_date = datetime.now().date() # Fecha actual para comparar vencimiento
            for tarea in tareas_pendientes:
                desc = html.escape(tarea.get('descripcion', 'Sin descripción'))
                cat = html.escape(tarea.get('categoria', 'General'))
                fecha_info = tarea.get("fecha_limite") or tarea.get("fecha_creacion", "N/A")
                fecha_display = fecha_info[:16] if fecha_info != "N/A" else "Sin fecha" # Mostrar hasta minutos

                status_class = "status-pending"
                icon = "●" # Icono pendiente

                # Verificar si está vencida (comparando con la fecha actual, no con el fin del período)
                is_overdue = False
                if tarea.get("fecha_limite"):
                     try:
                         limite_dt = datetime.strptime(tarea.get("fecha_limite"), '%Y-%m-%d %H:%M:%S').date()
                         if limite_dt < now_date: # Comparar con hoy
                             status_class = "status-overdue"
                             icon = "✕" # Icono vencido
                             is_overdue = True
                     except ValueError:
                         pass # Ignorar error de formato

                reporte_html += f"""
                     <li class="{status_class}">
                        <span class="task-icon">{icon}</span>
                        <div class="task-content">
                            <span class="task-desc">{desc}</span>
                            <span class="task-details">
                                <span class="date-info">{'Límite' if tarea.get("fecha_limite") else 'Creada'}: {fecha_display}</span>
                                <span class="category-tag">{cat}</span>
                            </span>
                        </div>
                    </li>
                """
            reporte_html += "</ul>"
        else:
            reporte_html += f"<p class='no-tasks'><i>¡Felicidades! Ninguna tarea pendiente para {periodo_tipo.lower()} {titulo_periodo}.</i></p>"

        reporte_html += f"<h3>Tareas Completadas ({len(tareas_completadas)})</h3>"

        if tareas_completadas:
            reporte_html += "<ul>"
            for tarea in tareas_completadas:
                desc = html.escape(tarea.get('descripcion', 'Sin descripción'))
                cat = html.escape(tarea.get('categoria', 'General'))
                # Mostrar fecha límite o creación como referencia
                fecha_info = tarea.get("fecha_limite") or tarea.get("fecha_creacion", "N/A")
                fecha_display = fecha_info[:16] if fecha_info != "N/A" else "N/A"
                reporte_html += f"""
                    <li class="status-completed">
                        <span class="task-icon">✓</span>
                        <div class="task-content">
                            <span class="task-desc">{desc}</span>
                             <span class="task-details">
                                <span class="date-info">Fecha: {fecha_display}</span>
                                <span class="category-tag">{cat}</span>
                            </span>
                        </div>
                    </li>
                """
            reporte_html += "</ul>"
        else:
            reporte_html += f"<p class='no-tasks'><i>Ninguna tarea completada para {periodo_tipo.lower()} {titulo_periodo}.</i></p>"

        reporte_html += """
            </div> </body>
        </html>"""
        # --- FIN: Generar reporte HTML ---
        return reporte_html

    except FileNotFoundError:
         # Devolver HTML simple para errores
        return f"<p style='color:orange; font-family: sans-serif;'>Aún no tienes tareas registradas ({email}) para generar un reporte.</p>"
    except json.JSONDecodeError:
        print(f"Error: Archivo corrupto para {email} al generar reporte.")
        return "<p style='color:red; font-family: sans-serif;'><b>Error interno al generar el reporte (archivo de tareas corrupto).</b></p>"
    except Exception as e:
        print(f"Error inesperado al generar reporte para {email}: {e}")
        return f"<p style='color:red; font-family: sans-serif;'><b>Error interno inesperado al generar el reporte:</b><br>{html.escape(str(e))}</p>"

# --- FIN DEL ARCHIVO commands.py ---
