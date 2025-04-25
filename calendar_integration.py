import os
import json
import datetime
from datetime import timedelta
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import base64

# Si modificas estos alcances, elimina el archivo token.json
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly',
          'https://www.googleapis.com/auth/calendar.events',
          'https://www.googleapis.com/auth/gmail.send']

def obtener_credenciales(email):
    """Obtiene las credenciales para acceder a la API de Google Calendar"""
    creds = None
    token_path = f"usuarios/{email}/token.json"
    
    # Verificar si el token existe y es válido
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_info(
            json.load(open(token_path)), SCOPES)
    
    # Si no hay credenciales válidas, necesitamos que el usuario autorice
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # La primera vez, el usuario deberá autenticar
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Guardar credenciales para la próxima vez
        os.makedirs(os.path.dirname(token_path), exist_ok=True)
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    
    return creds

def crear_servicio_calendario(email):
    """Crea un servicio de Google Calendar"""
    creds = obtener_credenciales(email)
    service = build('calendar', 'v3', credentials=creds)
    return service

def crear_servicio_gmail(email):
    """Crea un servicio de Gmail para enviar correos"""
    creds = obtener_credenciales(email)
    service = build('gmail', 'v1', credentials=creds)
    return service

def agregar_evento_calendario(tarea, fecha_limite, email):
    """Agrega una tarea como evento al calendario del usuario"""
    try:
        service = crear_servicio_calendario(email)
        
        # Parsear la fecha límite
        fecha_obj = datetime.datetime.strptime(fecha_limite, "%Y-%m-%d %H:%M:%S")
        
        # Crear evento
        evento = {
            'summary': f"Tarea: {tarea}",
            'description': f"Tarea pendiente: {tarea}",
            'start': {
                'dateTime': fecha_obj.isoformat(),
                'timeZone': 'America/Los_Angeles',  # Ajustar según zona horaria
            },
            'end': {
                'dateTime': (fecha_obj + timedelta(hours=1)).isoformat(),
                'timeZone': 'America/Los_Angeles',  # Ajustar según zona horaria
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},
                    {'method': 'popup', 'minutes': 30},
                ],
            },
        }
        
        # Insertar el evento en el calendario principal
        event = service.events().insert(calendarId='primary', body=evento).execute()
        
        return f"Evento creado en el calendario: {event.get('htmlLink')}"
        
    except Exception as e:
        print(f"Error al agregar evento al calendario: {e}")
        return f"No se pudo agregar la tarea al calendario: {e}"

def listar_eventos_proximos(email, dias=7):
    """Lista los próximos eventos del calendario"""
    try:
        service = crear_servicio_calendario(email)
        
        # Calcular fechas
        ahora = datetime.datetime.utcnow().isoformat() + 'Z'
        limite = (datetime.datetime.utcnow() + timedelta(days=dias)).isoformat() + 'Z'
        
        # Obtener eventos
        eventos = service.events().list(
            calendarId='primary',
            timeMin=ahora,
            timeMax=limite,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        # Procesar eventos
        items = eventos.get('items', [])
        if not items:
            return "No hay eventos próximos en tu calendario."
        
        resultado = f"Próximos eventos en tu calendario (próximos {dias} días):\n"
        for evento in items:
            start = evento['start'].get('dateTime', evento['start'].get('date'))
            fecha = datetime.datetime.fromisoformat(start.replace('Z', '+00:00'))
            resultado += f"- {fecha.strftime('%Y-%m-%d %H:%M')} - {evento['summary']}\n"
        
        return resultado
        
    except Exception as e:
        print(f"Error al listar eventos del calendario: {e}")
        return f"No se pudieron obtener los eventos: {e}"

def enviar_recordatorio_email(email_usuario, tarea, fecha_limite):
    """Envía un correo electrónico de recordatorio para una tarea"""
    try:
        service = crear_servicio_gmail(email_usuario)
        
        # Crear mensaje
        mensaje = MIMEMultipart()
        mensaje['to'] = email_usuario
        mensaje['subject'] = f"Recordatorio: Tarea pendiente - {tarea}"
        
        # Cuerpo del mensaje
        cuerpo = f"""
        <html>
        <body>
            <h2>Recordatorio de Tarea Pendiente</h2>
            <p>Hola,</p>
            <p>Te recordamos que tienes la siguiente tarea pendiente:</p>
            <div style="background-color: #f5f5f5; padding: 15px; border-left: 5px solid #4285f4;">
                <h3>{tarea}</h3>
                <p><strong>Fecha límite:</strong> {fecha_limite}</p>
            </div>
            <p>No olvides completarla a tiempo.</p>
            <p>Saludos,<br>Tu Asistente de Tareas</p>
        </body>
        </html>
        """
        
        # Adjuntar cuerpo HTML
        parte_html = MIMEText(cuerpo, 'html')
        mensaje.attach(parte_html)
        
        # Convertir a formato raw
        raw_message = base64.urlsafe_b64encode(mensaje.as_bytes()).decode()
        
        # Enviar mensaje
        message = service.users().messages().send(
            userId="me", 
            body={'raw': raw_message}
        ).execute()
        
        return f"Recordatorio enviado por correo electrónico: {message['id']}"
        
    except Exception as e:
        print(f"Error al enviar recordatorio por email: {e}")
        return f"No se pudo enviar el recordatorio: {e}"

def sincronizar_tareas_calendario(email):
    """Sincroniza todas las tareas con fecha límite al calendario"""
    try:
        # Obtener todas las tareas del usuario
        ruta_archivo = f"usuarios/{email}/tareas.json"
        
        with open(ruta_archivo, "r") as file:
            data = json.load(file)
            
            # Filtrar tareas con fecha límite
            tareas_con_fecha = [t for t in data["tareas"] if t["fecha_limite"] and not t["completada"]]
            
            if not tareas_con_fecha:
                return "No hay tareas con fecha límite para sincronizar."
            
            # Sincronizar cada tarea
            sincronizadas = 0
            for tarea in tareas_con_fecha:
                resultado = agregar_evento_calendario(
                    tarea["descripcion"], 
                    tarea["fecha_limite"], 
                    email
                )
                if "Evento creado" in resultado:
                    sincronizadas += 1
            
            return f"Se sincronizaron {sincronizadas} tareas con tu calendario."
            
    except Exception as e:
        print(f"Error al sincronizar tareas con calendario: {e}")
        return f"Error en la sincronización: {e}"

def programar_recordatorios_automaticos(email):
    """Configura recordatorios automáticos para tareas próximas"""
    try:
        # Obtener todas las tareas del usuario
        ruta_archivo = f"usuarios/{email}/tareas.json"
        
        with open(ruta_archivo, "r") as file:
            data = json.load(file)
            
            # Filtrar tareas con fecha límite próxima (dentro de 24 horas)
            ahora = datetime.datetime.now()
            manana = ahora + timedelta(hours=24)
            
            tareas_proximas = []
            for tarea in data["tareas"]:
                if tarea["fecha_limite"] and not tarea["completada"]:
                    fecha_limite = datetime.datetime.strptime(
                        tarea["fecha_limite"], "%Y-%m-%d %H:%M:%S")
                    if ahora < fecha_limite <= manana:
                        tareas_proximas.append(tarea)
            
            if not tareas_proximas:
                return "No hay tareas próximas para recordar."
            
            # Enviar recordatorios para cada tarea próxima
            enviados = 0
            for tarea in tareas_proximas:
                resultado = enviar_recordatorio_email(
                    email, 
                    tarea["descripcion"], 
                    tarea["fecha_limite"]
                )
                if "Recordatorio enviado" in resultado:
                    enviados += 1
            
            return f"Se enviaron {enviados} recordatorios por email para tareas próximas."
            
    except Exception as e:
        print(f"Error al programar recordatorios: {e}")
        return f"Error al programar recordatorios: {