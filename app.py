# app.py
from flask import Flask, request, send_from_directory
import logging
import os
from twilio_service import TwilioService
from ai_services import IAService
from message_parser import MessageParser
from document_generator import DocumentGenerator
from models import get_db_session, Cliente, Factura
from config import Config

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Inicialización de servicios
twilio_service = TwilioService()
ia_service = IAService()
doc_generator = DocumentGenerator()
parser = MessageParser()

# Inicialización de Flask
app = Flask(__name__)

# Ruta para servir archivos estáticos
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(Config.UPLOAD_FOLDER, filename)

# Webhook principal
@app.route("/webhook", methods=["POST"])
def webhook():
    logger.info("=== NUEVA SOLICITUD ===")
    logger.debug(f"Datos recibidos: {request.form}")
    
    # Obtener mensaje y remitente
    user_msg = request.form.get("Body", "").lower()
    sender = request.form.get("From", "")
    
    # Validar que sea un mensaje de WhatsApp
    if not sender.startswith('whatsapp:'):
        logger.warning(f"Remitente no válido: {sender}")
        return "Remitente no válido", 400

    # Crear respuesta de Twilio
    respuesta = twilio_service.crear_respuesta()
    
    try:
        # Clasificar intención del mensaje
        intencion = ia_service.clasificar_mensaje(user_msg)
        logger.info(f"Intención detectada: {intencion}")
        
        # Procesar según la intención
        if "facturar" in intencion:
            # Extraer datos del mensaje
            datos = parser.extraer_datos_factura(user_msg)
            logger.info(f"Datos extraídos: {datos}")
            
            # Validar datos
            if not datos['rfc'] or not datos['producto'] or not datos['cantidad']:
                respuesta.message("⚠️ Formato incorrecto. Ejemplo: 'Facturar 2 licencias a RFC ABC123'")
            elif not parser.validar_rfc(datos['rfc']):
                respuesta.message("⚠️ El RFC proporcionado no tiene un formato válido")
            else:
                # Generar factura
                pdf_path = doc_generator.generar_factura(
                    datos["rfc"], 
                    datos["producto"], 
                    int(datos["cantidad"])
                )
                
                if pdf_path:
                    # Guardar información en la base de datos
                    try:
                        db_session = get_db_session()
                        
                        # Buscar o crear cliente
                        cliente = db_session.query(Cliente).filter_by(rfc=datos["rfc"]).first()
                        if not cliente:
                            cliente = Cliente(rfc=datos["rfc"], nombre="Cliente " + datos["rfc"])
                            db_session.add(cliente)
                            db_session.flush()
                        
                        # Crear registro de factura
                        factura = Factura(
                            cliente_id=cliente.id,
                            producto=datos["producto"],
                            cantidad=int(datos["cantidad"]),
                            precio_unitario=100.0,  # Valor por defecto
                            total=100.0 * int(datos["cantidad"]),
                            ruta_pdf=pdf_path
                        )
                        db_session.add(factura)
                        db_session.commit()
                    except Exception as e:
                        logger.error(f"Error guardando en DB: {e}")
                        db_session.rollback()
                    
                    # Enviar factura
                    logger.info(f"Enviando PDF: {pdf_path}")
                    if twilio_service.enviar_factura(pdf_path, sender):
                        respuesta.message("✅ Factura generada y enviada. Revisa tus archivos adjuntos.")
                    else:
                        respuesta.message("⚠️ Factura generada pero hubo un error al enviarla. Intente nuevamente.")
                else:
                    respuesta.message("❌ Error generando la factura. Por favor, intente más tarde.")
        
        elif "consultar" in intencion:
            # Aquí puedes implementar la lógica para consultas
            respuesta.message("Para consultar facturas, especifique el RFC. Ejemplo: 'Consultar facturas RFC ABC123'")
        
        else:
            # Respuesta para mensajes no reconocidos
            respuesta.message("🤖 No he entendido tu mensaje. Puedes:\n- Facturar: 'Facturar 2 productos a RFC TU_RFC'\n- Consultar: 'Consultar facturas'")
            
    except Exception as e:
        logger.error(f"Error crítico: {str(e)}")
        respuesta.message("⚠️ Error interno. Contacte al soporte.")
    
    return str(respuesta)

# Ruta para verificar estado del servicio
@app.route("/health", methods=["GET"])
def health_check():
    return {"status": "ok", "version": "1.0.0"}

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)

# Ruta para simular un mensaje de WhatsApp (para pruebas)
@app.route("/test/webhook", methods=["GET", "POST"])
def test_webhook():
    """
    Endpoint para probar el webhook sin usar Twilio.
    
    Uso:
    - GET: Muestra un formulario simple para enviar mensajes
    - POST: Procesa el mensaje como si viniera de Twilio
    """
    if request.method == "GET":
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Prueba de Webhook</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                .form-group { margin-bottom: 15px; }
                label { display: block; margin-bottom: 5px; }
                input, textarea { width: 100%; padding: 8px; box-sizing: border-box; }
                button { padding: 10px 15px; background: #4CAF50; color: white; border: none; cursor: pointer; }
                .response { margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 5px; }
            </style>
        </head>
        <body>
            <h1>Prueba de Webhook</h1>
            <form action="/test/webhook" method="post">
                <div class="form-group">
                    <label for="Body">Mensaje:</label>
                    <textarea name="Body" rows="3" required placeholder="Ej: Facturar 2 remeras a RFC ASDD121212ASD"></textarea>
                </div>
                <div class="form-group">
                    <label for="From">Número de WhatsApp (con whatsapp: prefijo):</label>
                    <input type="text" name="From" required value="whatsapp:+5491112345678">
                </div>
                <button type="submit">Enviar</button>
            </form>
            
            <div class="response">
                <h3>Información:</h3>
                <p>Esta página simula el envío de un mensaje como si viniera de Twilio.</p>
                <p>Modo de prueba: <strong>{"Activado" if Config.TEST_MODE else "Desactivado"}</strong></p>
                <p>En modo de prueba no se envían mensajes reales a Twilio.</p>
            </div>
        </body>
        </html>
        """
    
    # Si es POST, procesar como si fuera una solicitud de Twilio
    logger.info("=== NUEVA SOLICITUD DE PRUEBA ===")
    
    # Obtener datos del formulario
    user_msg = request.form.get("Body", "")
    sender = request.form.get("From", "")
    
    # Validar que sea un formato de WhatsApp
    if not sender.startswith('whatsapp:'):
        return "Error: El número debe comenzar con 'whatsapp:'", 400
    
    # Crear una solicitud similar a la que enviaría Twilio
    mock_request_data = {
        "Body": user_msg,
        "From": sender,
        "To": Config.TWILIO_PHONE_NUMBER
    }
    
    # Log para depuración
    logger.info(f"Datos de prueba: {mock_request_data}")
    
    try:
        # Procesar el mensaje igual que en la ruta webhook normal
        intencion = ia_service.clasificar_mensaje(user_msg)
        logger.info(f"Intención detectada: {intencion}")
        
        # Crear respuesta
        respuesta = twilio_service.crear_respuesta()
        
        if "facturar" in intencion:
            datos = parser.extraer_datos_factura(user_msg)
            logger.info(f"Datos extraídos: {datos}")
            
            if not datos['rfc'] or not datos['producto'] or not datos['cantidad']:
                respuesta.message("⚠️ Formato incorrecto. Ejemplo: 'Facturar 2 licencias a RFC ABC123'")
            elif not parser.validar_rfc(datos['rfc']):
                respuesta.message("⚠️ El RFC proporcionado no tiene un formato válido")
            else:
                pdf_path = doc_generator.generar_factura(
                    datos["rfc"], 
                    datos["producto"], 
                    int(datos["cantidad"])
                )
                
                if pdf_path:
                    # Guardar en DB y enviar factura (igual que en webhook normal)
                    try:
                        db_session = get_db_session()
                        
                        # Buscar o crear cliente
                        cliente = db_session.query(Cliente).filter_by(rfc=datos["rfc"]).first()
                        if not cliente:
                            cliente = Cliente(rfc=datos["rfc"], nombre="Cliente " + datos["rfc"])
                            db_session.add(cliente)
                            db_session.flush()
                        
                        # Crear factura
                        factura = Factura(
                            cliente_id=cliente.id,
                            producto=datos["producto"],
                            cantidad=int(datos["cantidad"]),
                            precio_unitario=100.0,
                            total=100.0 * int(datos["cantidad"]),
                            ruta_pdf=pdf_path
                        )
                        db_session.add(factura)
                        db_session.commit()
                    except Exception as e:
                        logger.error(f"Error guardando en DB: {e}")
                        db_session.rollback()
                    
                    # Enviar factura (o simular envío en modo prueba)
                    if twilio_service.enviar_factura(pdf_path, sender):
                        respuesta.message("✅ Factura generada y enviada. Revisa tus archivos adjuntos.")
                        
                        # En modo prueba, ofrecer un enlace para ver el PDF
                        if Config.TEST_MODE:
                            pdf_filename = os.path.basename(pdf_path)
                            respuesta.message(f"[MODO PRUEBA] Ver factura: {Config.BASE_URL}/static/{pdf_filename}")
                    else:
                        respuesta.message("⚠️ Error al enviar factura. Intente nuevamente.")
                else:
                    respuesta.message("❌ Error generando la factura.")
        else:
            respuesta.message("No entendí. Envía 'Facturar 2 productos a RFC TU_RFC'")
        
        # Convertir la respuesta TwiML a HTML para mostrarla en el navegador
        twiml_response = str(respuesta)
        html_response = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Resultado de Prueba</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
                .back-link {{ margin-bottom: 20px; }}
                .result {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin-top: 20px; }}
                .twiml {{ background: #e9ecef; padding: 15px; border-radius: 5px; margin-top: 20px; font-family: monospace; white-space: pre-wrap; }}
                .message {{ background: #d4edda; padding: 15px; border-radius: 5px; margin-top: 20px; }}
                .pdf-link {{ margin-top: 20px; }}
                a {{ color: #007bff; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            <div class="back-link">
                <a href="/test/webhook">&larr; Volver</a>
            </div>
            
            <h1>Resultado de Prueba</h1>
            
            <div class="result">
                <h3>Solicitud:</h3>
                <p><strong>De:</strong> {sender}</p>
                <p><strong>Mensaje:</strong> {user_msg}</p>
                <p><strong>Intención detectada:</strong> {intencion}</p>
            </div>
            
            <div class="message">
                <h3>Respuesta:</h3>
                <p>{twiml_response.replace('<Message>', '').replace('</Message>', '').strip()}</p>
            </div>
            
            <div class="twiml">
                <h3>TwiML Generado:</h3>
                {twiml_response}
            </div>
            
            <div class="pdf-link">
                <p>Si se generó una factura, puedes verla en la carpeta <strong>{Config.UPLOAD_FOLDER}</strong>.</p>
            </div>
        </body>
        </html>
        """
        return html_response
        
    except Exception as e:
        logger.error(f"Error en prueba: {str(e)}")
        return f"Error: {str(e)}", 500

# Ruta para ver archivos generados
@app.route("/static/<path:filename>")
def ver_archivo(filename):
    """Ver archivos generados (útil en modo prueba)"""
    return send_from_directory(Config.UPLOAD_FOLDER, filename)