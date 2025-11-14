"""
Lambda Handler para AWS Lambda.

Este es el punto de entrada para AWS Lambda. Traduce eventos de Lambda
(provenientes de API Gateway, CloudWatch, etc.) a las funciones del servicio.

IMPORTANTE: Este archivo NO reemplaza a main.py
- main.py se usa para desarrollo local (servidor HTTP tradicional)
- lambda_handler.py se usa para AWS Lambda (sin servidor/serverless)
"""
import json
import logging
import os
from urllib.parse import parse_qs

# Importar dependencias del proyecto
from src.config import Config
from src.clients import CoinGeckoClient, GoldApiClient, GoogleSheetClient, TelegramClient
from src.repositories import PriceRepository
from src.services import PriceDataService
from src.handlers import PriceHandler
from src.middleware import AuthMiddleware

# Configurar logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Variables globales para reutilizar entre invocaciones (mejora de rendimiento)
# En Lambda, la función se "congela" entre invocaciones, permitiendo reutilizar objetos
_price_handler = None


def _initialize_dependencies():
    """
    Inicializa todas las dependencias de la aplicación.
    
    Se ejecuta solo la primera vez (en el Cold Start), luego se reutiliza
    gracias a las variables globales.
    
    Returns:
        Instancia de PriceHandler
    """
    global _price_handler
    
    logger.info("Inicializando dependencias...")
    
    try:
        # Inicializar clientes de API
        coingecko_client = CoinGeckoClient(Config.COINGECKO_API_KEY)
        goldapi_client = GoldApiClient(Config.GOLDAPI_KEY)
        google_sheet_client = GoogleSheetClient(Config.GOOGLE_SHEET_API_URL)
        
        logger.info("✓ Clientes de API inicializados")
        
        # Inicializar cliente de Telegram (opcional)
        telegram_client = None
        if Config.TELEGRAM_API_URL and Config.TELEGRAM_API_KEY:
            try:
                telegram_client = TelegramClient(
                    api_url=Config.TELEGRAM_API_URL,
                    api_key=Config.TELEGRAM_API_KEY
                )
                logger.info("✓ TelegramClient inicializado")
            except Exception as e:
                logger.warning(f"⚠️  No se pudo inicializar TelegramClient: {e}")
        else:
            logger.warning("⚠️  TELEGRAM_API_URL o TELEGRAM_API_KEY no configuradas")
        
        # Inicializar repositorio (MongoDB)
        try:
            price_repository = PriceRepository(
                mongo_uri=Config.MONGO_URI,
                db_name=Config.MONGO_DB_NAME
            )
            logger.info("✓ Repositorio MongoDB inicializado")
        except Exception as e:
            logger.warning(f"⚠️  MongoDB no disponible: {e}. Continuando sin persistencia.")
            price_repository = None
        
        # Inicializar servicio
        price_service = PriceDataService(
            coingecko_client=coingecko_client,
            goldapi_client=goldapi_client,
            google_sheet_client=google_sheet_client,
            telegram_client=telegram_client,
            price_repository=price_repository
        )
        
        logger.info("✓ Servicio de precios inicializado")
        
        # Inicializar handler
        _price_handler = PriceHandler(price_service)
        
        logger.info("✓ Dependencias inicializadas correctamente")
        
        return _price_handler
        
    except Exception as e:
        logger.error(f"Error inicializando dependencias: {e}", exc_info=True)
        raise


def _parse_query_parameters(event):
    """
    Extrae los query parameters del evento de Lambda.
    
    El evento puede venir de diferentes fuentes:
    - API Gateway (tiene queryStringParameters)
    - CloudWatch Events (no tiene query parameters)
    
    Args:
        event: Evento de Lambda
    
    Returns:
        Diccionario con los query parameters
    """
    query_params = {}
    
    if event.get('queryStringParameters'):
        query_params = event['queryStringParameters']
    elif event.get('body'):
        # Si viene como formulario POST
        try:
            query_params = json.loads(event['body'])
        except (json.JSONDecodeError, TypeError):
            pass
    
    return query_params or {}


def _create_response(status_code, body):
    """
    Crea una respuesta HTTP en el formato esperado por API Gateway.
    
    Args:
        status_code: Código HTTP (200, 400, 500, etc.)
        body: Cuerpo de la respuesta (será convertido a JSON)
    
    Returns:
        Diccionario en formato de respuesta de API Gateway
    """
    return {
        'statusCode': status_code,
        'body': json.dumps(body, default=str),
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        }
    }


def lambda_handler(event, context):
    """
    Manejador principal de AWS Lambda.
    
    Este es el punto de entrada que AWS Lambda ejecuta. Recibe un evento
    y un contexto, y debe retornar una respuesta en formato de API Gateway.
    
    Endpoints soportados:
    - GET /health
    - GET /api/v1/health
    - GET /api/v1/trigger-fetch
    
    Args:
        event: Evento desencadenante de API Gateway
        context: Contexto de ejecución de Lambda
    
    Returns:
        Diccionario con statusCode, body y headers para API Gateway
    """
    
    global _price_handler
    
    try:
        logger.info(f"Evento recibido: {json.dumps(event)}")
        
        # Extraer información del evento de API Gateway
        http_method = event.get('httpMethod', 'GET')
        path = event.get('rawPath') or event.get('path', '/')
        query_string_params = event.get('queryStringParameters') or {}
        headers = event.get('headers') or {}
        
        logger.info(f"Método: {http_method}, Path: {path}")
        logger.info(f"Headers recibidos: {json.dumps(headers)}")
        logger.info(f"API_KEY configurada: {Config.API_KEY[:10] if Config.API_KEY else 'NO CONFIGURADA'}...")
        
        # =========================================================================
        # VALIDAR AUTENTICACIÓN (MIDDLEWARE)
        # =========================================================================
        is_valid, error_message = AuthMiddleware.validate_api_key(headers, path)
        
        if not is_valid:
            logger.warning(f"Autenticación fallida: {error_message}")
            response = AuthMiddleware.create_unauthorized_response(error_message)
            return _create_response(response['status'], response['body'])
        
        # =========================================================================
        # AUTENTICACIÓN EXITOSA - PROCESAR REQUEST
        # =========================================================================
        
        # Inicializar dependencias si es la primera invocación
        if _price_handler is None:
            _price_handler = _initialize_dependencies()
        
        # Procesar según el path
        if path == '/health' or path == '/api/v1/health':
            logger.info("Ejecutando health-check...")
            handler_response = _price_handler.handle_health_check()
        
        elif path == '/api/v1/trigger-fetch':
            logger.info("Ejecutando trigger-fetch...")
            handler_response = _price_handler.handle_trigger_fetch(query_string_params)
        
        else:
            logger.warning(f"Path no reconocido: {path}")
            return _create_response(404, {
                'success': False,
                'message': 'Endpoint no encontrado',
                'path': path,
                'available_endpoints': [
                    'GET /health',
                    'GET /api/v1/health',
                    'GET /api/v1/trigger-fetch?hour=10'
                ]
            })
        
        # Convertir respuesta del handler al formato de API Gateway
        status_code = handler_response.get('status', 200)
        body = handler_response.get('body', {})
        
        logger.info(f"Respuesta exitosa: status_code={status_code}")
        
        return _create_response(status_code, body)
    
    except Exception as e:
        logger.error(f"Error en lambda_handler: {e}", exc_info=True)
        
        return _create_response(500, {
            'success': False,
            'message': 'Error interno del servidor',
            'error': str(e)
        })


# Evento de prueba (para testing en AWS Console)
if __name__ == "__main__":
    # Ejemplo de evento de prueba
    test_event = {
        "queryStringParameters": {
            "hour": "10"
        },
        "path": "/api/v1/trigger-fetch"
    }
    
    # Contexto dummy para pruebas locales
    class MockContext:
        function_name = "btc-oro-fetcher"
        invoked_function_arn = "arn:aws:lambda:us-east-1:123456789:function:btc-oro-fetcher"
    
    result = lambda_handler(test_event, MockContext())
    print(json.dumps(result, indent=2))
