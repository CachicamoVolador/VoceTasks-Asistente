import speech_recognition as sr
import pyttsx3
import getpass
import json
import os

# Variable global para el modo de entrada (voz o texto)
MODO_ENTRADA = 'voz'  # Valores posibles: 'voz', 'texto'

def escuchar_comando():
    """Función para escuchar y reconocer comandos de voz"""
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Escuchando...")
        r.adjust_for_ambient_noise(source)  # Ajusta para reducir ruido ambiente
        audio = r.listen(source)
        try:
            print("Reconociendo...")
            texto = r.recognize_google(audio, language='es-ES')
            print(f"Has dicho: {texto}")
            return texto.lower()
        except sr.UnknownValueError:
            print("No se pudo entender el audio")
            return "No entendí"
        except sr.RequestError as e:
            print(f"Error de conexión con el servicio de reconocimiento: {e}")
            return "Error de conexión"

def hablar(texto):
    """Función para convertir texto a voz"""
    if MODO_ENTRADA == 'texto':
        # En modo texto, solo imprimir en pantalla
        print(f"Asistente: {texto}")
        return
        
    motor = pyttsx3.init()
    voces = motor.getProperty('voices')
    # Configurar una voz en español si está disponible
    for voz in voces:
        if "spanish" in voz.name.lower():
            motor.setProperty('voice', voz.id)
            break
    motor.say(texto)
    motor.runAndWait()

def entrada_texto(prompt, ocultar=False):
    """Función para recibir entrada de texto del usuario"""
    if ocultar:
        return getpass.getpass(prompt)
    else:
        return input(prompt)

def cambiar_modo_entrada(modo, email=None):
    """Cambia el modo de entrada entre voz y texto, y actualiza la configuración del usuario si está logueado"""
    global MODO_ENTRADA
    if modo in ['voz', 'texto']:
        MODO_ENTRADA = modo
        
        # Si el usuario está logueado, guardar preferencia en su configuración
        if email:
            config = obtener_configuracion_usuario(email)
            if config:
                config['modo_silencioso'] = (modo == 'texto')
                guardar_configuracion_usuario(email, config)
                
        return f"Modo de entrada cambiado a: {modo}"
    else:
        return "Modo no válido. Use 'voz' o 'texto'."

def obtener_modo_entrada():
    """Devuelve el modo de entrada actual"""
    return MODO_ENTRADA

def cargar_modo_entrada_usuario(email):
    """Carga y establece el modo de entrada preferido por el usuario"""
    global MODO_ENTRADA
    config = obtener_configuracion_usuario(email)
    if config and 'modo_silencioso' in config:
        MODO_ENTRADA = 'texto' if config['modo_silencioso'] else 'voz'
    return MODO_ENTRADA

def guardar_configuracion_usuario(email, config):
    """Guarda la configuración del usuario"""
    try:
        with open("usuarios.json", "r+") as file:
            data = json.load(file)
            
            for i, usuario in enumerate(data["usuarios"]):
                if usuario["email"] == email:
                    data["usuarios"][i]["config"] = config
                    file.seek(0)
                    json.dump(data, file, indent=4)
                    file.truncate()
                    return True
            
            return False
    except Exception as e:
        print(f"Error al guardar configuración: {e}")
        return False

def obtener_configuracion_usuario(email):
    """Obtiene la configuración del usuario"""
    try:
        with open("usuarios.json", "r") as file:
            data = json.load(file)
            
            for usuario in data["usuarios"]:
                if usuario["email"] == email:
                    return usuario["config"]
            
            return None
    except Exception as e:
        print(f"Error al obtener configuración: {e}")
        return None

def inicializar_entorno():
    """Inicializa el entorno necesario para la aplicación"""
    # Crear directorio de usuarios si no existe
    os.makedirs("usuarios", exist_ok=True)
    
    # Crear archivo de usuarios si no existe
    if not os.path.exists("usuarios.json"):
        with open("usuarios.json", "w") as file:
            json.dump({"usuarios": []}, file, indent=4)
