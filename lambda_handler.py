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
from src.clients import CoinGeckoClient, GoldApiClient, GoogleSheetClient
from src.repositories import PriceRepository
from src.services import PriceDataService
from src.handlers import PriceHandler

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
    y un contexto, y debe retornar una respuesta.
    
    Eventos esperados:
    - De API Gateway: event['queryStringParameters']['hour']
    - De CloudWatch: event['source'] == 'aws.events'
    - Manual: event['action'] == 'trigger-fetch'
    
    Args:
        event: Evento desencadenante (dict)
        context: Contexto de ejecución de Lambda (objeto)
    
    Returns:
        Diccionario con statusCode y body
    
    Ejemplos de eventos:
    
    # 1. Desde API Gateway GET /trigger-fetch?hour=10
    {
        "queryStringParameters": {"hour": "10"}
    }
    
    # 2. Desde CloudWatch Events (cron job automático)
    {
        "source": "aws.events",
        "detail-type": "Scheduled Event"
    }
    
    # 3. Test manual
    {
        "action": "trigger-fetch"
    }
    """
    
    global _price_handler
    
    logger.info(f"Evento recibido: {json.dumps(event)}")
    logger.info(f"Contexto: function_name={context.function_name}, "
                f"invoked_function_arn={context.invoked_function_arn}")
    
    try:
        # Inicializar dependencias si es la primera invocación
        if _price_handler is None:
            _price_handler = _initialize_dependencies()
        
        # Extraer parámetros de la query
        query_params = _parse_query_parameters(event)
        
        logger.info(f"Query parameters: {query_params}")
        
        # Determinar la acción a realizar
        path = event.get('path', '/api/v1/trigger-fetch')
        
        # Enrutar la petición según el path
        if '/trigger-fetch' in path or event.get('action') == 'trigger-fetch':
            logger.info("Ejecutando trigger-fetch...")
            handler_response = _price_handler.handle_trigger_fetch(query_params)
        
        elif '/health' in path or event.get('action') == 'health':
            logger.info("Ejecutando health-check...")
            handler_response = _price_handler.handle_health_check()
        
        else:
            logger.warning(f"Path no reconocido: {path}")
            return _create_response(404, {
                'success': False,
                'message': 'Endpoint no encontrado',
                'path': path
            })
        
        # Convertir respuesta del handler al formato de API Gateway
        status_code = handler_response.get('status', 200)
        body = handler_response.get('body', {})
        
        logger.info(f"Respuesta: status_code={status_code}")
        
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
