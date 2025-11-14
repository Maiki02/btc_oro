"""
Cliente para enviar notificaciones mediante Telegram Bot API.
"""
import requests
import logging
from typing import Dict, List, Optional
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TelegramClient:
    """
    Cliente para enviar broadcasts de notificaciones a través de Telegram Bot API.
    
    Envía mensajes sobre precios de BTC y XAU a los suscriptores del bot.
    """
    
    def __init__(self, api_url: str, api_key: str):
        """
        Inicializa el cliente de Telegram.
        
        Args:
            api_url: URL del endpoint de broadcast del bot de Telegram
            api_key: API Key para autenticación
        """
        self.api_url = api_url
        self.api_key = api_key
        self.timeout = 10  # Timeout de 10 segundos
        
        logger.info("TelegramClient inicializado")
    
    def send_price_notification(
        self,
        hour: int,
        btc_price: Optional[float] = None,
        xau_price: Optional[float] = None
    ) -> bool:
        """
        Envía una notificación con los precios actuales de BTC y XAU.
        
        Args:
            hour: Hora a la que se obtuvieron los precios (0-23)
            btc_price: Precio de Bitcoin en USD (opcional)
            xau_price: Precio de Oro por onza en USD (opcional)
        
        Returns:
            True si el envío fue exitoso, False en caso contrario
        """
        try:
            # Construir el mensaje principal
            first_message = f"📊 Precios actualizados a las {hour:02d}:00 hs"
            
            # Construir las entradas individuales por suscripción
            entries = []
            
            if btc_price is not None:
                btc_formatted = self._format_price(btc_price)
                entries.append({
                    "subscription": "prices:BTC",
                    "message": f"₿ Bitcoin: ${btc_formatted} USD"
                })
            
            if xau_price is not None:
                xau_formatted = self._format_price(xau_price)
                entries.append({
                    "subscription": "prices:XAU",
                    "message": f"🥇 Oro (XAU): ${xau_formatted} USD/oz"
                })
            
            # Si no hay precios, no enviar nada
            if not entries:
                logger.warning("No hay precios para notificar")
                return False
            
            # Construir payload
            payload = {
                "first_message": first_message,
                "entries": entries
            }
            
            logger.info(f"Enviando notificación Telegram para hora {hour}")
            logger.debug(f"Payload: {payload}")
            
            # Realizar POST request
            response = requests.post(
                self.api_url,
                json=payload,
                headers={
                    'x-api-key': self.api_key,
                    'Content-Type': 'application/json'
                },
                timeout=self.timeout
            )
            
            # Verificar respuesta
            response.raise_for_status()
            
            logger.info(f"✓ Notificación Telegram enviada exitosamente (status: {response.status_code})")
            logger.debug(f"Respuesta: {response.text}")
            
            return True
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout al enviar notificación Telegram (>{self.timeout}s)")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al enviar notificación Telegram: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado al enviar notificación Telegram: {e}", exc_info=True)
            return False
    
    def _format_price(self, price: float) -> str:
        """
        Formatea un precio para mostrar de forma legible.
        
        Args:
            price: Precio numérico
        
        Returns:
            String formateado (ej: "43,250.75")
        """
        return f"{price:,.2f}"
    
    def test_connection(self) -> bool:
        """
        Prueba la conexión con la API de Telegram (envía un mensaje de test).
        
        Returns:
            True si la conexión es exitosa, False en caso contrario
        """
        try:
            logger.info("Probando conexión con Telegram API...")
            
            payload = {
                "first_message": "🧪 Test de conexión",
                "entries": [
                    {
                        "subscription": "prices:BTC",
                        "message": "Test message"
                    }
                ]
            }
            
            response = requests.post(
                self.api_url,
                json=payload,
                headers={
                    'x-api-key': self.api_key,
                    'Content-Type': 'application/json'
                },
                timeout=self.timeout
            )
            
            response.raise_for_status()
            logger.info("✓ Conexión con Telegram API exitosa")
            return True
            
        except Exception as e:
            logger.error(f"Error al probar conexión con Telegram API: {e}")
            return False
