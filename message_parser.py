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
                r'quiero\s+facturar\s+(\d+)\s+(.+?)\s+(?:al|a)\s+RFC\s+(\w+)'
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
    def validar_rfc(rfc):
        """Valida el formato de un RFC mexicano"""
        if not rfc:
            return False
        
        # Patrón básico para RFC
        patron_rfc = r'^[A-Z&Ñ]{3,4}\d{6}[A-Z\d]{3}$'
        return bool(re.match(patron_rfc, rfc))