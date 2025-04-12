# ai_services.py
from langchain_ollama import OllamaLLM
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from config import Config
import logging

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
    
    def clasificar_mensaje(self, mensaje):
        """
        Clasifica un mensaje en una de estas categorías: facturar, consultar, ayuda, estado, otro
        """
        if not mensaje or not self.llm:
            return "otro"
            
        try:
            prompt = ChatPromptTemplate.from_template(
                "Clasifica este mensaje usando exactamente una de estas opciones:\n"
                "- facturar (si solicita generar una factura)\n"
                "- consultar (si solicita ver facturas existentes)\n"
                "- ayuda (si pide instrucciones o ayuda)\n"
                "- estado (si pregunta por el estado de un trámite o factura)\n"
                "- otro (si no encaja en las anteriores)\n\n"
                "Mensaje: {mensaje}\n"
                "Respuesta (solo una palabra):"
            )
            chain = LLMChain(llm=self.llm, prompt=prompt)
            respuesta = chain.run(mensaje=mensaje)
            return respuesta.strip().lower()
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