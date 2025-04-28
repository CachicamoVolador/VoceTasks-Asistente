# user_management.py (Con método get_user_config añadido)

import os
import json
import hashlib
import re
from datetime import datetime

class UserManager:
    def __init__(self, users_file="usuarios.json"):
        self.users_file = users_file
        self.current_user = None
        self.load_users()

    def load_users(self):
        """Carga los usuarios desde el archivo JSON"""
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, 'r') as file:
                    data = json.load(file)
                    # Asegurarse de que la clave 'usuarios' existe y es una lista
                    self.users = {usuario["email"]: usuario for usuario in data.get("usuarios", []) if "email" in usuario}
            except json.JSONDecodeError:
                print(f"Error al decodificar {self.users_file}. Inicializando usuarios.")
                self.users = {}
            except Exception as e:
                print(f"Error inesperado al cargar usuarios: {e}")
                self.users = {}
        else:
            self.users = {}
            self.save_users() # Crear el archivo si no existe

    def save_users(self):
        """Guarda los usuarios en el archivo JSON"""
        try:
            with open(self.users_file, 'w') as file:
                # Convertir el diccionario de usuarios de nuevo a una lista para guardar
                data = {"usuarios": list(self.users.values())}
                json.dump(data, file, indent=4)
        except Exception as e:
            print(f"Error al guardar usuarios: {e}")


    def hash_password(self, password):
        """Crea un hash seguro de la contraseña"""
        return hashlib.sha256(password.encode()).hexdigest()

    def is_valid_email(self, email):
        """Verifica si un email tiene un formato válido"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def register_user(self, email, name, password):
        """Registra un nuevo usuario"""
        if not self.is_valid_email(email):
            return False, "Email inválido. Introduce un email con formato correcto."

        if email in self.users:
            return False, "Este email ya está registrado."

        hashed_password = self.hash_password(password)
        new_user = {
            "email": email,
            "name": name,
            "password": hashed_password,
            "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "config": {
                "recordatorios_activos": True, # Configuración por defecto
                "modo_silencioso": False
            }
        }
        self.users[email] = new_user
        self.save_users()

        # Crear el directorio de tareas para el nuevo usuario
        user_tasks_dir = f"usuarios/{email}"
        os.makedirs(user_tasks_dir, exist_ok=True)
        # Crear el archivo de tareas inicial si no existe (aunque commands.py también lo hace)
        user_tasks_file = os.path.join(user_tasks_dir, "tareas.json")
        if not os.path.exists(user_tasks_file):
             with open(user_tasks_file, "w") as f:
                 json.dump({"tareas": []}, f, indent=4)


        return True, "Usuario registrado exitosamente."

    def login(self, email, password):
        """Inicia sesión con un usuario existente"""
        if email not in self.users:
            return False, "Email no registrado."

        stored_password_hash = self.users[email]["password"]
        if self.hash_password(password) == stored_password_hash:
            self.current_user = email
            return True, f"Bienvenido, {self.users[email].get('name', email)}!"
        else:
            return False, "Contraseña incorrecta."

    def logout(self):
        """Cierra la sesión del usuario actual"""
        if self.current_user:
            print(f"Cerrando sesión de {self.current_user}")
            self.current_user = None
            return True, "Sesión cerrada."
        else:
            return False, "No hay ninguna sesión activa."

    def get_current_user_email(self):
        """Obtiene el email del usuario actual"""
        return self.current_user

    def get_user_name(self):
        """Obtiene el nombre del usuario actual"""
        if self.current_user and self.current_user in self.users:
            return self.users[self.current_user].get("name", self.current_user)
        return None

    # Añadido: Método para obtener la configuración del usuario actual
    def get_user_config(self):
        """Obtiene el diccionario de configuración del usuario actual."""
        if self.current_user and self.current_user in self.users:
            # Devolver el diccionario de configuración o un diccionario vacío si no existe
            return self.users[self.current_user].get("config", {})
        return {} # Devolver diccionario vacío si no hay usuario logueado


    # Métodos relacionados con la configuración que ya existían
    def is_silent_mode(self):
        """Verifica si el modo silencioso está activo para el usuario actual"""
        if self.current_user and self.current_user in self.users:
            # Usar get con valor por defecto False para manejar el caso si 'config' o 'modo_silencioso' no existen
            return self.users[self.current_user].get("config", {}).get("modo_silencioso", False)
        return False

    def toggle_silent_mode(self):
        """Cambia el estado del modo silencioso para el usuario actual"""
        if not self.current_user or self.current_user not in self.users:
            return False, "No hay ninguna sesión activa."

        # Asegurarse de que la clave 'config' existe y es un diccionario
        if "config" not in self.users[self.current_user] or not isinstance(self.users[self.current_user]["config"], dict):
            self.users[self.current_user]["config"] = {} # Inicializar si no existe

        current_mode = self.users[self.current_user]["config"].get("modo_silencioso", False)
        new_mode = not current_mode
        self.users[self.current_user]["config"]["modo_silencioso"] = new_mode
        self.save_users()

        mode_text = "activado" if new_mode else "desactivado"
        return True, f"Modo silencioso {mode_text} correctamente."

    def get_notification_email(self):
        """Obtiene el email para notificaciones del usuario actual"""
        if self.current_user and self.current_user in self.users:
            # Usar get con valor por defecto el email del usuario
            return self.users[self.current_user].get("config", {}).get("notificacion_email", self.current_user)
        return None

    def update_notification_email(self, email):
        """Actualiza el email para notificaciones"""
        if not self.current_user or self.current_user not in self.users:
            return False, "No hay ninguna sesión activa."

        if not self.is_valid_email(email):
            return False, "Email inválido. Introduce un email con formato correcto."

        # Asegurarse de que la clave 'config' existe y es un diccionario
        if "config" not in self.users[self.current_user] or not isinstance(self.users[self.current_user]["config"], dict):
            self.users[self.current_user]["config"] = {} # Inicializar si no existe


        self.users[self.current_user]["config"]["notificacion_email"] = email
        self.save_users()
        return True, f"Email de notificación actualizado a: {email}"

    def get_all_users(self):
        """Obtiene una lista de todos los usuarios registrados (útil para administración)"""
        return list(self.users.values())
