"""
Handlers para procesar las peticiones HTTP.
"""
import json
import logging
from typing import Dict, Any

from ..services.service import PriceDataService

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PriceHandler:
    """
    Handler para gestionar las peticiones relacionadas con precios.
    """
    
    def __init__(self, price_service: PriceDataService):
        """
        Inicializa el handler con el servicio de precios.
        
        Args:
            price_service: Instancia de PriceDataService
        """
        self.price_service = price_service
    
    def handle_trigger_fetch(self, query_params: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Maneja la petición para iniciar la obtención de precios.
        
        Args:
            query_params: Parámetros de la query (opcional)
        
        Returns:
            Diccionario con la respuesta en formato JSON
        """
        try:
            logger.info("Recibida petición para obtener precios")
            
            # Extraer parámetro opcional de hora objetivo
            target_hour = None
            if query_params and 'hour' in query_params:
                try:
                    target_hour = int(query_params['hour'])
                except ValueError:
                    return {
                        'status': 400,
                        'body': {
                            'success': False,
                            'message': 'El parámetro hour debe ser un número entero',
                            'error': 'Invalid parameter'
                        }
                    }
            
            # Llamar al servicio
            result = self.price_service.fetch_and_store_prices(target_hour)
            
            # Determinar el código de estado HTTP
            status_code = 200 if result.success else 500
            
            # Preparar la respuesta
            response = {
                'status': status_code,
                'body': result.model_dump()
            }
            
            logger.info(f"Respuesta preparada: status={status_code}, success={result.success}")
            
            return response
            
        except Exception as e:
            logger.error(f"Error en el handler: {e}", exc_info=True)
            return {
                'status': 500,
                'body': {
                    'success': False,
                    'message': 'Error interno del servidor',
                    'error': str(e)
                }
            }
    
    def handle_health_check(self) -> Dict[str, Any]:
        """
        Maneja la petición de health check.
        
        Returns:
            Diccionario con la respuesta en formato JSON
        """
        return {
            'status': 200,
            'body': {
                'success': True,
                'version': "0.1.1",
                'message': 'Service is running',
                'service': 'BTC-Oro Price Fetcher'
            }
        }