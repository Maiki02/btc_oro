"""
Archivo principal del servidor HTTP.
"""
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import logging
from urllib.parse import urlparse

from src.config import Config
from src.clients import CoinGeckoClient, GoldApiClient, GoogleSheetClient, TelegramClient
from src.repositories import PriceRepository
from src.services import PriceDataService
from src.handlers import PriceHandler
from src.routes import Router
from src.middleware import AuthMiddleware

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RequestHandler(BaseHTTPRequestHandler):
    """
    Handler personalizado para procesar las peticiones HTTP.
    """
    
    # El router se inicializará una vez y se compartirá entre todas las instancias
    router = None
    
    def do_GET(self):
        """
        Maneja las peticiones GET.
        """
        try:
            # Parsear la URL
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            query_string = parsed_url.query
            
            # =========================================================================
            # VALIDAR AUTENTICACIÓN (MIDDLEWARE)
            # =========================================================================
            # Convertir headers HTTP a diccionario
            headers = {key: value for key, value in self.headers.items()}
            
            is_valid, error_message = AuthMiddleware.validate_api_key(headers, path)
            
            if not is_valid:
                logger.warning(f"Autenticación fallida: {error_message}")
                response = AuthMiddleware.create_unauthorized_response(error_message)
                self._send_response(response)
                return
            
            # =========================================================================
            # AUTENTICACIÓN EXITOSA - PROCESAR REQUEST
            # =========================================================================
            
            # Enrutar la petición
            response = self.router.route_request('GET', path, query_string)
            
            # Enviar la respuesta
            self._send_response(response)
            
        except Exception as e:
            logger.error(f"Error procesando petición GET: {e}", exc_info=True)
            self._send_error_response(500, str(e))
    
    def do_POST(self):
        """
        Maneja las peticiones POST.
        """
        self._send_error_response(405, "Método POST no implementado")
    
    def _send_response(self, response: dict):
        """
        Envía una respuesta HTTP.
        
        Args:
            response: Diccionario con 'status' y 'body'
        """
        status_code = response.get('status', 200)
        body = response.get('body', {})
        
        # Enviar código de estado
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        # Enviar cuerpo de la respuesta
        response_json = json.dumps(body, default=str, indent=2)
        self.wfile.write(response_json.encode('utf-8'))
    
    def _send_error_response(self, status_code: int, message: str):
        """
        Envía una respuesta de error.
        
        Args:
            status_code: Código de estado HTTP
            message: Mensaje de error
        """
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        
        error_response = {
            'success': False,
            'message': message,
            'status_code': status_code
        }
        
        response_json = json.dumps(error_response, indent=2)
        self.wfile.write(response_json.encode('utf-8'))
    
    def log_message(self, format, *args):
        """
        Sobrescribe el método de logging para usar el logger configurado.
        """
        logger.info(f"{self.address_string()} - {format % args}")


def initialize_dependencies():
    """
    Inicializa todas las dependencias de la aplicación.
    
    Returns:
        Instancia del Router configurado
    """
    logger.info("Inicializing dependencies...")
    
    # Validar configuración (COMENTADO para pruebas)
    # try:
    #     Config.validate_config()
    # except ValueError as e:
    #     logger.error(f"Error en la configuración: {e}")
    #     raise
    
    logger.warning("⚠️  MODO DE PRUEBA: Validación de config desactivada")
    
    # Inicializar clientes de API
    coingecko_client = CoinGeckoClient(Config.COINGECKO_API_KEY)
    goldapi_client = GoldApiClient(Config.GOLDAPI_KEY)
    google_sheet_client = GoogleSheetClient(Config.GOOGLE_SHEET_API_URL)
    
    # Inicializar cliente de Telegram (opcional)
    telegram_client = None
    if Config.TELEGRAM_API_URL and Config.TELEGRAM_API_KEY:
        try:
            telegram_client = TelegramClient(
                api_url=Config.TELEGRAM_API_URL,
                api_key=Config.TELEGRAM_API_KEY
            )
            logger.info("✓ TelegramClient inicializado correctamente")
        except Exception as e:
            logger.warning(f"⚠️  No se pudo inicializar TelegramClient: {e}")
    else:
        logger.warning("⚠️  TELEGRAM_API_URL o TELEGRAM_API_KEY no configuradas")
    
    # Inicializar repositorio
    try:
        price_repository = PriceRepository(
            mongo_uri=Config.MONGO_URI,
            db_name=Config.MONGO_DB_NAME
        )
        logger.info("✓ Repository MongoDB inicializado correctamente")
    except Exception as e:
        logger.error(f"Error al conectar MongoDB: {e}")
        logger.warning("⚠️  MongoDB no disponible. El servicio continuará pero sin persistencia.")
        price_repository = None
    
    # Inicializar servicio
    price_service = PriceDataService(
        coingecko_client=coingecko_client,
        goldapi_client=goldapi_client,
        google_sheet_client=google_sheet_client,
        telegram_client=telegram_client,
        price_repository=price_repository
    )
    
    # Inicializar handler
    price_handler = PriceHandler(price_service)
    
    # Inicializar router
    router = Router(price_handler)
    
    logger.info("Dependencias inicializadas correctamente")
    logger.info(f"Rutas disponibles: {router.get_available_routes()}")
    
    return router


def run_server():
    """
    Inicia el servidor HTTP.
    """
    try:
        # Inicializar dependencias
        router = initialize_dependencies()
        
        # Asignar el router a la clase RequestHandler
        RequestHandler.router = router
        
        # Configurar y arrancar el servidor
        server_address = ('', Config.SERVER_PORT)
        httpd = HTTPServer(server_address, RequestHandler)
        
        logger.info(f"Servidor iniciado en http://localhost:{Config.SERVER_PORT}")
        logger.info("Presiona Ctrl+C para detener el servidor")
        
        # Imprimir información útil
        print("\n" + "="*60)
        print(f"🚀 Servidor BTC-Oro ejecutándose en puerto {Config.SERVER_PORT}")
        print("="*60)
        print("\nEndpoints disponibles:")
        for route in router.get_available_routes():
            print(f"  • {route}")
        print("\nEjemplos de uso:")
        print(f"  curl http://localhost:{Config.SERVER_PORT}/api/v1/health")
        print(f"  curl http://localhost:{Config.SERVER_PORT}/api/v1/trigger-fetch")
        print(f"  curl http://localhost:{Config.SERVER_PORT}/api/v1/trigger-fetch?hour=10")
        print("="*60 + "\n")
        
        # Iniciar el servidor
        httpd.serve_forever()
        
    except KeyboardInterrupt:
        logger.info("\nServidor detenido por el usuario")
        httpd.shutdown()
    except Exception as e:
        logger.error(f"Error al iniciar el servidor: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    run_server()