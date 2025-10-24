"""
Clientes para consumir las APIs externas.
"""
import requests
from typing import Optional, Dict, Any
import logging

from ..models.schemas import GoldApiResponse, CoinGeckoResponse

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# COINGECKO CLIENT
# =============================================================================
class CoinGeckoClient:
    """
    Cliente para la API de CoinGecko.
    """
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    
    def __init__(self, api_key: str):
        """
        Inicializa el cliente de CoinGecko.
        
        Args:
            api_key: API Key de CoinGecko
        """
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({'x-cg-demo-api-key': api_key})
    
    def get_bitcoin_price_in_range(self, from_timestamp: int, to_timestamp: int) -> CoinGeckoResponse:
        """
        Obtiene los precios de Bitcoin en un rango de tiempo.
        
        Args:
            from_timestamp: Timestamp de inicio en segundos (Unix)
            to_timestamp: Timestamp de fin en segundos (Unix)
        
        Returns:
            CoinGeckoResponse con los datos de precios
        
        Raises:
            requests.exceptions.RequestException: Si hay un error en la petición
            ValueError: Si la respuesta no es válida
        """
        endpoint = f"{self.BASE_URL}/coins/bitcoin/market_chart/range"
        params = {
            'vs_currency': 'usd',
            'from': from_timestamp,
            'to': to_timestamp
        }
        
        try:
            logger.info(f"Consultando CoinGecko API: from={from_timestamp}, to={to_timestamp}")
            response = self.session.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Respuesta de CoinGecko recibida: {len(data.get('prices', []))} puntos de precio")
            
            return CoinGeckoResponse(**data)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al consultar CoinGecko API: {e}")
            raise
        except Exception as e:
            logger.error(f"Error al procesar respuesta de CoinGecko: {e}")
            raise ValueError(f"Respuesta inválida de CoinGecko: {e}")


# =============================================================================
# GOLDAPI.IO CLIENT - NUEVO
# =============================================================================
class GoldApiClient:
    """
    Cliente para la API de GoldAPI.io
    """
    
    BASE_URL = "https://www.goldapi.io/api"
    
    def __init__(self, api_key: str):
        """
        Inicializa el cliente de GoldAPI.io.
        
        Args:
            api_key: API Key de GoldAPI.io
        """
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'x-access-token': api_key,
            'Content-Type': 'application/json'
        })
    
    def get_gold_price(self, symbol: str = "XAU", currency: str = "USD") -> GoldApiResponse:
        """
        Obtiene el precio actual del oro.
        
        Args:
            symbol: Símbolo del metal (default: "XAU" para oro)
            currency: Moneda de cotización (default: "USD")
        
        Returns:
            GoldApiResponse con los datos del oro
        
        Raises:
            requests.exceptions.RequestException: Si hay un error en la petición
            ValueError: Si la respuesta no es válida
        """
        endpoint = f"{self.BASE_URL}/{symbol}/{currency}"
        
        try:
            logger.info(f"Consultando GoldAPI.io: {symbol}/{currency}")
            response = self.session.get(endpoint, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Respuesta de GoldAPI.io recibida: precio={data.get('price', 'N/A')}")
            
            return GoldApiResponse(**data)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al consultar GoldAPI.io: {e}")
            raise
        except Exception as e:
            logger.error(f"Error al procesar respuesta de GoldAPI.io: {e}")
            raise ValueError(f"Respuesta inválida de GoldAPI.io: {e}")


class GoogleSheetClient:
    """
    Cliente para enviar datos a Google Sheets.
    """
    
    def __init__(self, api_url: str):
        """
        Inicializa el cliente de Google Sheets.
        
        Args:
            api_url: URL de la API de Google Sheets
        """
        self.api_url = api_url
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
    
    def save_record(self, data: Dict[str, Any]) -> bool:
        """
        Guarda un registro en Google Sheets.
        
        Args:
            data: Diccionario con los datos a guardar
        
        Returns:
            True si se guardó exitosamente, False en caso contrario
        
        Raises:
            requests.exceptions.RequestException: Si hay un error en la petición
        """
        try:
            logger.info(f"Enviando datos a Google Sheets: {data}")
            response = self.session.post(self.api_url, json=data, timeout=10)
            response.raise_for_status()
            
            logger.info("Datos enviados exitosamente a Google Sheets")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al enviar datos a Google Sheets: {e}")
            raise
        except Exception as e:
            logger.error(f"Error inesperado al enviar a Google Sheets: {e}")
            raise