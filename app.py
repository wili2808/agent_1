# app.py
from flask import Flask, request, send_from_directory
import logging
import os
from twilio_service import TwilioService
from ai_services import IAService
from message_parser import MessageParser
from document_generator import DocumentGenerator
from models import get_db_session, Cliente, Factura, Producto, DetalleFactura
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

# Ruta para recibir mensajes de WhatsApp
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
        # Preprocesar el mensaje
        user_msg = ia_service.preprocesar_mensaje(user_msg)
        logger.info(f"Mensaje preprocesado: {user_msg}")

        # Clasificar intención del mensaje
        intencion = ia_service.clasificar_mensaje(user_msg)
        logger.info(f"Intención detectada: {intencion}")
        
        # Procesar según la intención
        
        if "facturar" in intencion:
            # Extraer datos del mensaje
            datos = parser.extraer_datos_factura(user_msg)
            logger.info(f"Datos extraídos: {datos}")
        
            # Si la extracción regular falló, intentar con el LLM
            if not datos['productos'] and not datos['rfc']:
                datos_llm = ia_service.extraer_detalles_con_llm(user_msg)
                if datos_llm:
                    datos = datos_llm
                    logger.info(f"Datos extraídos con LLM: {datos}")
        
            # Validar datos
            if not datos['rfc']:
                respuesta.message("⚠️ No pude identificar el RFC en tu solicitud. Por favor, incluye el RFC en tu mensaje.")
            elif not datos['productos'] or len(datos['productos']) == 0:
                respuesta.message("⚠️ No pude identificar productos en tu solicitud. Por favor, especifica los productos y cantidades.")
            elif not parser.validar_rfc(datos['rfc']):
                respuesta.message("⚠️ El RFC proporcionado no tiene un formato válido. Un RFC debe tener 12 caracteres para personas morales o 13 para personas físicas.")
            else:
                # Obtener precios de los productos
                from producto_service import ProductoService
                precios = ProductoService.obtener_precios_productos(datos['productos'])
                
                # Generar factura con múltiples productos
                pdf_path = doc_generator.generar_factura(
                    datos["rfc"], 
                    datos["productos"],
                    precios
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
                        
                        # Crear registro de factura (cabecera)
                        total_factura = sum(item['cantidad'] * precios.get(item['nombre'].lower(), 100.0) for item in datos['productos'])
                        
                        factura = Factura(
                            cliente_id=cliente.id,
                            producto=", ".join([f"{p['cantidad']} {p['nombre']}" for p in datos['productos']]),
                            cantidad=sum(p['cantidad'] for p in datos['productos']),
                            precio_unitario=0.0,  # Ya no relevante para múltiples productos
                            total=total_factura,
                            ruta_pdf=pdf_path
                        )
                        db_session.add(factura)
                        db_session.flush()
                        
                        # Crear registros de detalle para cada producto
                        for item in datos['productos']:
                            nombre_producto = item['nombre']
                            cantidad = item['cantidad']
                            precio = precios.get(nombre_producto.lower(), 100.0)
                            
                            # Buscar producto en la BD o crear uno nuevo
                            producto = db_session.query(Producto).filter(Producto.nombre.ilike(f"%{nombre_producto}%")).first()
                            if not producto:
                                producto = Producto(
                                    codigo=nombre_producto[:10].upper(),
                                    nombre=nombre_producto,
                                    precio=precio
                                )
                                db_session.add(producto)
                                db_session.flush()
                            
                            # Crear detalle de factura
                            detalle = DetalleFactura(
                                factura_id=factura.id,
                                producto_id=producto.id,
                                cantidad=cantidad,
                                precio_unitario=precio,
                                subtotal=cantidad * precio
                            )
                            db_session.add(detalle)
                        
                        db_session.commit()
                    except Exception as e:
                        logger.error(f"Error guardando en DB: {e}")
                        db_session.rollback()
                    
                    # Enviar factura
                    logger.info(f"Enviando PDF: {pdf_path}")
                    if twilio_service.enviar_factura(pdf_path, sender):
                        # Formar detalle de productos para el mensaje
                        detalle_productos = ""
                        for p in datos['productos']:
                            precio = precios.get(p['nombre'].lower(), 100.0)
                            subtotal = precio * p['cantidad']

        
        elif "consultar" in intencion:
            # Extraer RFC para consulta
            datos = parser.extraer_datos_consulta(user_msg)
            logger.info(f"Datos de consulta: {datos}")
            
            if not datos['rfc']:
                respuesta.message("⚠️ Por favor, especifica el RFC para consultar facturas.\n"
                                 "Ejemplo: \"Consultar facturas de RFC ABC123456XYZ\"")
            elif not parser.validar_rfc(datos['rfc']):
                respuesta.message("⚠️ El RFC proporcionado no tiene un formato válido. Verifica e intenta nuevamente.")
            else:
                # Consultar facturas en la base de datos
                try:
                    db_session = get_db_session()
                    cliente = db_session.query(Cliente).filter_by(rfc=datos["rfc"]).first()
                    
                    if not cliente:
                        respuesta.message(f"📝 No se encontraron registros para el RFC {datos['rfc']}")
                    else:
                        facturas = db_session.query(Factura).filter_by(cliente_id=cliente.id).all()
                        
                        if not facturas:
                            respuesta.message(f"📝 El cliente con RFC {datos['rfc']} está registrado pero no tiene facturas emitidas.")
                        else:
                            # Formatear la respuesta
                            mensaje = f"📊 *Facturas encontradas para RFC {datos['rfc']}*\n\n"
                            
                            for i, factura in enumerate(facturas, 1):
                                fecha = factura.fecha_emision.strftime("%d/%m/%Y")
                                mensaje += f"*{i}.* {factura.producto} ({factura.cantidad}) - ${factura.total:.2f} - {fecha}\n"
                            
                            respuesta.message(mensaje)
                except Exception as e:
                    logger.error(f"Error consultando facturas: {e}")
                    respuesta.message("❌ Ocurrió un error al consultar las facturas. Intenta nuevamente más tarde.")
        

        elif "ayuda" in intencion:
            # Enviar mensaje de ayuda
            respuesta.message(ia_service.generar_respuesta_ayuda())


        elif "estado" in intencion:
            # Por ahora, dar una respuesta genérica para estado
            respuesta.message("🔍 El sistema de consulta de estado de facturas está en desarrollo. Próximamente podrás consultar el estado de tus trámites.")


        else:
            # Respuesta para mensajes no reconocidos
            respuesta.message("🤖 No he entendido tu mensaje. Puedes escribir *ayuda* para ver las opciones disponibles.")
            
    except Exception as e:
        logger.error(f"Error crítico: {str(e)}")
        respuesta.message("⚠️ Ha ocurrido un error inesperado. Por favor, intenta nuevamente más tarde o contacta a soporte técnico.")
    
    return str(respuesta)



# Ruta para verificar estado del servicio
@app.route("/health", methods=["GET"])
def health_check():
    return {"status": "ok", "version": "1.0.0"}



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
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                .form-group { margin-bottom: 15px; }
                label { display: block; margin-bottom: 5px; font-weight: bold; }
                input, textarea { width: 100%; padding: 8px; box-sizing: border-box; border: 1px solid #ddd; border-radius: 4px; }
                button { padding: 10px 15px; background: #4CAF50; color: white; border: none; cursor: pointer; border-radius: 4px; }
                button:hover { background: #45a049; }
                .response { margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 5px; }
                .examples { margin-top: 20px; padding: 15px; background: #e9f7fe; border-radius: 5px; }
                .example { padding: 8px; cursor: pointer; margin-bottom: 5px; background: #d1ecf1; border-radius: 4px; }
                .example:hover { background: #bee5eb; }
                h3 { color: #2c3e50; }
            </style>
        </head>
        <body>
            <h1>Prueba de Webhook</h1>
            <form action="/test/webhook" method="post">
                <div class="form-group">
                    <label for="Body">Mensaje:</label>
                    <textarea name="Body" id="messageInput" rows="3" required placeholder="Ej: Facturar 2 remeras a RFC ASDD121212ASD"></textarea>
                </div>
                <div class="form-group">
                    <label for="From">Número de WhatsApp (con whatsapp: prefijo):</label>
                    <input type="text" name="From" required value="whatsapp:+5491112345678">
                </div>
                <button type="submit">Enviar</button>
            </form>
            
            <div class="examples">
                <h3>Ejemplos de mensajes:</h3>
                <div class="example" onclick="fillMessage('Facturar 2 licencias a RFC XAXX010101000')">Facturar 2 licencias a RFC XAXX010101000</div>
                <div class="example" onclick="fillMessage('Necesito una factura por 3 servicios para RFC XAXX010101000')">Necesito una factura por 3 servicios para RFC XAXX010101000</div>
                <div class="example" onclick="fillMessage('Consultar facturas de RFC XAXX010101000')">Consultar facturas de RFC XAXX010101000</div>
                <div class="example" onclick="fillMessage('Ver facturas del RFC XAXX010101000')">Ver facturas del RFC XAXX010101000</div>
                <div class="example" onclick="fillMessage('ayuda')">ayuda</div>
            </div>
            
            <div class="response">
                <h3>Información:</h3>
                <p>Esta página simula el envío de un mensaje como si viniera de Twilio.</p>
                <p>Modo de prueba: <strong>{"Activado" if Config.TEST_MODE else "Desactivado"}</strong></p>
                <p>En modo de prueba no se envían mensajes reales a Twilio.</p>
            </div>
            
            <script>
                function fillMessage(text) {
                    document.getElementById('messageInput').value = text;
                }
            </script>
        </body>
        </html>
        """
    
    # Si es POST, procesar como si fuera una solicitud de Twilio
    logger.info("=== NUEVA SOLICITUD DE PRUEBA ===")
    
    # Obtener datos del formulario
    user_msg = request.form.get("Body", "").lower()
    sender = request.form.get("From", "")
    
    # Validar que sea un mensaje de WhatsApp
    if not sender.startswith('whatsapp:'):
        logger.warning(f"Remitente no válido: {sender}")
        return "Remitente no válido", 400

    # Crear respuesta de Twilio
    respuesta = twilio_service.crear_respuesta()
    
    try:
        # Preprocesar el mensaje
        user_msg = ia_service.preprocesar_mensaje(user_msg)
        logger.info(f"Mensaje preprocesado: {user_msg}")

        # Clasificar intención del mensaje
        intencion = ia_service.clasificar_mensaje(user_msg)
        logger.info(f"Intención detectada: {intencion}")
        
        # Procesar según la intención
        
        if "facturar" in intencion:
            # Extraer datos del mensaje
            datos = parser.extraer_datos_factura(user_msg)
            logger.info(f"Datos extraídos: {datos}")
        
            # Si la extracción regular falló, intentar con el LLM
            if not datos['productos'] and not datos['rfc']:
                datos_llm = ia_service.extraer_detalles_con_llm(user_msg)
                if datos_llm:
                    datos = datos_llm
                    logger.info(f"Datos extraídos con LLM: {datos}")
        
            # Validar datos
            if not datos['rfc']:
                respuesta.message("⚠️ No pude identificar el RFC en tu solicitud. Por favor, incluye el RFC en tu mensaje.")
            elif not datos['productos'] or len(datos['productos']) == 0:
                respuesta.message("⚠️ No pude identificar productos en tu solicitud. Por favor, especifica los productos y cantidades.")
            elif not parser.validar_rfc(datos['rfc']):
                respuesta.message("⚠️ El RFC proporcionado no tiene un formato válido. Un RFC debe tener 12 caracteres para personas morales o 13 para personas físicas.")
            else:
                # Obtener precios de los productos
                from producto_service import ProductoService
                precios = ProductoService.obtener_precios_productos(datos['productos'])
                
                # Generar factura con múltiples productos
                pdf_path = doc_generator.generar_factura(
                    datos["rfc"], 
                    datos["productos"],
                    precios
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
                        
                        # Crear registro de factura (cabecera)
                        total_factura = sum(item['cantidad'] * precios.get(item['nombre'].lower(), 100.0) for item in datos['productos'])
                        
                        factura = Factura(
                            cliente_id=cliente.id,
                            producto=", ".join([f"{p['cantidad']} {p['nombre']}" for p in datos['productos']]),
                            cantidad=sum(p['cantidad'] for p in datos['productos']),
                            precio_unitario=0.0,  # Ya no relevante para múltiples productos
                            total=total_factura,
                            ruta_pdf=pdf_path
                        )
                        db_session.add(factura)
                        db_session.flush()
                        
                        # Crear registros de detalle para cada producto
                        for item in datos['productos']:
                            nombre_producto = item['nombre']
                            cantidad = item['cantidad']
                            precio = precios.get(nombre_producto.lower(), 100.0)
                            
                            # Buscar producto en la BD o crear uno nuevo
                            producto = db_session.query(Producto).filter(Producto.nombre.ilike(f"%{nombre_producto}%")).first()
                            if not producto:
                                producto = Producto(
                                    codigo=nombre_producto[:10].upper(),
                                    nombre=nombre_producto,
                                    precio=precio
                                )
                                db_session.add(producto)
                                db_session.flush()
                            
                            # Crear detalle de factura
                            detalle = DetalleFactura(
                                factura_id=factura.id,
                                producto_id=producto.id,
                                cantidad=cantidad,
                                precio_unitario=precio,
                                subtotal=cantidad * precio
                            )
                            db_session.add(detalle)
                        
                        db_session.commit()
                    except Exception as e:
                        logger.error(f"Error guardando en DB: {e}")
                        db_session.rollback()
                    
                    # Enviar factura
                    logger.info(f"Enviando PDF: {pdf_path}")
                    if twilio_service.enviar_factura(pdf_path, sender):
                        # Formar detalle de productos para el mensaje
                        detalle_productos = ""
                        for p in datos['productos']:
                            precio = precios.get(p['nombre'].lower(), 100.0)
                            subtotal = precio * p['cantidad']

        
        elif "consultar" in intencion:
            # Extraer RFC para consulta
            datos = parser.extraer_datos_consulta(user_msg)
            logger.info(f"Datos de consulta: {datos}")
            
            if not datos['rfc']:
                respuesta.message("⚠️ Por favor, especifica el RFC para consultar facturas.\n"
                                 "Ejemplo: \"Consultar facturas de RFC ABC123456XYZ\"")
            elif not parser.validar_rfc(datos['rfc']):
                respuesta.message("⚠️ El RFC proporcionado no tiene un formato válido. Verifica e intenta nuevamente.")
            else:
                # Consultar facturas en la base de datos
                try:
                    db_session = get_db_session()
                    cliente = db_session.query(Cliente).filter_by(rfc=datos["rfc"]).first()
                    
                    if not cliente:
                        respuesta.message(f"📝 No se encontraron registros para el RFC {datos['rfc']}")
                    else:
                        facturas = db_session.query(Factura).filter_by(cliente_id=cliente.id).all()
                        
                        if not facturas:
                            respuesta.message(f"📝 El cliente con RFC {datos['rfc']} está registrado pero no tiene facturas emitidas.")
                        else:
                            # Formatear la respuesta
                            mensaje = f"📊 *Facturas encontradas para RFC {datos['rfc']}*\n\n"
                            
                            for i, factura in enumerate(facturas, 1):
                                fecha = factura.fecha_emision.strftime("%d/%m/%Y")
                                mensaje += f"*{i}.* {factura.producto} ({factura.cantidad}) - ${factura.total:.2f} - {fecha}\n"
                            
                            respuesta.message(mensaje)
                except Exception as e:
                    logger.error(f"Error consultando facturas: {e}")
                    respuesta.message("❌ Ocurrió un error al consultar las facturas. Intenta nuevamente más tarde.")
        

        elif "ayuda" in intencion:
            # Enviar mensaje de ayuda
            respuesta.message(ia_service.generar_respuesta_ayuda())


        elif "estado" in intencion:
            # Por ahora, dar una respuesta genérica para estado
            respuesta.message("🔍 El sistema de consulta de estado de facturas está en desarrollo. Próximamente podrás consultar el estado de tus trámites.")
    



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

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)