# gui.py (Refactored - Two Windows - Fixed show_add_task_dialog position)
import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                           QTabWidget, QLabel, QPushButton, QLineEdit, QTextEdit,
                           QTableWidget, QTableWidgetItem, QCalendarWidget, QFrame,
                           QMessageBox, QSplitter, QDialog, QFormLayout,
                           QCheckBox, QComboBox, QGroupBox, QScrollArea, QStackedWidget,
                           QInputDialog, QDialogButtonBox, QDateTimeEdit)
from PyQt5.QtCore import Qt, QDate, QTimer, pyqtSignal, QThread, QDateTime
from PyQt5.QtGui import QIcon, QFont, QColor, QTextCharFormat # Importar QTextCharFormat

# Importar los módulos existentes y las funciones actualizadas de commands
from utils import escuchar_comando, hablar
from commands import (agregar_tarea, eliminar_tarea, mostrar_tareas, modificar_tarea,
                     agregar_recordatorio, cambiar_categoria, marcar_como_completada,
                     mostrar_tareas_por_categoria, mostrar_tareas_calendario_local,
                     generar_reporte_mensual)
from user_management import UserManager
import os
import json
import datetime
from datetime import timedelta, datetime
import re


class RecognizerThread(QThread):
    """Hilo para el reconocimiento de voz en segundo plano"""
    textDetected = pyqtSignal(str)
    listenStateChanged = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.running = False

    def run(self):
        import speech_recognition as sr
        r = sr.Recognizer()
        with sr.Microphone() as source:
            self.listenStateChanged.emit(True)
            r.adjust_for_ambient_noise(source)
            audio = r.listen(source)
            self.listenStateChanged.emit(False)

            try:
                texto = r.recognize_google(audio, language='es-ES')
                self.textDetected.emit(texto.lower())
            except sr.UnknownValueError:
                self.textDetected.emit("No entendí")
            except sr.RequestError:
                self.textDetected.emit("Error de conexión")


class LoginDialog(QDialog):
    """Diálogo para inicio de sesión y registro de usuarios con diseño moderno"""
    def __init__(self, user_manager, parent=None):
        super().__init__(parent)
        self.user_manager = user_manager
        self.setWindowTitle("Acceso a VoceTasks") # Cambiado el título de la ventana
        self.setMinimumSize(400, 300) # Ajustar tamaño mínimo

        # Aplicar estilo oscuro y moderno al diálogo
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
                font-size: 12pt;
            }
            QLineEdit {
                background-color: #333333;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 5px;
                border-radius: 5px;
                font-size: 12pt;
            }
            QPushButton {
                background-color: #007acc;
                color: #ffffff;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 12pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #005f99;
            }
            QTabWidget::pane {
                border: 1px solid #555555;
                background-color: #2b2b2b;
                border-radius: 5px;
            }
            QTabBar::tab {
                background: #333333;
                color: #ffffff;
                padding: 8px 15px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                margin-right: 1px;
            }
            QTabBar::tab:selected {
                background: #007acc;
                color: #ffffff;
            }
             QTabBar::tab:hover {
                background: #005f99;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        app_name_label = QLabel("VoceTasks")
        app_name_label.setFont(QFont("Arial", 24, QFont.Bold))
        app_name_label.setAlignment(Qt.AlignCenter)
        app_name_label.setStyleSheet("color: #007acc;")

        tab_widget = QTabWidget()

        login_widget = QWidget()
        login_layout = QVBoxLayout(login_widget)
        login_layout.setContentsMargins(10, 10, 10, 10)

        form_layout = QFormLayout()
        form_layout.setRowWrapPolicy(QFormLayout.WrapAllRows)
        form_layout.setLabelAlignment(Qt.AlignLeft)
        form_layout.setFormAlignment(Qt.AlignCenter)
        form_layout.setHorizontalSpacing(10)
        form_layout.setVerticalSpacing(10)

        self.login_email = QLineEdit()
        self.login_email.setPlaceholderText("Introduce tu email")
        self.login_password = QLineEdit()
        self.login_password.setEchoMode(QLineEdit.Password)

        form_layout.addRow("Email:", self.login_email)
        form_layout.addRow("Contraseña:", self.login_password)

        login_button = QPushButton("Iniciar Sesión")
        login_button.clicked.connect(self.handle_login)

        login_layout.addLayout(form_layout)
        login_layout.addSpacing(10)
        login_layout.addWidget(login_button)

        register_widget = QWidget()
        register_layout = QVBoxLayout(register_widget)
        register_layout.setContentsMargins(10, 10, 10, 10)

        register_form = QFormLayout()
        register_form.setRowWrapPolicy(QFormLayout.WrapAllRows)
        register_form.setLabelAlignment(Qt.AlignLeft)
        register_form.setFormAlignment(Qt.AlignCenter)
        register_form.setHorizontalSpacing(10)
        register_form.setVerticalSpacing(10)

        self.register_name = QLineEdit()
        self.register_name.setPlaceholderText("Introduce tu nombre")
        self.register_email = QLineEdit()
        self.register_email.setPlaceholderText("Introduce tu email")
        self.register_password = QLineEdit()
        self.register_password.setEchoMode(QLineEdit.Password)

        register_form.addRow("Nombre:", self.register_name)
        register_form.addRow("Email:", self.register_email)
        register_form.addRow("Contraseña:", self.register_password)

        register_button = QPushButton("Registrarse")
        register_button.clicked.connect(self.handle_register)

        register_layout.addLayout(register_form)
        register_layout.addSpacing(10)
        register_layout.addWidget(register_button)

        tab_widget.addTab(login_widget, "Iniciar Sesión")
        tab_widget.addTab(register_widget, "Registrarse")

        main_layout.addWidget(app_name_label)
        main_layout.addWidget(tab_widget)

        self.setLayout(main_layout)

    def handle_login(self):
        email = self.login_email.text()
        password = self.login_password.text()

        success, message = self.user_manager.login(email, password)
        if success:
            QMessageBox.information(self, "Éxito", message)
            self.accept()
        else:
            QMessageBox.warning(self, "Error", message)

    def handle_register(self):
        name = self.register_name.text()
        email = self.register_email.text()
        password = self.register_password.text()

        success, message = self.user_manager.register_user(email, password, name)
        if success:
            QMessageBox.information(self, "Éxito", message)
            self.user_manager.login(email, password)
            self.accept()
        else:
            QMessageBox.warning(self, "Error", message)


class TasksTable(QTableWidget):
    """Widget personalizado para mostrar tareas en formato de tabla"""
    taskCompleted = pyqtSignal(str)
    taskDeleted = pyqtSignal(str)
    taskModified = pyqtSignal(str) # Señal para notificar modificación (nueva)

    def __init__(self):
        super().__init__()
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels(["Tarea", "Categoría", "Fecha límite", "Estado", "Acciones"])
        self.horizontalHeader().setStretchLastSection(True)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setAlternatingRowColors(True)

        self.setStyleSheet("""
            QTableWidget {
                gridline-color: #555555;
                color: #ffffff;
                background-color: #2b2b2b;
            }
            QTableWidget::item {
                color: #ffffff;
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #007acc;
                color: #ffffff;
            }
            QTableWidget::item:!selected {
                 background-color: #2b2b2b;
            }
            QTableWidget::item:!selected:alternate {
                 background-color: #333333;
            }
            QTableWidget QHeaderView::section {
                background-color: #3a3a3a;
                color: #ffffff;
                padding: 5px;
                border: 1px solid #555555;
            }
        """)

    def load_tasks(self, email):
        """Carga las tareas del usuario en la tabla"""
        self.setRowCount(0)

        try:
            ruta_archivo = f"usuarios/{email}/tareas.json"
            if not os.path.exists(ruta_archivo):
                return

            with open(ruta_archivo, "r") as file:
                data = json.load(file)

                for row, task in enumerate(data["tareas"]):
                    self.insertRow(row)

                    # Descripción
                    desc_item = QTableWidgetItem(task["descripcion"])
                    desc_item.setForeground(QColor(255, 255, 255))
                    self.setItem(row, 0, desc_item)

                    # Categoría
                    cat_item = QTableWidgetItem(task["categoria"])
                    cat_item.setForeground(QColor(255, 255, 255))
                    self.setItem(row, 1, cat_item)

                    # Fecha límite
                    fecha = "No establecida" if not task.get("fecha_limite") else task["fecha_limite"]
                    fecha_item = QTableWidgetItem(fecha)
                    fecha_item.setForeground(QColor(255, 255, 255))
                    self.setItem(row, 2, fecha_item)

                    # Estado
                    estado = "Completada" if task.get("completada") else "Pendiente"
                    estado_item = QTableWidgetItem(estado)
                    if task.get("completada"):
                        estado_item.setBackground(QColor(50, 150, 50))
                    else:
                        estado_item.setBackground(QColor(150, 50, 50))
                    estado_item.setForeground(QColor(255, 255, 255))
                    self.setItem(row, 3, estado_item)

                    # Botones de acción (Completar, Eliminar, Modificar)
                    actions_widget = QWidget()
                    actions_layout = QHBoxLayout(actions_widget)
                    actions_layout.setContentsMargins(0, 0, 0, 0)
                    actions_layout.setAlignment(Qt.AlignCenter)

                    # Botón completar
                    complete_btn = QPushButton("✓")
                    complete_btn.setToolTip("Marcar como completada")
                    complete_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #4CAF50;
                            color: white;
                            border: none;
                            padding: 5px;
                            border-radius: 3px;
                            min-width: 20px;
                        }
                        QPushButton:hover {
                            background-color: #388E3C;
                        }
                    """)
                    complete_btn.clicked.connect(lambda _, t=task["descripcion"]: self.taskCompleted.emit(t))

                    # Botón eliminar
                    delete_btn = QPushButton("✕")
                    delete_btn.setToolTip("Eliminar tarea")
                    delete_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #F44336;
                            color: white;
                            border: none;
                            padding: 5px;
                            border-radius: 3px;
                             min-width: 20px;
                        }
                        QPushButton:hover {
                            background-color: #D32F2F;
                        }
                    """)
                    delete_btn.clicked.connect(lambda _, t=task["descripcion"]: self.taskDeleted.emit(t))

                    # Botón modificar (Nuevo)
                    modify_btn = QPushButton("✎") # Icono de lápiz o similar
                    modify_btn.setToolTip("Modificar tarea")
                    modify_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #ff9800; /* Naranja */
                            color: white;
                            border: none;
                            padding: 5px;
                            border-radius: 3px;
                            min-width: 20px;
                        }
                        QPushButton:hover {
                            background-color: #f57c00;
                        }
                    """)
                    # Conectar el botón modificar a una nueva señal taskModified
                    modify_btn.clicked.connect(lambda _, t=task["descripcion"]: self.taskModified.emit(t))


                    actions_layout.addWidget(complete_btn)
                    actions_layout.addWidget(delete_btn)
                    actions_layout.addWidget(modify_btn) # Añadir el botón modificar

                    self.setCellWidget(row, 4, actions_widget)

        except Exception as e:
            print(f"Error al cargar tareas: {e}")


# Nueva clase para el diálogo de agregar/modificar tarea
class TaskDialog(QDialog): # Renombrada para servir a ambos propósitos
    def __init__(self, user_manager, task_data=None, parent=None):
        super().__init__(parent)
        self.user_manager = user_manager
        self.task_data = task_data # None para agregar, dict para modificar

        if task_data:
            self.setWindowTitle("Modificar Tarea")
        else:
            self.setWindowTitle("Agregar Nueva Tarea")

        self.setMinimumSize(300, 200)

        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QLineEdit, QComboBox, QDateTimeEdit {
                background-color: #333333;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 5px;
                border-radius: 5px;
            }
             QComboBox QAbstractItemView {
                 background-color: #333333;
                 color: #ffffff;
                 selection-background-color: #007acc;
             }
            QPushButton {
                background-color: #007acc;
                color: #ffffff;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #005f99;
            }
            QDialogButtonBox QPushButton {
                 min-width: 60px;
            }
             QCalendarWidget { /* Asegura el estilo del calendario en el DateTimEdit */
                background-color: #2b2b2b;
                color: #ffffff;
                 border: 1px solid #555555;
                 border-radius: 5px;
            }
            QCalendarWidget QAbstractItemView:enabled {
                color: #ffffff;
            }
             QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: #3a3a3a;
                border-bottom: 1px solid #555555;
            }
             QCalendarWidget QToolButton {
                 background-color: #3a3a3a;
                 color: #ffffff;
                 border: none;
                 margin: 2px;
                 border-radius: 3px;
             }
             QCalendarWidget QToolButton:hover {
                 background-color: #555555;
             }
             QCalendarWidget QToolButton::menu-indicator {
                 image: none;
             }
             QCalendarWidget QSpinBox {
                 background-color: #3a3a3a;
                 color: #ffffff;
                 border: 1px solid #555555;
                 border-radius: 3px;
                 padding-right: 5px;
             }
              QCalendarWidget QSpinBox::up-button, QCalendarWidget QSpinBox::down-button {
                  background-color: #555555;
                  border-radius: 3px;
              }
             QCalendarWidget QSpinBox::up-button:hover, QCalendarWidget QSpinBox::down-button:hover {
                 background-color: #666666;
             }
              QCheckBox {
                 color: #ffffff;
             }
             QCheckBox::indicator {
                 background-color: #555555;
                 border: 1px solid #777777;
                 width: 12px;
                 height: 12px;
                 border-radius: 3px;
             }
              QCheckBox::indicator:checked {
                 background-color: #007acc;
                 border: 1px solid #005f99;
              }
        """)


        layout = QFormLayout(self)
        self.task_description_input = QLineEdit()
        self.category_input = QComboBox()
        self.category_input.setEditable(True)
        self.category_input.addItem("General")
        self.load_categories()

        self.datetime_input = QDateTimeEdit(QDateTime.currentDateTime())
        self.datetime_input.setCalendarPopup(True)
        self.datetime_input.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.datetime_input.setMinimumDateTime(QDateTime.currentDateTime().addSecs(-1))

        self.completed_checkbox = QCheckBox("Completada")


        layout.addRow("Descripción:", self.task_description_input)
        layout.addRow("Categoría:", self.category_input)
        layout.addRow("Fecha Límite:", self.datetime_input)
        layout.addRow(self.completed_checkbox)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout.addWidget(self.button_box)

        self.setLayout(layout)

        # Cargar datos si es una modificación
        if self.task_data:
            self.task_description_input.setText(self.task_data.get("descripcion", ""))
            category = self.task_data.get("categoria", "General")
            if self.category_input.findText(category) == -1:
                 self.category_input.addItem(category)
            self.category_input.setCurrentText(category)

            fecha_limite_str = self.task_data.get("fecha_limite")
            if fecha_limite_str:
                try:
                     date_time = QDateTime.strptime(fecha_limite_str, "%Y-%m-%d %H:%M:%S")
                     self.datetime_input.setDateTime(date_time)
                except ValueError:
                     pass # Ignorar si el formato de fecha es inválido


            self.completed_checkbox.setChecked(self.task_data.get("completada", False))


    def load_categories(self):
        """Carga las categorías existentes del usuario en el QComboBox"""
        try:
            ruta_archivo = f"usuarios/{self.user_manager.current_user}/tareas.json"
            if not os.path.exists(ruta_archivo):
                return

            with open(ruta_archivo, "r") as file:
                data = json.load(file)

                categorias = set()
                for tarea in data["tareas"]:
                    if "categoria" in tarea:
                         categorias.add(tarea["categoria"])

                for cat in sorted(categorias):
                    if cat != "General":
                         self.category_input.addItem(cat)

        except Exception as e:
            print(f"Error al cargar categorías para diálogo: {e}")

    def get_task_data(self):
        """Retorna los datos ingresados por el usuario"""
        description = self.task_description_input.text().strip()
        category = self.category_input.currentText().strip()
        fecha_limite = self.datetime_input.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        completed = self.completed_checkbox.isChecked()

        if not description:
            return None, None, None, None
        if not category:
             category = "general"

        return description, category, fecha_limite, completed


# Nueva ventana independiente para gestión de tareas y calendario
class TaskCalendarWindow(QMainWindow):
    def __init__(self, user_manager, main_window):
        super().__init__(main_window) # Pasa la ventana principal como padre
        self.user_manager = user_manager
        self.main_window = main_window # Guarda una referencia a la ventana principal

        self.setWindowTitle("Gestión de Tareas y Calendario")
        self.setMinimumSize(1000, 600)

        # Aplicar estilo oscuro
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
             QLabel {
                 color: #ffffff;
                 font-size: 12pt;
            }
            QFrame {
                border: 1px solid #555555;
                border-radius: 5px;
                background-color: #2b2b2b;
            }
            QGroupBox {
                border: 1px solid #555555;
                border-radius: 5px;
                margin-top: 10px;
                background-color: #2b2b2b;
                color: #ffffff;
                font-weight: bold;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 3px;
                color: #ffffff;
            }

            QLineEdit {
                background-color: #333333;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 5px;
                border-radius: 5px;
                font-size: 12pt;
            }
             QDateTimeEdit {
                background-color: #333333;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 5px;
                border-radius: 5px;
                font-size: 12pt;
            }

            QPushButton {
                background-color: #007acc;
                color: #ffffff;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                font-size: 11pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #005f99;
            }
             QPushButton#add_task_btn {
                background-color: #4CAF50; /* Verde */
             }
             QPushButton#add_task_btn:hover {
                background-color: #388E3C;
             }
             QPushButton#report_btn {
                 background-color: #ff9800; /* Naranja */
             }
             QPushButton#report_btn:hover {
                 background-color: #f57c00;
             }


            QTableWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #555555;
                gridline-color: #555555;
                font-size: 11pt;
                selection-background-color: #007acc;
            }
             QTableWidget QHeaderView::section {
                background-color: #3a3a3a;
                color: #ffffff;
                padding: 5px;
                border: 1px solid #555555;
            }
             QTableWidget::item {
                padding: 5px;
                color: #ffffff;
            }
            QTableWidget::item:selected {
                background-color: #007acc;
                color: #ffffff;
            }
            QTableWidget::item:!selected {
                 background-color: #2b2b2b;
            }
            QTableWidget::item:!selected:alternate {
                 background-color: #333333;
            }

            QTextEdit {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 5px;
                border-radius: 5px;
                font-size: 11pt;
            }

            QCalendarWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                 border: 1px solid #555555;
                 border-radius: 5px;
            }
            QCalendarWidget QAbstractItemView:enabled {
                color: #ffffff; /* Color por defecto de los números del calendario (blanco) */
            }
             QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: #3a3a3a;
                border-bottom: 1px solid #555555;
            }
             QCalendarWidget QToolButton {
                 background-color: #3a3a3a;
                 color: #ffffff;
                 border: none;
                 margin: 2px;
                 border-radius: 3px;
             }
             QCalendarWidget QToolButton:hover {
                 background-color: #555555;
             }
             QCalendarWidget QToolButton::menu-indicator {
                 image: none;
             }
             QCalendarWidget QSpinBox {
                 background-color: #3a3a3a;
                 color: #ffffff;
                 border: 1px solid #555555;
                 border-radius: 3px;
                 padding-right: 5px;
             }
              QCalendarWidget QSpinBox::up-button, QCalendarWidget QSpinBox::down-button {
                  background-color: #555555;
                  border-radius: 3px;
              }
             QCalendarWidget QSpinBox::up-button:hover, QCalendarWidget QSpinBox::down-button:hover {
                 background-color: #666666;
             }

            QTabWidget::pane {
                border: 1px solid #555555;
                background-color: #2b2b2b;
                border-radius: 5px;
            }
            QTabBar::tab {
                background: #333333;
                color: #ffffff;
                padding: 8px 15px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                margin-right: 1px;
            }
            QTabBar::tab:selected {
                background: #007acc;
                color: #ffffff;
            }
             QTabBar::tab:hover {
                background: #005f99;
            }

            QSplitter::handle {
                background-color: #555555;
            }
             QSplitter::handle:hover {
                 background-color: #007acc;
             }

             QCheckBox {
                 color: #ffffff;
             }
             QCheckBox::indicator {
                 background-color: #555555;
                 border: 1px solid #777777;
                 width: 12px;
                 height: 12px;
                 border-radius: 3px;
             }
              QCheckBox::indicator:checked {
                 background-color: #007acc;
                 border: 1px solid #005f99;
              }

             QComboBox {
                 background-color: #333333;
                 color: #ffffff;
                 border: 1px solid #555555;
                 padding: 5px;
                 border-radius: 5px;
                 font-size: 11pt;
             }
             QComboBox::drop-down {
                 border: none;
             }
             QComboBox::down-arrow {
                 /* Puedes necesitar una imagen de flecha blanca o estilizar con fuente */
                 /* image: url(down_arrow_white.png); */
                 width: 10px;
                 height: 10px;
             }
              QComboBox QAbstractItemView {
                 background-color: #333333;
                 color: #ffffff;
                 selection-background-color: #007acc;
             }
             QPushButton#back_button { /* Estilo para el botón de volver */
                 background-color: #555555;
             }
             QPushButton#back_button:hover {
                 background-color: #777777;
             }

        """)

        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        # --- Controles de la ventana de tareas ---
        control_frame = QFrame()
        control_layout = QHBoxLayout(control_frame)

        # Mover la definición de show_add_task_dialog antes de __init__

        add_task_btn = QPushButton("Agregar Tarea Nueva")
        add_task_btn.setObjectName("add_task_btn")
        add_task_btn.clicked.connect(self.show_add_task_dialog) # Ahora sí se conecta correctamente


        # Botón para generar reporte mensual
        report_btn = QPushButton("Generar Reporte Mensual")
        report_btn.setObjectName("report_btn")
        report_btn.clicked.connect(self.generate_monthly_report)


        # Botón para volver a la ventana principal
        back_to_main_btn = QPushButton("Volver a Principal")
        back_to_main_btn.setObjectName("back_button") # Asigna objectName para estilo
        back_to_main_btn.clicked.connect(self.show_main_window)


        control_layout.addWidget(add_task_btn)
        control_layout.addWidget(report_btn)
        control_layout.addStretch() # Espacio flexible
        control_layout.addWidget(back_to_main_btn)


        # --- Contenido principal de la ventana de tareas (Tabla y Paneles) ---
        content_splitter = QSplitter(Qt.Horizontal)

        # Panel izquierdo (Tabla de Tareas)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        tasks_label = QLabel("Todas Mis Tareas")
        tasks_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.tasks_table = TasksTable()
        # Conectar señales de la tabla a métodos de esta ventana
        self.tasks_table.taskCompleted.connect(self.complete_task)
        self.tasks_table.taskDeleted.connect(self.delete_task)
        self.tasks_table.taskModified.connect(self.modify_task) # Conectar nueva señal

        left_layout.addWidget(tasks_label)
        left_layout.addWidget(self.tasks_table)


        # Panel derecho (Calendario y Categorías)
        right_panel = QTabWidget()
        self.right_panel = right_panel # Guarda referencia al QTabWidget para cambiar pestañas

        # Pestaña del Calendario
        calendar_widget = QWidget()
        calendar_layout = QVBoxLayout(calendar_widget)
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)

        # Formato de texto por defecto para el calendario (blanco)
        default_format = QTextCharFormat()
        default_format.setForeground(QColor(255, 255, 255)) # Blanco
        # Aplicar a todas las fechas (esto se hace por defecto, pero lo aseguramos)
        self.calendar.setDateTextFormat(QDate(), default_format)

        calendar_tasks_label = QLabel("Tareas en fecha seleccionada:")
        self.calendar_tasks_list = QTextEdit()
        self.calendar_tasks_list.setReadOnly(True)

        self.calendar.clicked.connect(self.update_calendar_tasks)

        calendar_layout.addWidget(self.calendar)
        calendar_layout.addWidget(calendar_tasks_label)
        calendar_layout.addWidget(self.calendar_tasks_list)


        # Pestaña de Categorías
        categories_widget = QWidget()
        categories_layout = QVBoxLayout(categories_widget)
        categories_label = QLabel("Filtrar por categoría:")
        self.category_combo = QComboBox()
        self.category_combo.addItem("Todas")
        self.category_tasks_list = QTextEdit()
        self.category_tasks_list.setReadOnly(True)
        self.category_combo.currentTextChanged.connect(self.filter_by_category)

        categories_layout.addWidget(categories_label)
        categories_layout.addWidget(self.category_combo)
        categories_layout.addWidget(self.category_tasks_list)

        right_panel.addTab(calendar_widget, "Calendario")
        right_panel.addTab(categories_widget, "Categorías")


        content_splitter.addWidget(left_panel)
        content_splitter.addWidget(right_panel)
        content_splitter.setSizes([600, 400]) # Distribución inicial


        # Añadir todo al layout principal de la ventana de tareas
        main_layout.addWidget(control_frame)
        main_layout.addWidget(content_splitter, 1)


        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Cargar datos iniciales al abrir la ventana
        self.refresh_tasks()


    def show_main_window(self):
        """Muestra la ventana principal y oculta esta ventana"""
        self.main_window.show()
        self.hide()


    def refresh_tasks(self):
        """Actualiza la tabla de tareas y el calendario en esta ventana"""
        if self.user_manager.current_user:
            self.tasks_table.load_tasks(self.user_manager.current_user)
            self.update_calendar_tasks() # Actualizar también las tareas del calendario
            self.update_categories()
            # Mantener el filtro de categoría si no está en "Todas"
            if self.category_combo.currentText() != "Todas":
                self.filter_by_category(self.category_combo.currentText())


    def update_calendar_tasks(self):
        """Actualiza las tareas para la fecha seleccionada en el calendario y resalta días con pendientes"""
        selected_date = self.calendar.selectedDate().toString("yyyy-MM-dd")

        try:
            ruta_archivo = f"usuarios/{self.user_manager.current_user}/tareas.json"
            if not os.path.exists(ruta_archivo):
                self.calendar_tasks_list.setText("No hay tareas para mostrar")
                 # Asegurarse de restablecer el formato de todos los días a blanco si no hay tareas
                default_format = QTextCharFormat()
                default_format.setForeground(QColor(255, 255, 255)) # Blanco
                current_date = QDate(self.calendar.yearShown(), self.calendar.monthShown(), 1)
                while current_date.month() == self.calendar.monthShown():
                     self.calendar.setDateTextFormat(current_date, default_format)
                     current_date = current_date.addDays(1)
                return

            with open(ruta_archivo, "r") as file:
                data = json.load(file)
                all_tasks = data.get("tareas", [])

                # Resetear el formato de texto para todos los días del mes visible a blanco
                default_format = QTextCharFormat()
                default_format.setForeground(QColor(255, 255, 255)) # Blanco
                first_day_of_month = QDate(self.calendar.yearShown(), self.calendar.monthShown(), 1)
                current_day = first_day_of_month
                # Iterar sobre los días del mes visible y los días de las semanas incompletas del mes anterior/siguiente que se muestran
                # Para simplificar, reseteamos un rango fijo de días alrededor del mes actual
                # Un enfoque más preciso sería iterar sobre las fechas visibles del widget
                # Por ahora, iteremos sobre un rango amplio alrededor del mes actual
                start_date_reset = first_day_of_month.addDays(-10) # 10 días antes del inicio del mes
                end_date_reset = first_day_of_month.addDays(45) # 45 días desde el inicio del mes (cubre ~6 semanas)

                current_day_reset = start_date_reset
                while current_day_reset <= end_date_reset:
                    self.calendar.setDateTextFormat(current_day_reset, default_format)
                    current_day_reset = current_day_reset.addDays(1)


                # Identificar días con tareas pendientes y resaltar
                red_format = QTextCharFormat()
                red_format.setForeground(QColor(255, 0, 0)) # Rojo
                days_with_pending_tasks = set()

                for tarea in all_tasks:
                    if tarea.get("fecha_limite") and not tarea.get("completada"):
                        try:
                            deadline_date_str = tarea["fecha_limite"].split(" ")[0] # Obtener solo la parte de la fecha
                            deadline_date = QDate.fromString(deadline_date_str, "yyyy-MM-dd")
                            days_with_pending_tasks.add(deadline_date) # Añadir la fecha completa

                        except ValueError:
                            print(f"Advertencia: Tarea con formato de fecha inválido para resaltar: {tarea.get('descripcion')}")


                # Aplicar formato rojo a los días con tareas pendientes
                for date in days_with_pending_tasks:
                     self.calendar.setDateTextFormat(date, red_format)


                # Filtrar tareas para la fecha seleccionada en el área de texto
                tareas_fecha = []
                for tarea in all_tasks:
                    if tarea.get("fecha_limite") and tarea["fecha_limite"].startswith(selected_date):
                        tareas_fecha.append(tarea)


                if tareas_fecha:
                    text = f"Tareas para {selected_date}:\n\n"
                    tareas_fecha.sort(key=lambda x: x.get("fecha_limite", ""))

                    for tarea in tareas_fecha:
                        estado = "✓ " if tarea.get("completada") else "□ "
                        hora = tarea["fecha_limite"].split(" ")[1][:5] if " " in tarea["fecha_limite"] and len(tarea["fecha_limite"].split(" ")[1]) >= 5 else ""
                        text += f"{estado}{hora} - {tarea['descripcion']} ({tarea['categoria']})\n"

                    self.calendar_tasks_list.setText(text)
                else:
                    self.calendar_tasks_list.setText(f"No hay tareas para el {selected_date}")


        except Exception as e:
            self.calendar_tasks_list.setText(f"Error al cargar tareas: {e}")
            print(f"Error detallado al actualizar calendario: {e}")

    def update_categories(self):
        """Actualiza la lista de categorías disponibles"""
        try:
            ruta_archivo = f"usuarios/{self.user_manager.current_user}/tareas.json"
            if not os.path.exists(ruta_archivo):
                return

            with open(ruta_archivo, "r") as file:
                data = json.load(file)

                categorias = set()
                for tarea in data["tareas"]:
                    if "categoria" in tarea:
                         categorias.add(tarea["categoria"])

                current = self.category_combo.currentText()

                self.category_combo.clear()
                self.category_combo.addItem("Todas")
                for cat in sorted(categorias):
                    self.category_combo.addItem(cat)

                index = self.category_combo.findText(current)
                if index >= 0:
                    self.category_combo.setCurrentIndex(index)

        except Exception as e:
            print(f"Error al actualizar categorías: {e}")

    def filter_by_category(self, category):
        """Filtra tareas por categoría"""
        if category == "Todas":
            # Si se selecciona "Todas", cargamos todas las tareas en la tabla
            self.refresh_tasks() # Llama a refresh_tasks para mostrar todas las tareas en la tabla

            # Y limpia el área de texto o muestra un mensaje
            self.category_tasks_list.setText("Selecciona una categoría específica para ver sus tareas aquí.")
            return

        try:
            # Mostrar solo las tareas de esa categoría en la tabla
            ruta_archivo = f"usuarios/{self.user_manager.current_user}/tareas.json"
            if not os.path.exists(ruta_archivo):
                 self.tasks_table.setRowCount(0) # Limpiar tabla si no hay archivo
                 self.category_tasks_list.setText(f"No hay tareas en la categoría '{category}'.")
                 return

            with open(ruta_archivo, "r") as file:
                 data = json.load(file)
                 all_tasks = data.get("tareas", [])

                 # Filtrar tareas para mostrar en la tabla
                 filtered_tasks = [t for t in all_tasks if t.get("categoria", "").lower() == category.lower()]

                 # Limpiar la tabla y cargar solo las tareas filtradas
                 self.tasks_table.setRowCount(0)
                 for row, task in enumerate(filtered_tasks):
                    self.tasks_table.insertRow(row)
                    self.tasks_table.setItem(row, 0, QTableWidgetItem(task["descripcion"]))
                    self.tasks_table.setItem(row, 1, QTableWidgetItem(task["categoria"]))
                    fecha = "No establecida" if not task.get("fecha_limite") else task["fecha_limite"]
                    self.tasks_table.setItem(row, 2, QTableWidgetItem(fecha))
                    estado = "Completada" if task.get("completada") else "Pendiente"
                    estado_item = QTableWidgetItem(estado)
                    if task.get("completada"):
                        estado_item.setBackground(QColor(50, 150, 50))
                    else:
                        estado_item.setBackground(QColor(150, 50, 50))
                    estado_item.setForeground(QColor(255, 255, 255))
                    self.tasks_table.setItem(row, 3, estado_item)

                    # Recrear botones de acción (simplificado, deberías copiar la lógica de load_tasks)
                    actions_widget = QWidget()
                    actions_layout = QHBoxLayout(actions_widget)
                    actions_layout.setContentsMargins(0, 0, 0, 0)
                    actions_layout.setAlignment(Qt.AlignCenter)
                    complete_btn = QPushButton("✓")
                    delete_btn = QPushButton("✕")
                    modify_btn = QPushButton("✎")
                    actions_layout.addWidget(complete_btn)
                    actions_layout.addWidget(delete_btn)
                    actions_layout.addWidget(modify_btn)
                    self.tasks_table.setCellWidget(row, 4, actions_widget)
                    # Conectar señales de los nuevos botones
                    complete_btn.clicked.connect(lambda _, t=task["descripcion"]: self.complete_task(t))
                    delete_btn.clicked.connect(lambda _, t=task["descripcion"]: self.delete_task(t))
                    modify_btn.clicked.connect(lambda _, t=task["descripcion"]: self.modify_task(t))


            # Mostrar las descripciones en el área de texto (opcional, ya están en la tabla)
            response = mostrar_tareas_por_categoria(category, self.user_manager.current_user)
            self.category_tasks_list.setText(response)

        except Exception as e:
            self.category_tasks_list.setText(f"Error al filtrar por categoría: {e}")
            print(f"Error al filtrar por categoría: {e}")


    def show_add_task_dialog(self):
        """Muestra el diálogo para agregar una nueva tarea."""
        if not self.user_manager.current_user:
             QMessageBox.warning(self, "Error", "Debes iniciar sesión para agregar tareas.")
             return

        dialog = TaskDialog(self.user_manager, parent=self) # Usa TaskDialog
        if dialog.exec_() == QDialog.Accepted:
            description, category, fecha_limite, completed = dialog.get_task_data() # Obtiene también el estado completado
            if description:
                response = agregar_tarea(description, category, fecha_limite, self.user_manager.current_user, completed=completed) # Pasar estado completado
                # No hay área de respuesta en esta ventana, podrías mostrar un QMessageBox o imprimir en consola
                print(f"Respuesta agregar tarea: {response}")
                self.refresh_tasks()
            else:
                QMessageBox.warning(self, "Entrada Inválida", "La descripción de la tarea no puede estar vacía.")

    def complete_task(self, task_name):
        """Marca una tarea como completada"""
        response = marcar_como_completada(task_name, self.user_manager.current_user)
        print(f"Respuesta completar tarea: {response}")
        self.refresh_tasks() # Refrescar la vista después de completar

    def delete_task(self, task_name):
        """Elimina una tarea"""
        confirmation = QMessageBox.question(
            self, "Confirmar eliminación",
            f"¿Estás seguro de que quieres eliminar la tarea '{task_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirmation == QMessageBox.Yes:
            response = eliminar_tarea(task_name, self.user_manager.current_user)
            print(f"Respuesta eliminar tarea: {response}")
            self.refresh_tasks() # Refrescar la vista después de eliminar


    def modify_task(self, task_name):
        """Muestra el diálogo para modificar una tarea existente."""
        if not self.user_manager.current_user:
             QMessageBox.warning(self, "Error", "Debes iniciar sesión para modificar tareas.")
             return

        task_to_modify = None
        try:
            ruta_archivo = f"usuarios/{self.user_manager.current_user}/tareas.json"
            if os.path.exists(ruta_archivo):
                with open(ruta_archivo, "r") as file:
                    data = json.load(file)
                    for tarea in data.get("tareas", []):
                        if tarea.get("descripcion", "").lower() == task_name.lower():
                            task_to_modify = tarea
                            break
        except Exception as e:
             print(f"Error al buscar tarea para modificar: {e}")
             QMessageBox.critical(self, "Error", "No se pudo obtener la información de la tarea para modificar.")
             return


        if task_to_modify:
            dialog = TaskDialog(self.user_manager, task_data=task_to_modify, parent=self)
            if dialog.exec_() == QDialog.Accepted:
                new_description, new_category, new_fecha_limite, new_completed = dialog.get_task_data()
                if new_description:
                    # Llama a la función modificar_tarea con los datos originales y los nuevos
                    response = modificar_tarea(
                        task_name, # Descripción original
                        {"descripcion": new_description,
                         "categoria": new_category,
                         "fecha_limite": new_fecha_limite,
                         "completada": new_completed
                        },
                        self.user_manager.current_user
                    )
                    print(f"Respuesta modificar tarea: {response}")
                    self.refresh_tasks() # Refrescar la vista después de modificar
                else:
                    QMessageBox.warning(self, "Entrada Inválida", "La descripción de la tarea no puede estar vacía.")
        else:
            QMessageBox.warning(self, "Tarea no encontrada", f"No se encontró la tarea '{task_name}' para modificar.")


    def generate_monthly_report(self):
        """Solicita año y mes y genera el reporte mensual de tareas (en la ventana de tareas)."""
        if not self.user_manager.current_user:
             QMessageBox.warning(self, "Error", "Debes iniciar sesión para generar reportes.")
             return

        year, ok_year = QInputDialog.getInt(self, "Reporte Mensual", "Introduce el año:", datetime.now().year, 1900, 2100, 1)
        if not ok_year:
            return

        months = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        month, ok_month = QInputDialog.getItem(self, "Reporte Mensual", "Selecciona el mes:", months, datetime.now().month - 1, False)

        if not ok_month:
            return

        month_number = months.index(month) + 1

        report = generar_reporte_mensual(self.user_manager.current_user, year, month_number)

        # Mostrar el reporte en una QMessageBox
        QMessageBox.information(self, f"Reporte de Tareas ({months[month_number-1]} de {year})", report)



class MainWindow(QMainWindow):
    """Ventana principal de la aplicación (Panel de control/Comandos)"""
    def __init__(self):
        super().__init__()

        self.user_manager = UserManager()
        self.mode = "text"

        self.setWindowTitle("Asistente Principal - VoceTasks")
        self.setMinimumSize(600, 400)

        # Instancia de la ventana de tareas (inicialmente no visible)
        self.task_calendar_window = None # Se creará al hacer clic en el botón


        self.show_login()

        if self.user_manager.current_user:
            self.init_ui()
            self.show() # Mostrar la ventana principal después del login


            # Configurar reconocimiento de voz si no hay error de importación
            try:
                self.recognizer_thread = RecognizerThread()
                self.recognizer_thread.textDetected.connect(self.on_voice_command)
                self.recognizer_thread.listenStateChanged.connect(self.update_mic_status)
            except ImportError:
                print("Advertencia: speech_recognition no instalado. El modo de voz no estará disponible.")
                self.mode = "text"
                self.update_interface_for_mode()
                mic_btn_widget = self.findChild(QPushButton, "mic_btn")
                if mic_btn_widget:
                     mic_btn_widget.setEnabled(False)
                     mic_btn_widget.setStyleSheet("background-color: #f0f0f0;")
                self.text_mode_btn.setChecked(True)
                self.voice_mode_btn.setEnabled(False)


            # Timer de notificaciones (se mantiene en la ventana principal)
            self.notification_timer = QTimer(self)
            self.notification_timer.setInterval(60000)
            self.notification_timer.timeout.connect(self.check_upcoming_tasks)
            self.notification_timer.start()
            self.checked_tasks_for_notification = set()
            self.check_upcoming_tasks(initial_check=True)


    def show_login(self):
        """Muestra el diálogo de inicio de sesión"""
        dialog = LoginDialog(self.user_manager)
        result = dialog.exec_()

        if result != QDialog.Accepted or not self.user_manager.current_user:
            QMessageBox.critical(self, "Error", "Debes iniciar sesión para usar la aplicación")
            sys.exit()


    def init_ui(self):
        """Inicializa la interfaz de usuario de la ventana principal"""
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QLabel {
                 color: #ffffff;
                 font-size: 12pt;
            }
            QFrame {
                border: 1px solid #555555;
                border-radius: 5px;
                background-color: #2b2b2b;
            }
            QGroupBox {
                border: 1px solid #555555;
                border-radius: 5px;
                margin-top: 10px;
                background-color: #2b2b2b;
                color: #ffffff;
                font-weight: bold;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 3px;
                color: #ffffff;
            }

            QLineEdit {
                background-color: #333333;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 5px;
                border-radius: 5px;
                font-size: 12pt;
            }
            QPushButton {
                background-color: #007acc;
                color: #ffffff;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                font-size: 11pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #005f99;
            }
             QPushButton#mic_btn {
                background-color: #ff6b6b;
                min-width: 30px;
                min-height: 30px;
                border-radius: 15px;
            }
            QPushButton#mic_btn:hover {
                background-color: #ff4c4c;
            }
            QPushButton#manage_tasks_btn { /* Estilo para el botón de gestionar tareas */
                 background-color: #ff9800; /* Naranja */
            }
             QPushButton#manage_tasks_btn:hover {
                 background-color: #f57c00;
             }
             QPushButton#report_btn_main { /* Estilo específico para el botón de reporte en la ventana principal */
                 background-color: #4CAF50; /* Verde */
            }
             QPushButton#report_btn_main:hover {
                 background-color: #388E3C; /* Verde más oscuro */
             }


            QTextEdit {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 5px;
                border-radius: 5px;
                font-size: 11pt;
            }
             QCheckBox {
                 color: #ffffff;
             }
             QCheckBox::indicator {
                 background-color: #555555;
                 border: 1px solid #777777;
                 width: 12px;
                 height: 12px;
                 border-radius: 3px;
             }
              QCheckBox::indicator:checked {
                 background-color: #007acc;
                 border: 1px solid #005f99;
              }


        """)

        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        # --- CABECERA ---
        header_frame = QFrame()
        header_layout = QHBoxLayout(header_frame)

        user_data = self.user_manager.get_user_data()
        user_label = QLabel(f"Hola, {user_data['name']}!")
        user_label.setFont(QFont("Arial", 14, QFont.Bold))
        user_label.setStyleSheet("color: #ffffff;")

        mode_group = QGroupBox("Modo de entrada")
        mode_layout = QHBoxLayout()
        self.text_mode_btn = QCheckBox("Texto")
        self.voice_mode_btn = QCheckBox("Voz")

        if self.user_manager.get_silent_mode():
            self.text_mode_btn.setChecked(True)
            self.voice_mode_btn.setChecked(False)
            self.mode = "text"
        else:
            self.voice_mode_btn.setChecked(True)
            self.text_mode_btn.setChecked(False)
            self.mode = "voice"

        self.text_mode_btn.clicked.connect(lambda: self.change_mode("text"))
        self.voice_mode_btn.clicked.connect(lambda: self.change_mode("voice"))
        mode_layout.addWidget(self.text_mode_btn)
        mode_layout.addWidget(self.voice_mode_btn)
        mode_group.setLayout(mode_layout)

        # Botón para abrir la ventana de gestión de tareas y calendario
        self.manage_tasks_btn = QPushButton("Gestionar Tareas y Calendario")
        self.manage_tasks_btn.setObjectName("manage_tasks_btn")
        self.manage_tasks_btn.clicked.connect(self.show_task_calendar_window)


        # Botón para Reporte Mensual (en la ventana principal)
        self.report_btn_main = QPushButton("Generar Reporte Mensual") # Renombrado para diferenciar
        self.report_btn_main.setObjectName("report_btn_main")
        self.report_btn_main.clicked.connect(self.generate_monthly_report)


        # Botón de cerrar sesión
        logout_btn = QPushButton("Cerrar Sesión")
        logout_btn.clicked.connect(self.handle_logout)

        header_layout.addWidget(user_label)
        header_layout.addWidget(mode_group)
        header_layout.addStretch()
        header_layout.addWidget(self.manage_tasks_btn) # Añadir el botón para ir a la ventana de tareas
        header_layout.addWidget(self.report_btn_main) # Añadir botón de reporte de la ventana principal
        header_layout.addWidget(logout_btn)


        # --- PANEL DE COMANDOS ---
        command_frame = QFrame()
        command_frame.setObjectName("commandFrame")
        command_layout = QHBoxLayout(command_frame)

        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Escribe un comando o pregúntame algo...")
        self.command_input.returnPressed.connect(self.process_command)

        self.mic_btn = QPushButton("🎤")
        self.mic_btn.setObjectName("mic_btn")
        self.mic_btn.setToolTip("Hablar (mantener presionado)")
        self.mic_btn.setCheckable(True)
        self.mic_btn.pressed.connect(self.start_listening)
        self.mic_btn.released.connect(self.stop_listening)

        command_layout.addWidget(self.command_input)
        command_layout.addWidget(self.mic_btn)

        # --- PANEL DE RESPUESTA ---
        self.response_area = QTextEdit()
        self.response_area.setReadOnly(True)
        self.response_area.setPlaceholderText("Aquí aparecerán mis respuestas...")
        self.response_area.setMinimumHeight(100)

        # Añadir todo al layout principal
        main_layout.addWidget(header_frame)
        main_layout.addStretch(1) # Espacio flexible en el centro
        main_layout.addWidget(command_frame)
        main_layout.addWidget(self.response_area)

        self.setCentralWidget(central_widget)

        # Asegurarse de que el modo de interfaz inicial sea correcto
        self.update_interface_for_mode()


    def show_task_calendar_window(self):
        """Crea y muestra la ventana de Gestión de Tareas y Calendario"""
        # Crear la ventana de tareas/calendario si no existe
        if self.task_calendar_window is None:
             # Pasa self (la instancia de MainWindow) a la ventana de tareas
             self.task_calendar_window = TaskCalendarWindow(self.user_manager, self)

        # Muestra la ventana de tareas y oculta la principal
        self.task_calendar_window.show()
        self.hide()


    def show_main_window(self):
        """Muestra la ventana principal (esta ventana) y oculta la de tareas"""
        self.show()
        if self.task_calendar_window:
            self.task_calendar_window.hide()

    # --- Métodos relacionados con comandos de voz/texto (se quedan aquí) ---
    def handle_logout(self):
        """Maneja el cierre de sesión"""
        result = QMessageBox.question(self, "Cerrar Sesión",
                                     "¿Estás seguro de que quieres cerrar sesión?",
                                     QMessageBox.Yes | QMessageBox.No)

        if result == QMessageBox.Yes:
            self.user_manager.logout()
            if hasattr(self, 'notification_timer') and self.notification_timer.isActive():
                self.notification_timer.stop()

            self.close()
            # Reabrir la ventana de login
            # Aquí podrías decidir si quieres mostrar de nuevo el LoginDialog
            # o simplemente salir de la aplicación. Salir es más limpio por ahora.
            # Si quisieras reloguear, necesitarías crear una nueva QApplication o manejar el estado.
            sys.exit() # Salir de la aplicación


    def change_mode(self, mode):
        # ... (código existente) ...
        if mode == "voice" and not hasattr(self, 'recognizer_thread'):
             QMessageBox.warning(self, "Modo no disponible", "El modo de voz no está disponible. Asegúrate de tener 'speech_recognition' instalado.")
             self.text_mode_btn.setChecked(True)
             self.voice_mode_btn.setChecked(False)
             self.mode = "text"
             self.user_manager.update_user_preference("modo_silencioso", True)
             self.update_interface_for_mode()
             return

        self.mode = mode

        if mode == "text":
            self.text_mode_btn.setChecked(True)
            self.voice_mode_btn.setChecked(False)
            self.user_manager.update_user_preference("modo_silencioso", True)
            if hasattr(self, 'recognizer_thread') and self.recognizer_thread.isRunning():
                 self.recognizer_thread.running = False

        else: # mode == "voice"
            self.text_mode_btn.setChecked(False)
            self.voice_mode_btn.setChecked(True)
            self.user_manager.update_user_preference("modo_silencioso", False)

        self.update_interface_for_mode()

    def update_interface_for_mode(self):
        # ... (código existente) ...
        if self.mode == "text":
            mic_btn_widget = self.findChild(QPushButton, "mic_btn")
            if mic_btn_widget:
                 mic_btn_widget.setEnabled(False)
                 mic_btn_widget.setStyleSheet("background-color: #f0f0f0;")
        else: # mode == "voice"
            if hasattr(self, 'recognizer_thread'):
                 mic_btn_widget = self.findChild(QPushButton, "mic_btn")
                 if mic_btn_widget:
                     mic_btn_widget.setEnabled(True)
                     mic_btn_widget.setStyleSheet("""
                            QPushButton#mic_btn {
                                background-color: #ff6b6b;
                                color: white;
                                border: none;
                                padding: 5px;
                                border-radius: 15px;
                                min-width: 30px;
                                min-height: 30px;
                            }
                            QPushButton#mic_btn:hover {
                                background-color: #ff4c4c;
                            }
                        """)
            else:
                 mic_btn_widget = self.findChild(QPushButton, "mic_btn")
                 if mic_btn_widget:
                      mic_btn_widget.setEnabled(False)
                      mic_btn_widget.setStyleSheet("background-color: #f0f0f0;")


    def start_listening(self):
        # ... (código existente) ...
        if self.mode == "voice" and hasattr(self, 'recognizer_thread') and not self.recognizer_thread.isRunning():
             self.show_response("Escuchando...")
             self.recognizer_thread.running = True
             self.recognizer_thread.start()

    def stop_listening(self):
        # ... (código existente) ...
        if self.mode == "voice" and hasattr(self, 'recognizer_thread') and not self.recognizer_thread.isRunning():
             self.update_mic_status(False)

    def update_mic_status(self, is_listening):
        # ... (código existente) ...
        if self.mode == "voice":
            mic_btn_widget = self.findChild(QPushButton, "mic_btn")
            if mic_btn_widget:
                if is_listening:
                    mic_btn_widget.setStyleSheet("""
                        QPushButton#mic_btn {
                            background-color: #ff9800;
                            color: white;
                            border: none;
                            padding: 5px;
                            border-radius: 15px;
                            min-width: 30px;
                            min-height: 30px;
                        }
                    """)
                else:
                    mic_btn_widget.setStyleSheet("""
                        QPushButton#mic_btn {
                            background-color: #ff6b6b;
                            color: white;
                            border: none;
                            padding: 5px;
                            border-radius: 15px;
                            min-width: 30px;
                            min-height: 30px;
                        }
                        QPushButton#mic_btn:hover {
                            background-color: #ff4c4c;
                        }
                    """)
                    self.show_response("Procesando...")

    def on_voice_command(self, text):
        # ... (código existente) ...
        self.command_input.setText(text)
        self.process_command()

    def process_command(self):
        # ... (código existente) ...
        command = self.command_input.text().strip()
        if not command:
            return

        self.response_area.append(f"<b>Tú:</b> {command}")

        try:
            from main import interpretar_comando
            action = interpretar_comando(command)
            response = self.execute_action(action, command)

            # Corregido: Eliminado el paréntesis extra al final
            if self.mode == "voice" and response != "Procesando...":
                 try:
                     from utils import hablar
                     hablar(response)
                 except ImportError:
                      print("Advertencia: pyttsx3 no instalado. La síntesis de voz no estará disponible.")

        except ImportError:
             response = "Error: No se pudo importar el módulo 'main'. Asegúrate de que 'main.py' existe y no tiene errores."
             self.mode = "text"
             self.update_interface_for_mode()


        self.show_response(response)
        self.command_input.clear()

        # Si un comando afecta las tareas, refrescar la ventana de tareas si está abierta
        task_modifying_actions = ['agregar', 'eliminar', 'modificar', 'recordatorio', 'completar', 'categoria']
        action_type = action[0] if isinstance(action, tuple) else action

        if action_type in task_modifying_actions:
             if self.task_calendar_window and self.task_calendar_window.isVisible():
                  self.task_calendar_window.refresh_tasks() # Llama a refresh_tasks de la ventana de tareas


    def execute_action(self, action, original_command):
        """Ejecuta la acción correspondiente al comando interpretado (solo comandos de la ventana principal)"""
        email = self.user_manager.current_user

        # Acciones que podrían abrir la ventana de tareas/calendario
        if action in ['mostrar', 'ver_calendario_local'] or (isinstance(action, tuple) and action[0] == 'mostrar_categoria') or (isinstance(action, tuple) and action[0] == 'formato_calendario'):
            self.show_task_calendar_window()
            # Opcionalmente, puedes hacer que la ventana de tareas vaya a la pestaña correcta
            # if action == 'ver_calendario_local' or (isinstance(action, tuple) and action[0] == 'formato_calendario'):
            #     self.task_calendar_window.right_panel.setCurrentIndex(0) # Ir a pestaña Calendario
            # elif isinstance(action, tuple) and action[0] == 'mostrar_categoria':
            #      self.task_calendar_window.right_panel.setCurrentIndex(1) # Ir a pestaña Categorías
            #      self.task_calendar_window.category_combo.setCurrentText(action[1]) # Seleccionar categoría


            if action == 'mostrar':
                return "Abriendo ventana de gestión de tareas..."
            elif action == 'ver_calendario_local':
                 return "Abriendo calendario de tareas..."
            elif isinstance(action, tuple) and action[0] == 'mostrar_categoria':
                 return f"Abriendo ventana de gestión y filtrando por categoría '{action[1]}'"
            elif isinstance(action, tuple) and action[0] == 'formato_calendario':
                 return "Abriendo ventana de gestión en vista calendario..."


        # Comando de ayuda (se queda en la ventana principal)
        elif action == 'ayuda':
            try:
                from main import mostrar_ayuda
                return mostrar_ayuda()
            except ImportError:
                return "No se pudo cargar la ayuda. Asegúrate de que 'main.py' existe."

        # Comando de reporte mensual (se queda en la ventana principal, aunque también está en la de tareas)
        elif isinstance(action, tuple) and action[0] == 'generar_reporte':
             año = action[1]
             mes = action[2]
             return generar_reporte_mensual(email, año, mes) # Llama a la función y muestra en response_area


        # Otros comandos que modifican tareas se manejan (y muestran respuesta) en la ventana de tareas
        # si se activa desde allí. Si se activan desde aquí (vía voz/texto), la respuesta
        # se mostrará aquí, y la ventana de tareas (si está abierta) se refrescará.
        elif isinstance(action, tuple) and action[0] in ['agregar', 'eliminar', 'modificar', 'recordatorio', 'completar', 'categoria']:
            # Estos comandos deberían ser procesados por la ventana de tareas idealmente.
            # Si llegan aquí, solo mostramos una indicación de que la ventana de tareas es la que maneja esto.
            return f"Comando '{original_command}' procesado. Por favor, usa la ventana de Gestión de Tareas para estas acciones o consulta los resultados allí."


        # Comando no reconocido
        return f"No he podido entender el comando: '{original_command}'\nPrueba con 'ayuda' para ver los comandos disponibles."

    def show_response(self, response):
        """Muestra respuesta en el área designada de MainWindow"""
        self.response_area.append(f"<b>Asistente:</b> {response}")
        self.response_area.verticalScrollBar().setValue(
            self.response_area.verticalScrollBar().maximum()
        )


    def generate_monthly_report(self):
        """Solicita año y mes y genera el reporte mensual de tareas (en la ventana principal)."""
        if not self.user_manager.current_user:
             QMessageBox.warning(self, "Error", "Debes iniciar sesión para generar reportes.")
             return

        year, ok_year = QInputDialog.getInt(self, "Reporte Mensual", "Introduce el año:", datetime.now().year, 1900, 2100, 1)
        if not ok_year:
            return

        months = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"] # Corregido "Septiembre" duplicado
        month, ok_month = QInputDialog.getItem(self, "Reporte Mensual", "Selecciona el mes:", months, datetime.now().month - 1, False)

        if not ok_month:
            return

        month_number = months.index(month) + 1

        report = generar_reporte_mensual(self.user_manager.current_user, year, month_number)

        # Mostrar el reporte en el área de respuesta de la ventana principal
        self.show_response(f"Reporte de Tareas ({months[month_number-1]} de {year}):\n\n{report}")


    def check_upcoming_tasks(self, initial_check=False):
        """Verifica tareas próximas y muestra notificaciones (se queda en la ventana principal)."""
        if not self.user_manager.current_user:
            return

        try:
            ruta_archivo = f"usuarios/{self.user_manager.current_user}/tareas.json"
            if not os.path.exists(ruta_archivo):
                return

            with open(ruta_archivo, "r") as file:
                data = json.load(file)
                tareas = data.get("tareas", [])

                now = datetime.now()
                notification_threshold = now + timedelta(hours=2)
                past_threshold = now - timedelta(minutes=30)

                for tarea in tareas:
                    if tarea.get("fecha_limite") and not tarea.get("completada"):
                        try:
                            deadline_dt = datetime.strptime(tarea["fecha_limite"], "%Y-%m-%d %H:%M:%S")

                            if (now < deadline_dt <= notification_threshold) or (not initial_check and past_threshold <= deadline_dt <= now) and tarea["descripcion"] not in self.checked_tasks_for_notification:

                                time_diff = deadline_dt - now
                                if time_diff > timedelta(0):
                                    days = time_diff.days
                                    hours, remainder = divmod(time_diff.seconds, 3600)
                                    minutes, _ = divmod(remainder, 60)
                                    time_until = f"en {days} días, {hours} horas y {minutes} minutos"
                                else:
                                     abs_time_diff = abs(time_diff)
                                     hours, remainder = divmod(abs_time_diff.seconds, 3600)
                                     minutes, _ = divmod(remainder, 60)
                                     time_until = f"hace {hours} horas y {minutes} minutos"


                                notification_msg = (
                                    f"¡Recordatorio de Tarea!\n\n"
                                    f"Tarea: {tarea['descripcion']}\n"
                                    f"Fecha límite: {tarea['fecha_limite']}\n"
                                    f"Categoría: {tarea['categoria']}\n\n"
                                    f"La fecha límite es {time_until}."
                                )

                                QMessageBox.information(self, "Recordatorio de Tarea", notification_msg)

                                self.checked_tasks_for_notification.add(tarea["descripcion"])

                        except ValueError:
                            print(f"Advertencia: Tarea con formato de fecha inválido: {tarea.get('descripcion')}")
                            pass

        except Exception as e:
            print(f"Error al verificar tareas próximas: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    # La ventana principal se muestra automáticamente después del login
    sys.exit(app.exec_())
