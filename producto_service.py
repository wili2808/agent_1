# producto_service.py
import logging
from models import get_db_session, Producto
from difflib import get_close_matches
import re

logger = logging.getLogger(__name__)

class ProductoService:
    @staticmethod
    def buscar_producto(nombre):
        """
        Busca un producto en la base de datos por su nombre
        Utiliza algoritmos de coincidencia aproximada para encontrar productos similares
        
        Args:
            nombre (str): Nombre del producto a buscar
            
        Returns:
            tuple: (Producto, precio) o (None, None) si no se encuentra
        """
        try:
            db_session = get_db_session()
            
            # Normalizar el nombre del producto (quitar caracteres especiales, minúsculas)
            nombre_normalizado = re.sub(r'[^\w\s]', '', nombre.lower())
            palabras_clave = nombre_normalizado.split()
            
            # Buscar productos en la base de datos
            productos = db_session.query(Producto).all()
            
            if not productos:
                logger.warning("No hay productos en la base de datos")
                return None, None
            
            # Obtener nombres normalizados de productos en la BD
            nombres_productos = [re.sub(r'[^\w\s]', '', p.nombre.lower()) for p in productos]
            
            # Buscar coincidencia exacta
            for idx, nombre_prod in enumerate(nombres_productos):
                if nombre_normalizado == nombre_prod:
                    logger.info(f"Coincidencia exacta encontrada: {productos[idx].nombre}")
                    return productos[idx], productos[idx].precio
            
            # Buscar por palabras clave
            for palabra in palabras_clave:
                if len(palabra) < 3:  # Ignorar palabras muy cortas
                    continue
                    
                for idx, nombre_prod in enumerate(nombres_productos):
                    if palabra in nombre_prod:
                        logger.info(f"Coincidencia por palabra clave encontrada: {productos[idx].nombre}")
                        return productos[idx], productos[idx].precio
            
            # Buscar coincidencia aproximada
            coincidencias = get_close_matches(nombre_normalizado, nombres_productos, n=1, cutoff=0.6)
            if coincidencias:
                idx = nombres_productos.index(coincidencias[0])
                logger.info(f"Coincidencia aproximada encontrada: {productos[idx].nombre}")
                return productos[idx], productos[idx].precio
            
            logger.warning(f"No se encontró producto similar a: {nombre}")
            return None, None
        except Exception as e:
            logger.error(f"Error buscando producto: {e}")
            return None, None
    
    @staticmethod
    def obtener_precios_productos(productos):
        """
        Obtiene los precios para una lista de productos
        
        Args:
            productos (list): Lista de diccionarios con nombres de productos
            
        Returns:
            dict: Diccionario con los precios {nombre_producto: precio}
        """
        precios = {}
        
        for producto in productos:
            nombre = producto.get("nombre", "").lower()
            if not nombre:
                continue
                
            # Buscar producto en la BD
            producto_db, precio = ProductoService.buscar_producto(nombre)
            
            if producto_db:
                precios[nombre] = precio
            else:
                # Si no se encuentra, usar precio por defecto
                precios[nombre] = 100.0
                
        return precios