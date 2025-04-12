# twilio_service.py
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from twilio.base.exceptions import TwilioRestException
import os
import logging
from config import Config

logger = logging.getLogger(__name__)

class TwilioService:
    def __init__(self):
        self.test_mode = Config.TEST_MODE
        if self.test_mode:
            logger.info("Iniciando Twilio en MODO PRUEBA (no se enviarán mensajes reales)")
            self.client = None
        else:
            try:
                self.client = Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)
                logger.info("Cliente Twilio inicializado")
            except Exception as e:
                logger.error(f"Error inicializando Twilio: {e}")
                self.client = None
    
    def enviar_factura(self, pdf_path, to):
        """
        Envía un PDF por WhatsApp usando Twilio
        """
        if self.test_mode:
            # En modo prueba, solo registra la acción pero no envía realmente
            logger.info(f"[MODO PRUEBA] Simulando envío de factura a {to}")
            logger.info(f"[MODO PRUEBA] Ruta del PDF: {pdf_path}")
            pdf_filename = os.path.basename(pdf_path)
            logger.info(f"[MODO PRUEBA] URL simulada: {Config.BASE_URL}/static/{pdf_filename}")
            return "TEST-MESSAGE-SID-12345"
        
        if not self.client:
            logger.error("Cliente Twilio no inicializado")
            return None
            
        try:
            # Construir URL pública del archivo
            # Asegúrate de que la URL incluya /static/ para coincidir con la ruta de tu aplicación
            pdf_filename = os.path.basename(pdf_path)
            pdf_url = f"{Config.BASE_URL}/static/{pdf_filename}"
            
            # Enviar mensaje
            message = self.client.messages.create(
                media_url=[pdf_url],
                from_=Config.TWILIO_PHONE_NUMBER,
                to=to
            )
            logger.info(f"Factura enviada a {to}, SID: {message.sid}")
            return message.sid
        except TwilioRestException as e:
            if e.code == 63038:  # Código para límite diario excedido
                logger.warning(f"Límite diario de mensajes Twilio excedido: {e}")
                return "LIMIT_EXCEEDED"
            else:
                logger.error(f"Error de Twilio al enviar factura: {e}")
                return None
        except Exception as e:
            logger.error(f"Error enviando factura: {e}")
            return None
    
    def crear_respuesta(self):
        """Crea un objeto de respuesta TwiML"""
        return MessagingResponse()