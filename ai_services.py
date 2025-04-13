# ai_services.py
from langchain_ollama import OllamaLLM
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from config import Config
import logging
import re

logger = logging.getLogger(__name__)

class IAService:
    def __init__(self):
        try:
            self.llm = OllamaLLM(model=Config.LLM_MODEL, temperature=Config.LLM_TEMPERATURE)
            logger.info(f"Modelo LLM inicializado: {Config.LLM_MODEL}")
        except Exception as e:
            logger.error(f"Error inicializando LLM: {e}")
            # Fallback a un modelo simple si hay error
            self.llm = None
    
    def preprocesar_mensaje(self, mensaje):
        """
        Normaliza el mensaje eliminando ruido y preparándolo para el modelo.
        """
        mensaje = mensaje.lower().strip()  # Convertir a minúsculas y eliminar espacios
        mensaje = re.sub(r"[^a-zA-Z0-9áéíóúñü\s]", "", mensaje)  # Eliminar caracteres especiales
        return mensaje
    
    def clasificar_mensaje(self, mensaje):
        """
        Clasifica un mensaje en una de estas categorías: facturar, consultar, ayuda, estado, otro.
        """
        if not mensaje or not self.llm:
            return "otro"
            
        try:
            # Prompt mejorado con ejemplos claros
            prompt = ChatPromptTemplate.from_template(
                "Eres un asistente que clasifica mensajes en una de las siguientes categorías:\n"
                "- facturar: si el mensaje solicita generar una factura. Ejemplo: 'Facturar 2 licencias a RFC ABC123456XYZ', 'Hacer factura de 3 productos a RFC DEF456789HIJ'.\n"
                "- consultar: si el mensaje solicita ver, listar o mostrar facturas existentes. Ejemplo: 'Consultar facturas de RFC ABC123456XYZ', 'Ver facturas emitidas', 'Listar todas mis facturas'.\n"
                "- ayuda: si el mensaje solicita opciones, instrucciones o asistencia. Ejemplo: '¿Cómo puedo generar una factura?', 'Ayuda', 'Opciones disponibles', 'menu', 'help', 'opciones'.\n"
                "- estado: si el mensaje pregunta por el estado de un trámite o factura. Ejemplo: 'Estado de mi factura para RFC ABC123456XYZ', '¿Cuál es el estado de mi solicitud?'.\n"
                "- otro: si el mensaje no encaja en ninguna de las categorías anteriores.\n\n"
                "Clasifica el siguiente mensaje en una de las categorías anteriores. Responde con una sola palabra (facturar, consultar, ayuda, estado, otro):\n\n"
                "Mensaje: {mensaje}\n"
                "Respuesta:"
            )
            chain = LLMChain(llm=self.llm, prompt=prompt)
            respuesta = chain.run(mensaje=mensaje).strip().lower()

            # Validar que la respuesta esté en las categorías esperadas
            categorias_validas = {"facturar", "consultar", "ayuda", "estado", "otro"}
            if respuesta not in categorias_validas:
                logger.warning(f"Respuesta inesperada del modelo: {respuesta}")
                return "otro"
            
            return respuesta
        except Exception as e:
            logger.error(f"Error clasificando mensaje: {e}")
            return "otro"
            
    def generar_respuesta_ayuda(self):
        """
        Genera un mensaje de ayuda para el usuario
        """
        return (
            "🔍 *Asistente de Facturación* 🔍\n\n"
            "Puedes realizar las siguientes acciones:\n\n"
            "📝 *Generar una factura*\n"
            "Ejemplo: \"Facturar 2 licencias a RFC ABC123456XYZ\"\n\n"
            "📊 *Consultar facturas*\n"
            "Ejemplo: \"Consultar facturas de RFC ABC123456XYZ\"\n\n"
            "❓ *Ayuda*\n"
            "Escribe \"ayuda\" para ver este mensaje\n\n"
            "📱 *Estado de facturas*\n"
            "Ejemplo: \"Estado de mi factura para RFC ABC123456XYZ\""
        )
