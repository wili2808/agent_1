# document_generator.py
from fpdf import FPDF
import os
import logging
from config import Config

logger = logging.getLogger(__name__)

class DocumentGenerator:
    def __init__(self):
        # Asegúrate de que exista el directorio para los PDFs
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    
    def generar_factura(self, rfc, producto, cantidad, precio_unitario=100.0):
        """
        Genera un PDF con la factura
        """
        try:
            # Calcular total
            total = float(cantidad) * precio_unitario
            
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
            pdf.cell(200, 10, txt=f"Fecha: {os.popen('date').read().strip()}", ln=1)
            
            # Detalles del producto
            pdf.set_font("Arial", "B", size=12)
            pdf.cell(100, 10, txt="Producto", border=1)
            pdf.cell(30, 10, txt="Cantidad", border=1)
            pdf.cell(30, 10, txt="Precio", border=1)
            pdf.cell(30, 10, txt="Total", border=1, ln=1)
            
            pdf.set_font("Arial", size=12)
            pdf.cell(100, 10, txt=producto, border=1)
            pdf.cell(30, 10, txt=str(cantidad), border=1)
            pdf.cell(30, 10, txt=f"${precio_unitario:.2f}", border=1)
            pdf.cell(30, 10, txt=f"${total:.2f}", border=1, ln=1)
            
            # Total
            pdf.set_font("Arial", "B", size=12)
            pdf.cell(160, 10, txt="Total", border=1)
            pdf.cell(30, 10, txt=f"${total:.2f}", border=1, ln=1)
            
            # Guardar archivo
            filename = f"{Config.UPLOAD_FOLDER}/factura_{rfc}_{producto.replace(' ', '_')}.pdf"
            pdf.output(filename)
            logger.info(f"Factura generada: {filename}")
            
            return filename
        except Exception as e:
            logger.error(f"Error generando factura: {e}")
            return None