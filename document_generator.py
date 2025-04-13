# document_generator.py (mejorado para múltiples productos)
from fpdf import FPDF
import os
import logging
from config import Config
from datetime import datetime

logger = logging.getLogger(__name__)

class DocumentGenerator:
    def __init__(self):
        # Asegúrate de que exista el directorio para los PDFs
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    
    def generar_factura(self, rfc, productos, precios=None):
        """
        Genera un PDF con la factura para múltiples productos
        
        Args:
            rfc (str): RFC del cliente
            productos (list): Lista de diccionarios con los productos y cantidades
                             [{"nombre": "licencia", "cantidad": 2}, ...]
            precios (dict, optional): Diccionario con los precios de los productos
                                     {"licencia": 100.0, ...}
        """
        try:
            if precios is None:
                # Si no se proporciona un diccionario de precios, usar precio por defecto
                precios = {}
            
            # Generar PDF
            pdf = FPDF()
            pdf.add_page()
            
            # Encabezado
            pdf.set_font("Arial", "B", size=16)
            pdf.cell(200, 10, txt="FACTURA", ln=1, align="C")
            pdf.line(10, 25, 200, 25)
            
            # Información del cliente
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt=f"RFC: {rfc}", ln=1)
            fecha_actual = datetime.now().strftime("%d/%m/%Y")
            pdf.cell(200, 10, txt=f"Fecha: {fecha_actual}", ln=1)
            
            # Detalles de los productos
            pdf.set_font("Arial", "B", size=12)
            pdf.cell(100, 10, txt="Producto", border=1)
            pdf.cell(30, 10, txt="Cantidad", border=1)
            pdf.cell(30, 10, txt="Precio", border=1)
            pdf.cell(30, 10, txt="Total", border=1, ln=1)
            
            pdf.set_font("Arial", size=12)
            
            # Total general
            total_general = 0
            
            # Iterar sobre cada producto
            for producto in productos:
                nombre = producto.get("nombre", "Producto")
                cantidad = producto.get("cantidad", 1)
                
                # Obtener precio del producto, o usar precio por defecto
                precio_unitario = precios.get(nombre.lower(), 100.0)
                subtotal = float(cantidad) * precio_unitario
                total_general += subtotal
                
                # Agregar línea de producto
                pdf.cell(100, 10, txt=nombre, border=1)
                pdf.cell(30, 10, txt=str(cantidad), border=1)
                pdf.cell(30, 10, txt=f"${precio_unitario:.2f}", border=1)
                pdf.cell(30, 10, txt=f"${subtotal:.2f}", border=1, ln=1)
            
            # Total
            pdf.set_font("Arial", "B", size=12)
            pdf.cell(160, 10, txt="Total", border=1)
            pdf.cell(30, 10, txt=f"${total_general:.2f}", border=1, ln=1)
            
            # Guardar archivo
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"{Config.UPLOAD_FOLDER}/factura_{rfc}_{timestamp}.pdf"
            pdf.output(filename)
            logger.info(f"Factura generada: {filename}")
            
            return filename
        except Exception as e:
            logger.error(f"Error generando factura: {e}")
            return None