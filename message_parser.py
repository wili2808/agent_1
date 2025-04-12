# message_parser.py
import re
import logging

logger = logging.getLogger(__name__)

class MessageParser:
    @staticmethod
    def extraer_datos_factura(mensaje):
        """
        Extrae datos de facturación del mensaje
        Formato esperado: "facturar <cantidad> <producto> a RFC <rfc>"
        """
        try:
            # Expresión regular mejorada para capturar diferentes formatos
            patrones = [
                # Patrón principal: "facturar 2 licencias a RFC ABC123"
                r'facturar\s+(\d+)\s+(.+?)\s+a\s+RFC\s+(\w+)',
                # Patrón alternativo: "facturar 2 licencias RFC ABC123"
                r'facturar\s+(\d+)\s+(.+?)\s+RFC\s+(\w+)',
                # Patrón alternativo: "quiero facturar 2 licencias al RFC ABC123"
                r'quiero\s+facturar\s+(\d+)\s+(.+?)\s+(?:al|a)\s+RFC\s+(\w+)',
                # Patrón para "necesito una factura por 2 productos para RFC ABC123"
                r'necesito\s+(?:una|un)\s+factura\s+por\s+(\d+)\s+(.+?)\s+para\s+(?:el\s+)?RFC\s+(\w+)',
                # Patrón para "generar factura de 3 servicios RFC ABC123"
                r'generar\s+factura\s+de\s+(\d+)\s+(.+?)\s+(?:para\s+)?(?:el\s+)?RFC\s+(\w+)',
                # Patrón para "emitir factura: 2 equipos, RFC ABC123"
                r'emitir\s+factura\s*:\s*(\d+)\s+(.+?)(?:\s*,\s*|\s+)(?:para\s+)?RFC\s+(\w+)'
            ]
            
            for patron in patrones:
                match = re.search(patron, mensaje, re.IGNORECASE)
                if match:
                    return {
                        "cantidad": match.group(1),
                        "producto": match.group(2).strip(),
                        "rfc": match.group(3).strip().upper()
                    }
            
            # Si no se encontró coincidencia con ningún patrón
            logger.warning(f"No se pudo extraer datos de: '{mensaje}'")
            return {"cantidad": None, "producto": None, "rfc": None}
        except Exception as e:
            logger.error(f"Error extrayendo datos: {e}")
            return {"cantidad": None, "producto": None, "rfc": None}
    
    @staticmethod
    def extraer_datos_consulta(mensaje):
        """
        Extrae datos para consulta de facturas
        Formato esperado: "consultar facturas de/para RFC <rfc>"
        """
        try:
            patrones = [
                # "consultar facturas RFC ABC123"
                r'consultar\s+facturas\s+(?:de\s+)?(?:para\s+)?(?:el\s+)?RFC\s+(\w+)',
                # "mostrar facturas para RFC ABC123"
                r'mostrar\s+facturas\s+(?:de\s+)?(?:para\s+)?(?:el\s+)?RFC\s+(\w+)',
                # "ver facturas del RFC ABC123"
                r'ver\s+facturas\s+(?:de\s+)?(?:para\s+)?(?:el\s+)?RFC\s+(\w+)',
                # "facturas emitidas a RFC ABC123"
                r'facturas\s+emitidas\s+(?:a|para|de)\s+(?:el\s+)?RFC\s+(\w+)'
            ]
            
            for patron in patrones:
                match = re.search(patron, mensaje, re.IGNORECASE)
                if match:
                    return {"rfc": match.group(1).strip().upper()}
            
            # Si no se encontró coincidencia específica pero menciona consulta y RFC
            # Patrón genérico para extraer cualquier RFC mencionado en un mensaje de consulta
            if re.search(r'consulta|ver|mostrar|listar|facturas', mensaje, re.IGNORECASE):
                rfc_match = re.search(r'RFC\s+(\w+)', mensaje, re.IGNORECASE)
                if rfc_match:
                    return {"rfc": rfc_match.group(1).strip().upper()}
            
            logger.warning(f"No se pudo extraer RFC para consulta: '{mensaje}'")
            return {"rfc": None}
        except Exception as e:
            logger.error(f"Error extrayendo datos de consulta: {e}")
            return {"rfc": None}
    
    @staticmethod
    def validar_rfc(rfc):
        """
        Valida el formato de un RFC mexicano
        
        RFC Persona Física: 13 caracteres
        RFC Persona Moral: 12 caracteres
        """
        if not rfc:
            return False
        
        # Patrón completo para RFC (permite 12 o 13 caracteres)
        patron_rfc = r'^[A-Z&Ñ]{3,4}\d{6}[A-Z\d]{3}$'
        
        # Verificar longitud y formato
        if not re.match(patron_rfc, rfc):
            return False
            
        return True