# config.py
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Configuración de la aplicación
class Config:
    # Modo de prueba (no envía mensajes reales)
    TEST_MODE = os.getenv("TEST_MODE", "False").lower() == "true"
    
    # Twilio
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "whatsapp:+14155238886")
    
    # Base de datos
    DATABASE_URI = os.getenv("DATABASE_URI", "sqlite:///facturas.db")
    
    # LLM
    LLM_MODEL = os.getenv("LLM_MODEL", "llama2:7b")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.0"))
    
    # Aplicación
    BASE_URL = os.getenv("BASE_URL", "https://your-app.ngrok-free.app")
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "static")
    