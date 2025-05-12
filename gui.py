# gui.py

import sys
import os
import json
import datetime
from datetime import timedelta 
import re
import html
from collections import defaultdict
import traceback 

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                           QLabel, QPushButton, QLineEdit, QTextEdit,
                           QTableWidget, QTableWidgetItem, QCalendarWidget,
                           QMessageBox, QSplitter, QDialog, QFormLayout,
                           QCheckBox, QComboBox, QGroupBox, QStackedWidget,
                           QDialogButtonBox, QDateTimeEdit, QHeaderView,
                           QAction, QToolBar, QFileDialog, QDateEdit,
                           QAbstractItemView, QTextBrowser) 
from PyQt5.QtCore import (Qt, QDate, QTimer, pyqtSignal, QThread, QDateTime,
                          QSize, QObject, pyqtSlot, QMetaObject)
from PyQt5.QtGui import QIcon, QFont, QColor, QTextCharFormat, QPixmap

from commands import (agregar_tarea, eliminar_tarea, mostrar_tareas, modificar_tarea,
                     marcar_como_completada, generar_reporte)
from user_management import UserManager
from google_drive_sync import sync_tasks_to_drive, sync_tasks_from_drive

try:
    from utils import (escuchar_comando, hablar, cambiar_modo_entrada, MODO_ENTRADA,
                       cargar_modo_entrada_usuario, obtener_configuracion_usuario)
except ImportError:
    print("ADVERTENCIA: No se pudo importar 'utils'. La funcionalidad de voz y algunas configuraciones pueden no estar disponibles.")
    def escuchar_comando(): print("Escucha no disponible"); return "No entendí"
    def hablar(texto): print(f"Hablar (simulado): {texto}")
    def cambiar_modo_entrada(modo, email): print(f"Cambio de modo no disponible ({modo})"); return False, "Función no disponible"
    MODO_ENTRADA = 'texto'
    def cargar_modo_entrada_usuario(email): pass
    def obtener_configuracion_usuario(email): return {}

from main import interpretar_comando, mostrar_ayuda as obtener_manual_texto


class DriveSyncWorker(QObject): 
    syncFinished = pyqtSignal(bool, str, str)
    def __init__(self, email):
        super().__init__()
        self.email = email
        self._is_running = False
    @pyqtSlot()
    def do_sync_upload(self):
        if self._is_running or not self.email: return
        self._is_running = True; op_type = 'upload'
        try: success, message = sync_tasks_to_drive(self.email); self.syncFinished.emit(success, message, op_type)
        except Exception as e: self.syncFinished.emit(False, f"Error inesperado en worker (subida): {e}", op_type)
        finally: self._is_running = False
    @pyqtSlot()
    def do_sync_download(self):
        if self._is_running or not self.email: return
        self._is_running = True; op_type = 'download'
        try: success, message = sync_tasks_from_drive(self.email); self.syncFinished.emit(success, message, op_type)
        except Exception as e: self.syncFinished.emit(False, f"Error inesperado en worker (descarga): {e}", op_type)
        finally: self._is_running = False
    @pyqtSlot()
    def do_initial_sync_download(self):
        if self._is_running or not self.email: return
        self._is_running = True; op_type = 'initial_download'
        try: success, message = sync_tasks_from_drive(self.email); self.syncFinished.emit(success, message, op_type)
        except Exception as e: self.syncFinished.emit(False, f"Error inesperado en worker (descarga inicial): {e}", op_type)
        finally: self._is_running = False


class VoiceCommandWorker(QObject): 
    listening_status_changed = pyqtSignal(bool, str)
    command_recognized = pyqtSignal(str)
    command_processed = pyqtSignal(bool, str)
    speak_response = pyqtSignal(str)
    request_ui_refresh = pyqtSignal()
    request_gui_report_generation = pyqtSignal(str, int, int)
    request_view_change = pyqtSignal(int)
    request_logout = pyqtSignal()
    request_show_manual = pyqtSignal()

    def __init__(self, user_manager):
        super().__init__()
        self.user_manager = user_manager
        self._is_running_listener = False

    @pyqtSlot()
    def start_listening(self):
        if self._is_running_listener:
            self.listening_status_changed.emit(False, "Proceso de escucha ya iniciado.")
            return
        self._is_running_listener = True
        self.listening_status_changed.emit(True, "Escuchando...")
        try:
            if not self.user_manager.current_user:
                self.speak_response.emit("Error: No hay usuario logueado.")
                self.listening_status_changed.emit(False, "Usuario no logueado.")
                self._is_running_listener = False
                return
            
            if 'cargar_modo_entrada_usuario' in globals() and callable(globals()['cargar_modo_entrada_usuario']):
                 cargar_modo_entrada_usuario(self.user_manager.current_user)
            comando_texto_recibido = escuchar_comando()

            if comando_texto_recibido in ["No entendí", "Error de conexión"]:
                self.speak_response.emit(f"Lo siento, {comando_texto_recibido}.")
                self.listening_status_changed.emit(False, f"Error de escucha: {comando_texto_recibido}")
            elif comando_texto_recibido:
                self.command_recognized.emit(comando_texto_recibido)
                self.process_command_text(comando_texto_recibido)
            else:
                self.speak_response.emit("No pude entender eso.")
                self.listening_status_changed.emit(False, "No se recibió ningún comando inteligible.")
        except Exception as e:
            self.speak_response.emit("Hubo un error al procesar tu voz.")
            self.listening_status_changed.emit(False, f"Error interno en reconocimiento: {e}")
        finally:
            self._is_running_listener = False

    def process_command_text(self, texto_comando):
        if not self.user_manager.current_user:
            self.command_processed.emit(False, "Usuario no logueado."); return

        accion_interpretada = interpretar_comando(texto_comando)
        email_usuario = self.user_manager.current_user
        success = False
        message = f"Comando '{texto_comando}' no reconocido." 
        needs_refresh = False
        print(f"GUI VoiceWorker: Texto comando: '{texto_comando}', Acción interpretada: {accion_interpretada}") 

        try:
            if isinstance(accion_interpretada, tuple):
                comando_clave = accion_interpretada[0]
                
                if comando_clave == 'agregar':
                    if len(accion_interpretada) == 4: 
                        tarea_desc, fecha_limite_detectada, categoria_detectada = accion_interpretada[1], accion_interpretada[2], accion_interpretada[3]
                        
                        if not tarea_desc: 
                            success = False
                            message = "No se proporcionó descripción para la tarea."
                        else:
                            cat_para_agregar = categoria_detectada if categoria_detectada else "General"
                            success, cmd_message = agregar_tarea(tarea_desc, cat_para_agregar, fecha_limite_detectada, email_usuario)
                            
                            if success: 
                                needs_refresh = True
                                message = f"Tarea '{tarea_desc}' agregada en categoría '{cat_para_agregar}'"
                                message += f" con fecha límite {fecha_limite_detectada}." if fecha_limite_detectada else " sin fecha límite."
                            else: 
                                message = cmd_message 
                    else: 
                        success = False
                        message = "Error de formato interno para agregar tarea (se esperaban 4 elementos)."

                elif comando_clave == 'agregar_sin_info':
                    message, success = "No entendí qué tarea agregar. Por favor, especifica la descripción.", False
                elif comando_clave == 'agregar_sin_descripcion_con_fecha':
                    fecha_detectada = accion_interpretada[1]
                    message, success = f"Entendí una fecha ({fecha_detectada}) pero no la descripción de la tarea. Prueba 'agregar [descripción] para {fecha_detectada}'.", False
                elif comando_clave == 'agregar_sin_descripcion_con_cat':
                    categoria_detectada_err = accion_interpretada[2] 
                    message, success = f"Entendí una categoría ('{categoria_detectada_err}') pero no la descripción. Prueba 'agregar [descripción] en categoría {categoria_detectada_err}'.", False
                elif comando_clave == 'agregar_sin_descripcion_con_fecha_cat':
                    fecha_detectada_err = accion_interpretada[1]
                    categoria_detectada_err = accion_interpretada[2]
                    message, success = f"Entendí fecha ({fecha_detectada_err}) y categoría ('{categoria_detectada_err}') pero no la descripción. Por favor, especifica la tarea.", False

                elif comando_clave == 'eliminar':
                    success, message = eliminar_tarea(accion_interpretada[1], email_usuario)
                    if success: needs_refresh = True
                
                elif comando_clave == 'modificar_descripcion':
                    tarea_orig, nueva_desc = accion_interpretada[1], accion_interpretada[2]
                    success, message = modificar_tarea(tarea_orig, {"descripcion": nueva_desc}, email_usuario)
                    if success: needs_refresh = True
                elif comando_clave == 'modificar_fecha':
                    tarea_orig_f, nueva_fecha_f = accion_interpretada[1], accion_interpretada[2]
                    success, message = modificar_tarea(tarea_orig_f, {"fecha_limite": nueva_fecha_f}, email_usuario)
                    if success: needs_refresh = True
                elif comando_clave == 'modificar_categoria':
                    tarea_orig_c, nueva_cat_c = accion_interpretada[1], accion_interpretada[2]
                    success, message = modificar_tarea(tarea_orig_c, {"categoria": nueva_cat_c}, email_usuario)
                    if success: needs_refresh = True
                elif comando_clave == 'modificar_fecha_invalida':
                    tarea_orig_fi, fecha_texto_fi = accion_interpretada[1], accion_interpretada[2]
                    message = f"No pude entender la nueva fecha '{fecha_texto_fi}' para la tarea '{tarea_orig_fi}'."
                    success = False
                
                elif comando_clave == 'completar':
                    success, message = marcar_como_completada(accion_interpretada[1], email_usuario)
                    if success: needs_refresh = True
                
                elif comando_clave == 'mostrar_categoria':
                    categoria_buscada = accion_interpretada[1]
                    todas_las_tareas_data = mostrar_tareas(email_usuario)
                    tareas_de_categoria = [t['descripcion'] for t in todas_las_tareas_data.get("tareas", []) if t.get("categoria", "General").lower() == categoria_buscada.lower()] 
                    if tareas_de_categoria:
                        message = f"Tareas en '{categoria_buscada}': " + ", ".join(tareas_de_categoria[:3])
                        if len(tareas_de_categoria) > 3: message += f" y {len(tareas_de_categoria)-3} más."
                        success = True
                    else: message = f"No hay tareas en la categoría '{categoria_buscada}'."; success = True

                elif comando_clave == 'recordatorio_sin_fecha_clara':
                    message = f"No entendí bien la fecha '{accion_interpretada[2]}' para la tarea '{accion_interpretada[1]}'."
                    success = False
                elif comando_clave == 'recordatorio_sin_tarea_clara':
                    message = f"Entendí la fecha '{accion_interpretada[1]}', pero no la descripción de la tarea."
                    success = False
                elif comando_clave == 'generar_reporte':
                    año, mes = accion_interpretada[1], accion_interpretada[2]
                    self.request_gui_report_generation.emit("mensual", año, mes)
                    message = f"Generando reporte para {mes}/{año}."
                    success = True
                
                elif comando_clave == 'desconocido_modificar':
                    message = "No entendí cómo quieres modificar. Prueba 'modificar descripción de X a Y', 'fecha de X a Y', o 'categoría de X a Y'."
                    success = False
                elif comando_clave == 'desconocido_recordatorio':
                    message = "No entendí el recordatorio. Prueba 'agregar [tarea] para [fecha]'."
                    success = False
                elif comando_clave == 'desconocido_categoria':
                    message = "No entendí el comando de categoría. Prueba 'asignar categoría X a tarea Y'."
                    success = False

            elif isinstance(accion_interpretada, str): 
                if accion_interpretada == 'mostrar' or accion_interpretada == 'mostrar tareas':
                    self.request_view_change.emit(0)
                    tareas_data = mostrar_tareas(email_usuario)
                    pendientes = [t['descripcion'] for t in tareas_data.get("tareas", []) if not t.get("completada")] 
                    message = ("Mostrando tus tareas. Tienes " + str(len(pendientes)) + " pendientes." if pendientes else "Mostrando tareas. ¡No tienes pendientes!")
                    success = True; needs_refresh = True
                elif accion_interpretada == 'ayuda': 
                    self.request_show_manual.emit()
                    message = "Mostrando el manual de ayuda."
                    success = True
                elif accion_interpretada == 'activar_silencioso':
                     if 'cambiar_modo_entrada' in globals() and callable(globals()['cambiar_modo_entrada']):
                        success, message = cambiar_modo_entrada('texto', email_usuario)
                elif accion_interpretada == 'desactivar_silencioso':
                     if 'cambiar_modo_entrada' in globals() and callable(globals()['cambiar_modo_entrada']):
                        success, message = cambiar_modo_entrada('voz', email_usuario)
                elif accion_interpretada == 'toggle_silencioso':
                     if 'cambiar_modo_entrada' in globals() and callable(globals()['cambiar_modo_entrada']):
                        nuevo_modo = 'texto' if MODO_ENTRADA == 'voz' else 'voz'
                        success, message = cambiar_modo_entrada(nuevo_modo, email_usuario)
                elif accion_interpretada in ['formato_calendario', 'ver_calendario_local', 'mostrar calendario', 'calendario']:
                    self.request_view_change.emit(1); message = "Mostrando calendario."; success = True
                elif accion_interpretada in ['mostrar reportes', 'ver reportes']:
                    self.request_view_change.emit(2); message = "Mostrando la vista de reportes."; success = True
                elif accion_interpretada == 'logout':
                    self.request_logout.emit(); message = "Cerrando sesión..."; success = True
                elif accion_interpretada == 'desconocido':
                     message = f"No pude entender el comando: '{texto_comando}'. Intenta de nuevo o di 'ayuda'."
                     success = False
            
            if not success and message == f"Comando '{texto_comando}' no reconocido.":
                 message = f"No pude procesar: '{texto_comando}'. Intenta de nuevo o di 'ayuda'."

        except Exception as e:
            success = False
            message = f"Error al procesar comando por voz: {str(e)}"
            print(f"Error detallado en process_command_text: {e}\n{traceback.format_exc()}")

        self.command_processed.emit(success, message)
        if 'hablar' in globals() and callable(globals()['hablar']):
            self.speak_response.emit(message)
        self.listening_status_changed.emit(False, message)
        
        if needs_refresh and success:
            self.request_ui_refresh.emit()
# --- Fin Worker Voz ---

# --- Diálogo para mostrar el Manual ---
class ManualDialog(QDialog):
    def __init__(self, manual_texto, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manual de Usuario - VoceTasks")
        self.setGeometry(150, 150, 750, 600) 
        self.setMinimumSize(600, 400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout(self)
        
        text_browser = QTextBrowser(self)
        text_browser.setReadOnly(True)
        text_browser.setOpenExternalLinks(True)
        
        html_content_lines = []
        current_list_open = False
        title_line = "Bienvenido a VoceTasks - Tu Asistente de Tareas Inteligente"
        manual_texto_sin_titulo = manual_texto.replace(title_line, "", 1).strip()

        for line in manual_texto_sin_titulo.splitlines():
            stripped_line = line.strip()
            if stripped_line.startswith("**") and stripped_line.endswith("**"):
                if current_list_open:
                    html_content_lines.append("</ul>")
                    current_list_open = False
                html_content_lines.append(f"<h2>{html.escape(stripped_line.strip('** '))}</h2>")
            elif stripped_line.startswith("* "):
                if not current_list_open:
                    html_content_lines.append("<ul>")
                    current_list_open = True
                item_content = html.escape(stripped_line[2:])
                item_content = re.sub(r'`(.*?)`', r'<code>\1</code>', item_content)
                html_content_lines.append(f"<li>{item_content}</li>")
            else:
                if current_list_open: 
                    html_content_lines.append("</ul>")
                    current_list_open = False
                if stripped_line: 
                    line_content = html.escape(line) 
                    line_content = re.sub(r'`(.*?)`', r'<code>\1</code>', line_content)
                    html_content_lines.append(f"<p>{line_content}</p>")
                elif not html_content_lines or not html_content_lines[-1].endswith("<br>"): 
                     html_content_lines.append("<br>")


        if current_list_open:
            html_content_lines.append("</ul>")
            
        html_body = "\n".join(html_content_lines)
        
        styled_html = f"""
        <html>
        <head>
            <style>
                body {{ 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                    font-size: 10pt; 
                    line-height: 1.6; 
                    margin: 15px;
                    background-color: #f9f9f9; 
                }}
                h1 {{ 
                    color: #004a8d; 
                    font-size: 1.5em; 
                    text-align: center; 
                    margin-bottom: 1em;
                    border-bottom: 2px solid #005a9e;
                    padding-bottom: 0.5em;
                }}
                h2 {{ 
                    color: #005a9e; 
                    font-size: 1.25em; 
                    margin-top: 1.5em; 
                    margin-bottom: 0.7em;
                    border-bottom: 1px solid #ccc;
                    padding-bottom: 0.3em;
                }}
                p {{ margin-bottom: 0.8em; /*text-align: justify;*/ }} /* Comentado text-align justify por si no gusta */
                ul {{ 
                    list-style-type: disc; 
                    padding-left: 25px; 
                    margin-bottom: 0.8em;
                }}
                li {{ margin-bottom: 0.5em; }}
                code {{ 
                    background-color: #e8f0fe; 
                    padding: 2px 5px; 
                    border-radius: 4px; 
                    font-family: Consolas, 'Courier New', monospace;
                    color: #2a5298; 
                    border: 1px solid #c9dfff;
                }}
            </style>
        </head>
        <body>
            <h1>{html.escape(title_line)}</h1>
            {html_body}
        </body>
        </html>
        """
        text_browser.setHtml(styled_html)
        
        layout.addWidget(text_browser)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Close, self)
        button_box.rejected.connect(self.reject) 
        layout.addWidget(button_box)
        
        self.setLayout(layout)


# --- Diálogos (LoginDialog, RegisterDialog, TaskDialog) ---
# ...(Se mantienen sin cambios)...
class LoginDialog(QDialog):
    def __init__(self, user_manager, parent=None):
        super().__init__(parent)
        self.user_manager = user_manager
        self.setWindowTitle("Iniciar Sesión")
        self.setGeometry(100, 100, 300, 150)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        layout = QFormLayout()
        self.login_email = QLineEdit(self)
        self.login_email.setPlaceholderText("Email")
        layout.addRow("Email:", self.login_email)
        self.login_password = QLineEdit(self)
        self.login_password.setPlaceholderText("Contraseña")
        self.login_password.setEchoMode(QLineEdit.Password)
        layout.addRow("Contraseña:", self.login_password)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.button_box.accepted.connect(self.handle_login)
        self.button_box.rejected.connect(self.reject)
        layout.addRow(self.button_box)
        self.setLayout(layout)

    def handle_login(self):
        email = self.login_email.text()
        password = self.login_password.text()
        success, message = self.user_manager.login(email, password)
        if success:
            QMessageBox.information(self, "Éxito", message)
            if self.user_manager.current_user:
                 print(f"Usuario logueado: {self.user_manager.current_user}. La sincronización inicial se hará en la ventana principal.")
            self.accept()
        else:
            QMessageBox.warning(self, "Error", message)


class RegisterDialog(QDialog):
    def __init__(self, user_manager, parent=None):
        super().__init__(parent)
        self.user_manager = user_manager
        self.setWindowTitle("Registrar Nuevo Usuario")
        self.setGeometry(100, 100, 300, 200)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        layout = QFormLayout()
        self.reg_email = QLineEdit(self)
        self.reg_email.setPlaceholderText("Email (será tu nombre de usuario)")
        layout.addRow("Email:", self.reg_email)
        self.reg_name = QLineEdit(self)
        self.reg_name.setPlaceholderText("Tu nombre")
        layout.addRow("Nombre:", self.reg_name)
        self.reg_password = QLineEdit(self)
        self.reg_password.setPlaceholderText("Contraseña")
        self.reg_password.setEchoMode(QLineEdit.Password)
        layout.addRow("Contraseña:", self.reg_password)
        self.reg_confirm_password = QLineEdit(self)
        self.reg_confirm_password.setPlaceholderText("Confirmar Contraseña")
        self.reg_confirm_password.setEchoMode(QLineEdit.Password)
        layout.addRow("Confirmar Contraseña:", self.reg_confirm_password)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.button_box.accepted.connect(self.handle_register)
        self.button_box.rejected.connect(self.reject)
        layout.addRow(self.button_box)
        self.setLayout(layout)

    def handle_register(self):
        email = self.reg_email.text()
        name = self.reg_name.text()
        password = self.reg_password.text()
        confirm_password = self.reg_confirm_password.text()
        if password != confirm_password:
            QMessageBox.warning(self, "Error de Registro", "Las contraseñas no coinciden.")
            return
        success, message = self.user_manager.register_user(email, name, password)
        if success:
            QMessageBox.information(self, "Registro Exitoso", message)
            self.accept()
        else:
            QMessageBox.warning(self, "Error de Registro", message)


class TaskDialog(QDialog):
    def __init__(self, user_manager, task_data=None, parent=None):
        super().__init__(parent)
        self.user_manager = user_manager
        self.task_data = task_data
        title = f"Modificar Tarea: {task_data['descripcion']}" if task_data and task_data.get('descripcion') else "Agregar Tarea"
        self.setWindowTitle(title)
        self.setGeometry(100, 100, 400, 250)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        layout = QFormLayout()
        self.description_edit = QLineEdit(self)
        self.description_edit.setPlaceholderText("Descripción de la tarea")
        layout.addRow("Descripción:", self.description_edit)
        self.category_combo = QComboBox(self)
        self.category_combo.addItem("General")
        self.category_combo.setEditable(True)
        self.category_combo.setStyleSheet("QComboBox { background-color: white; color: black; }")
        layout.addRow("Categoría:", self.category_combo)
        self.datetime_edit = QDateTimeEdit(self)
        self.datetime_edit.setCalendarPopup(True)
        self.datetime_edit.setDateTime(QDateTime.currentDateTime())
        self.datetime_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.datetime_edit.setStyleSheet("QDateTimeEdit { background-color: white; color: black; }")
        self.no_due_date_checkbox = QCheckBox("Sin fecha límite", self)
        self.no_due_date_checkbox.stateChanged.connect(self.toggle_datetime_edit)
        layout.addRow("Fecha y Hora Límite:", self.datetime_edit)
        layout.addRow("", self.no_due_date_checkbox)
        self.completed_checkbox = QCheckBox("Completada", self)
        layout.addRow("", self.completed_checkbox)
        if self.task_data:
            self.description_edit.setText(self.task_data.get("descripcion", ""))
            category = self.task_data.get("categoria", "General")
            if self.category_combo.findText(category) == -1 and category != "General":
                 self.category_combo.addItem(category)
            self.category_combo.setCurrentText(category)
            fecha_limite_str = self.task_data.get("fecha_limite")
            if fecha_limite_str:
                try:
                    dt_obj = datetime.datetime.strptime(fecha_limite_str, '%Y-%m-%d %H:%M:%S')
                    qdt = QDateTime(dt_obj.year, dt_obj.month, dt_obj.day, dt_obj.hour, dt_obj.minute, dt_obj.second)
                    self.datetime_edit.setDateTime(qdt)
                    self.no_due_date_checkbox.setChecked(False); self.datetime_edit.setEnabled(True)
                except ValueError:
                    print(f"Advertencia: Formato de fecha inválido al editar: {fecha_limite_str}."); self.no_due_date_checkbox.setChecked(True); self.datetime_edit.setEnabled(False)
            else: self.no_due_date_checkbox.setChecked(True); self.datetime_edit.setEnabled(False)
            self.completed_checkbox.setChecked(self.task_data.get("completada", False))
        else: self.no_due_date_checkbox.setChecked(False); self.datetime_edit.setEnabled(True)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        button_box.accepted.connect(self.accept); button_box.rejected.connect(self.reject); layout.addRow(button_box); self.setLayout(layout)

    def toggle_datetime_edit(self, state): self.datetime_edit.setEnabled(state != Qt.Checked)
    def set_initial_date(self, qdate): self.datetime_edit.setDateTime(QDateTime(qdate, QDateTime.currentDateTime().time())); self.no_due_date_checkbox.setChecked(False); self.datetime_edit.setEnabled(True)
    def get_task_data(self):
        fls = self.datetime_edit.dateTime().toString("yyyy-MM-dd HH:mm:ss") if not self.no_due_date_checkbox.isChecked() else None
        return {"descripcion": self.description_edit.text().strip(), "categoria": self.category_combo.currentText().strip() or "General", "fecha_limite": fls, "completada": self.completed_checkbox.isChecked()}

# --- Clases para las Vistas (TasksViewWidget, CalendarViewWidget, ReportsViewWidget) ---
class TasksViewWidget(QWidget):
    request_refresh_views = pyqtSignal()
    def __init__(self, user_manager, parent=None):
        super().__init__(parent)
        self.user_manager = user_manager
        self.tasks_data = {"tareas": []}
        self.layout = QVBoxLayout(self)
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(350) 
        self.search_timer.timeout.connect(self.refresh_tasks_display)

        self.view_title = QLabel("Lista de Tareas", self)
        self.view_title.setObjectName("viewTitleLabel")
        self.view_title.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.view_title)

        controls_group_box = QGroupBox("Controles")
        controls_layout = QHBoxLayout(controls_group_box)
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Buscar tarea...")
        self.search_input.textChanged.connect(self.on_search_text_changed)
        controls_layout.addWidget(QLabel("Buscar:", self))
        controls_layout.addWidget(self.search_input, 1)
        self.filter_label = QLabel("Categoría:", self) 
        controls_layout.addWidget(self.filter_label)
        self.category_filter_combo = QComboBox(self)
        self.category_filter_combo.addItem("Todas")
        self.category_filter_combo.currentIndexChanged.connect(self.filter_by_category)
        controls_layout.addWidget(self.category_filter_combo)
        add_icon_path = os.path.join("icons", "add.png")
        add_icon = QIcon(add_icon_path) if os.path.exists(add_icon_path) else QIcon.fromTheme("list-add")
        self.add_button = QPushButton(add_icon, "Agregar Tarea", self)
        self.add_button.clicked.connect(self.handle_add_task_dialog_show)
        controls_layout.addWidget(self.add_button)
        self.layout.addWidget(controls_group_box)

        self.task_table = QTableWidget(self)
        self.task_table.setColumnCount(5)
        self.task_table.setHorizontalHeaderLabels(["Descripción", "Categoría", "Fecha Límite", "Completada", "Acciones"]) 
        self.task_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch) 
        for col in range(1, 5): self.task_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.task_table.setEditTriggers(QAbstractItemView.NoEditTriggers) 
        self.task_table.setSelectionBehavior(QAbstractItemView.SelectRows) 
        self.task_table.setAlternatingRowColors(True)
        self.layout.addWidget(self.task_table)

    def load_and_display_tasks(self):
        if self.user_manager.current_user:
            self.tasks_data = mostrar_tareas(self.user_manager.current_user)
            if not (isinstance(self.tasks_data,dict) and "tareas" in self.tasks_data and isinstance(self.tasks_data["tareas"], list)):
                self.tasks_data={"tareas":[]} 
            self.refresh_tasks_display()
        else:
            self.tasks_data = {"tareas":[]}; self.refresh_tasks_display() 

    @pyqtSlot()
    def on_search_text_changed(self): self.search_timer.start() 

    def refresh_tasks_display(self):
        search_term = self.search_input.text()
        current_category_filter = self.category_filter_combo.currentText()
        tareas_list = self.tasks_data.get("tareas", [])
        self.populate_category_filter(tareas_list, current_category_filter) 
        category_filter_to_use = self.category_filter_combo.currentText() 
        filtered_tasks_list = self._filter_tasks(tareas_list, search_term, category_filter_to_use)
        self.populate_task_table(filtered_tasks_list)

    def _filter_tasks(self, tasks, search_term, category):
        filtered = list(tasks) 
        search_term_lower = search_term.lower().strip()
        category_lower = category.strip().lower()
        if category_lower != "todas":
            filtered = [t for t in filtered if t.get("categoria","General").strip().lower() == category_lower]
        if search_term_lower:
            filtered = [t for t in filtered if search_term_lower in t.get("descripcion","").lower() or \
                                                search_term_lower in t.get("categoria","").lower()]
        filtered.sort(key=lambda t: (t.get("completada", False), t.get("fecha_limite") or t.get("fecha_creacion") or "9999-12-31 23:59:59", t.get("descripcion", "").lower()))
        return filtered

    def populate_task_table(self, tasks_to_display):
        self.task_table.setRowCount(0) 
        self.task_table.setRowCount(len(tasks_to_display))
        now_datetime = datetime.datetime.now()
        for row_idx, task_item in enumerate(tasks_to_display):
            desc, cat, due_date_str, is_completed = task_item.get("descripcion", ""), task_item.get("categoria", "N/A"), task_item.get("fecha_limite", ""), task_item.get("completada", False)
            display_due_date = due_date_str[:16] if due_date_str else "Sin Fecha" 
            desc_item, cat_item, due_date_item, completed_item = QTableWidgetItem(desc), QTableWidgetItem(cat), QTableWidgetItem(display_due_date), QTableWidgetItem("Sí" if is_completed else "No")
            completed_item.setTextAlignment(Qt.AlignCenter)
            if is_completed:
                font = desc_item.font(); font.setStrikeOut(True)
                for item_ in [desc_item, cat_item, due_date_item, completed_item]: item_.setFont(font); item_.setBackground(QColor(235, 245, 235)); item_.setForeground(QColor(120, 120, 120))
            elif due_date_str and isinstance(due_date_str, str): 
                try:
                    if datetime.datetime.strptime(due_date_str, '%Y-%m-%d %H:%M:%S') < now_datetime: 
                        for item_ in [desc_item, due_date_item]: item_.setForeground(QColor("red")); font_b = item_.font(); font_b.setBold(True); item_.setFont(font_b)
                except ValueError: pass 
            self.task_table.setItem(row_idx, 0, desc_item); self.task_table.setItem(row_idx, 1, cat_item); self.task_table.setItem(row_idx, 2, due_date_item); self.task_table.setItem(row_idx, 3, completed_item)
            actions_widget = QWidget(); actions_layout = QHBoxLayout(actions_widget); actions_layout.setContentsMargins(5,0,5,0); actions_layout.setSpacing(5); actions_layout.setAlignment(Qt.AlignCenter)
            icon_size = 24; original_desc_for_action = task_item.get("descripcion","") 
            comp_icon_path = os.path.join("icons","complete.png"); comp_icon = QIcon(comp_icon_path) if os.path.exists(comp_icon_path) else QIcon.fromTheme("task-complete")
            comp_btn = QPushButton(comp_icon, "", actions_widget); comp_btn.setToolTip("Marcar Completada/Pendiente"); comp_btn.setFixedSize(icon_size,icon_size); comp_btn.setEnabled(not is_completed); comp_btn.clicked.connect(lambda ch, d=original_desc_for_action: self.complete_task(d)); actions_layout.addWidget(comp_btn)
            edit_icon_path = os.path.join("icons","edit.png"); edit_icon = QIcon(edit_icon_path) if os.path.exists(edit_icon_path) else QIcon.fromTheme("document-edit")
            edit_btn = QPushButton(edit_icon, "", actions_widget); edit_btn.setToolTip("Modificar Tarea"); edit_btn.setFixedSize(icon_size,icon_size); edit_btn.clicked.connect(lambda ch, d=original_desc_for_action: self.modify_task(d)); actions_layout.addWidget(edit_btn)
            del_icon_path = os.path.join("icons","delete.png"); del_icon = QIcon(del_icon_path) if os.path.exists(del_icon_path) else QIcon.fromTheme("edit-delete")
            del_btn = QPushButton(del_icon, "", actions_widget); del_btn.setToolTip("Eliminar Tarea"); del_btn.setFixedSize(icon_size,icon_size); del_btn.clicked.connect(lambda ch, d=original_desc_for_action: self.delete_task(d)); actions_layout.addWidget(del_btn)
            self.task_table.setCellWidget(row_idx, 4, actions_widget)
        self.task_table.verticalHeader().setDefaultSectionSize(max(28, icon_size + 4)) 

    def populate_category_filter(self,tasks_list,current_selection_text):
        self.category_filter_combo.blockSignals(True); self.category_filter_combo.clear(); self.category_filter_combo.addItem("Todas")
        if tasks_list: categories = sorted(list(set(t.get("categoria","General").strip() or "General" for t in tasks_list if isinstance(t,dict))), key=str.lower)
        else: categories = []
        for cat_name in categories:
            if cat_name != "Todas": self.category_filter_combo.addItem(cat_name)
        idx = self.category_filter_combo.findText(current_selection_text); self.category_filter_combo.setCurrentIndex(idx if idx != -1 else 0); self.category_filter_combo.blockSignals(False)

    def filter_by_category(self): self.refresh_tasks_display()
    def handle_add_task_dialog_show(self):
        dialog = TaskDialog(self.user_manager, parent=self)
        tasks_list_for_dialog = self.tasks_data.get("tareas",[])
        all_categories = set(t.get("categoria","General").strip() or "General" for t in tasks_list_for_dialog if isinstance(t,dict))
        sorted_categories = sorted(list(all_categories),key=str.lower)
        existing_dialog_cats = {dialog.category_combo.itemText(i) for i in range(dialog.category_combo.count())}
        for cat_item in sorted_categories:
            if cat_item not in existing_dialog_cats: dialog.category_combo.addItem(cat_item)
        self.handle_add_modify_task_dialog_result(dialog)

    def handle_add_modify_task_dialog_result(self, dialog_instance):
        if dialog_instance.exec_() == QDialog.Accepted:
            task_data_from_dialog = dialog_instance.get_task_data()
            description = task_data_from_dialog.get("descripcion")
            if not description: QMessageBox.warning(self, "Descripción Inválida", "La descripción no puede estar vacía."); return
            if not self.user_manager.current_user: QMessageBox.warning(self,"Error de Usuario","No hay usuario."); return
            op_type = "modificar" if dialog_instance.task_data else "agregar"
            orig_desc = dialog_instance.task_data.get("descripcion") if dialog_instance.task_data else None
            if op_type == "agregar": success, message = agregar_tarea(description, task_data_from_dialog.get("categoria"), task_data_from_dialog.get("fecha_limite"), self.user_manager.current_user, task_data_from_dialog.get("completada",False))
            else: success, message = modificar_tarea(orig_desc, task_data_from_dialog, self.user_manager.current_user)
            if success: self.request_refresh_views.emit()
            else: QMessageBox.warning(self, f"Error al {op_type} Tarea", message)

    def complete_task(self, task_description):
        if task_description and self.user_manager.current_user:
            success, message = marcar_como_completada(task_description, self.user_manager.current_user)
            if success: self.request_refresh_views.emit()
            else: QMessageBox.warning(self, "Error al Completar", message)

    def delete_task(self, task_description):
        if task_description and QMessageBox.question(self, "Confirmar", f"Eliminar '{task_description}'?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            if self.user_manager.current_user:
                success, message = eliminar_tarea(task_description, self.user_manager.current_user)
                if success: self.request_refresh_views.emit()
                else: QMessageBox.warning(self, "Error al Eliminar", message)

    def modify_task(self, task_name_to_modify):
        if not task_name_to_modify: return
        task_data_to_modify = next((t for t in self.tasks_data.get("tareas", []) if isinstance(t,dict) and t.get("descripcion","").strip().lower() == task_name_to_modify.strip().lower()), None)
        if not task_data_to_modify: QMessageBox.warning(self,"No Encontrada",f"Tarea '{task_name_to_modify}' no encontrada."); return
        dialog = TaskDialog(self.user_manager, task_data=task_data_to_modify, parent=self)
        all_categories_mod = set(t.get("categoria","General").strip() or "General" for t in self.tasks_data.get("tareas",[]) if isinstance(t,dict))
        sorted_categories_mod = sorted(list(all_categories_mod),key=str.lower)
        dialog.category_combo.clear(); dialog.category_combo.addItem("General"); existing_dialog_cats_mod = {"General"}
        for cat_item_mod in sorted_categories_mod:
            if cat_item_mod not in existing_dialog_cats_mod: dialog.category_combo.addItem(cat_item_mod); existing_dialog_cats_mod.add(cat_item_mod)
        current_task_cat = task_data_to_modify.get("categoria","General")
        if dialog.category_combo.findText(current_task_cat) == -1:
            if current_task_cat: dialog.category_combo.addItem(current_task_cat)
        dialog.category_combo.setCurrentText(current_task_cat if current_task_cat else "General")
        self.handle_add_modify_task_dialog_result(dialog)

class CalendarViewWidget(QWidget):
    request_refresh_views = pyqtSignal()
    def __init__(self, user_manager, parent=None):
        super().__init__(parent)
        self.user_manager=user_manager; self.tasks_data={"tareas":[]}; self.layout=QVBoxLayout(self)
        self.view_title=QLabel("Calendario",self); self.view_title.setObjectName("viewTitleLabel"); self.view_title.setAlignment(Qt.AlignCenter); self.layout.addWidget(self.view_title)
        splitter=QSplitter(Qt.Horizontal); cal_container=QWidget(); cal_layout=QVBoxLayout(cal_container); self.calendar_widget=QCalendarWidget(self)
        self.calendar_widget.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader); self.calendar_widget.currentPageChanged.connect(self.update_calendar_highlight); self.calendar_widget.clicked[QDate].connect(self.show_tasks_for_date); self.calendar_widget.activated.connect(self.handle_calendar_activated)
        self.calendar_widget.setStyleSheet("QCalendarWidget QToolButton {color:black; background-color:#f0f0f0; border:1px solid #ccc; padding:5px; min-width:80px;} QCalendarWidget QMenu {background-color:white;} QCalendarWidget QSpinBox {padding:2px; margin:0 5px; background-color:white; color:black;} QCalendarWidget QAbstractItemView {selection-background-color:#a8d8ff; selection-color:black;} QCalendarWidget QWidget#qt_calendar_navigationbar {background-color:#e8e8e8;} QCalendarWidget QAbstractItemView:enabled {color:#333;}")
        cal_layout.addWidget(self.calendar_widget); splitter.addWidget(cal_container)
        tasks_display_container=QWidget(); tasks_display_layout=QVBoxLayout(tasks_display_container); self.tasks_for_date_label=QLabel("Tareas para fecha:",self); self.tasks_for_date_text_edit=QTextEdit(self); self.tasks_for_date_text_edit.setObjectName("calendarTaskDisplay"); self.tasks_for_date_text_edit.setReadOnly(True)
        tasks_display_layout.addWidget(self.tasks_for_date_label); tasks_display_layout.addWidget(self.tasks_for_date_text_edit); splitter.addWidget(tasks_display_container)
        splitter.setSizes([600,400]); self.layout.addWidget(splitter)

    def load_and_display_tasks(self):
        self.tasks_data = mostrar_tareas(self.user_manager.current_user) if self.user_manager.current_user else {"tareas":[]}
        if not (isinstance(self.tasks_data, dict) and "tareas" in self.tasks_data and isinstance(self.tasks_data["tareas"], list)): self.tasks_data = {"tareas":[]}
        self.update_calendar_highlight()
        self.show_tasks_for_date(self.calendar_widget.selectedDate())

    def update_calendar_highlight(self):
        year, month = self.calendar_widget.yearShown(), self.calendar_widget.monthShown(); default_fmt = QTextCharFormat()
        date_iter = QDate(year,month,1)
        if date_iter.isValid():
            for day_off in range(date_iter.daysInMonth()): self.calendar_widget.setDateTextFormat(date_iter.addDays(day_off), default_fmt)
        pending_fmt, overdue_fmt, completed_fmt, mixed_fmt = QTextCharFormat(), QTextCharFormat(), QTextCharFormat(), QTextCharFormat()
        pending_fmt.setBackground(QColor("#FFFACD")); overdue_fmt.setBackground(QColor("#FFC0CB")); overdue_fmt.setFontWeight(QFont.Bold); completed_fmt.setBackground(QColor("#90EE90")); mixed_fmt.setBackground(QColor("#ADD8E6"))
        fmts = {"pending":pending_fmt, "overdue":overdue_fmt, "completed":completed_fmt, "mixed":mixed_fmt}
        tasks_by_date = defaultdict(lambda: {'pending':0,'completed':0,'overdue':0}); today = QDate.currentDate()
        
        tasks_list_calendar = self.tasks_data.get("tareas", [])
        if not isinstance(tasks_list_calendar, list): tasks_list_calendar = []

        for task in tasks_list_calendar:
            if not isinstance(task, dict): continue
            due_str = task.get("fecha_limite") 
            if isinstance(due_str, str): 
                try:
                    qdt = QDateTime.fromString(due_str, "yyyy-MM-dd HH:mm:ss")
                    if qdt.isValid():
                        qdate = qdt.date(); completed = task.get("completada",False)
                        if completed: tasks_by_date[qdate]['completed']+=1
                        else: 
                            tasks_by_date[qdate]['pending']+=1
                            if qdate < today: tasks_by_date[qdate]['overdue']+=1
                except Exception as e: 
                    print(f"Error al procesar fecha '{due_str}' para resaltado: {e}")
        
        for qd, counts in tasks_by_date.items():
            if qd.year()==year and qd.month()==month:
                fmt_key = "overdue" if counts['overdue']>0 else ("mixed" if counts['pending']>0 and counts['completed']>0 else ("pending" if counts['pending']>0 else ("completed" if counts['completed']>0 else None)))
                if fmt_key and fmt_key in fmts: self.calendar_widget.setDateTextFormat(qd, QTextCharFormat(fmts[fmt_key]))
        sel_date = self.calendar_widget.selectedDate()
        if sel_date.isValid() and sel_date.year()==year and sel_date.month()==month:
            sel_fmt = QTextCharFormat(self.calendar_widget.dateTextFormat(sel_date)); sel_fmt.setFontWeight(QFont.Bold); self.calendar_widget.setDateTextFormat(sel_date, sel_fmt)

    def show_tasks_for_date(self, q_date_selected):
        self.update_calendar_highlight() 
        selected_date_str = q_date_selected.toString("yyyy-MM-dd")
        tasks_on_date = []
        now_dt = datetime.datetime.now()
        
        tasks_list_for_display = self.tasks_data.get("tareas", [])
        if not isinstance(tasks_list_for_display, list): 
            tasks_list_for_display = []

        for task_item_disp in tasks_list_for_display:
            if not isinstance(task_item_disp, dict): 
                continue 

            due_date_val = task_item_disp.get("fecha_limite") 

            if isinstance(due_date_val, str) and due_date_val.startswith(selected_date_str):
                tasks_on_date.append(task_item_disp)
        
        tasks_on_date.sort(key=lambda t:(t.get("fecha_limite",""),t.get("descripcion","").lower()))
        html_str = f"<style>body{{font-size:10pt;}}.task-item{{margin-bottom:8px;padding:6px 8px;border-left:4px solid #ccc;}}.task-item.completed{{border-left-color:#28a745;background-color:#e8f5e9;text-decoration:line-through;color:grey;}}.task-item.overdue{{border-left-color:#dc3545;background-color:#fdecea;}}.task-item.pending{{border-left-color:#ffc107;}}.task-desc{{font-weight:bold;}}.task-details{{font-size:9pt;color:#555;}}</style><b>Tareas para {selected_date_str}:</b> ({len(tasks_on_date)})<br><br>"
        if tasks_on_date:
            for t_html_item in tasks_on_date:
                comp_html, desc_html, cat_html, due_full_html = t_html_item.get("completada",False), html.escape(t_html_item.get('descripcion','N/A')), html.escape(t_html_item.get('categoria','N/A')), t_html_item.get('fecha_limite')
                time_str_html, overdue_html, status_cls_html = "", False, "pending"
                if due_full_html and isinstance(due_full_html, str): 
                    try: 
                        due_dt_obj_item = datetime.datetime.strptime(due_full_html, '%Y-%m-%d %H:%M:%S')
                        time_str_html = due_dt_obj_item.strftime(' a las %H:%M')
                        if not comp_html and due_dt_obj_item < now_dt: 
                            overdue_html, status_cls_html = True, "overdue"
                    except ValueError: time_str_html = " (Hora Inv.)"
                if comp_html: status_cls_html="completed"
                overdue_lbl_str = '<span style="color:red;font-weight:bold;">¡VENCIDA!</span> ' if overdue_html else ""
                html_str+=f"<div class='task-item {status_cls_html}'><span class='task-desc'>{desc_html}</span><span class='task-details'>{overdue_lbl_str}Cat: {cat_html} | Límite: {selected_date_str}{time_str_html}</span></div>"
        else: html_str+=f"<i>No hay tareas para {selected_date_str}.</i>"
        self.tasks_for_date_text_edit.setHtml(html_str)

    def handle_calendar_activated(self, q_date_activated):
        dialog = TaskDialog(self.user_manager, parent=self)
        all_categories_cal_act = set(t.get("categoria","General").strip() or "General" for t in self.tasks_data.get("tareas",[]) if isinstance(t,dict))
        sorted_categories_cal_act = sorted(list(all_categories_cal_act),key=str.lower)
        dialog.category_combo.clear(); dialog.category_combo.addItem("General")
        existing_dialog_cats_cal_act = {"General"}
        for cat_item_cal_act in sorted_categories_cal_act:
            if cat_item_cal_act not in existing_dialog_cats_cal_act:
                dialog.category_combo.addItem(cat_item_cal_act)
                existing_dialog_cats_cal_act.add(cat_item_cal_act)
        dialog.set_initial_date(q_date_activated)
        if dialog.exec_() == QDialog.Accepted:
            task_data_dlg = dialog.get_task_data()
            if task_data_dlg.get("descripcion") and self.user_manager.current_user:
                s,m = agregar_tarea(task_data_dlg.get("descripcion"),task_data_dlg.get("categoria"),task_data_dlg.get("fecha_limite"),self.user_manager.current_user,task_data_dlg.get("completada",False))
                if s: self.request_refresh_views.emit()
                else: QMessageBox.warning(self,"Error Agregando",m)
            elif not task_data_dlg.get("descripcion"): QMessageBox.warning(self,"Desc. Inválida","La descripción no puede ser vacía.")


class ReportGeneratorWorker(QObject):
    reportReady = pyqtSignal(str)
    @pyqtSlot(str,QDate,QDate,str)
    def generate_report_slot(self,pt,fI,fF,em):
        try:
            fid,ffd=fI.toPyDate(),fF.toPyDate()
            rh=generar_reporte(pt,fid,ffd,em)
            self.reportReady.emit(rh)
        except Exception as e:
            eh=f"<!DOCTYPE html><html><body><h2>Error Reporte ({html.escape(pt)})</h2><pre>{html.escape(str(e))}</pre></body></html>"
            self.reportReady.emit(eh)

class ReportsViewWidget(QWidget):
    request_report_generation_signal = pyqtSignal(str, QDate, QDate, str)
    def __init__(self, user_manager, parent=None):
        super().__init__(parent)
        self.user_manager = user_manager
        self.current_report_html = ""
        self.layout = QVBoxLayout(self)

        self.report_thread = QThread(self)
        self.report_worker = ReportGeneratorWorker()
        self.report_worker.moveToThread(self.report_thread)
        self.report_worker.reportReady.connect(self.display_generated_report)
        self.request_report_generation_signal.connect(self.report_worker.generate_report_slot)
        self.report_thread.start()

        self.view_title = QLabel("Generar Reporte", self)
        self.view_title.setObjectName("viewTitleLabel")
        self.view_title.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.view_title)

        form_group_box = QGroupBox("Periodo y Fecha")
        self.report_form_layout = QFormLayout(form_group_box)

        self.period_type_combo = QComboBox(self)
        self.period_type_combo.addItems(["Diario", "Semanal", "Mensual"])
        self.period_type_combo.currentIndexChanged.connect(self.update_date_selectors_visibility)
        self.report_form_layout.addRow("Tipo:", self.period_type_combo)

        self.date_selectors_stack = QStackedWidget(self)
        self.report_form_layout.addRow(self.date_selectors_stack)

        daily_widget = QWidget(); daily_layout = QFormLayout(daily_widget); daily_layout.setContentsMargins(0,0,0,0)
        self.daily_date_edit = QDateEdit(self); self.daily_date_edit.setCalendarPopup(True); self.daily_date_edit.setDate(QDate.currentDate()); self.daily_date_edit.setDisplayFormat("yyyy-MM-dd")
        daily_layout.addRow("Día:", self.daily_date_edit); self.date_selectors_stack.addWidget(daily_widget)

        weekly_widget = QWidget(); weekly_layout = QFormLayout(weekly_widget); weekly_layout.setContentsMargins(0,0,0,0)
        self.weekly_date_edit = QDateEdit(self); self.weekly_date_edit.setCalendarPopup(True); self.weekly_date_edit.setDate(QDate.currentDate()); self.weekly_date_edit.setDisplayFormat("yyyy-MM-dd")
        weekly_layout.addRow("Semana de (Lunes):", self.weekly_date_edit); self.date_selectors_stack.addWidget(weekly_widget)

        monthly_widget = QWidget(); monthly_layout = QFormLayout(monthly_widget); monthly_layout.setContentsMargins(0,0,0,0)
        self.month_combo = QComboBox(self); self.month_combo.addItems(["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]); self.month_combo.setCurrentIndex(datetime.datetime.now().month - 1)
        monthly_layout.addRow("Mes:", self.month_combo)
        self.year_input = QLineEdit(self); self.year_input.setText(str(datetime.datetime.now().year)); self.year_input.setPlaceholderText("Año (ej: 2024)")
        monthly_layout.addRow("Año:", self.year_input); self.date_selectors_stack.addWidget(monthly_widget)

        actions_layout = QHBoxLayout()
        report_icon_path = os.path.join("icons", "report.png"); save_icon_path = os.path.join("icons", "save.png")
        report_icon = QIcon(report_icon_path) if os.path.exists(report_icon_path) else QIcon.fromTheme("document-print")
        save_icon = QIcon(save_icon_path) if os.path.exists(save_icon_path) else QIcon.fromTheme("document-save")
        self.generate_button = QPushButton(report_icon, " Generar", self); self.generate_button.clicked.connect(self.trigger_report_generation); actions_layout.addWidget(self.generate_button)
        self.export_button = QPushButton(save_icon, " Exportar HTML", self); self.export_button.clicked.connect(self.export_report_to_html_file); self.export_button.setEnabled(False); actions_layout.addWidget(self.export_button)
        actions_layout.addStretch(1); self.report_form_layout.addRow(actions_layout); self.layout.addWidget(form_group_box)
        self.report_display_title = QLabel("Reporte Generado", self); self.report_display_title.setObjectName("reportTitleLabel"); self.report_display_title.setAlignment(Qt.AlignCenter); self.report_display_title.hide(); self.layout.addWidget(self.report_display_title)
        self.report_text_edit = QTextEdit(self); self.report_text_edit.setReadOnly(True); self.layout.addWidget(self.report_text_edit)
        self.update_date_selectors_visibility()

    def update_date_selectors_visibility(self): self.date_selectors_stack.setCurrentIndex(self.period_type_combo.currentIndex())
    def trigger_report_generation(self):
        self.report_text_edit.clear(); self.current_report_html = ""; self.export_button.setEnabled(False); self.generate_button.setEnabled(False); self.report_display_title.hide()
        period_idx, period_str = self.period_type_combo.currentIndex(), self.period_type_combo.currentText().lower()
        start_dt, end_dt = None, None
        try:
            if period_idx == 0: start_dt = end_dt = self.daily_date_edit.date().toPyDate()
            elif period_idx == 1: s_qdate = self.weekly_date_edit.date(); day_of_wk = s_qdate.dayOfWeek(); start_dt = s_qdate.addDays(-(day_of_wk -1)).toPyDate(); end_dt = s_qdate.addDays(7-day_of_wk).toPyDate()
            elif period_idx == 2:
                month, year_str_val = self.month_combo.currentIndex()+1, self.year_input.text().strip()
                if not year_str_val.isdigit() or not (1900 < int(year_str_val) < 2200): raise ValueError("Año inválido.")
                year_val = int(year_str_val); start_dt = datetime.date(year_val,month,1)
                end_dt = datetime.date(year_val,month+1,1)-timedelta(days=1) if month<12 else datetime.date(year_val,12,31)
            if start_dt and end_dt and self.user_manager.current_user: self.request_report_generation_signal.emit(period_str, QDate(start_dt), QDate(end_dt), self.user_manager.current_user)
            elif not self.user_manager.current_user: QMessageBox.warning(self, "Error Usuario", "No hay usuario."); self.generate_button.setEnabled(True)
            else: QMessageBox.warning(self, "Error Fechas", "Fechas inválidas."); self.generate_button.setEnabled(True)
        except ValueError as ve: QMessageBox.warning(self,"Entrada Inválida",str(ve)); self.generate_button.setEnabled(True)
        except Exception as e: QMessageBox.critical(self,"Error Inesperado",f"Error: {e}"); self.generate_button.setEnabled(True)
    @pyqtSlot(str)
    def display_generated_report(self, report_html):
        self.current_report_html = report_html
        title_m = re.search(r"<title>(.*?)</title>",report_html,re.I|re.S); disp_title = title_m.group(1).strip() if title_m else "Reporte"
        self.report_display_title.setText(disp_title); self.report_display_title.show(); self.report_text_edit.setHtml(report_html)
        self.export_button.setEnabled(bool(report_html and "<html" in report_html.lower())); self.generate_button.setEnabled(True)
    def export_report_to_html_file(self):
        if not self.current_report_html: QMessageBox.warning(self,"Sin Reporte","Genere uno primero."); return
        period_s = self.period_type_combo.currentText(); suffix = ""
        try:
            if period_s=="Diario": suffix=self.daily_date_edit.date().toString("yyyyMMdd")
            elif period_s=="Semanal": s_qd_exp=self.weekly_date_edit.date(); suffix=s_qd_exp.addDays(-(s_qd_exp.dayOfWeek()-1)).toString("yyyyMMdd")+"_Semanal"
            elif period_s=="Mensual": suffix=f"{self.year_input.text()}{self.month_combo.currentIndex()+1:02d}"
            def_fn = f"Reporte_{period_s}_{suffix}.html"
        except: def_fn = "Reporte_VoceTasks.html"
        fn, _ = QFileDialog.getSaveFileName(self,"Guardar Reporte HTML",def_fn,"HTML (*.html);;Todos (*)")
        if fn:
            if not fn.lower().endswith(".html"): fn+=".html"
            try:
                with open(fn,'w',encoding='utf-8') as f_exp: f_exp.write(self.current_report_html)
                QMessageBox.information(self,"Exportado",f"Reporte guardado en:\n{fn}")
            except Exception as e_exp: QMessageBox.critical(self,"Error Exportación",f"No se pudo guardar:\n{e_exp}")
    def __del__(self):
        if hasattr(self,'report_thread') and self.report_thread.isRunning(): self.report_thread.quit(); self.report_thread.wait(1500)

class TaskCalendarWindow(QMainWindow):
    tasks_updated_signal = pyqtSignal()
    request_final_sync = pyqtSignal()
    def __init__(self, user_manager):
        super().__init__(); self.user_manager = user_manager
        user_name_disp = self.user_manager.get_user_name() or self.user_manager.current_user
        self.setWindowTitle(f"VoceTasks - {user_name_disp}"); self.setGeometry(100,100,1050,700)
        
        self.drive_thread = QThread(self); self.drive_worker = DriveSyncWorker(self.user_manager.current_user); self.drive_worker.moveToThread(self.drive_thread); self.drive_worker.syncFinished.connect(self.handle_sync_finished); self.request_final_sync.connect(self.drive_worker.do_sync_upload, Qt.QueuedConnection); self.drive_thread.finished.connect(self.drive_worker.deleteLater); self.drive_thread.finished.connect(self.drive_thread.deleteLater); self.drive_thread.start(); self.is_syncing=False; self.logout_pending=False
        
        self.voice_command_thread = QThread(self); self.voice_worker = VoiceCommandWorker(self.user_manager); self.voice_worker.moveToThread(self.voice_command_thread); self.voice_worker.listening_status_changed.connect(self.handle_listening_status); self.voice_worker.command_recognized.connect(self.handle_command_recognized_text); self.voice_worker.command_processed.connect(self.handle_command_processed_status)
        if 'hablar' in globals() and callable(globals()['hablar']): self.voice_worker.speak_response.connect(self.speak_message_from_gui)
        self.voice_worker.request_ui_refresh.connect(self.refresh_views_local); self.voice_worker.request_gui_report_generation.connect(self.handle_voice_request_report); self.voice_worker.request_view_change.connect(self.handle_voice_request_view_change); self.voice_worker.request_logout.connect(self.handle_voice_request_logout)
        self.voice_worker.request_show_manual.connect(self.mostrar_manual_popup) 
        self.voice_command_thread.start()
        
        self.original_statusbar_stylesheet = ""; QTimer.singleShot(150, self._capture_original_statusbar_style)
        self.window_icon_path = "logo.png";
        if os.path.exists(self.window_icon_path): self.setWindowIcon(QIcon(self.window_icon_path))
        else: print(f"Advertencia: Ícono ventana '{self.window_icon_path}' no hallado.")
        
        self.tool_bar = QToolBar("Barra Principal"); self.addToolBar(self.tool_bar); self.tool_bar.setMovable(False); self.tool_bar.setIconSize(QSize(24,24))
        self.icon_paths_map = {"tasks":"icons/tasks.png","calendar":"icons/calendar.png","reports":"icons/report.png","download":"icons/download.png","upload":"icons/upload.png","logout":"icons/logout.png","mic":"icons/microphone.png", "help":"icons/help.png"}
        self.theme_fallbacks_map = {"tasks":"view-list-text","calendar":"x-office-calendar","reports":"document-print","download":"arrow-down","upload":"arrow-up","logout":"system-log-out","mic":"audio-input-microphone", "help":"help-contents"}
        
        def get_ico(n, fb_emoji="❓"): 
            ip=self.icon_paths_map.get(n); tfb=self.theme_fallbacks_map.get(n)
            if ip and os.path.exists(ip): return QIcon(ip)
            if tfb: return QIcon.fromTheme(tfb, QIcon(fb_emoji))
            return QIcon(fb_emoji)
        
        self.action_show_tasks=QAction(get_ico("tasks"),"Tareas",self);self.action_show_tasks.triggered.connect(lambda:self.change_view(0));self.tool_bar.addAction(self.action_show_tasks)
        self.action_show_calendar=QAction(get_ico("calendar"),"Calendario",self);self.action_show_calendar.triggered.connect(lambda:self.change_view(1));self.tool_bar.addAction(self.action_show_calendar)
        self.action_show_reports=QAction(get_ico("reports"),"Reportes",self);self.action_show_reports.triggered.connect(lambda:self.change_view(2));self.tool_bar.addAction(self.action_show_reports)
        self.tool_bar.addSeparator()
        self.action_sync_from=QAction(get_ico("download"),"Descargar",self);self.action_sync_from.setToolTip("Descargar de Drive");self.action_sync_from.triggered.connect(self.sync_from_drive_action);self.tool_bar.addAction(self.action_sync_from)
        self.action_sync_to=QAction(get_ico("upload"),"Subir",self);self.action_sync_to.setToolTip("Subir a Drive");self.action_sync_to.triggered.connect(self.sync_to_drive_action);self.tool_bar.addAction(self.action_sync_to)
        self.tool_bar.addSeparator()
        
        self.action_voice_command=QAction(get_ico("mic","🎤"),"Comando Voz",self)
        self.action_voice_command.setToolTip("Activar comando de voz (Ctrl+Shift+M)") # Tooltip actualizado
        self.action_voice_command.triggered.connect(self.trigger_voice_command_listening)
        self.action_voice_command.setShortcut(Qt.CTRL + Qt.Key_M) # Atajo añadido
        self.tool_bar.addAction(self.action_voice_command)
        self.voice_button_label_original_tooltip=self.action_voice_command.toolTip()
        
        self.action_show_manual = QAction(get_ico("help", "❓"), "Ayuda/Manual", self)
        self.action_show_manual.setToolTip("Mostrar el manual de usuario y guía de comandos (F1)") 
        self.action_show_manual.triggered.connect(self.mostrar_manual_popup)
        self.action_show_manual.setShortcut(Qt.Key_F1) # Atajo F1 para el manual
        self.tool_bar.addAction(self.action_show_manual)
        
        self.tool_bar.addSeparator()
        self.action_logout=QAction(get_ico("logout"),"Cerrar Sesión",self);self.action_logout.setObjectName("action_logout");self.action_logout.setToolTip("Cerrar sesión");self.action_logout.triggered.connect(self.logout);self.tool_bar.addAction(self.action_logout)
        
        self.central_widget=QWidget();self.setCentralWidget(self.central_widget);self.layout=QVBoxLayout(self.central_widget);self.layout.setContentsMargins(5,5,5,5)
        self.views_stack=QStackedWidget(self);self.layout.addWidget(self.views_stack)
        self.tasks_view=TasksViewWidget(self.user_manager,self);self.views_stack.addWidget(self.tasks_view)
        self.calendar_view=CalendarViewWidget(self.user_manager,self);self.views_stack.addWidget(self.calendar_view)
        self.reports_view=ReportsViewWidget(self.user_manager,self);self.views_stack.addWidget(self.reports_view)
        self.tasks_updated_signal.connect(self.tasks_view.load_and_display_tasks);self.tasks_updated_signal.connect(self.calendar_view.load_and_display_tasks)
        self.tasks_view.request_refresh_views.connect(self.refresh_views_local);self.calendar_view.request_refresh_views.connect(self.refresh_views_local)
        self.notification_timer=QTimer(self);self.notification_timer.timeout.connect(self.check_upcoming_tasks_for_notification);self.notification_timer.start(300000);self.checked_tasks_for_notification=set()
        if self.user_manager.current_user and 'cargar_modo_entrada_usuario' in globals() and callable(globals()['cargar_modo_entrada_usuario']): cargar_modo_entrada_usuario(self.user_manager.current_user)
        self.load_tasks_initial();self.change_view(0);self.statusBar().showMessage("Listo.",2000)

    @pyqtSlot() 
    def mostrar_manual_popup(self):
        manual_texto = obtener_manual_texto() 
        dialog = ManualDialog(manual_texto, self)
        dialog.exec_()
        
    def _capture_original_statusbar_style(self): self.original_statusbar_stylesheet = self.statusBar().styleSheet()
    def _set_statusbar_style_and_message(self, message, style_extra, timeout=7000, persistent=False):
        current_style = self.original_statusbar_stylesheet;
        if style_extra: current_style += " " + style_extra
        self.statusBar().setStyleSheet(current_style); self.statusBar().showMessage(message, 0 if persistent else timeout)
        if not persistent and timeout > 0: QTimer.singleShot(timeout, lambda: self.statusBar().setStyleSheet(self.original_statusbar_stylesheet or ""))
    def change_view(self, index): self.views_stack.setCurrentIndex(index); current_w = self.views_stack.widget(index); hasattr(current_w,"load_and_display_tasks") and current_w.load_and_display_tasks()
    @pyqtSlot()
    def refresh_views_local(self): self.tasks_updated_signal.emit()
    @pyqtSlot()
    def sync_to_drive_action(self):
        if self.user_manager.current_user and not self.is_syncing: self.is_syncing=True;self.set_sync_buttons_enabled(False);self._set_statusbar_style_and_message("Subiendo a Drive...","QStatusBar{background-color:#e6f7ff;color:#005a9e;border-top:1px solid #b3d9ff;}",persistent=True);QMetaObject.invokeMethod(self.drive_worker,"do_sync_upload",Qt.QueuedConnection)
        elif self.is_syncing: QMessageBox.information(self,"En Progreso","Sincronización en curso.")
        else: QMessageBox.warning(self,"Error","Debes iniciar sesión.")
    @pyqtSlot()
    def sync_from_drive_action(self):
        if self.user_manager.current_user and not self.is_syncing: self.is_syncing=True;self.set_sync_buttons_enabled(False);self._set_statusbar_style_and_message("Descargando de Drive...","QStatusBar{background-color:#e6f7ff;color:#005a9e;border-top:1px solid #b3d9ff;}",persistent=True);QMetaObject.invokeMethod(self.drive_worker,"do_sync_download",Qt.QueuedConnection)
        elif self.is_syncing: QMessageBox.information(self,"En Progreso","Sincronización en curso.")
        else: QMessageBox.warning(self,"Error","Debes iniciar sesión.")
    @pyqtSlot(bool,str,str)
    def handle_sync_finished(self,success,message,op_type):
        self.is_syncing=False;self.set_sync_buttons_enabled(True);status_msg=f"Sinc.Drive({op_type}):{message}";style_sb="QStatusBar{background-color:#e6ffee;color:#006400;border-top:1px solid #b3ffb3;}" if success else "QStatusBar{background-color:#ffe6e6;color:#d8000c;border-top:1px solid #ffb3b3;font-weight:bold;}";self._set_statusbar_style_and_message(status_msg,style_sb,timeout=7000)
        if success and (op_type=='initial_download' or op_type=='download'): self.tasks_updated_signal.emit()
        if op_type=='initial_download':
            if success: QMessageBox.information(self,"Sinc.Inicial",f"Drive:{message}")
            elif "Error" in message or "no encontrado" not in message.lower(): QMessageBox.warning(self,"Sinc.Inicial Fallida",f"Drive:{message}")
        elif not success: QMessageBox.warning(self,"Error Sinc.",f"Drive({op_type}):{message}")
        if self.logout_pending and op_type=='upload': self.logout_pending=False;self.perform_logout_steps()
        elif self.logout_pending and not success and op_type=='upload': self.logout_pending=False;QMessageBox.warning(self,"Error Logout Sync","No se pudo guardar en Drive.Cerrar sesión igual?");self.perform_logout_steps()
    def load_tasks_initial(self):
        if self.user_manager.current_user and not self.is_syncing: self.is_syncing=True;self.set_sync_buttons_enabled(False);self._set_statusbar_style_and_message("Sincronizando(inicio)...","QStatusBar{background-color:#e6f7ff;color:#005a9e;border-top:1px solid #b3d9ff;}",persistent=True);QMetaObject.invokeMethod(self.drive_worker,"do_initial_sync_download",Qt.QueuedConnection)
        elif not self.user_manager.current_user: self.tasks_updated_signal.emit()
    def logout(self):
        r=QMessageBox.question(self,'Cerrar Sesión','Guardar en Drive antes de salir?',QMessageBox.Yes|QMessageBox.No|QMessageBox.Cancel,QMessageBox.Yes)
        if r==QMessageBox.Cancel:return
        if r==QMessageBox.Yes:
            if self.user_manager.current_user and not self.is_syncing: self.is_syncing=True;self.logout_pending=True;self.set_sync_buttons_enabled(False);self.centralWidget().setEnabled(False);self._set_statusbar_style_and_message("Guardando y cerrando...","QStatusBar{background-color:#e6f7ff;color:#005a9e;border-top:1px solid #b3d9ff;}",persistent=True);self.request_final_sync.emit()
            elif self.is_syncing: QMessageBox.warning(self,"En Progreso","Sincronización en curso.")
            else:self.perform_logout_steps()
        elif r==QMessageBox.No: self.perform_logout_steps()
    def perform_logout_steps(self): self.user_manager.logout();self.centralWidget().setEnabled(True);self.statusBar().setStyleSheet(self.original_statusbar_stylesheet or "");self.statusBar().clearMessage();self.close()
    def set_sync_buttons_enabled(self,enabled): self.action_sync_from.setEnabled(enabled);self.action_sync_to.setEnabled(enabled)
    @pyqtSlot()
    def trigger_voice_command_listening(self):
        if not ('escuchar_comando' in globals() and callable(globals()['escuchar_comando'])): QMessageBox.warning(self,"Voz no Disponible","Función no configurada.");return
        self.action_voice_command.setEnabled(False);QMetaObject.invokeMethod(self.voice_worker,"start_listening",Qt.QueuedConnection)
    @pyqtSlot(bool,str)
    def handle_listening_status(self,is_listening,message):
        self.action_voice_command.setToolTip(message if is_listening else self.voice_button_label_original_tooltip);style_ex="";is_err=any(ek.lower() in message.lower() for ek in ["error","no se recibió","no logueado","no entendí","no pude entender","no implementado","no se pudo procesar"])
        if is_listening:style_ex="QStatusBar{background-color:#e6f7ff;color:#005a9e;}"
        elif "procesando" in message.lower():style_ex="QStatusBar{background-color:#fffacd;color:#5c5c00;}"
        elif is_err:style_ex="QStatusBar{background-color:#ffe6e6;color:#d8000c;font-weight:bold;}"
        else:style_ex="QStatusBar{background-color:#e6ffee;color:#006400;}"
        self._set_statusbar_style_and_message(message,style_ex,persistent=(is_listening or "procesando" in message.lower()),timeout=7000 if not(is_listening or "procesando" in message.lower())else 0)
        if not is_listening:self.action_voice_command.setEnabled(True)
    @pyqtSlot(str)
    def handle_command_recognized_text(self,text): print(f"GUI:Comando:{text}");self._set_statusbar_style_and_message(f"Has dicho:\"{text}\"-Procesando...","QStatusBar{background-color:#fffacd;color:#5c5c00;}",persistent=True)
    @pyqtSlot(bool,str)
    def handle_command_processed_status(self,success,message): print(f"GUI:Procesado-Éxito:{success},Msg:{message}")
    @pyqtSlot(str)
    def speak_message_from_gui(self,text_to_speak):
        if 'hablar' in globals() and callable(globals()['hablar']): hablar(text_to_speak)
    @pyqtSlot(str, int, int)
    def handle_voice_request_report(self, period_type, year, month):
        print(f"GUI: Solicitud de reporte por voz: {period_type}, {month}/{year}")
        if not (hasattr(self, 'reports_view') and self.reports_view): QMessageBox.warning(self, "Error", "Vista de reportes no disponible."); return
        if period_type == "mensual":
            self.reports_view.period_type_combo.setCurrentText("Mensual")
            self.reports_view.month_combo.setCurrentIndex(month - 1)
            self.reports_view.year_input.setText(str(year))
            self.reports_view.trigger_report_generation()
            self.change_view(2)
        else:
            msg_unsupported = "Reportes diarios/semanales por voz no implementados aún."
            if 'hablar' in globals() and callable(globals()['hablar']): self.speak_message_from_gui(msg_unsupported)
            QMessageBox.information(self, "Comando de Voz", msg_unsupported)
    @pyqtSlot(int)
    def handle_voice_request_view_change(self, view_index):
        print(f"GUI: Solicitud de cambio de vista por voz al índice: {view_index}")
        if 0 <= view_index < self.views_stack.count(): self.change_view(view_index)
        else:
            msg_err_view = f"No se pudo cambiar a la vista (índice {view_index} no válido)."
            if 'hablar' in globals() and callable(globals()['hablar']): self.speak_message_from_gui(msg_err_view)
            QMessageBox.warning(self, "Error de Vista", msg_err_view)
    @pyqtSlot()
    def handle_voice_request_logout(self): print("GUI: Logout por voz."); self.logout()
    def check_upcoming_tasks_for_notification(self):
        if not self.user_manager.current_user: return
        try:
            current_tasks_data = mostrar_tareas(self.user_manager.current_user)
            upcoming_tasks_to_notify, now = [], datetime.datetime.now()
            
            tasks_list = current_tasks_data.get("tareas", [])
            if not isinstance(tasks_list, list): tasks_list = []

            for tarea in tasks_list:
                if not isinstance(tarea, dict): continue
                if not tarea.get("completada", False):
                    fecha_limite_str = tarea.get("fecha_limite")
                    task_id_tuple = (tarea.get("descripcion","").strip().lower(), fecha_limite_str)
                    if fecha_limite_str and isinstance(fecha_limite_str, str): 
                        try:
                            fecha_limite_obj = datetime.datetime.strptime(fecha_limite_str, '%Y-%m-%d %H:%M:%S')
                            if timedelta(0) < (fecha_limite_obj - now) <= timedelta(days=1) and task_id_tuple not in self.checked_tasks_for_notification:
                                upcoming_tasks_to_notify.append(tarea)
                                self.checked_tasks_for_notification.add(task_id_tuple)
                        except ValueError: pass
            for tarea_notif in upcoming_tasks_to_notify:
                fl_str_notif = tarea_notif.get("fecha_limite")
                if fl_str_notif and isinstance(fl_str_notif, str): 
                    try:
                        td_notif = datetime.datetime.strptime(fl_str_notif,'%Y-%m-%d %H:%M:%S') - now
                        d_notif,r_s_notif=divmod(td_notif.total_seconds(),86400);h_notif,r_s_notif=divmod(r_s_notif,3600);m_notif,_=divmod(r_s_notif,60)
                        parts_notif=[f"{int(val)} {unit}{'s' if int(val)!=1 else ''}" for val,unit in [(d_notif,"día"),(h_notif,"hora"),(m_notif,"minuto")] if int(val)>0]
                        time_msg_notif = f"Faltan {', '.join(parts_notif[:-1])+' y '+parts_notif[-1] if len(parts_notif)>1 else (parts_notif[0] if parts_notif else 'menos de un minuto')}."
                        QMessageBox.information(self, f"Recordatorio: {html.escape(tarea_notif.get('descripcion','Tarea'))}", f"<b>¡Tarea Próxima!</b><br><b>Tarea:</b> {html.escape(tarea_notif.get('descripcion','N/A'))}<br><b>Límite:</b> {fl_str_notif}<br><i>{time_msg_notif}</i>")
                    except ValueError: print(f"Error parseando fecha '{fl_str_notif}' para notif.")
        except Exception as e_notif: print(f"Error notificaciones: {e_notif}")
    def closeEvent(self, event):
        print("Cerrando TaskCalendarWindow...")
        self.notification_timer.stop()
        threads_to_stop = [("Drive", self.drive_thread), ("Voz", self.voice_command_thread)]
        if hasattr(self, 'reports_view') and hasattr(self.reports_view, 'report_thread'):
             threads_to_stop.append(("Reportes", self.reports_view.report_thread))
        for thread_name, thread_obj in threads_to_stop:
            if thread_obj and thread_obj.isRunning():
                print(f"Deteniendo hilo {thread_name}..."); thread_obj.quit()
                if not thread_obj.wait(1500):
                    print(f"Advertencia: Hilo {thread_name} no terminó, forzando."); thread_obj.terminate(); thread_obj.wait()
                else: print(f"Hilo {thread_name} detenido.")
        super().closeEvent(event)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.user_manager = UserManager(); self.task_calendar_window = None
        self.setWindowTitle("VoceTasks - Inicio"); self.setGeometry(200,200,450,380); self.setMinimumSize(400,350); self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.logo_path="logo.png" 
        if os.path.exists(self.logo_path): self.setWindowIcon(QIcon(self.logo_path))
        else:print(f"DEBUG:Icono '{self.logo_path}' no encontrado.")
        self.central_widget=QWidget();self.setCentralWidget(self.central_widget);self.layout=QVBoxLayout(self.central_widget);self.layout.setContentsMargins(30,20,30,30);self.layout.setSpacing(15);self.layout.setAlignment(Qt.AlignCenter)
        self.logo_label=QLabel(self);logo_ok=False
        if os.path.exists(self.logo_path):
            pixmap=QPixmap(self.logo_path)
            if not pixmap.isNull():self.logo_label.setPixmap(pixmap.scaled(120,120,Qt.KeepAspectRatio,Qt.SmoothTransformation));self.logo_label.setAlignment(Qt.AlignCenter);logo_ok=True
            else:print(f"DEBUG:No se pudo cargar QPixmap'{self.logo_path}'.")
        if not logo_ok:self.logo_label.setText("VoceTasks");self.logo_label.setFont(QFont("Arial",24,QFont.Bold));self.logo_label.setAlignment(Qt.AlignCenter);print(f"DEBUG:Logo'{self.logo_path}'no cargado.Texto mostrado.")
        self.layout.addWidget(self.logo_label);self.layout.addSpacing(10)
        self.title_label=QLabel("Bienvenido a VoceTasks",self);self.title_label.setObjectName("mainWindowTitleLabel");self.title_label.setFont(QFont("Arial",18,QFont.Bold));self.title_label.setAlignment(Qt.AlignCenter);self.layout.addWidget(self.title_label);self.layout.addSpacing(25)
        bw,bh=180,45;self.btn_login=QPushButton("Iniciar Sesión",self);self.btn_login.setFixedSize(bw,bh);self.btn_login.clicked.connect(self.show_login_dialog);self.layout.addWidget(self.btn_login,alignment=Qt.AlignCenter)
        self.btn_reg=QPushButton("Registrarse",self);self.btn_reg.setFixedSize(bw,bh);self.btn_reg.clicked.connect(self.show_register_dialog);self.layout.addWidget(self.btn_reg,alignment=Qt.AlignCenter)
        self.layout.addStretch(1);self.show()
    def show_login_dialog(self): d=LoginDialog(self.user_manager,self); (d.exec_()==QDialog.Accepted and self.user_manager.current_user) and self.show_task_calendar_window()
    def show_register_dialog(self): RegisterDialog(self.user_manager,self).exec_()
    def show_task_calendar_window(self):
        if self.task_calendar_window is None or not self.task_calendar_window.isVisible(): self.task_calendar_window=TaskCalendarWindow(self.user_manager);self.task_calendar_window.destroyed.connect(self.on_task_window_closed);self.task_calendar_window.show();self.hide()
    @pyqtSlot()
    def on_task_window_closed(self): print("TaskCalendarWindow cerrada.");self.task_calendar_window=None; (not self.isVisible() and QApplication.instance()) and self.show()

def load_stylesheet(filepath):
    try:
        with open(filepath,"r",encoding="utf-8") as f_st: return f_st.read()
    except FileNotFoundError: print(f"Warn: Stylesheet '{filepath}' no hallado."); return ""
    except Exception as e_st: print(f"Error cargando stylesheet '{filepath}': {e_st}"); return ""

if __name__=="__main__":
    try:
        if not os.path.exists("usuarios"): os.makedirs("usuarios",exist_ok=True)
        if not os.path.exists("usuarios.json"):
            with open("usuarios.json","w",encoding='utf-8') as file_ujs: json.dump({"usuarios":[]}, file_ujs, indent=4)
    except Exception as e_init: print(f"Error crítico inicialización: {e_init}"); sys.exit(1)
    app=QApplication(sys.argv);stylesheet_data=load_stylesheet("styles.qss")
    if stylesheet_data: app.setStyleSheet(stylesheet_data)
    else: app.setStyle("Fusion")
    main_window_app = MainWindow()
    sys.exit(app.exec_())
