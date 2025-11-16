"""
Middleware para autenticación y validación de requests.
"""
import logging
from typing import Optional, Dict, Any

from .config import Config

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AuthMiddleware:
    """
    Middleware para validar autenticación mediante API Key.
    
    Valida que los requests incluyan un header 'X-API-Key' con la
    API Key correcta configurada en las variables de entorno.
    """
    
    # Header donde se espera recibir la API Key
    API_KEY_HEADER = 'X-API-Key'
    
    @classmethod
    def validate_api_key(
        cls,
        headers: Dict[str, str],
        path: str = '/'
    ) -> tuple[bool, Optional[str]]:
        """
        Valida que el request incluya una API Key válida.
        
        Args:
            headers: Diccionario con los headers del request
            path: Path del endpoint solicitado
        
        Returns:
            Tupla (is_valid, error_message)
            - is_valid: True si la autenticación es válida, False en caso contrario
            - error_message: Mensaje de error si la validación falla, None si es exitosa
        """
        
        # Verificar que la API Key esté configurada en el servidor
        configured_api_key = Config.API_KEY
        if not configured_api_key:
            logger.error("❌ API_KEY no configurada en variables de entorno")
            return False, "Server configuration error: API_KEY not set"
                
        # Normalizar headers (API Gateway puede enviar headers en diferentes formatos)
        normalized_headers = cls._normalize_headers(headers)
                
        # Extraer la API Key del header
        provided_api_key = normalized_headers.get(cls.API_KEY_HEADER.lower())
                
        if not provided_api_key:
            logger.warning(f"Request sin API Key en header '{cls.API_KEY_HEADER}'")
            return False, f"Missing authentication header: {cls.API_KEY_HEADER}"
        
        # Validar que la API Key coincida
        if provided_api_key != configured_api_key:
            logger.warning(f"API Key inválida. Esperada: {configured_api_key[:10]}..., Recibida: {provided_api_key[:10]}...")
            logger.warning(f"Longitud esperada: {len(configured_api_key)}, Longitud recibida: {len(provided_api_key)}")
            return False, "Invalid API Key"
        
        # Autenticación exitosa
        return True, None
    
    @classmethod
    def _normalize_headers(cls, headers: Dict[str, str]) -> Dict[str, str]:
        """
        Normaliza los headers a lowercase para comparación case-insensitive.
        
        API Gateway puede enviar headers con diferentes capitalizaciones.
        
        Args:
            headers: Diccionario original de headers
        
        Returns:
            Diccionario con keys en lowercase
        """
        if not headers:
            return {}
        
        return {k.lower(): v for k, v in headers.items()}
    
    @classmethod
    def create_unauthorized_response(cls, error_message: str = None) -> Dict[str, Any]:
        """
        Crea una respuesta de error 401 Unauthorized.
        
        Args:
            error_message: Mensaje de error personalizado
        
        Returns:
            Diccionario con la respuesta de error
        """
        return {
            'status': 401,
            'body': {
                'success': False,
                'message': error_message or 'Unauthorized: Invalid or missing API Key',
                'error': 'authentication_required',
                'hint': f'Include a valid API Key in the "{cls.API_KEY_HEADER}" header'
            }
        }
