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
            # Timeout de 15 segundos (CoinGecko suele ser rápido)
            response = self.session.get(endpoint, params=params, timeout=15)
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
    
    def get_gold_price(self, symbol: str = "XAU", currency: str = "USD", retry_count: int = 2) -> GoldApiResponse:
        """
        Obtiene el precio actual del oro.
        
        Implementa reintentos automáticos en caso de timeout.
        GoldAPI.io puede ser lento ocasionalmente.
        
        Args:
            symbol: Símbolo del metal (default: "XAU" para oro)
            currency: Moneda de cotización (default: "USD")
            retry_count: Número de reintentos en caso de timeout (default: 2)
        
        Returns:
            GoldApiResponse con los datos del oro
        
        Raises:
            requests.exceptions.RequestException: Si hay un error en la petición
            ValueError: Si la respuesta no es válida
        """
        endpoint = f"{self.BASE_URL}/{symbol}/{currency}"
        last_error = None
        
        for attempt in range(retry_count + 1):
            try:
                logger.info(f"Consultando GoldAPI.io: {symbol}/{currency}" + 
                           (f" (intento {attempt + 1}/{retry_count + 1})" if attempt > 0 else ""))
                
                # Usar timeout más generoso (30s en lugar de 10s)
                # GoldAPI.io puede tardar, especialmente en horas pico
                response = self.session.get(endpoint, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                logger.info(f"Respuesta de GoldAPI.io recibida: precio={data.get('price', 'N/A')}")
                
                return GoldApiResponse(**data)
                
            except requests.exceptions.Timeout as e:
                last_error = e
                logger.warning(f"Timeout en GoldAPI.io (intento {attempt + 1}/{retry_count + 1}): {e}")
                if attempt < retry_count:
                    logger.info(f"Reintentando...")
                    continue
                else:
                    logger.error(f"GoldAPI.io agotó reintentos por timeout")
                    raise
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Error al consultar GoldAPI.io: {e}")
                raise
            except Exception as e:
                logger.error(f"Error al procesar respuesta de GoldAPI.io: {e}")
                raise ValueError(f"Respuesta inválida de GoldAPI.io: {e}")
        
        # Fallback (no debería llegar aquí)
        raise last_error if last_error else Exception("Error desconocido en GoldAPI.io")


class GoogleSheetClient:
    """
    Cliente para enviar datos a Google Sheets.
    
    Envía la estructura consolidada de precios diarios (como viene de MongoDB)
    directamente al Google Apps Script. El script es responsable de procesar
    y formatear los datos como sea necesario.
    """
    
    def __init__(self, api_url: str):
        """
        Inicializa el cliente de Google Sheets.
        
        Args:
            api_url: URL de la API de Google Sheets (Google Apps Script)
        """
        self.api_url = api_url
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
    
    def save_record(self, daily_record_dict: Dict[str, Any]) -> bool:
        """
        Envía un registro de precios consolidado a Google Sheets.
        
        Envía la estructura completa del documento MongoDB:
        {
            "date": "2025-10-25",
            "date_art": "2025-10-24T15:55:53.125396-03:00",
            "prices": {
                "BTC": [
                    {
                        "hour": 17,
                        "price_usd": 110340.829253726,
                        "timestamp_utc": "2025-10-24T17:55:52.341000Z",
                        "source_api": "coingecko",
                        "collection_time_art": "2025-10-24T15:55:53.125396-03:00"
                    }
                ],
                "XAU": [
                    {
                        "hour": 17,
                        "price_usd": 4500,
                        "timestamp_utc": "2025-10-24T18:55:53.125396Z",
                        "source_api": "goldapi",
                        "collection_time_art": "2025-10-24T15:55:53.125396-03:00"
                    }
                ]
            }
        }
        
        El Google Apps Script recibe este JSON y es responsable de:
        - Procesar y formatear los datos
        - Escribir en las celdas correspondientes
        - Aplicar estilos, validaciones, etc.
        
        Args:
            daily_record_dict: Diccionario con la estructura consolidada
                             (resultado de DailyPriceRecord.model_dump(mode='json'))
        
        Returns:
            True si se envió exitosamente, False en caso contrario
        """
        try:
            if not self.api_url:
                logger.warning("URL de Google Sheets no configurada. Saltando envío.")
                return False
            
            logger.info(f"Enviando DailyPriceRecord a Google Sheets para fecha: {daily_record_dict.get('date')}")
            logger.debug(f"Payload: {daily_record_dict}")
            
            # POST directo a la URL con la estructura completa
            response = self.session.post(
                self.api_url,
                json=daily_record_dict,
                timeout=15
            )
            response.raise_for_status()
            
            logger.info(f"✓ Datos enviados exitosamente a Google Sheets. Status: {response.status_code}")
            return True
            
        except requests.exceptions.Timeout:
            logger.error("Timeout al enviar a Google Sheets (>15s)")
            return False
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error HTTP al enviar a Google Sheets: {response.status_code} - {e}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de conexión al enviar a Google Sheets: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado al enviar a Google Sheets: {e}", exc_info=True)
            return False