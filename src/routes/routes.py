"""
Definición de rutas del servidor.
"""
from urllib.parse import parse_qs, urlparse
from typing import Dict, Any, Callable
import logging

from ..handlers.handler import PriceHandler

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Router:
    """
    Router para gestionar las rutas del servidor.
    """
    
    def __init__(self, price_handler: PriceHandler):
        """
        Inicializa el router con los handlers necesarios.
        
        Args:
            price_handler: Instancia de PriceHandler
        """
        self.price_handler = price_handler
        self.routes = self._define_routes()
    
    def _define_routes(self) -> Dict[str, Dict[str, Callable]]:
        """
        Define las rutas disponibles y sus handlers.
        
        Returns:
            Diccionario con las rutas y sus métodos
        """
        return {
            '/api/v1/trigger-fetch': {
                'GET': self._handle_trigger_fetch_route
            },
            '/api/v1/health': {
                'GET': self._handle_health_check_route
            },
            '/health': {
                'GET': self._handle_health_check_route
            }
        }
    
    def route_request(self, method: str, path: str, query_string: str = '') -> Dict[str, Any]:
        """
        Enruta una petición al handler correspondiente.
        
        Args:
            method: Método HTTP (GET, POST, etc.)
            path: Ruta de la petición
            query_string: String de query parameters
        
        Returns:
            Diccionario con la respuesta
        """
        logger.info(f"Enrutando petición: {method} {path}")
        
        # Verificar si la ruta existe
        if path not in self.routes:
            logger.warning(f"Ruta no encontrada: {path}")
            return {
                'status': 404,
                'body': {
                    'success': False,
                    'message': 'Ruta no encontrada',
                    'path': path
                }
            }
        
        # Verificar si el método está soportado
        if method not in self.routes[path]:
            logger.warning(f"Método no permitido: {method} para {path}")
            return {
                'status': 405,
                'body': {
                    'success': False,
                    'message': 'Método no permitido',
                    'allowed_methods': list(self.routes[path].keys())
                }
            }
        
        # Parsear query parameters
        query_params = {}
        if query_string:
            parsed = parse_qs(query_string)
            # Convertir listas de un elemento a strings
            query_params = {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
        
        # Ejecutar el handler correspondiente
        handler = self.routes[path][method]
        return handler(query_params)
    
    def _handle_trigger_fetch_route(self, query_params: Dict[str, str]) -> Dict[str, Any]:
        """
        Handler para la ruta /api/v1/trigger-fetch.
        
        Args:
            query_params: Parámetros de la query
        
        Returns:
            Respuesta del handler
        """
        return self.price_handler.handle_trigger_fetch(query_params)
    
    def _handle_health_check_route(self, query_params: Dict[str, str]) -> Dict[str, Any]:
        """
        Handler para la ruta /health.
        
        Args:
            query_params: Parámetros de la query (no usados)
        
        Returns:
            Respuesta del handler
        """
        return self.price_handler.handle_health_check()
    
    def get_available_routes(self) -> list:
        """
        Retorna la lista de rutas disponibles.
        
        Returns:
            Lista de rutas con sus métodos
        """
        routes_info = []
        for path, methods in self.routes.items():
            for method in methods.keys():
                routes_info.append(f"{method} {path}")
        return routes_info