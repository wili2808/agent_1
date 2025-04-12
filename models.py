# models.py
from sqlalchemy import Column, String, Integer, Float, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from config import Config

Base = declarative_base()

class Cliente(Base):
    __tablename__ = "clientes"
    id = Column(Integer, primary_key=True)
    rfc = Column(String(13), unique=True, nullable=False)
    nombre = Column(String(100), nullable=False)
    email = Column(String(100))
    telefono = Column(String(20))
    fecha_registro = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return f"<Cliente(rfc='{self.rfc}', nombre='{self.nombre}')>"

class Factura(Base):
    __tablename__ = "facturas"
    id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer)
    producto = Column(String(100), nullable=False)
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    fecha_emision = Column(DateTime, default=datetime.now)
    ruta_pdf = Column(String(200))
    
    def __repr__(self):
        return f"<Factura(id={self.id}, cliente_id={self.cliente_id}, producto='{self.producto}')>"

# Inicialización de la base de datos
def init_db():
    engine = create_engine(Config.DATABASE_URI)
    Base.metadata.create_all(engine)
    return engine

# Crear sesión de base de datos
def get_db_session():
    engine = init_db()
    Session = sessionmaker(bind=engine)
    return Session()