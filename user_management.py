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
                    self.users = {usuario["email"]: usuario for usuario in data["usuarios"]} if "usuarios" in data else {}
            except json.JSONDecodeError:
                self.users = {}
        else:
            self.users = {}
            self.save_users()
    
    def save_users(self):
        """Guarda los usuarios en el archivo JSON"""
        with open(self.users_file, 'w') as file:
            data = {"usuarios": list(self.users.values())}
            json.dump(data, file, indent=4)
    
    def hash_password(self, password):
        """Crea un hash seguro de la contraseña"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def is_valid_email(self, email):
        """Verifica si un email tiene un formato válido"""
        pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        return re.match(pattern, email) is not None
    
    def register_user(self, email, password, name):
        """Registra un nuevo usuario"""
        if not self.is_valid_email(email):
            return False, "Email inválido. Introduce un email con formato correcto."
        
        if email in self.users:
            return False, "Este email ya está registrado."
        
        if len(password) < 6:
            return False, "La contraseña debe tener al menos 6 caracteres."
        
        user_data = {
            "email": email,
            "name": name,
            "password": self.hash_password(password),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "config": {
                "recordatorios_activos": True,
                "modo_silencioso": False
            }
        }
        
        # Crear carpeta de usuario y archivo de tareas
        carpeta_usuario = f"usuarios/{email}"
        os.makedirs(carpeta_usuario, exist_ok=True)
        
        with open(f"{carpeta_usuario}/tareas.json", "w") as tareas_file:
            json.dump({"tareas": []}, tareas_file, indent=4)
        
        self.users[email] = user_data
        self.save_users()
        return True, f"Usuario {name} ({email}) registrado correctamente."
    
    def login(self, email, password):
        """Autentica a un usuario"""
        if email not in self.users:
            return False, "Email no registrado."
        
        if self.users[email]["password"] != self.hash_password(password):
            return False, "Contraseña incorrecta."
        
        self.current_user = email
        return True, f"Bienvenido, {self.users[email]['name']}!"
    
    def logout(self):
        """Cierra la sesión del usuario actual"""
        if self.current_user:
            user_name = self.users[self.current_user]["name"]
            self.current_user = None
            return True, f"Hasta pronto, {user_name}!"
        return False, "No hay ninguna sesión activa."
    
    def get_user_data(self):
        """Obtiene los datos del usuario actual"""
        if not self.current_user:
            return None
        return self.users[self.current_user]
    
    def update_user_preference(self, preference, value):
        """Actualiza una preferencia del usuario"""
        if not self.current_user:
            return False, "No hay ninguna sesión activa."
        
        if preference not in self.users[self.current_user]["config"]:
            self.users[self.current_user]["config"][preference] = value
        else:
            self.users[self.current_user]["config"][preference] = value
        
        self.save_users()
        return True, f"Preferencia {preference} actualizada correctamente."
    
    def get_silent_mode(self):
        """Obtiene el estado del modo silencioso para el usuario actual"""
        if not self.current_user:
            return False
        return self.users[self.current_user]["config"].get("modo_silencioso", False)
    
    def toggle_silent_mode(self):
        """Alterna el modo silencioso para el usuario actual"""
        if not self.current_user:
            return False, "No hay ninguna sesión activa."
        
        current_mode = self.users[self.current_user]["config"].get("modo_silencioso", False)
        new_mode = not current_mode
        self.users[self.current_user]["config"]["modo_silencioso"] = new_mode
        self.save_users()
        
        mode_text = "activado" if new_mode else "desactivado"
        return True, f"Modo silencioso {mode_text} correctamente."
    
    def get_notification_email(self):
        """Obtiene el email para notificaciones del usuario actual"""
        if not self.current_user:
            return None
        
        # Por defecto, el email de notificación es el mismo email del usuario
        return self.current_user
    
    def update_notification_email(self, email):
        """Actualiza el email para notificaciones"""
        if not self.current_user:
            return False, "No hay ninguna sesión activa."
        
        if not self.is_valid_email(email):
            return False, "Email inválido. Introduce un email con formato correcto."
        
        # Guardar el email de notificación en la configuración
        if "notificacion_email" not in self.users[self.current_user]["config"]:
            self.users[self.current_user]["config"]["notificacion_email"] = email
        else:
            self.users[self.current_user]["config"]["notificacion_email"] = email
        
        self.save_users()
        return True, f"Email de notificación actualizado a: {email}"
    
    def get_all_users(self):
        """Retorna una lista de todos los emails de usuarios registrados"""
        return list(self.users.keys())