# ai_services.py (con prompts mejorados)
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
            # Prompt mejorado con ejemplos más diversos
            prompt = ChatPromptTemplate.from_template(
                "Eres un asistente especializado en sistemas de facturación que clasifica mensajes en una de estas categorías:\n"
                "- facturar: mensajes que solicitan generar una factura o documento fiscal. Ejemplos: 'Facturar 2 licencias', 'Necesito factura de 3 monitores y 1 teclado', 'Generar factura para 5 servicios de consultoría', 'Facturar los siguientes productos: 2 mesas, 4 sillas'.\n"
                "- consultar: mensajes que solicitan información sobre facturas existentes. Ejemplos: 'Consultar facturas de RFC ABC123456XYZ', 'Mostrar mis facturas del mes pasado', 'Ver facturas pendientes', 'Estado de mis facturas'.\n"
                "- ayuda: mensajes que piden instrucciones o información sobre el servicio. Ejemplos: '¿Cómo funciona?', 'Opciones disponibles', 'Necesito ayuda', 'No sé cómo usar este servicio'.\n"
                "- estado: mensajes que preguntan específicamente por el estado de una factura o trámite. Ejemplos: '¿En qué estado está mi factura?', 'Estado de trámite 12345', 'Seguimiento de factura'.\n"
                "- otro: mensajes que no pertenecen a ninguna categoría anterior como saludos, agradecimientos o consultas no relacionadas.\n\n"
                "Analiza el siguiente mensaje y clasifícalo en una sola categoría. Tu respuesta debe ser únicamente la categoría:\n\n"
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
    
    def extraer_detalles_con_llm(self, mensaje):
        """
        Utiliza el LLM para extraer detalles más complejos de un mensaje de facturación
        cuando los patrones regulares no son suficientes
        """
        if not self.llm:
            return None
            
        try:
            prompt = ChatPromptTemplate.from_template(
                "Extrae la información de facturación del siguiente mensaje. Debes identificar:\n"
                "1. El RFC del cliente\n"
                "2. Los productos mencionados y sus cantidades\n\n"
                "Devuelve tu respuesta en formato JSON con las siguientes propiedades:\n"
                "- rfc: El RFC mencionado (si existe)\n"
                "- productos: Lista de objetos, cada uno con 'nombre' y 'cantidad'\n\n"
                "Mensaje: {mensaje}\n\n"
                "JSON:"
            )
            chain = LLMChain(llm=self.llm, prompt=prompt)
            respuesta = chain.run(mensaje=mensaje).strip()
            
            # Intentar convertir la respuesta a JSON
            import json
            try:
                datos = json.loads(respuesta)
                return datos
            except json.JSONDecodeError:
                logger.warning(f"No se pudo decodificar la respuesta como JSON: {respuesta}")
                return None
                
        except Exception as e:
            logger.error(f"Error extrayendo detalles con LLM: {e}")
            return None
            
    def generar_respuesta_ayuda(self):
        """
        Genera un mensaje de ayuda para el usuario
        """
        return (
            "🔍 *Asistente de Facturación* 🔍\n\n"
            "Puedes realizar las siguientes acciones:\n\n"
            "📝 *Generar una factura*\n"
            "Ejemplo: \"Facturar 2 licencias a RFC ABC123456XYZ\"\n"
            "También puedes facturar varios productos: \"Facturar 2 licencias y 3 servicios a RFC ABC123456XYZ\"\n\n"
            "📊 *Consultar facturas*\n"
            "Ejemplo: \"Consultar facturas de RFC ABC123456XYZ\"\n\n"
            "❓ *Ayuda*\n"
            "Escribe \"ayuda\" para ver este mensaje\n\n"
            "📱 *Estado de facturas*\n"
            "Ejemplo: \"Estado de mi factura para RFC ABC123456XYZ\""
        )