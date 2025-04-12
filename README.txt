# Agente IA para Facturación

Esta aplicación permite generar facturas a través de WhatsApp utilizando procesamiento de lenguaje natural.

## Características

- Recepción de mensajes de WhatsApp a través de Twilio
- Procesamiento de lenguaje natural con LangChain y Ollama
- Generación automática de facturas en PDF
- Almacenamiento de datos de clientes y facturas en base de datos
- API REST para integración con otros sistemas

## Configuración

1. Crea un archivo `.env` basado en el ejemplo proporcionado
2. Instala las dependencias: `pip install -r requirements.txt`
3. Inicia el servicio: `python app.py`
4. Para producción, usa: `gunicorn -w 4 -b 0.0.0.0:5000 app:app`

## Uso de la API

La aplicación expone las siguientes rutas:

- `POST /webhook`: Punto de entrada para mensajes de Twilio
- `GET /health`: Verificación del estado del servicio

## Formatos de mensajes soportados

- Facturación: "Facturar 2 licencias a RFC ABC123"
- Consulta: "Consultar facturas RFC ABC123"

## Estructura del proyecto

```
├── app.py                  # Aplicación principal
├── config.py               # Configuración centralizada
├── models.py               # Modelos de base de datos
├── ai_services.py          # Servicios de IA
├── message_parser.py       # Analizador de mensajes
├── document_generator.py   # Generador de documentos
├── twilio_service.py       # Servicio de Twilio
├── static/                 # Archivos generados
├── .env                    # Variables de entorno
└── requirements.txt        # Dependencias
```

## Seguridad

- No incluir el archivo `.env` en control de versiones
- Rotar periódicamente las credenciales de Twilio
- Utilizar HTTPS para todas las comunicaciones