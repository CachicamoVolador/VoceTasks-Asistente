import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                           QTabWidget, QLabel, QPushButton, QLineEdit, QTextEdit,
                           QTableWidget, QTableWidgetItem, QCalendarWidget, QFrame,
                           QMessageBox, QSplitter, QDialog, QFormLayout,
                           QCheckBox, QComboBox, QGroupBox, QScrollArea, QStackedWidget, QHeaderView) # Añadido QHeaderView para estilizar cabecera de tabla
from PyQt5.QtCore import Qt, QDate, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QIcon, QFont, QColor

# Importar los módulos existentes
from utils import escuchar_comando, hablar
from commands import (agregar_tarea, eliminar_tarea, mostrar_tareas, modificar_tarea,
                     agregar_recordatorio, cambiar_categoria, marcar_como_completada,
                     mostrar_tareas_por_categoria, mostrar_tareas_calendario,
                     sincronizar_todas_tareas_calendario, enviar_recordatorios_email,
                     mostrar_tareas_formato_calendario)
from user_management import UserManager
import os
import json
import datetime
from datetime import timedelta
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
                background-color: #1e1e1e; /* Fondo negro oscuro */
                color: #ffffff; /* Color de texto blanco por defecto */
            }
            QLabel {
                color: #ffffff; /* Color de texto blanco para etiquetas */
                font-size: 12pt; /* Tamaño de fuente para etiquetas */
            }
            QLineEdit {
                background-color: #333333; /* Fondo oscuro para campos de texto */
                color: #ffffff; /* Color de texto blanco */
                border: 1px solid #555555; /* Borde sutil */
                padding: 5px; /* Espaciado interno */
                border-radius: 5px; /* Bordes redondeados */
                font-size: 12pt;
            }
            QPushButton {
                background-color: #007acc; /* Color de fondo para botones (azul vibrante) */
                color: #ffffff; /* Color de texto blanco */
                border: none; /* Sin borde */
                padding: 10px 20px; /* Espaciado interno */
                border-radius: 5px; /* Bordes redondeados */
                font-size: 12pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #005f99; /* Color al pasar el ratón por encima */
            }
            QTabWidget::pane { /* El área de contenido de las pestañas */
                border: 1px solid #555555;
                background-color: #2b2b2b; /* Fondo oscuro para el contenido de la pestaña */
                border-radius: 5px;
            }
            QTabBar::tab {
                background: #333333; /* Fondo de las pestañas inactivas */
                color: #ffffff; /* Color de texto de las pestañas inactivas */
                padding: 8px 15px; /* Espaciado interno de las pestañas */
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                margin-right: 1px;
            }
            QTabBar::tab:selected {
                background: #007acc; /* Fondo de la pestaña activa */
                color: #ffffff; /* Color de texto de la pestaña activa */
            }
             QTabBar::tab:hover {
                background: #005f99; /* Fondo de las pestañas al pasar el ratón */
            }
        """)

        # Layout principal del diálogo
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20) # Márgenes internos
        main_layout.setSpacing(15) # Espacio entre elementos

        # Etiqueta para el nombre de la aplicación
        app_name_label = QLabel("VoceTasks")
        app_name_label.setFont(QFont("Arial", 24, QFont.Bold)) # Fuente más grande y en negrita
        app_name_label.setAlignment(Qt.AlignCenter) # Centrar texto
        app_name_label.setStyleSheet("color: #007acc;") # Color que resalta

        # Crear pestañas para login y registro
        tab_widget = QTabWidget()

        # Pestaña de inicio de sesión
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
        self.login_password.setPlaceholderText("Introduce tu contraseña")

        form_layout.addRow("Email:", self.login_email)
        form_layout.addRow("Contraseña:", self.login_password)

        login_button = QPushButton("Iniciar Sesión")
        login_button.clicked.connect(self.handle_login)

        login_layout.addLayout(form_layout)
        login_layout.addSpacing(10) # Espacio entre formulario y botón
        login_layout.addWidget(login_button)


        # Pestaña de registro
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
        self.register_password.setPlaceholderText("Crea una contraseña")

        register_form.addRow("Nombre:", self.register_name)
        register_form.addRow("Email:", self.register_email)
        register_form.addRow("Contraseña:", self.register_password)

        register_button = QPushButton("Registrarse")
        register_button.clicked.connect(self.handle_register)

        register_layout.addLayout(register_form)
        register_layout.addSpacing(10) # Espacio entre formulario y botón
        register_layout.addWidget(register_button)


        # Añadir pestañas
        tab_widget.addTab(login_widget, "Iniciar Sesión")
        tab_widget.addTab(register_widget, "Registrarse")

        # Añadir elementos al layout principal
        main_layout.addWidget(app_name_label)
        main_layout.addWidget(tab_widget)

        # Establecer el layout principal en el diálogo
        self.setLayout(main_layout)


    def handle_login(self):
        email = self.login_email.text()
        password = self.login_password.text()

        success, message = self.user_manager.login(email, password)
        if success:
            QMessageBox.information(self, "Éxito", message)
            self.accept()  # Cerrar diálogo con éxito
        else:
            QMessageBox.warning(self, "Error", message)

    def handle_register(self):
        name = self.register_name.text()
        email = self.register_email.text()
        password = self.register_password.text()

        success, message = self.user_manager.register_user(email, password, name)
        if success:
            QMessageBox.information(self, "Éxito", message)
            # Automáticamente iniciar sesión después de registrar
            self.user_manager.login(email, password)
            self.accept()
        else:
            QMessageBox.warning(self, "Error", message)


class TasksTable(QTableWidget):
    """Widget personalizado para mostrar tareas en formato de tabla"""
    taskCompleted = pyqtSignal(str)
    taskDeleted = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels(["Tarea", "Categoría", "Fecha límite", "Estado", "Acciones"])
        self.horizontalHeader().setStretchLastSection(True)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setAlternatingRowColors(True) # Para un mejor contraste en tema oscuro


    def load_tasks(self, email):
        """Carga las tareas del usuario en la tabla"""
        self.setRowCount(0)  # Limpiar tabla

        try:
            ruta_archivo = f"usuarios/{email}/tareas.json"
            if not os.path.exists(ruta_archivo):
                return

            with open(ruta_archivo, "r") as file:
                data = json.load(file)

                for row, task in enumerate(data["tareas"]):
                    self.insertRow(row)

                    # Descripción
                    self.setItem(row, 0, QTableWidgetItem(task["descripcion"]))

                    # Categoría
                    self.setItem(row, 1, QTableWidgetItem(task["categoria"]))

                    # Fecha límite
                    fecha = "No establecida" if not task.get("fecha_limite") else task["fecha_limite"]
                    self.setItem(row, 2, QTableWidgetItem(fecha))

                    # Estado
                    estado = "Completada" if task.get("completada") else "Pendiente"
                    estado_item = QTableWidgetItem(estado)
                    # Colores de estado adaptados a tema oscuro
                    if task.get("completada"):
                        estado_item.setBackground(QColor(50, 150, 50)) # Verde oscuro
                    else:
                        estado_item.setBackground(QColor(150, 50, 50)) # Rojo oscuro
                    estado_item.setForeground(QColor(255, 255, 255)) # Texto blanco
                    self.setItem(row, 3, estado_item)

                    # Botones de acción
                    actions_widget = QWidget()
                    actions_layout = QHBoxLayout(actions_widget)
                    actions_layout.setContentsMargins(0, 0, 0, 0)
                    actions_layout.setAlignment(Qt.AlignCenter)


                    # Botón completar
                    complete_btn = QPushButton("✓")
                    complete_btn.setToolTip("Marcar como completada")
                    complete_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #4CAF50; /* Verde */
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
                            background-color: #F44336; /* Rojo */
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

                    actions_layout.addWidget(complete_btn)
                    actions_layout.addWidget(delete_btn)

                    self.setCellWidget(row, 4, actions_widget)

                # Estilo de las celdas de la tabla
                for row in range(self.rowCount()):
                    for col in range(self.columnCount()):
                         item = self.item(row, col)
                         if item:
                             item.setForeground(QColor(255, 255, 255)) # Texto blanco
                             if row % 2 == 0:
                                  item.setBackground(QColor(45, 45, 45)) # Fondo oscuro alternado
                             else:
                                 item.setBackground(QColor(60, 60, 60)) # Fondo oscuro alternado

        except Exception as e:
            print(f"Error al cargar tareas: {e}")


class MainWindow(QMainWindow):
    """Ventana principal de la aplicación"""
    def __init__(self):
        super().__init__()

        # Inicialización
        self.user_manager = UserManager()
        self.mode = "text"  # Modo inicial (text/voice)

        # Configuración de la ventana
        self.setWindowTitle("Asistente de Tareas")
        self.setMinimumSize(1000, 600)

        # Mostrar login antes de iniciar
        self.show_login()

        # Si el login fue exitoso, inicializar UI y mostrar en pantalla completa
        if self.user_manager.current_user:
            self.init_ui()
            self.showFullScreen() # Muestra la ventana principal en pantalla completa

            # Configurar reconocimiento de voz (si no está ya configurado)
            try:
                self.recognizer_thread = RecognizerThread()
                self.recognizer_thread.textDetected.connect(self.on_voice_command)
                self.recognizer_thread.listenStateChanged.connect(self.update_mic_status)
            except ImportError:
                print("Advertencia: speech_recognition no instalado. El modo de voz no estará disponible.")
                self.mode = "text" # Forzar modo texto si no hay speech_recognition
                self.update_interface_for_mode()
                self.voice_mode_btn.setEnabled(False) # Desactivar botón de voz
                self.text_mode_btn.setChecked(True)


    def show_login(self):
        """Muestra el diálogo de inicio de sesión"""
        dialog = LoginDialog(self.user_manager)
        result = dialog.exec_()

        # Si el resultado no es Accepted o no hay usuario logueado, salir
        if result != QDialog.Accepted or not self.user_manager.current_user:
            QMessageBox.critical(self, "Error", "Debes iniciar sesión para usar la aplicación")
            sys.exit()


    def init_ui(self):
        """Inicializa la interfaz de usuario con el tema oscuro"""
        # Aplicar estilo oscuro a la ventana principal y sus widgets
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1e1e1e; /* Fondo oscuro principal */
                color: #ffffff; /* Color de texto por defecto */
            }
            QLabel {
                 color: #ffffff; /* Color de texto blanco para etiquetas */
                 font-size: 12pt;
            }
            QFrame {
                border: 1px solid #555555; /* Borde sutil para frames */
                border-radius: 5px;
                background-color: #2b2b2b; /* Fondo un poco más claro para frames */
            }
            QGroupBox {
                border: 1px solid #555555;
                border-radius: 5px;
                margin-top: 10px; /* Espacio para el título del GroupBox */
                background-color: #2b2b2b;
                color: #ffffff;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left; /* Posicionar título arriba a la izquierda */
                padding: 0 3px; /* Espaciado alrededor del título */
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
                background-color: #007acc; /* Color de fondo para botones */
                color: #ffffff;
                border: none;
                padding: 8px 15px; /* Ajustado un poco para botones pequeños */
                border-radius: 5px;
                font-size: 11pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #005f99;
            }
             QPushButton#mic_btn { /* Estilo específico para el botón de micrófono */
                background-color: #ff6b6b; /* Rojo */
                min-width: 30px; /* Tamaño mínimo para que sea más cuadrado */
                min-height: 30px;
                border-radius: 15px; /* Bordes muy redondeados */
            }
            QPushButton#mic_btn:hover {
                background-color: #ff4c4c; /* Rojo más oscuro al pasar el ratón */
            }

            QTableWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #555555;
                gridline-color: #555555; /* Color de las líneas de la cuadrícula */
                font-size: 11pt;
            }
             QTableWidget QHeaderView::section {
                background-color: #3a3a3a; /* Fondo oscuro para la cabecera de la tabla */
                color: #ffffff;
                padding: 5px;
                border: 1px solid #555555;
            }
             QTableWidget::item {
                padding: 5px;
                /* Los colores alternados y de estado se manejan en load_tasks */
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
                color: #ffffff; /* Color de los números del calendario */
            }
             QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: #3a3a3a; /* Fondo de la barra de navegación del calendario */
                border-bottom: 1px solid #555555;
            }
             QCalendarWidget QToolButton { /* Botones de navegación del calendario */
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
                 image: none; /* Eliminar indicador de menú */
             }
             QCalendarWidget QSpinBox { /* Año en el calendario */
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
                background-color: #555555; /* Color del manejador del splitter */
            }
             QSplitter::handle:hover {
                 background-color: #007acc; /* Color al pasar el ratón */
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
                 background-color: #007acc; /* Color cuando está marcado */
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
                 border: none; /* Eliminar borde del desplegable */
             }
             QComboBox::down-arrow {
                 image: url(down_arrow_white.png); /* Puedes necesitar una imagen de flecha blanca */
                 width: 10px;
                 height: 10px;
             }
              QComboBox QAbstractItemView { /* Estilo de los elementos de la lista desplegable */
                 background-color: #333333;
                 color: #ffffff;
                 selection-background-color: #007acc;
             }

        """)

        # Widget central
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        # --- CABECERA ---
        header_frame = QFrame()
        header_frame.setObjectName("headerFrame") # Nombre de objeto para posible estilo específico
        header_layout = QHBoxLayout(header_frame)

        # Información de usuario
        user_data = self.user_manager.get_user_data()
        user_label = QLabel(f"Hola, {user_data['name']}!")
        user_label.setFont(QFont("Arial", 14, QFont.Bold))
        user_label.setStyleSheet("color: #ffffff;") # Asegurar color blanco

        # Botones de modo
        mode_group = QGroupBox("Modo de entrada")
        mode_layout = QHBoxLayout()

        self.text_mode_btn = QCheckBox("Texto")
        self.voice_mode_btn = QCheckBox("Voz")

        # Configurar estado inicial según preferencias del usuario
        # Asegurarse de que solo uno esté marcado
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

        # Botón de cerrar sesión
        logout_btn = QPushButton("Cerrar Sesión")
        logout_btn.clicked.connect(self.handle_logout)

        header_layout.addWidget(user_label)
        header_layout.addWidget(mode_group)
        header_layout.addStretch()
        header_layout.addWidget(logout_btn)

        # --- CONTENIDO PRINCIPAL ---
        content_splitter = QSplitter(Qt.Horizontal)

        # Panel izquierdo (Tareas)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        tasks_label = QLabel("Mis Tareas")
        tasks_label.setFont(QFont("Arial", 12, QFont.Bold))


        # Tabla de tareas
        self.tasks_table = TasksTable()
        self.tasks_table.taskCompleted.connect(self.complete_task)
        self.tasks_table.taskDeleted.connect(self.delete_task)

        # Panel de acción rápida
        quick_panel = QGroupBox("Acción Rápida")
        quick_layout = QHBoxLayout()

        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("Escribir una nueva tarea...")

        add_btn = QPushButton("Agregar")
        add_btn.clicked.connect(self.quick_add_task)

        quick_layout.addWidget(self.task_input)
        quick_layout.addWidget(add_btn)
        quick_panel.setLayout(quick_layout)

        left_layout.addWidget(tasks_label)
        left_layout.addWidget(self.tasks_table)
        left_layout.addWidget(quick_panel)

        # Panel derecho (Calendario y opciones)
        right_panel = QTabWidget()

        # Pestaña del Calendario
        calendar_widget = QWidget()
        calendar_layout = QVBoxLayout(calendar_widget)

        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)


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
        # Las categorías del usuario se añadirán en refresh_tasks/update_categories


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
        content_splitter.setSizes([600, 400])  # Distribución inicial ajustada


        # --- PANEL DE COMANDOS ---
        command_frame = QFrame()
        command_frame.setObjectName("commandFrame") # Nombre de objeto para estilo
        command_layout = QHBoxLayout(command_frame)

        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Escribe un comando o pregúntame algo...")
        self.command_input.returnPressed.connect(self.process_command)

        self.mic_btn = QPushButton("🎤")
        self.mic_btn.setObjectName("mic_btn") # Nombre de objeto para estilo específico
        self.mic_btn.setToolTip("Hablar (mantener presionado)")
        self.mic_btn.setCheckable(True)
        # Conectar pressed/released para iniciar/detener la escucha
        self.mic_btn.pressed.connect(self.start_listening)
        self.mic_btn.released.connect(self.stop_listening)


        command_layout.addWidget(self.command_input)
        command_layout.addWidget(self.mic_btn)

        # --- PANEL DE RESPUESTA ---
        self.response_area = QTextEdit()
        self.response_area.setReadOnly(True)
        self.response_area.setPlaceholderText("Aquí aparecerán mis respuestas...")
        self.response_area.setMinimumHeight(100)

        # --- AGREGAR TODO AL LAYOUT PRINCIPAL ---
        main_layout.addWidget(header_frame)
        main_layout.addWidget(content_splitter, 1)  # Le damos más espacio
        main_layout.addWidget(command_frame)
        main_layout.addWidget(self.response_area)

        self.setCentralWidget(central_widget)

        # Asegurarse de que el modo de interfaz inicial sea correcto
        self.update_interface_for_mode()

        # Cargar datos iniciales
        self.refresh_tasks()
        self.show_welcome_message()


    def show_welcome_message(self, initial=True):
        """Muestra mensaje de bienvenida"""
        user_data = self.user_manager.get_user_data()
        msg = f"¡Bienvenido a tu Asistente de Tareas, {user_data['name']}! ¿En qué puedo ayudarte hoy?"
        self.show_response(msg)

        # Solo hablar el mensaje de bienvenida al inicio si el modo es voz
        if initial and self.mode == "voice":
             # Importar hablar aquí para evitar importación circular si no se usa
            try:
                from utils import hablar
                hablar(msg)
            except ImportError:
                 print("Advertencia: pyttsx3 no instalado. La síntesis de voz no estará disponible.")


    def handle_logout(self):
        """Maneja el cierre de sesión"""
        result = QMessageBox.question(self, "Cerrar Sesión",
                                     "¿Estás seguro de que quieres cerrar sesión?",
                                     QMessageBox.Yes | QMessageBox.No)

        if result == QMessageBox.Yes:
            self.user_manager.logout()
            # Reiniciar aplicación mostrando login
            self.close()
            # Crear una nueva instancia de la aplicación
            if __name__ == "__main__": # Evitar crear una nueva instancia si no es el punto de entrada
                 new_instance = MainWindow()
                 new_instance.show()


    def change_mode(self, mode):
        """Cambia el modo de entrada entre texto y voz"""
        # Evitar cambiar si el reconocimiento de voz no está disponible
        if mode == "voice" and not hasattr(self, 'recognizer_thread'):
             QMessageBox.warning(self, "Modo no disponible", "El modo de voz no está disponible. Asegúrate de tener 'speech_recognition' instalado.")
             self.text_mode_btn.setChecked(True) # Mantener en modo texto
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
            # Si cambiamos a texto mientras escuchamos, detener la escucha
            if self.recognizer_thread.isRunning():
                 self.recognizer_thread.running = False # Señalar al hilo que se detenga


        else: # mode == "voice"
            self.text_mode_btn.setChecked(False)
            self.voice_mode_btn.setChecked(True)
            self.user_manager.update_user_preference("modo_silencioso", False)


        self.update_interface_for_mode()


    def update_interface_for_mode(self):
        """Actualiza la interfaz según el modo activo"""
        if self.mode == "text":
            self.mic_btn.setEnabled(False)
            self.mic_btn.setStyleSheet("background-color: #f0f0f0;") # Estilo para deshabilitado
        else: # mode == "voice"
             # Habilitar solo si el reconocedor de voz fue inicializado correctamente
            if hasattr(self, 'recognizer_thread'):
                 self.mic_btn.setEnabled(True)
                 self.mic_btn.setStyleSheet("""
                        QPushButton#mic_btn {
                            background-color: #ff6b6b; /* Rojo */
                            color: white; /* Color del ícono */
                            border: none;
                            padding: 5px;
                            border-radius: 15px;
                            min-width: 30px;
                            min-height: 30px;
                        }
                        QPushButton#mic_btn:hover {
                            background-color: #ff4c4c; /* Rojo más oscuro al pasar el ratón */
                        }
                    """)
            else: # Si no hay reconocedor, mantener deshabilitado
                 self.mic_btn.setEnabled(False)
                 self.mic_btn.setStyleSheet("background-color: #f0f0f0;")


    def start_listening(self):
        """Inicia la escucha por voz"""
        if self.mode == "voice" and hasattr(self, 'recognizer_thread') and not self.recognizer_thread.isRunning():
             self.show_response("Escuchando...")
             self.recognizer_thread.running = True # Asegurar que el hilo sepa que debe correr
             self.recognizer_thread.start()


    def stop_listening(self):
        """Detiene la escucha por voz"""
        # No es necesario detener explícitamente el hilo aquí
        # El hilo se detendrá después de procesar la escucha

        # Asegurarse de actualizar el estado visual si el botón se soltó
        if self.mode == "voice" and not self.recognizer_thread.isRunning():
             self.update_mic_status(False)


    def update_mic_status(self, is_listening):
        """Actualiza el estado visual del botón del micrófono"""
        if self.mode == "voice": # Solo actualizar si estamos en modo voz
            if is_listening:
                self.mic_btn.setStyleSheet("""
                    QPushButton#mic_btn {
                        background-color: #ff9800; /* Naranja cuando está escuchando */
                        color: white;
                        border: none;
                        padding: 5px;
                        border-radius: 15px;
                        min-width: 30px;
                        min-height: 30px;
                    }
                """)
            else:
                # Volver al color original cuando termina de escuchar
                self.mic_btn.setStyleSheet("""
                    QPushButton#mic_btn {
                        background-color: #ff6b6b; /* Rojo */
                        color: white;
                        border: none;
                        padding: 5px;
                        border-radius: 15px;
                        min-width: 30px;
                        min-height: 30px;
                    }
                    QPushButton#mic_btn:hover {
                        background-color: #ff4c4c; /* Rojo más oscuro al pasar el ratón */
                    }
                """)
                self.show_response("Procesando...")


    def on_voice_command(self, text):
        """Maneja comandos recibidos por voz"""
        self.command_input.setText(text)
        self.process_command()


    def process_command(self):
        """Procesa el comando ingresado"""
        command = self.command_input.text().strip()
        if not command:
            return

        # Mostrar comando en área de respuesta
        self.response_area.append(f"<b>Tú:</b> {command}")

        # Procesar comando utilizando la lógica existente
        # Importar aquí para evitar importación circular si no se usa
        try:
            from main import interpretar_comando
            # Interpretar comando
            action = interpretar_comando(command)
            # Ejecutar acción según comando interpretado
            response = self.execute_action(action, command)

             # Pronunciar respuesta si estamos en modo voz y la respuesta no es el mensaje "Procesando..."
            if self.mode == "voice" and response != "Procesando...":
                 try:
                     from utils import hablar
                     hablar(response)
                 except ImportError:
                      print("Advertencia: pyttsx3 no instalado. La síntesis de voz no estará disponible.")


        except ImportError:
             response = "Error: No se pudo importar el módulo 'main'. Asegúrate de que 'main.py' existe y no tiene errores."
             # Forzar modo texto si hay un error de importación en main
             self.mode = "text"
             self.update_interface_for_mode()


        # Mostrar respuesta
        self.show_response(response)


        # Limpiar campo de entrada
        self.command_input.clear()

        # Actualizar interfaz
        self.refresh_tasks()


    def execute_action(self, action, original_command):
        """Ejecuta la acción correspondiente al comando interpretado"""
        email = self.user_manager.current_user

        # Acciones directas
        if action == 'mostrar':
            return mostrar_tareas(email)

        elif action == 'ver_calendario':
            # Importar aquí para evitar importación circular
            try:
                from commands import mostrar_tareas_calendario
                return mostrar_tareas_calendario(email)
            except ImportError:
                 return "Para ver el calendario, asegúrate de tener la integración configurada."


        elif action == 'sincronizar_calendario':
             # Importar aquí para evitar importación circular
             try:
                 from commands import sincronizar_todas_tareas_calendario
                 return sincronizar_todas_tareas_calendario(email)
             except ImportError:
                 return "La sincronización del calendario no está disponible."


        elif action == 'formato_calendario':
             # Importar aquí para evitar importación circular
             try:
                 from commands import mostrar_tareas_formato_calendario
                 return mostrar_tareas_formato_calendario(email)
             except ImportError:
                  return "El formato calendario no está disponible."


        elif action == 'enviar_recordatorios':
             # Importar aquí para evitar importación circular
             try:
                 from commands import enviar_recordatorios_email
                 return enviar_recordatorios_email(email)
             except ImportError:
                  return "El envío de recordatorios por email no está disponible."


        elif action == 'ayuda':
            # Importar aquí para evitar importación circular
            try:
                from main import mostrar_ayuda
                return mostrar_ayuda()
            except ImportError:
                return "No se pudo cargar la ayuda. Asegúrate de que 'main.py' existe."


        # Acciones con parámetros
        elif isinstance(action, tuple):
            if action[0] == 'agregar':
                return agregar_tarea(action[1], email)

            elif action[0] == 'eliminar':
                return eliminar_tarea(action[1], email)

            elif action[0] == 'modificar':
                return modificar_tarea(action[1], action[2], email)

            elif action[0] == 'recordatorio':
                 # Importar aquí para evitar importación circular
                 try:
                     from commands import agregar_recordatorio
                     return agregar_recordatorio(action[1], action[2], email)
                 except ImportError:
                     return "No se pudo agregar el recordatorio. Asegúrate de tener las dependencias necesarias para el calendario."

            elif action[0] == 'completar':
                return marcar_como_completada(action[1], email)

            elif action[0] == 'categoria':
                return cambiar_categoria(action[1], action[2], email)

            elif action[0] == 'mostrar_categoria':
                return mostrar_tareas_por_categoria(action[1], email)

        # Comando no reconocido
        return f"No he podido entender el comando: '{original_command}'\nPrueba con 'ayuda' para ver los comandos disponibles."

    def show_response(self, response):
        """Muestra respuesta en el área designada"""
        self.response_area.append(f"<b>Asistente:</b> {response}")
        self.response_area.verticalScrollBar().setValue(
            self.response_area.verticalScrollBar().maximum()
        )

    def refresh_tasks(self):
        """Actualiza la tabla de tareas"""
        if self.user_manager.current_user:
            self.tasks_table.load_tasks(self.user_manager.current_user)

            # También actualiza filtros y calendario
            self.update_calendar_tasks()
            self.update_categories()
            if self.category_combo.currentText() != "Todas":
                self.filter_by_category(self.category_combo.currentText())


    def quick_add_task(self):
        """Agrega una tarea rápidamente desde el panel de acción rápida"""
        task_text = self.task_input.text().strip()
        if not task_text:
            return

        response = agregar_tarea(task_text, self.user_manager.current_user)
        self.show_response(response)
        self.task_input.clear()
        self.refresh_tasks()

    def complete_task(self, task_name):
        """Marca una tarea como completada"""
        response = marcar_como_completada(task_name, self.user_manager.current_user)
        self.show_response(response)
        self.refresh_tasks()

    def delete_task(self, task_name):
        """Elimina una tarea"""
        confirmation = QMessageBox.question(
            self, "Confirmar eliminación",
            f"¿Estás seguro de que quieres eliminar la tarea '{task_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirmation == QMessageBox.Yes:
            response = eliminar_tarea(task_name, self.user_manager.current_user)
            self.show_response(response)
            self.refresh_tasks()

    def update_calendar_tasks(self):
        """Actualiza las tareas para la fecha seleccionada en el calendario"""
        selected_date = self.calendar.selectedDate().toString("yyyy-MM-dd")

        try:
            # Obtener todas las tareas
            ruta_archivo = f"usuarios/{self.user_manager.current_user}/tareas.json"
            if not os.path.exists(ruta_archivo):
                self.calendar_tasks_list.setText("No hay tareas para mostrar")
                return

            with open(ruta_archivo, "r") as file:
                data = json.load(file)

                # Filtrar tareas para la fecha seleccionada
                tareas_fecha = []
                for tarea in data["tareas"]:
                    if tarea.get("fecha_limite") and tarea["fecha_limite"].startswith(selected_date):
                        tareas_fecha.append(tarea)

                if tareas_fecha:
                    text = f"Tareas para {selected_date}:\n\n"
                    for tarea in tareas_fecha:
                        estado = "✓ " if tarea.get("completada") else "□ "
                        hora = tarea["fecha_limite"].split(" ")[1] if " " in tarea["fecha_limite"] else ""
                        text += f"{estado}{hora} - {tarea['descripcion']} ({tarea['categoria']})\n"

                    self.calendar_tasks_list.setText(text)
                else:
                    self.calendar_tasks_list.setText(f"No hay tareas para el {selected_date}")

                # Señalizar días con tareas en el calendario (simplificado)
                # Para una implementación completa, usar QCalendarWidget.setDateTextFormat
                pass


        except Exception as e:
            self.calendar_tasks_list.setText(f"Error al cargar tareas: {e}")

    def highlight_calendar_dates(self):
        """Resalta fechas en el calendario que tienen tareas asignadas (simplificado)"""
        # Esta función se deja como placeholder para una implementación más avanzada
        pass

    def update_categories(self):
        """Actualiza la lista de categorías disponibles"""
        try:
            ruta_archivo = f"usuarios/{self.user_manager.current_user}/tareas.json"
            if not os.path.exists(ruta_archivo):
                return

            with open(ruta_archivo, "r") as file:
                data = json.load(file)

                # Obtener categorías únicas
                categorias = set()
                for tarea in data["tareas"]:
                    categorias.add(tarea["categoria"])

                # Guardar selección actual
                current = self.category_combo.currentText()

                # Actualizar combo
                self.category_combo.clear()
                self.category_combo.addItem("Todas")
                for cat in sorted(categorias):
                    self.category_combo.addItem(cat)

                # Restaurar selección si sigue existiendo
                index = self.category_combo.findText(current)
                if index >= 0:
                    self.category_combo.setCurrentIndex(index)

        except Exception as e:
            print(f"Error al actualizar categorías: {e}")

    def filter_by_category(self, category):
        """Filtra tareas por categoría"""
        if category == "Todas":
            self.category_tasks_list.setText("Selecciona una categoría específica para ver sus tareas")
            # Opcionalmente, podrías mostrar todas las tareas aquí si "Todas" significa eso
            return

        try:
            response = mostrar_tareas_por_categoria(category, self.user_manager.current_user)
            self.category_tasks_list.setText(response)
        except Exception as e:
            self.category_tasks_list.setText(f"Error al filtrar por categoría: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec_())