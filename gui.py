# gui.py (Optimización 2: Debouncing para Búsqueda)

import sys
import os
import json
import datetime
import re
import html
from collections import defaultdict

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                           QTabWidget, QLabel, QPushButton, QLineEdit, QTextEdit,
                           QTableWidget, QTableWidgetItem, QCalendarWidget, QFrame,
                           QMessageBox, QSplitter, QDialog, QFormLayout,
                           QCheckBox, QComboBox, QGroupBox, QScrollArea, QStackedWidget,
                           QInputDialog, QDialogButtonBox, QDateTimeEdit, QHeaderView,
                           QMenuBar, QMenu, QAction, QSizePolicy,
                           QAbstractItemView,
                           QToolBar,
                           QFileDialog, QProgressDialog)
# Importaciones para QThread y QTimer
from PyQt5.QtCore import (Qt, QDate, QTimer, pyqtSignal, QThread, QDateTime,
                          QTimeZone, QSize, QObject, pyqtSlot, QMetaObject)
# ---------------------------------
from PyQt5.QtGui import QIcon, QFont, QColor, QTextCharFormat, QPixmap

# Importar módulos del proyecto
from commands import (agregar_tarea, eliminar_tarea, mostrar_tareas, modificar_tarea,
                     marcar_como_completada, generar_reporte_mensual)
from user_management import UserManager
# Importar funciones de sync directamente
from google_drive_sync import sync_tasks_to_drive, sync_tasks_from_drive


# --- Worker para Operaciones de Drive en Hilo Separado ---
class DriveSyncWorker(QObject):
    # Señal emitida al finalizar una operación de sync
    # Argumentos: bool success, str message, str operation_type ('upload'/'download'/'initial_download')
    syncFinished = pyqtSignal(bool, str, str)
    # Podría añadirse una señal para progreso si googleapiclient lo soporta bien

    def __init__(self, email):
        super().__init__()
        self.email = email
        self._is_running = False # Flag para evitar ejecuciones concurrentes

    @pyqtSlot() # Marcar como slot para ser llamado vía invokeMethod
    def do_sync_upload(self):
        """Realiza la subida de tareas a Google Drive."""
        if self._is_running or not self.email: return
        self._is_running = True
        print("Worker: Iniciando subida a Drive...")
        op_type = 'upload'
        try:
            success, message = sync_tasks_to_drive(self.email)
            print(f"Worker: Resultado subida: {success}, {message}")
            self.syncFinished.emit(success, message, op_type)
        except Exception as e:
             error_msg = f"Error inesperado en worker (subida): {e}"
             print(f"Worker: {error_msg}")
             self.syncFinished.emit(False, error_msg, op_type)
        finally:
             self._is_running = False

    @pyqtSlot() # Marcar como slot
    def do_sync_download(self):
        """Realiza la descarga de tareas desde Google Drive."""
        if self._is_running or not self.email: return
        self._is_running = True
        print("Worker: Iniciando descarga de Drive...")
        op_type = 'download'
        try:
            success, message = sync_tasks_from_drive(self.email)
            print(f"Worker: Resultado descarga: {success}, {message}")
            self.syncFinished.emit(success, message, op_type)
        except Exception as e:
            error_msg = f"Error inesperado en worker (descarga): {e}"
            print(f"Worker: {error_msg}")
            self.syncFinished.emit(False, error_msg, op_type)
        finally:
            self._is_running = False

    @pyqtSlot() # Slot para la carga inicial (funcionalmente igual a download)
    def do_initial_sync_download(self):
        """Realiza la descarga inicial de tareas desde Google Drive."""
        if self._is_running or not self.email: return
        self._is_running = True
        print("Worker: Iniciando descarga INICIAL de Drive...")
        op_type = 'initial_download'
        try:
            success, message = sync_tasks_from_drive(self.email)
            print(f"Worker: Resultado descarga inicial: {success}, {message}")
            self.syncFinished.emit(success, message, op_type)
        except Exception as e:
            error_msg = f"Error inesperado en worker (descarga inicial): {e}"
            print(f"Worker: {error_msg}")
            self.syncFinished.emit(False, error_msg, op_type)
        finally:
            self._is_running = False

# --- Fin Worker ---


# --- Diálogos (Sin cambios respecto a la versión anterior)---

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
        self.task_data = task_data # Guardamos la data original para saber si es modificación
        title = f"Modificar Tarea: {task_data['descripcion']}" if task_data and task_data.get('descripcion') else "Agregar Tarea"
        self.setWindowTitle(title)
        self.setGeometry(100, 100, 400, 250)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QFormLayout()

        self.description_edit = QLineEdit(self)
        self.description_edit.setPlaceholderText("Descripción de la tarea")
        layout.addRow("Descripción:", self.description_edit)

        self.category_combo = QComboBox(self)
        self.category_combo.addItem("General") # Añadir 'General' por defecto
        self.category_combo.setEditable(True) # Permitir añadir nuevas categorías
        self.category_combo.setStyleSheet("QComboBox { background-color: white; color: black; }")
        layout.addRow("Categoría:", self.category_combo)

        self.datetime_edit = QDateTimeEdit(self)
        self.datetime_edit.setCalendarPopup(True)
        self.datetime_edit.setDateTime(QDateTime.currentDateTime())
        self.datetime_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss") # Formato deseado
        self.datetime_edit.setStyleSheet("QDateTimeEdit { background-color: white; color: black; }")
        self.no_due_date_checkbox = QCheckBox("Sin fecha límite", self)
        self.no_due_date_checkbox.stateChanged.connect(self.toggle_datetime_edit)
        layout.addRow("Fecha y Hora Límite:", self.datetime_edit)
        layout.addRow("", self.no_due_date_checkbox) # Añadir debajo

        self.completed_checkbox = QCheckBox("Completada", self)
        layout.addRow("", self.completed_checkbox)

        # Pre-llenar si es para modificar
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
                    self.no_due_date_checkbox.setChecked(False)
                    self.datetime_edit.setEnabled(True)
                except ValueError:
                    print(f"Advertencia: Formato de fecha inválido al editar: {fecha_limite_str}. Se marcará sin fecha límite.")
                    self.no_due_date_checkbox.setChecked(True)
                    self.datetime_edit.setEnabled(False)
            else:
                 self.no_due_date_checkbox.setChecked(True)
                 self.datetime_edit.setEnabled(False)
            self.completed_checkbox.setChecked(self.task_data.get("completada", False))
        else:
             self.no_due_date_checkbox.setChecked(False)
             self.datetime_edit.setEnabled(True)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)

        self.setLayout(layout)

    def toggle_datetime_edit(self, state):
        self.datetime_edit.setEnabled(state != Qt.Checked)

    def set_initial_date(self, qdate):
        current_time = QDateTime.currentDateTime().time()
        initial_datetime = QDateTime(qdate, current_time)
        self.datetime_edit.setDateTime(initial_datetime)
        self.no_due_date_checkbox.setChecked(False)
        self.datetime_edit.setEnabled(True)

    def get_task_data(self):
        fecha_limite_str = None
        if not self.no_due_date_checkbox.isChecked():
             fecha_limite_str = self.datetime_edit.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        return {
            "descripcion": self.description_edit.text().strip(),
            "categoria": self.category_combo.currentText().strip() if self.category_combo.currentText().strip() else "General",
            "fecha_limite": fecha_limite_str,
            "completada": self.completed_checkbox.isChecked()
        }


# --- Clases para las Vistas (Widgets) (Modificada TasksViewWidget) ---

class TasksViewWidget(QWidget):
    request_refresh_views = pyqtSignal()

    def __init__(self, user_manager, parent=None):
        super().__init__(parent)
        self.user_manager = user_manager
        self.tasks_data = {"tareas": []}
        self.layout = QVBoxLayout(self)

        # --- Timer para Debouncing de Búsqueda (NUEVO) ---
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True) # Solo se dispara una vez por intervalo
        self.search_timer.setInterval(350) # Intervalo en milisegundos (ajustable)
        self.search_timer.timeout.connect(self.refresh_tasks_display) # Llama a refresh al terminar el timer
        # -------------------------------------------------

        # Título de la vista
        self.view_title = QLabel("Lista de Tareas", self)
        self.view_title.setObjectName("viewTitleLabel")
        self.view_title.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.view_title)

        # Controles
        controls_group_box = QGroupBox("Controles")
        controls_layout = QHBoxLayout(controls_group_box)

        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Buscar tarea...")
        # --- Conectar textChanged al INICIO del timer (NUEVO) ---
        self.search_input.textChanged.connect(self.on_search_text_changed)
        # -------------------------------------------------------
        controls_layout.addWidget(QLabel("Buscar:", self))
        controls_layout.addWidget(self.search_input, 1)

        self.filter_label = QLabel("Categoría:", self)
        controls_layout.addWidget(self.filter_label)
        self.category_filter_combo = QComboBox(self)
        self.category_filter_combo.addItem("Todas")
        # Filtrado por categoría sigue siendo inmediato
        self.category_filter_combo.currentIndexChanged.connect(self.filter_by_category)
        controls_layout.addWidget(self.category_filter_combo)

        add_icon = QIcon("icons/add.png") if os.path.exists("icons/add.png") else QIcon.fromTheme("list-add")
        self.add_button = QPushButton(add_icon, "Agregar Tarea", self)
        self.add_button.clicked.connect(self.handle_add_task_dialog_show)
        controls_layout.addWidget(self.add_button)

        self.layout.addWidget(controls_group_box)

        # Tabla de Tareas
        self.task_table = QTableWidget(self)
        self.task_table.setColumnCount(5)
        self.task_table.setHorizontalHeaderLabels(["Descripción", "Categoría", "Fecha Límite", "Completada", "Acciones"])
        self.task_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.task_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.task_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.task_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.task_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.task_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.task_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.task_table.setAlternatingRowColors(True)
        self.layout.addWidget(self.task_table)

    def load_and_display_tasks(self):
        """Carga las tareas y actualiza la tabla y filtros."""
        print("TasksViewWidget: load_and_display_tasks llamado")
        if self.user_manager.current_user:
            self.tasks_data = mostrar_tareas(self.user_manager.current_user)
            if not isinstance(self.tasks_data, dict) or "tareas" not in self.tasks_data:
                 print(f"Advertencia: formato inesperado de mostrar_tareas: {self.tasks_data}. Reiniciando a vacío.")
                 self.tasks_data = {"tareas": []}
            # Llama a refresh para aplicar filtros y poblar tabla
            self.refresh_tasks_display()
        else:
            self.tasks_data = {"tareas": []}
            self.refresh_tasks_display()

    # --- Slot para iniciar/reiniciar el timer de búsqueda (NUEVO) ---
    @pyqtSlot()
    def on_search_text_changed(self):
        """Reinicia el temporizador de debouncing cada vez que el texto cambia."""
        # print("Texto cambiado, reiniciando timer...") # Debug (puede ser muy verboso)
        self.search_timer.start() # Reinicia el timer (o lo inicia si no estaba activo)
    # --------------------------------------------------------------

    def refresh_tasks_display(self):
        """Refresca la tabla y los filtros con los datos actuales en memoria."""
        # Esta función ahora es llamada por el timer de búsqueda o por el cambio de categoría
        print("TasksViewWidget: refresh_tasks_display llamado (filtrando/actualizando tabla)")
        search_term = self.search_input.text() # Obtiene el texto actual
        current_category_filter = self.category_filter_combo.currentText()

        tareas_list = []
        if isinstance(self.tasks_data, dict) and "tareas" in self.tasks_data and isinstance(self.tasks_data["tareas"], list):
             tareas_list = self.tasks_data["tareas"]
        else:
             print(f"Advertencia: Formato inesperado de tasks_data en refresh: {type(self.tasks_data)}")
             self.tasks_data = {"tareas": []}

        self.populate_category_filter(tareas_list, current_category_filter)
        category_filter_actual = self.category_filter_combo.currentText()
        filtered_list = self._filter_tasks(tareas_list, search_term, category_filter_actual)
        self.populate_task_table(filtered_list)


    def _filter_tasks(self, tasks, search_term, category):
        """Filtra y ordena la lista de tareas."""
        filtered = tasks
        search_term_lower = search_term.lower().strip()
        category_lower = category.strip().lower()

        if category_lower != "todas":
            filtered = [t for t in filtered if t.get("categoria", "General").strip().lower() == category_lower]

        if search_term_lower:
            filtered = [t for t in filtered if search_term_lower in t.get("descripcion", "").lower() or \
                                               search_term_lower in t.get("categoria", "").lower()]

        filtered.sort(key=lambda t: (
            t.get("completada", False),
            t.get("fecha_limite") or t.get("fecha_creacion") or "9999",
            t.get("descripcion", "").lower()
        ))
        return filtered


    def populate_task_table(self, tasks):
        """Llena la tabla QTableWidget con las tareas proporcionadas."""
        self.task_table.setRowCount(0)
        self.task_table.setRowCount(len(tasks))
        now_date = datetime.datetime.now().date()

        for row, task in enumerate(tasks):
            desc = task.get("descripcion", "")
            cat = task.get("categoria", "N/A")
            fecha_lim = task.get("fecha_limite", "")
            fecha_display = fecha_lim[:16] if fecha_lim else "Sin fecha límite"
            completada = task.get("completada", False)

            desc_item = QTableWidgetItem(desc)
            cat_item = QTableWidgetItem(cat)
            fecha_item = QTableWidgetItem(fecha_display)
            completed_item = QTableWidgetItem("Sí" if completada else "No")
            completed_item.setTextAlignment(Qt.AlignCenter)

            if completada:
                 font = desc_item.font()
                 font.setStrikeOut(True)
                 desc_item.setFont(font)
                 cat_item.setFont(font)
                 fecha_item.setFont(font)
                 bg_color = QColor(235, 245, 235)
                 fg_color = QColor(120, 120, 120)
                 for item in [desc_item, cat_item, fecha_item, completed_item]:
                     item.setBackground(bg_color)
                     item.setForeground(fg_color)
            elif fecha_lim:
                 try:
                     limite_dt = datetime.datetime.strptime(fecha_lim, '%Y-%m-%d %H:%M:%S').date()
                     if limite_dt < now_date:
                         fecha_item.setForeground(QColor("red"))
                         fecha_item.setFont(QFont(fecha_item.font().family(), -1, QFont.Bold))
                 except ValueError:
                     pass

            self.task_table.setItem(row, 0, desc_item)
            self.task_table.setItem(row, 1, cat_item)
            self.task_table.setItem(row, 2, fecha_item)
            self.task_table.setItem(row, 3, completed_item)

            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(5, 0, 5, 0)
            actions_layout.setSpacing(5)
            actions_layout.setAlignment(Qt.AlignCenter)

            task_original_desc = desc
            btn_size = 24

            icon_complete = QIcon("icons/complete.png") if os.path.exists("icons/complete.png") else QIcon.fromTheme("task-complete")
            icon_edit = QIcon("icons/edit.png") if os.path.exists("icons/edit.png") else QIcon.fromTheme("document-edit")
            icon_delete = QIcon("icons/delete.png") if os.path.exists("icons/delete.png") else QIcon.fromTheme("edit-delete")

            complete_button = QPushButton(icon_complete, "", actions_widget)
            complete_button.setToolTip("Marcar como completada")
            complete_button.setFixedSize(btn_size, btn_size)
            complete_button.clicked.connect(lambda checked, name=task_original_desc: self.complete_task(name))
            complete_button.setEnabled(not completada)
            actions_layout.addWidget(complete_button)

            modify_button = QPushButton(icon_edit, "", actions_widget)
            modify_button.setToolTip("Modificar tarea")
            modify_button.setFixedSize(btn_size, btn_size)
            modify_button.clicked.connect(lambda checked, name=task_original_desc: self.modify_task(name))
            actions_layout.addWidget(modify_button)

            delete_button = QPushButton(icon_delete, "", actions_widget)
            delete_button.setToolTip("Eliminar tarea")
            delete_button.setFixedSize(btn_size, btn_size)
            delete_button.clicked.connect(lambda checked, name=task_original_desc: self.delete_task(name))
            actions_layout.addWidget(delete_button)

            self.task_table.setCellWidget(row, 4, actions_widget)

        self.task_table.verticalHeader().setDefaultSectionSize(28)


    def populate_category_filter(self, tasks, current_selection):
        """Llena el QComboBox de filtro de categorías y restaura la selección."""
        self.category_filter_combo.blockSignals(True)
        self.category_filter_combo.clear()
        self.category_filter_combo.addItem("Todas")

        categories = set()
        for t in tasks:
             cat = t.get("categoria", "General").strip()
             categories.add(cat if cat else "General")
        sorted_categories = sorted(list(categories), key=str.lower)

        for cat in sorted_categories:
            if cat != "Todas":
                self.category_filter_combo.addItem(cat)

        index = self.category_filter_combo.findText(current_selection)
        self.category_filter_combo.setCurrentIndex(index if index != -1 else 0)
        self.category_filter_combo.blockSignals(False)


    # search_tasks ya no es necesario, on_search_text_changed maneja el inicio del timer
    # def search_tasks(self):
    #     self.refresh_tasks_display()

    def filter_by_category(self):
        """Se llama cuando la categoría seleccionada cambia."""
        # El filtrado por categoría sigue siendo inmediato
        self.refresh_tasks_display()

    def handle_add_task_dialog_show(self):
        """Muestra el diálogo para agregar una nueva tarea."""
        dialog = TaskDialog(self.user_manager, parent=self)
        tareas_list = self.tasks_data.get("tareas", []) if isinstance(self.tasks_data, dict) else []
        all_categories = set()
        for t in tareas_list:
            cat = t.get("categoria", "General").strip()
            all_categories.add(cat if cat else "General")
        sorted_categories = sorted(list(all_categories), key=str.lower)
        existing_dialog_categories = {dialog.category_combo.itemText(i) for i in range(dialog.category_combo.count())}
        for cat in sorted_categories:
            if cat not in existing_dialog_categories:
                dialog.category_combo.addItem(cat)
        self.handle_add_modify_task_dialog_result(dialog)


    def handle_add_modify_task_dialog_result(self, dialog):
         """Procesa el resultado del diálogo de agregar/modificar tarea."""
         if dialog.exec_() == QDialog.Accepted:
            task_data = dialog.get_task_data()
            description = task_data.get("descripcion")
            if not description:
                 QMessageBox.warning(self, "Entrada Inválida", "La descripción de la tarea no puede estar vacía.")
                 return
            if self.user_manager.current_user:
                if dialog.task_data:
                    original_desc = dialog.task_data.get("descripcion")
                    success, message = modificar_tarea(original_desc, task_data, self.user_manager.current_user)
                    op_type = "modificar"
                else:
                    success, message = agregar_tarea(
                        description,
                        task_data.get("categoria"),
                        task_data.get("fecha_limite"),
                        self.user_manager.current_user,
                        task_data.get("completada", False)
                    )
                    op_type = "agregar"
                print(f"Respuesta {op_type}: {success}, {message}")
                if success:
                    self.request_refresh_views.emit()
                else:
                    QMessageBox.warning(self, f"Error al {op_type.capitalize()}", message)
            else:
                 QMessageBox.warning(self, "Error", "No se pudo identificar al usuario actual.")


    def complete_task(self, task_name):
        """Marca una tarea como completada."""
        if not task_name: return
        print(f"Intentando completar tarea: '{task_name}'")
        if self.user_manager.current_user:
            success, message = marcar_como_completada(task_name, self.user_manager.current_user)
            print(f"Respuesta completar: {success}, {message}")
            if success:
                self.request_refresh_views.emit()
            else:
                QMessageBox.warning(self, "Error al Completar", message)
        else:
             QMessageBox.warning(self, "Error", "No se pudo identificar al usuario actual.")


    def delete_task(self, task_name):
        """Elimina una tarea previa confirmación."""
        if not task_name: return
        print(f"Intentando eliminar tarea: '{task_name}'")
        reply = QMessageBox.question(self, "Confirmar Eliminación",
                                     f"¿Estás seguro de que quieres eliminar la tarea:\n'{task_name}'?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.user_manager.current_user:
                success, message = eliminar_tarea(task_name, self.user_manager.current_user)
                print(f"Respuesta eliminar: {success}, {message}")
                if success:
                    self.request_refresh_views.emit()
                else:
                    QMessageBox.warning(self, "Error al Eliminar", message)
            else:
                 QMessageBox.warning(self, "Error", "No se pudo identificar al usuario actual.")


    def modify_task(self, task_name):
        """Abre el diálogo para modificar una tarea existente."""
        if not task_name: return
        print(f"Intentando modificar tarea: '{task_name}'")
        task_to_modify = None
        if isinstance(self.tasks_data, dict) and "tareas" in self.tasks_data:
            task_name_lower = task_name.strip().lower()
            for task in self.tasks_data.get("tareas", []):
                 if task.get("descripcion", "").strip().lower() == task_name_lower:
                     task_to_modify = task
                     print(f"Tarea encontrada para modificar: {task}")
                     break
        if task_to_modify:
            dialog = TaskDialog(self.user_manager, task_data=task_to_modify, parent=self)
            tareas_list = self.tasks_data.get("tareas", []) if isinstance(self.tasks_data, dict) else []
            all_categories = set()
            for t in tareas_list:
                 cat = t.get("categoria", "General").strip()
                 all_categories.add(cat if cat else "General")
            sorted_categories = sorted(list(all_categories), key=str.lower)
            existing_dialog_categories = {dialog.category_combo.itemText(i) for i in range(dialog.category_combo.count())}
            for cat in sorted_categories:
                if cat not in existing_dialog_categories:
                    dialog.category_combo.addItem(cat)
            current_task_category = task_to_modify.get("categoria", "General")
            if dialog.category_combo.findText(current_task_category) == -1:
                 dialog.category_combo.addItem(current_task_category)
            dialog.category_combo.setCurrentText(current_task_category)
            self.handle_add_modify_task_dialog_result(dialog)
        else:
            QMessageBox.warning(self, "Error", f"No se encontró la tarea '{task_name}' para modificar.")


# --- CLASE CalendarViewWidget (Sin cambios respecto a la versión anterior) ---

class CalendarViewWidget(QWidget):
    request_refresh_views = pyqtSignal()

    def __init__(self, user_manager, parent=None):
        super().__init__(parent)
        self.user_manager = user_manager
        self.tasks_data = {"tareas": []}
        self.layout = QVBoxLayout(self)

        self.view_title = QLabel("Calendario de Tareas", self)
        self.view_title.setObjectName("viewTitleLabel")
        self.view_title.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.view_title)

        h_splitter = QSplitter(Qt.Horizontal)

        calendar_container = QWidget()
        calendar_layout = QVBoxLayout(calendar_container)
        self.calendar_widget = QCalendarWidget(self)
        self.calendar_widget.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.calendar_widget.currentPageChanged.connect(self.update_calendar_highlight)
        self.calendar_widget.clicked[QDate].connect(self.show_tasks_for_date)
        self.calendar_widget.activated.connect(self.handle_calendar_activated)
        self.calendar_widget.setStyleSheet("""
            QCalendarWidget QToolButton { color: black; background-color: #f0f0f0; border: 1px solid #cccccc; padding: 5px; min-width: 80px; }
            QCalendarWidget QMenu { background-color: white; }
            QCalendarWidget QSpinBox { padding: 2px; margin: 0 5px; background-color: white; color: black; }
            QCalendarWidget QAbstractItemView { selection-background-color: #a8d8ff; selection-color: black; }
            QCalendarWidget QWidget#qt_calendar_navigationbar { background-color: #e8e8e8; }
            QCalendarWidget QAbstractItemView:enabled { color: #333; }
        """)
        calendar_layout.addWidget(self.calendar_widget)
        h_splitter.addWidget(calendar_container)

        tasks_list_container = QWidget()
        tasks_list_layout = QVBoxLayout(tasks_list_container)
        self.tasks_for_date_label = QLabel("Tareas para la fecha seleccionada:", self)
        self.tasks_for_date_text = QTextEdit(self)
        self.tasks_for_date_text.setObjectName("calendarTaskDisplay")
        self.tasks_for_date_text.setReadOnly(True)
        tasks_list_layout.addWidget(self.tasks_for_date_label)
        tasks_list_layout.addWidget(self.tasks_for_date_text)
        h_splitter.addWidget(tasks_list_container)

        h_splitter.setSizes([600, 400])
        self.layout.addWidget(h_splitter)

    def load_and_display_tasks(self):
         print("CalendarViewWidget: load_and_display_tasks llamado")
         if self.user_manager.current_user:
             self.tasks_data = mostrar_tareas(self.user_manager.current_user)
             if not isinstance(self.tasks_data, dict) or "tareas" not in self.tasks_data:
                  print(f"Advertencia: formato inesperado de mostrar_tareas: {self.tasks_data}. Reiniciando a vacío.")
                  self.tasks_data = {"tareas": []}
         else:
             self.tasks_data = {"tareas": []}
         self.update_calendar_highlight()
         self.show_tasks_for_date(self.calendar_widget.selectedDate())

    def update_calendar_highlight(self):
        print("CalendarViewWidget: update_calendar_highlight llamado")
        current_year = self.calendar_widget.yearShown()
        current_month = self.calendar_widget.monthShown()
        base_format = QTextCharFormat()
        date_iter = QDate(current_year, current_month, 1)
        if date_iter.isValid():
            for day_offset in range(date_iter.daysInMonth()):
                date_to_clear = date_iter.addDays(day_offset)
                self.calendar_widget.setDateTextFormat(date_to_clear, base_format)
        else:
            print(f"Advertencia: Fecha inválida para limpiar calendario: {current_year}-{current_month}")

        pending_format = QTextCharFormat()
        pending_format.setBackground(QColor("#FFFACD")); pending_format.setToolTip("Tareas pendientes"); pending_format.setForeground(QColor("black"))
        overdue_format = QTextCharFormat()
        overdue_format.setBackground(QColor("#FFC0CB")); overdue_format.setFontWeight(QFont.Bold); overdue_format.setToolTip("Tareas pendientes VENCIDAS"); overdue_format.setForeground(QColor("black"))
        completed_format = QTextCharFormat()
        completed_format.setBackground(QColor("#90EE90")); completed_format.setToolTip("Todas las tareas completadas"); completed_format.setForeground(QColor("black"))
        mixed_format = QTextCharFormat()
        mixed_format.setBackground(QColor("#ADD8E6")); mixed_format.setToolTip("Tareas completadas y pendientes"); mixed_format.setForeground(QColor("black"))

        tasks_by_date = defaultdict(lambda: {'pending': 0, 'completed': 0, 'overdue': 0})
        tareas_list = self.tasks_data.get("tareas", []) if isinstance(self.tasks_data, dict) else []
        today = QDate.currentDate()

        for task in tareas_list:
            fecha_limite_str = task.get("fecha_limite")
            if fecha_limite_str and isinstance(fecha_limite_str, str):
                try:
                    qdt = QDateTime.fromString(fecha_limite_str, "yyyy-MM-dd HH:mm:ss")
                    if qdt.isValid():
                        qdate = qdt.date()
                        completed = task.get("completada", False)
                        if completed: tasks_by_date[qdate]['completed'] += 1
                        else:
                            tasks_by_date[qdate]['pending'] += 1
                            if qdate < today: tasks_by_date[qdate]['overdue'] += 1
                except Exception as e: pass

        for qdate, counts in tasks_by_date.items():
             if qdate.year() == current_year and qdate.month() == current_month:
                final_format = None
                if counts['overdue'] > 0: final_format = overdue_format
                elif counts['pending'] > 0 and counts['completed'] > 0: final_format = mixed_format
                elif counts['pending'] > 0: final_format = pending_format
                elif counts['completed'] > 0: final_format = completed_format
                if final_format:
                    format_to_apply = QTextCharFormat(final_format)
                    self.calendar_widget.setDateTextFormat(qdate, format_to_apply)

        selected_date = self.calendar_widget.selectedDate()
        if selected_date.isValid() and selected_date.year() == current_year and selected_date.month() == current_month:
             current_format = self.calendar_widget.dateTextFormat(selected_date)
             selection_format = QTextCharFormat(current_format)
             selection_format.setBackground(QColor("#a8d8ff")); selection_format.setForeground(QColor("black")); selection_format.setFontWeight(QFont.Bold)
             self.calendar_widget.setDateTextFormat(selected_date, selection_format)

    def show_tasks_for_date(self, date):
        print(f"CalendarViewWidget: show_tasks_for_date llamado para {date.toString('yyyy-MM-dd')}")
        self.update_calendar_highlight()
        selected_date_str = date.toString("yyyy-MM-dd")
        tasks_on_date = []
        tareas_list = self.tasks_data.get("tareas", []) if isinstance(self.tasks_data, dict) else []
        now_dt = datetime.datetime.now()

        for task in tareas_list:
            fecha_limite = task.get("fecha_limite")
            if fecha_limite and isinstance(fecha_limite, str) and fecha_limite.startswith(selected_date_str):
                 tasks_on_date.append(task)

        tasks_on_date.sort(key=lambda t: (t.get("fecha_limite", ""), t.get("descripcion", "").lower()))

        if tasks_on_date:
            html_content = f"""<style> body {{ font-family: sans-serif; font-size: 10pt; }} .task-item {{ margin-bottom: 8px; padding: 6px 8px; border-left: 4px solid #ccc; background-color:#f8f8f8; border-radius: 3px; }} .task-item.completed {{ border-left-color: #28a745; background-color:#e8f5e9; }} .task-item.overdue {{ border-left-color: #dc3545; background-color:#fdecea; }} .task-item.pending {{ border-left-color: #ffc107; background-color:#fff8e1; }} .task-desc {{ font-weight: bold; display: block; margin-bottom: 3px; }} .task-desc.completed {{ text-decoration: line-through; color: grey; }} .task-details {{ font-size: 9pt; color: #555; }} .overdue-text {{ color: #dc3545; font-weight: bold; }} </style> <b>Tareas para {selected_date_str}:</b> ({len(tasks_on_date)})<br><br>"""
            for task in tasks_on_date:
                is_completed = task.get("completada", False)
                description = html.escape(task.get('descripcion', 'Sin descripción'))
                category = html.escape(task.get('categoria', 'N/A'))
                fecha_limite_str = task.get('fecha_limite')
                hora_limite_str = ""
                is_overdue = False
                status_class = "pending"
                if fecha_limite_str:
                    try:
                        limite_dt = datetime.datetime.strptime(fecha_limite_str, '%Y-%m-%d %H:%M:%S')
                        hora_limite_str = limite_dt.strftime(' a las %H:%M')
                        if not is_completed and limite_dt < now_dt:
                            is_overdue = True; status_class = "overdue"
                    except ValueError: hora_limite_str = " (Formato Hora Inválido)"
                else: hora_limite_str = " (Sin Hora)"
                if is_completed: status_class = "completed"
                desc_class = "task-desc completed" if is_completed else "task-desc"
                overdue_label = '<span class="overdue-text">¡VENCIDA!</span> ' if is_overdue else ""
                html_content += f'<div class="task-item {status_class}"><span class="{desc_class}">{description}</span><span class="task-details">{overdue_label}Categoría: {category} | Límite: {selected_date_str}{hora_limite_str}</span></div>'
        else:
            html_content = f"<i>No hay tareas con fecha límite para {selected_date_str}.</i>"
        self.tasks_for_date_text.setHtml(html_content)

    def handle_calendar_activated(self, date):
        print(f"Doble click detectado en fecha: {date.toString('yyyy-MM-dd')}")
        dialog = TaskDialog(self.user_manager, parent=self)
        tareas_list = self.tasks_data.get("tareas", []) if isinstance(self.tasks_data, dict) else []
        all_categories = set()
        for t in tareas_list:
             cat = t.get("categoria", "General").strip()
             all_categories.add(cat if cat else "General")
        sorted_categories = sorted(list(all_categories), key=str.lower)
        existing_dialog_categories = {dialog.category_combo.itemText(i) for i in range(dialog.category_combo.count())}
        for cat in sorted_categories:
            if cat not in existing_dialog_categories: dialog.category_combo.addItem(cat)
        dialog.set_initial_date(date)
        if dialog.exec_() == QDialog.Accepted:
            task_data = dialog.get_task_data()
            description = task_data.get("descripcion")
            if description:
                 if self.user_manager.current_user:
                     success, message = agregar_tarea(
                         description, task_data.get("categoria"), task_data.get("fecha_limite"),
                         self.user_manager.current_user, task_data.get("completada", False)
                     )
                     print(f"Respuesta agregar (desde calendario): {success}, {message}")
                     if success: self.request_refresh_views.emit()
                     else: QMessageBox.warning(self, "Error al Agregar", message)
                 else: QMessageBox.warning(self, "Error", "No se pudo identificar al usuario actual.")
            else: QMessageBox.warning(self, "Entrada Inválida", "La descripción de la tarea no puede estar vacía.")


# --- CLASE ReportsViewWidget (Sin cambios respecto a la versión anterior) ---
class ReportsViewWidget(QWidget):
    reportGenerated = pyqtSignal(str)
    request_report_generation = pyqtSignal(int, int, str)

    def __init__(self, user_manager, parent=None):
        super().__init__(parent)
        self.user_manager = user_manager
        self.current_report_html = ""
        self.layout = QVBoxLayout(self)

        self.report_thread = QThread(self)
        self.report_worker = ReportGeneratorWorker()
        self.report_worker.moveToThread(self.report_thread)
        self.report_worker.reportReady.connect(self.display_generated_report)
        self.request_report_generation.connect(self.report_worker.generate_report)
        self.report_thread.finished.connect(self.report_worker.deleteLater)
        self.report_thread.finished.connect(self.report_thread.deleteLater)
        self.report_thread.start()

        self.view_title = QLabel("Generar Reporte Mensual", self)
        self.view_title.setObjectName("viewTitleLabel")
        self.view_title.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.view_title)

        form_group_box = QGroupBox("Seleccionar Mes y Año")
        self.report_form_layout = QFormLayout(form_group_box)
        self.month_combo = QComboBox(self)
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        self.month_combo.addItems(meses)
        self.month_combo.setCurrentIndex(datetime.datetime.now().month - 1)
        self.report_form_layout.addRow("Mes:", self.month_combo)
        self.year_input = QLineEdit(self)
        self.year_input.setText(str(datetime.datetime.now().year))
        self.year_input.setPlaceholderText("Año (ej. 2024)")
        self.year_input.setStyleSheet("QLineEdit { background-color: white; color: black; }")
        self.report_form_layout.addRow("Año:", self.year_input)

        action_layout = QHBoxLayout()
        icon_report = QIcon("icons/report.png") if os.path.exists("icons/report.png") else QIcon.fromTheme("document-print")
        icon_save = QIcon("icons/save.png") if os.path.exists("icons/save.png") else QIcon.fromTheme("document-save")
        self.generate_button = QPushButton(icon_report, " Generar Reporte", self)
        self.generate_button.clicked.connect(self.request_report_generation_slot)
        action_layout.addWidget(self.generate_button)
        self.export_button = QPushButton(icon_save, " Exportar HTML", self)
        self.export_button.clicked.connect(self.export_report_to_html)
        self.export_button.setEnabled(False)
        action_layout.addWidget(self.export_button)
        action_layout.addStretch(1)
        self.report_form_layout.addRow(action_layout)
        self.layout.addWidget(form_group_box)

        self.report_title = QLabel("Reporte Mensual", self)
        self.report_title.setObjectName("reportTitleLabel")
        self.report_title.setAlignment(Qt.AlignCenter)
        self.report_title.hide()
        self.layout.addWidget(self.report_title)
        self.report_text_edit = QTextEdit(self)
        self.report_text_edit.setReadOnly(True)
        self.layout.addWidget(self.report_text_edit)

    @pyqtSlot()
    def request_report_generation_slot(self):
        self.report_text_edit.clear()
        self.current_report_html = ""
        self.export_button.setEnabled(False)
        self.generate_button.setEnabled(False)
        self.report_title.hide()
        try:
            month = self.month_combo.currentIndex() + 1
            year_str = self.year_input.text().strip()
            if not year_str or not year_str.isdigit():
                 QMessageBox.warning(self, "Entrada Inválida", "Por favor, introduce un año numérico válido.")
                 self.generate_button.setEnabled(True); return
            year = int(year_str)
            if not (1900 < year < 2200):
                 QMessageBox.warning(self, "Año Inválido", "Introduce un año válido (ej. 1980-2199).")
                 self.generate_button.setEnabled(True); return
            if self.user_manager.current_user:
                 print(f"ReportsViewWidget: Emitiendo request_report_generation para {month}/{year}")
                 self.request_report_generation.emit(month, year, self.user_manager.current_user)
            else:
                 QMessageBox.warning(self, "Usuario No Identificado", "Debes iniciar sesión para generar reportes.")
                 self.generate_button.setEnabled(True)
        except ValueError:
            QMessageBox.warning(self, "Entrada Inválida", "Introduce un año numérico válido.")
            self.generate_button.setEnabled(True)
        except Exception as e:
             QMessageBox.critical(self, "Error Inesperado", f"Ocurrió un error antes de generar el reporte:\n{e}")
             self.generate_button.setEnabled(True)

    @pyqtSlot(str)
    def display_generated_report(self, reporte_html):
        print("ReportsViewWidget: Recibido reportReady del worker.")
        self.current_report_html = reporte_html
        month_name = self.month_combo.currentText()
        year_str = self.year_input.text().strip()
        self.report_title.setText(f"Reporte - {month_name} {year_str}")
        self.report_title.show()
        self.report_text_edit.setHtml(reporte_html)
        self.export_button.setEnabled(bool(reporte_html and "<html" in reporte_html.lower()))
        self.generate_button.setEnabled(True)

    def export_report_to_html(self):
        if not self.current_report_html:
            QMessageBox.warning(self, "Sin Reporte", "Primero genera un reporte para poder exportarlo.")
            return
        default_filename = f"Reporte_Tareas_{self.month_combo.currentText()}_{self.year_input.text()}.html"
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getSaveFileName(self, "Guardar Reporte HTML", default_filename,
                                                  "Archivos HTML (*.html);;Todos los Archivos (*)", options=options)
        if fileName:
            try:
                with open(fileName, 'w', encoding='utf-8') as f: f.write(self.current_report_html)
                QMessageBox.information(self, "Éxito", f"Reporte guardado exitosamente en:\n{fileName}")
            except Exception as e:
                QMessageBox.critical(self, "Error al Guardar", f"No se pudo guardar el archivo:\n{e}")

    def __del__(self):
        print("Destruyendo ReportsViewWidget, deteniendo hilo de reporte...")
        if hasattr(self, 'report_thread') and self.report_thread.isRunning():
            self.report_thread.quit()
            if not self.report_thread.wait(1000):
                print("Advertencia: Hilo de reporte no terminó, terminando forzosamente.")
                self.report_thread.terminate(); self.report_thread.wait()
        print("Hilo de reporte detenido.")

# --- Worker simple para Generar Reportes (Sin cambios) ---
class ReportGeneratorWorker(QObject):
    reportReady = pyqtSignal(str)
    @pyqtSlot(int, int, str)
    def generate_report(self, mes, anho, email):
        print(f"ReportWorker: Generando reporte para {mes}/{anho}, email: {email}")
        try:
            reporte_html = generar_reporte_mensual(mes, anho, email)
            print("ReportWorker: Reporte generado, emitiendo señal.")
            self.reportReady.emit(reporte_html)
        except Exception as e:
            error_html = f"<p style='color:red; font-family: sans-serif;'><b>Error interno inesperado al generar el reporte en el worker:</b><br>{html.escape(str(e))}</p>"
            print(f"ReportWorker: Error durante generación: {e}")
            self.reportReady.emit(error_html)

# --- Ventana Principal Contenedora (TaskCalendarWindow) (Sin cambios respecto a la versión anterior) ---
class TaskCalendarWindow(QMainWindow):
    tasks_updated_signal = pyqtSignal()
    request_final_sync = pyqtSignal()

    def __init__(self, user_manager):
        super().__init__()
        self.user_manager = user_manager
        user_name = self.user_manager.get_user_name() or self.user_manager.current_user
        self.setWindowTitle(f"VoceTasks - {user_name}")
        self.setGeometry(100, 100, 1000, 650)

        self.drive_thread = QThread(self)
        self.drive_worker = DriveSyncWorker(self.user_manager.current_user)
        self.drive_worker.moveToThread(self.drive_thread)
        self.drive_worker.syncFinished.connect(self.handle_sync_finished)
        self.request_final_sync.connect(self.drive_worker.do_sync_upload, Qt.QueuedConnection)
        self.drive_thread.finished.connect(self.drive_worker.deleteLater)
        self.drive_thread.finished.connect(self.drive_thread.deleteLater)
        self.drive_thread.start()
        self.is_syncing = False
        self.logout_pending = False

        icon_path = "logo.png"; logo_to_use = icon_path if os.path.exists(icon_path) else None
        if logo_to_use: self.setWindowIcon(QIcon(logo_to_use))
        else: print(f"Advertencia: Ícono de ventana no encontrado ('{icon_path}').")

        self.tool_bar = QToolBar("Barra de Herramientas Principal"); self.addToolBar(self.tool_bar)
        self.tool_bar.setMovable(False); self.tool_bar.setIconSize(QSize(24, 24))
        icon_tasks = QIcon("icons/tasks.png") if os.path.exists("icons/tasks.png") else QIcon.fromTheme("view-list-text")
        icon_calendar = QIcon("icons/calendar.png") if os.path.exists("icons/calendar.png") else QIcon.fromTheme("x-office-calendar")
        icon_reports = QIcon("icons/report.png") if os.path.exists("icons/report.png") else QIcon.fromTheme("document-print")
        icon_download = QIcon("icons/download.png") if os.path.exists("icons/download.png") else QIcon.fromTheme("arrow-down")
        icon_upload = QIcon("icons/upload.png") if os.path.exists("icons/upload.png") else QIcon.fromTheme("arrow-up")
        icon_logout = QIcon("icons/logout.png") if os.path.exists("icons/logout.png") else QIcon.fromTheme("system-log-out")

        self.action_show_tasks = QAction(icon_tasks, "Tareas", self); self.action_show_tasks.setToolTip("Mostrar Lista de Tareas"); self.action_show_tasks.triggered.connect(lambda: self.change_view(0)); self.tool_bar.addAction(self.action_show_tasks)
        self.action_show_calendar = QAction(icon_calendar, "Calendario", self); self.action_show_calendar.setToolTip("Mostrar Calendario de Tareas"); self.action_show_calendar.triggered.connect(lambda: self.change_view(1)); self.tool_bar.addAction(self.action_show_calendar)
        self.action_show_reports = QAction(icon_reports, "Reportes", self); self.action_show_reports.setToolTip("Generar Reportes Mensuales"); self.action_show_reports.triggered.connect(lambda: self.change_view(2)); self.tool_bar.addAction(self.action_show_reports)
        self.tool_bar.addSeparator()
        self.action_sync_from = QAction(icon_download, "Descargar de Drive", self); self.action_sync_from.setToolTip("Sincronizar Tareas DESDE Google Drive (Descargar)"); self.action_sync_from.triggered.connect(self.sync_from_drive_action); self.tool_bar.addAction(self.action_sync_from)
        self.action_sync_to = QAction(icon_upload, "Subir a Drive", self); self.action_sync_to.setToolTip("Sincronizar Tareas HACIA Google Drive (Subir)"); self.action_sync_to.triggered.connect(self.sync_to_drive_action); self.tool_bar.addAction(self.action_sync_to)
        self.tool_bar.addSeparator()
        self.action_logout = QAction(icon_logout, "Cerrar Sesión", self); self.action_logout.setToolTip("Cerrar la sesión actual"); self.action_logout.triggered.connect(self.logout); self.tool_bar.addAction(self.action_logout)

        self.central_widget = QWidget(); self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget); self.layout.setContentsMargins(5, 5, 5, 5)
        self.views_stack = QStackedWidget(self); self.layout.addWidget(self.views_stack)

        self.tasks_view = TasksViewWidget(self.user_manager, parent=self)
        self.calendar_view = CalendarViewWidget(self.user_manager, parent=self)
        self.reports_view = ReportsViewWidget(self.user_manager, parent=self)

        self.views_stack.addWidget(self.tasks_view)
        self.views_stack.addWidget(self.calendar_view)
        self.views_stack.addWidget(self.reports_view)

        self.tasks_updated_signal.connect(self.tasks_view.load_and_display_tasks)
        self.tasks_updated_signal.connect(self.calendar_view.load_and_display_tasks)
        self.tasks_view.request_refresh_views.connect(self.refresh_views_local)
        self.calendar_view.request_refresh_views.connect(self.refresh_views_local)

        self.notification_timer = QTimer(self); self.notification_timer.timeout.connect(self.check_upcoming_tasks_for_notification); self.checked_tasks_for_notification = set()
        self.load_tasks_initial()
        self.change_view(0)

    def change_view(self, index):
        self.views_stack.setCurrentIndex(index)
        if index == 1: self.calendar_view.update_calendar_highlight()

    def refresh_views_local(self):
        print("TaskCalendarWindow: Solicitud para refrescar vistas locales.")
        self.tasks_updated_signal.emit()

    @pyqtSlot()
    def sync_to_drive_action(self):
        if self.user_manager.current_user and not self.is_syncing:
            print("TaskCalendarWindow: Solicitando subida a Drive en hilo...")
            self.is_syncing = True; self.set_sync_buttons_enabled(False)
            QMessageBox.information(self, "Sincronización", "Iniciando subida a Google Drive...\nPuedes seguir usando la aplicación.")
            QMetaObject.invokeMethod(self.drive_worker, "do_sync_upload", Qt.QueuedConnection)
        elif self.is_syncing: QMessageBox.information(self,"Sincronización","Ya hay una operación de sincronización en curso.")
        else: QMessageBox.warning(self, "Error", "Debes iniciar sesión para sincronizar.")

    @pyqtSlot()
    def sync_from_drive_action(self):
         if self.user_manager.current_user and not self.is_syncing:
              print("TaskCalendarWindow: Solicitando descarga de Drive en hilo...")
              self.is_syncing = True; self.set_sync_buttons_enabled(False)
              QMessageBox.information(self, "Sincronización", "Iniciando descarga desde Google Drive...\nPuedes seguir usando la aplicación.")
              QMetaObject.invokeMethod(self.drive_worker, "do_sync_download", Qt.QueuedConnection)
         elif self.is_syncing: QMessageBox.information(self,"Sincronización","Ya hay una operación de sincronización en curso.")
         else: QMessageBox.warning(self, "Error", "Debes iniciar sesión para sincronizar.")

    @pyqtSlot(bool, str, str)
    def handle_sync_finished(self, success, message, operation_type):
        print(f"TaskCalendarWindow: Recibido syncFinished - success={success}, op={operation_type}, msg={message}")
        self.is_syncing = False; self.set_sync_buttons_enabled(True)
        if operation_type == 'initial_download':
            if success:
                 print("Descarga inicial exitosa, refrescando vistas...")
                 self.tasks_updated_signal.emit()
            else:
                 if "Error" in message: QMessageBox.warning(self, "Sincronización Inicial Fallida", f"No se pudieron descargar las tareas de Google Drive al iniciar.\nDetalle: {message}\n\nSe mostrarán las tareas locales.")
                 else: print(f"Info Sync Inicial: {message}")
                 self.tasks_updated_signal.emit()
            return
        if success:
            QMessageBox.information(self, "Sincronización Exitosa", f"Operación ({operation_type}) completada:\n{message}")
            if operation_type == 'download':
                print("Descarga manual exitosa, refrescando vistas...")
                self.tasks_updated_signal.emit()
        else:
            QMessageBox.warning(self, "Error de Sincronización", f"Falló la operación ({operation_type}):\n{message}")
            if operation_type == 'download' and "Error" not in message: self.tasks_updated_signal.emit()
        if self.logout_pending and operation_type == 'upload':
            print("Sincronización final completada, procediendo con logout...")
            self.logout_pending = False
            self.perform_logout_steps()

    def load_tasks_initial(self):
        if self.user_manager.current_user and not self.is_syncing:
            print("TaskCalendarWindow: Solicitando descarga INICIAL en hilo...")
            self.is_syncing = True; self.set_sync_buttons_enabled(False)
            QMetaObject.invokeMethod(self.drive_worker, "do_initial_sync_download", Qt.QueuedConnection)
        elif self.is_syncing: print("Advertencia: Intento de carga inicial mientras otra sync está en curso.")
        else: print("Carga inicial: No hay usuario logueado."); self.tasks_updated_signal.emit()

    def logout(self):
        reply = QMessageBox.question(self, 'Cerrar Sesión', '¿Estás seguro de que quieres cerrar sesión?\nSe intentará guardar tus últimas tareas en Google Drive antes de salir.', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
             if self.user_manager.current_user:
                  if not self.is_syncing:
                       print("Cerrando sesión: Solicitando sincronización final HACIA Drive...")
                       self.is_syncing = True; self.logout_pending = True; self.set_sync_buttons_enabled(False)
                       self.centralWidget().setEnabled(False)
                       QMessageBox.information(self, "Cerrando Sesión", "Guardando tareas en Google Drive...")
                       self.request_final_sync.emit()
                  else: QMessageBox.warning(self, "Operación en Curso", "Espera a que termine la sincronización actual antes de cerrar sesión."); return
             else: self.perform_logout_steps()

    def perform_logout_steps(self):
         print("Ejecutando pasos finales de logout...")
         self.user_manager.logout()
         print("Sesión cerrada en UserManager.")
         self.centralWidget().setEnabled(True)
         self.close()

    def set_sync_buttons_enabled(self, enabled):
        self.action_sync_from.setEnabled(enabled)
        self.action_sync_to.setEnabled(enabled)

    def check_upcoming_tasks_for_notification(self):
        if not self.user_manager.current_user: return
        print("Chequeando tareas para notificación...")
        current_tasks_data = mostrar_tareas(self.user_manager.current_user)
        upcoming_tasks_to_notify = []; now = datetime.datetime.now(); notified_this_cycle = set()
        tareas_list = current_tasks_data.get("tareas", []) if isinstance(current_tasks_data, dict) else []
        for tarea in tareas_list:
            if not tarea.get("completada", False):
                fecha_limite_str = tarea.get("fecha_limite")
                task_identifier = (tarea.get("descripcion", ""), fecha_limite_str)
                if task_identifier in notified_this_cycle: continue
                if fecha_limite_str and isinstance(fecha_limite_str, str):
                    try:
                        fecha_limite = datetime.datetime.strptime(fecha_limite_str, '%Y-%m-%d %H:%M:%S')
                        time_difference = fecha_limite - now
                        if timedelta(0) < time_difference <= timedelta(days=1):
                            if task_identifier not in self.checked_tasks_for_notification:
                                upcoming_tasks_to_notify.append(tarea)
                                self.checked_tasks_for_notification.add(task_identifier)
                                notified_this_cycle.add(task_identifier)
                    except ValueError: pass
        for tarea in upcoming_tasks_to_notify:
             fecha_limite_str = tarea.get("fecha_limite")
             if fecha_limite_str:
                 try:
                     fecha_limite = datetime.datetime.strptime(fecha_limite_str, '%Y-%m-%d %H:%M:%S')
                     time_diff = fecha_limite - now; time_message = ""
                     if time_diff.total_seconds() > 0:
                         days=time_diff.days; hours,rem=divmod(time_diff.seconds,3600); minutes,_=divmod(rem,60)
                         parts=[];
                         if days > 0: parts.append(f"{days} día{'s' if days > 1 else ''}")
                         if hours > 0: parts.append(f"{hours} hora{'s' if hours > 1 else ''}")
                         if minutes > 0: parts.append(f"{minutes} minuto{'s' if minutes > 1 else ''}")
                         time_until = " y ".join(filter(None,[", ".join(parts[:-1]),parts[-1]])) if parts else "menos de un minuto"
                         time_message = f"Faltan {time_until}."
                     else: time_message = "¡Fecha límite pasada!"
                     msg = (f"<b>¡Recordatorio de Tarea!</b><br><br>"
                            f"<b>Tarea:</b> {html.escape(tarea.get('descripcion', 'N/A'))}<br>"
                            f"<b>Límite:</b> {fecha_limite_str}<br><br>"
                            f"<i>{time_message}</i>")
                     QMessageBox.information(self, f"Recordatorio: {html.escape(tarea.get('descripcion', 'Tarea'))}", msg)
                 except ValueError: pass

    def closeEvent(self, event):
        print("Cerrando ventana TaskCalendarWindow...")
        self.notification_timer.stop()
        if self.drive_thread.isRunning():
            print("Deteniendo hilo de Drive...")
            self.drive_thread.quit()
            if not self.drive_thread.wait(3000):
                 print("Advertencia: El hilo de Drive no terminó limpiamente, terminando forzosamente.")
                 self.drive_thread.terminate(); self.drive_thread.wait()
            print("Hilo de Drive detenido.")
        if hasattr(self.reports_view, 'report_thread') and self.reports_view.report_thread.isRunning():
            print("Deteniendo hilo de Reportes...")
            self.reports_view.report_thread.quit()
            if not self.reports_view.report_thread.wait(1000):
                print("Advertencia: Hilo de reporte no terminó, terminando forzosamente.")
                self.reports_view.report_thread.terminate(); self.reports_view.report_thread.wait()
            print("Hilo de Reportes detenido.")
        event.accept()

# --- Ventana Principal de Inicio (MainWindow) (Sin cambios) ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.user_manager = UserManager()
        self.task_calendar_window = None
        self.setWindowTitle("VoceTasks - Inicio")
        self.setGeometry(200, 200, 450, 350); self.setMinimumSize(400, 300)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        icon_path = "logo.png"; logo_to_use = icon_path if os.path.exists(icon_path) else None
        if logo_to_use: self.setWindowIcon(QIcon(logo_to_use))
        self.central_widget = QWidget(); self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget); self.layout.setContentsMargins(30, 20, 30, 30); self.layout.setSpacing(15); self.layout.setAlignment(Qt.AlignCenter)
        self.logo_label = QLabel(self)
        if logo_to_use:
            logo_pixmap = QPixmap(logo_to_use)
            if not logo_pixmap.isNull():
                 scaled_logo = logo_pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                 self.logo_label.setPixmap(scaled_logo); self.logo_label.setAlignment(Qt.AlignCenter)
                 self.layout.addWidget(self.logo_label); self.layout.addSpacing(10)
            else: print("Advertencia: No se pudo cargar el logo como QPixmap.")
        else: print("Advertencia: Archivo de logo no encontrado.")
        self.title_label = QLabel("Bienvenido a VoceTasks", self); self.title_label.setObjectName("mainWindowTitleLabel"); self.title_label.setFont(QFont("Arial", 18, QFont.Bold)); self.title_label.setAlignment(Qt.AlignCenter); self.layout.addWidget(self.title_label)
        self.layout.addSpacing(25)
        btn_w, btn_h = 180, 45
        self.login_button = QPushButton("Iniciar Sesión", self); self.login_button.setFixedSize(btn_w, btn_h); self.login_button.clicked.connect(self.show_login_dialog); self.layout.addWidget(self.login_button, alignment=Qt.AlignCenter)
        self.register_button = QPushButton("Registrarse", self); self.register_button.setFixedSize(btn_w, btn_h); self.register_button.clicked.connect(self.show_register_dialog); self.layout.addWidget(self.register_button, alignment=Qt.AlignCenter)
        self.layout.addStretch(1)
        self.show()

    def show_login_dialog(self):
        dialog = LoginDialog(self.user_manager, self)
        if dialog.exec_() == QDialog.Accepted and self.user_manager.current_user: self.show_task_calendar_window()

    def show_register_dialog(self):
        dialog = RegisterDialog(self.user_manager, self); dialog.exec_()

    def show_task_calendar_window(self):
        if self.task_calendar_window is None or not self.task_calendar_window.isVisible():
            self.task_calendar_window = TaskCalendarWindow(self.user_manager)
            self.task_calendar_window.destroyed.connect(self.on_task_window_closed)
            self.task_calendar_window.show(); self.hide()

    @pyqtSlot()
    def on_task_window_closed(self):
        print("Ventana de tareas cerrada. Mostrando ventana de inicio.")
        self.task_calendar_window = None
        if not self.isVisible(): self.show()

# --- Carga QSS y Punto de Entrada Principal (Sin cambios) ---
def load_stylesheet(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f: return f.read()
    except FileNotFoundError: print(f"Advertencia: Hoja de estilos '{filepath}' no encontrada."); return ""
    except Exception as e: print(f"Advertencia: No se pudo cargar la hoja de estilos '{filepath}'. Error: {e}"); return ""

if __name__ == "__main__":
    try: os.makedirs("usuarios", exist_ok=True); print("Directorio 'usuarios' verificado/creado.")
    except Exception as e: print(f"Error crítico al crear el directorio 'usuarios': {e}"); sys.exit(1)
    app = QApplication(sys.argv)
    stylesheet = load_stylesheet("styles.qss")
    if stylesheet: app.setStyleSheet(stylesheet); print("Hoja de estilos 'styles.qss' aplicada.")
    else: print("No se aplicó hoja de estilos externa."); app.setStyle("Fusion")
    window = MainWindow()
    sys.exit(app.exec_())
