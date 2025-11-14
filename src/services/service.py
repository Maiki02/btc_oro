"""
Capa de servicio con la lógica de negocio principal.
Orquesta la obtención, consolidación y almacenamiento de precios en la estructura
de documento diario unificado.
"""
from datetime import datetime
import logging
import pytz
import concurrent.futures

from ..clients.api_clients import CoinGeckoClient, GoldApiClient, GoogleSheetClient
from ..clients.telegram_client import TelegramClient
# from ..repositories.repository import PriceRepository  # COMENTADO - MongoDB
from ..models.schemas import (
    PriceEntry, DailyPriceRecord, GoogleSheetRecord, ServiceResponse, AssetPriceRecord
)
from ..utils.time_utils import (
    get_current_time_art, 
    get_timestamp_range_for_bitcoin,
    get_art_date_string
)
from ..config import Config

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PriceDataService:
    """
    Servicio principal que orquesta la obtención y almacenamiento de precios.
    
    Implementa la estructura consolidada donde todos los precios de un día se
    guardan en un único documento MongoDB, organizado por activo y hora.
    """
    
    def __init__(
        self,
        coingecko_client: CoinGeckoClient,
        goldapi_client: GoldApiClient,
        google_sheet_client: GoogleSheetClient,
        telegram_client: TelegramClient = None,
        price_repository=None  # INYECTADO - MongoDB (opcional para testing)
    ):
        """
        Inicializa el servicio con las dependencias inyectadas.
        
        Args:
            coingecko_client: Cliente para la API de CoinGecko
            goldapi_client: Cliente para la API de GoldAPI.io
            google_sheet_client: Cliente para Google Sheets
            telegram_client: Cliente para notificaciones Telegram (opcional)
            price_repository: Repository para MongoDB (opcional)
        """
        self.coingecko_client = coingecko_client
        self.goldapi_client = goldapi_client
        self.google_sheet_client = google_sheet_client
        self.telegram_client = telegram_client
        self.price_repository = price_repository
    
    def fetch_and_store_prices(self, target_hour: int = None) -> ServiceResponse:
        """
        Método principal que orquesta todo el flujo de obtención y almacenamiento de precios.
        
        Con la nueva estructura consolidada:
        1. Recolecta ambos precios (BTC y XAU)
        2. Crea un documento diario consolidado si no existe
        3. Actualiza los precios del activo/hora en el documento
        4. Envía datos a Google Sheets
        
        Args:
            target_hour: Hora objetivo en ART (10 o 17). Si es None, se usa la hora actual.
        
        Returns:
            ServiceResponse con el resultado de la operación
        """
        errors = []
        records_processed = 0
        
        try:
            # 1. Obtener la hora actual en ART
            now_art = get_current_time_art()
            logger.info(f"Iniciando proceso de obtención de precios. Hora ART: {now_art}")
            
            # 2. Determinar la hora objetivo
            # Ahora la hora objetivo es la hora actual (ej: si son 14:17 -> 14)
            # Si se pasa explícitamente target_hour, se utiliza tal cual.
            if target_hour is None:
                target_hour = now_art.hour

            logger.info(f"Hora objetivo (target_hour): {target_hour}:00 ART")
            
            # 3. Obtener fecha actual en formato YYYY-MM-DD (ART)
            date_str = get_art_date_string()
            logger.info(f"Fecha para documento consolidado: {date_str}")
            
            # 4. Recolectar precios de ambos activos
            prices_data = {}
            
            # =========================================================================
            # OBTENER PRECIOS EN PARALELO
            # Ejecutar _fetch_bitcoin_price y _fetch_gold_price en threads
            # =========================================================================
            prices_data_results = {}

            def _run_fetch(fetch_fn, key):
                try:
                    return key, fetch_fn(target_hour, now_art)
                except Exception as e:
                    logger.error(f"Error en hilo de fetch para {key}: {e}", exc_info=True)
                    return key, None

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                futures = [
                    executor.submit(_run_fetch, self._fetch_bitcoin_price, 'BTC'),
                    executor.submit(_run_fetch, self._fetch_gold_price, 'XAU')
                ]

                for fut in concurrent.futures.as_completed(futures):
                    key, result = fut.result()
                    if result:
                        prices_data[key] = result
                        records_processed += 1
                        logger.info(f"Precio de {key} recolectado: ${result['price_usd']}")
                    else:
                        errors.append(f"No se pudo obtener el precio de {key}")
            
            # 5. Construir documento consolidado
            if prices_data:
                # IMPORTANTE: Usar la hora ACTUAL (now_art.hour), no target_hour
                # target_hour es solo para contexto de búsqueda, pero guardamos el precio de AHORA
                current_hour = now_art.hour
                
                daily_record = self._build_daily_record(
                    date_str, current_hour, prices_data, now_art
                )
                
                logger.info(f"Documento consolidado preparado para {date_str} (hora {current_hour})")
                
                # =========================================================================
                # GUARDAR O ACTUALIZAR EN MONGODB (UPSERT)
                # =========================================================================
                if self.price_repository:
                    success = self.price_repository.save_price_record(daily_record)
                    if success:
                        logger.info(f"Documento guardado/actualizado en MongoDB")

                        # Recuperar documento actualizado de MongoDB
                        updated_record = self.price_repository.get_daily_prices(date_str)

                        if updated_record:
                            logger.info(f"Documento recuperado de MongoDB")
                            # Convertir dict a DailyPriceRecord para enviar a GoogleSheet
                            daily_record_from_db = DailyPriceRecord(**updated_record)

                            # =========================================================================
                            # ENVIAR A GOOGLE SHEETS Y TELEGRAM EN PARALELO
                            # =========================================================================
                            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                                # Enviar a Google Sheets
                                sheet_future = executor.submit(self._send_to_google_sheets, daily_record_from_db)
                                
                                # Enviar notificación Telegram
                                telegram_future = executor.submit(
                                    self._send_telegram_notification, 
                                    current_hour, 
                                    prices_data
                                )
                                
                                # Esperar a que ambas terminen
                                try:
                                    sheet_future.result(timeout=15)
                                    logger.info("✓ Envio a GoogleSheet completado")
                                except Exception as e:
                                    logger.error(f"Error al enviar a GoogleSheet: {e}", exc_info=True)
                                
                                try:
                                    telegram_future.result(timeout=15)
                                    logger.info("✓ Notificación Telegram completada")
                                except Exception as e:
                                    logger.error(f"Error al enviar notificación Telegram: {e}", exc_info=True)
                        else:
                            logger.warning(f"No se pudo recuperar documento de MongoDB")
                    else:
                        logger.error(f"Error al guardar documento en MongoDB")
                else:
                    # Si no hay repository (testing), enviar en paralelo de forma sincrónica
                    # para asegurar que las peticiones se completen antes de retornar.
                    logger.warning("Repository no disponible, enviando a GoogleSheet y Telegram")
                    
                    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                        sheet_future = executor.submit(self._send_to_google_sheets, daily_record)
                        telegram_future = executor.submit(
                            self._send_telegram_notification, 
                            current_hour, 
                            prices_data
                        )
                        
                        try:
                            sheet_future.result(timeout=15)
                        except Exception as e:
                            logger.error(f"Error al enviar a GoogleSheet: {e}", exc_info=True)
                        
                        try:
                            telegram_future.result(timeout=15)
                        except Exception as e:
                            logger.error(f"Error al enviar notificación Telegram: {e}", exc_info=True)
            
            # 6. Preparar respuesta
            success = records_processed > 0
            message = f"Proceso completado. Precios recolectados: {records_processed}"
            
            if errors:
                message += f". Errores: {len(errors)}"
            
            logger.info(message)
            
            return ServiceResponse(
                success=success,
                message=message,
                records_processed=records_processed,
                errors=errors
            )
            
        except Exception as e:
            error_msg = f"Error crítico en el servicio: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return ServiceResponse(
                success=False,
                message="Error crítico en el proceso",
                records_processed=records_processed,
                errors=[error_msg]
            )
    
    # =========================================================================
    # MÉTODOS PRIVADOS
    # =========================================================================
    def _fetch_bitcoin_price(
        self,
        target_hour: int,
        collection_time_art: datetime
    ) -> dict:
        """
        Obtiene y procesa el precio de Bitcoin usando CoinGecko.
        
        IMPORTANTE: Obtiene el precio de la HORA ACTUAL, no del target_hour futuro.
        Esto permite guardar el precio real en cualquier momento, no esperar a las 10 o 17.
        
        Args:
            target_hour: Hora objetivo (0-23) - usado como referencia, pero el precio
                        es de la hora actual
            collection_time_art: Hora de recolección en ART (NOW)
        
        Returns:
            Dict con los datos del precio o None si falla
        """
        try:
            # Usar la hora ACTUAL (collection_time_art) para la búsqueda de precio
            # no el target_hour (que podría ser pasado o el "default")
            current_hour = collection_time_art.hour
            
            from_ts, to_ts, target_datetime_utc = get_timestamp_range_for_bitcoin(
                current_hour,
                Config.TIME_RANGE_MINUTES
            )
            
            response = self.coingecko_client.get_bitcoin_price_in_range(
                from_ts, to_ts
            )
            
            price_points = response.get_price_points()
            
            if not price_points:
                logger.error(f"No se encontraron precios de Bitcoin en rango para hora {current_hour}")
                return None
            
            target_timestamp_ms = int(target_datetime_utc.timestamp() * 1000)
            
            closest_point = min(
                price_points,
                key=lambda p: abs(p.timestamp - target_timestamp_ms)
            )
            
            timestamp_utc = datetime.fromtimestamp(
                closest_point.timestamp / 1000, tz=pytz.utc
            )
            
            logger.info(f"Precio de Bitcoin encontrado (hora {current_hour}): ${closest_point.price}")
            
            # Retornar como dict para consolidación
            return {
                'price_usd': closest_point.price,
                'timestamp_utc': timestamp_utc,
                'source_api': 'coingecko',
                'collection_time_art': collection_time_art
            }
            
        except Exception as e:
            logger.error(f"Error al obtener precio de Bitcoin: {e}", exc_info=True)
            return None
    
    def _fetch_gold_price(
        self,
        target_hour: int,
        collection_time_art: datetime
    ) -> dict:
        """
        Obtiene y procesa el precio del Oro usando GoldAPI.io
        
        Args:
            target_hour: Hora objetivo en ART
            collection_time_art: Hora de recolección en ART
        
        Returns:
            Dict con los datos del precio o None si falla
        """
        try:
            response = self.goldapi_client.get_gold_price()
            price_usd_per_oz = response.get_price_usd()
            timestamp_utc = datetime.fromtimestamp(response.timestamp, tz=pytz.utc)
            
            logger.info(f"Precio del Oro encontrado: ${price_usd_per_oz} por onza")
            
            # Retornar como dict para consolidación
            return {
                'price_usd': price_usd_per_oz,
                'timestamp_utc': timestamp_utc,
                'source_api': 'goldapi',
                'collection_time_art': collection_time_art
            }
            
        except Exception as e:
            logger.error(f"Error al obtener precio del Oro: {e}", exc_info=True)
            return None
    
    def _build_daily_record(
        self,
        date_str: str,
        target_hour: int,
        prices_data: dict,
        collection_time_art: datetime
    ) -> DailyPriceRecord:
        """
        Construye un documento consolidado de precios diarios (array-based).
        
        Nueva estructura:
        {
            "date": "2025-10-24",
            "prices": {
                "BTC": [
                    { "hour": 10, "price_usd": 43250.75, "timestamp_utc": "...", ... },
                    { "hour": 15, "price_usd": 43300.50, "timestamp_utc": "...", ... }
                ],
                "XAU": [...]
            }
        }
        
        Args:
            date_str: Fecha en formato YYYY-MM-DD
            target_hour: Hora objetivo (cualquier hora 0-23)
            prices_data: Dict con {asset: {price, timestamp, source, collection_time}}
            collection_time_art: Hora de recolección en ART
        
        Returns:
            DailyPriceRecord listo para almacenar
        """
        prices_array = {}
        
        for asset, price_info in prices_data.items():
            # Crear PriceEntry para este activo/hora
            entry = PriceEntry(
                hour=target_hour,
                price_usd=price_info['price_usd'],
                timestamp_utc=price_info['timestamp_utc'],
                source_api=price_info['source_api'],
                collection_time_art=price_info['collection_time_art']
            )
            
            # Inicializar array si no existe
            if asset not in prices_array:
                prices_array[asset] = []
            
            # Añadir entry al array
            prices_array[asset].append(entry)
        
        # Crear documento consolidado
        daily_record = DailyPriceRecord(
            date=date_str,
            date_art=collection_time_art,
            prices=prices_array
        )
        
        return daily_record

    def _serialize_for_json(self, obj):
        """
        Convierte un objeto compuesto (dict/list/datetime) en una estructura
        totalmente JSON-serializable (convierte datetimes a ISO strings).
        """
        from datetime import datetime

        if obj is None:
            return None

        # Si es un modelo Pydantic
        try:
            # model_dump devuelve estructuras nativas
            if hasattr(obj, 'model_dump') and callable(obj.model_dump):
                obj = obj.model_dump()
        except Exception:
            pass

        if isinstance(obj, dict):
            new = {}
            for k, v in obj.items():
                new[k] = self._serialize_for_json(v)
            return new

        if isinstance(obj, list):
            return [self._serialize_for_json(v) for v in obj]

        if isinstance(obj, datetime):
            # Asegurarse que tenga tzinfo y usar ISO 8601
            try:
                return obj.isoformat()
            except Exception:
                return str(obj)

        # Para otros tipos primitivos
        return obj
    
    def _send_to_google_sheets(
        self,
        daily_record: DailyPriceRecord
    ):
        """
        Envía el documento consolidado diario completo a Google Sheets.
        
        GoogleSheet recibe el mismo documento que se almacenó en MongoDB.
        Estructura enviada:
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
                "XAU": [...]
            }
        }
        
        GoogleSheet (vía Google Apps Script) es responsable de procesar y formatear
        los datos como sea necesario en la hoja de cálculo.
        
        Args:
            daily_record: DailyPriceRecord consolidado (desde MongoDB o local)
        """
        try:
            logger.info(f"Enviando DailyPriceRecord a GoogleSheet: {daily_record.date}")
            
            # Serializar a dict con datetimes convertidos a ISO 8601 strings
            # mode='json' convierte datetimes automáticamente
            serialized_record = daily_record.model_dump(mode='json')
            
            logger.debug(f"Payload enviado a GoogleSheet: {serialized_record}")
            
            # Enviar POST a la URL de Google Apps Script
            success = self.google_sheet_client.save_record(serialized_record)
            
            if success:
                logger.info(f"✓ Documento enviado a GoogleSheet exitosamente")
            else:
                logger.warning(f"⚠ No se pudo enviar documento a GoogleSheet (ver logs del cliente)")
        
        except Exception as e:
            logger.error(f"Error al enviar documento a GoogleSheet: {e}", exc_info=True)
    
    def _send_telegram_notification(
        self,
        hour: int,
        prices_data: dict
    ):
        """
        Envía una notificación de precios a Telegram.
        
        Args:
            hour: Hora a la que se obtuvieron los precios (0-23)
            prices_data: Dict con {asset: {price_usd, timestamp_utc, ...}}
                        Ejemplo: {'BTC': {'price_usd': 43250.75, ...}, 'XAU': {...}}
        """
        try:
            # Verificar si el cliente de Telegram está disponible
            if not self.telegram_client:
                logger.debug("TelegramClient no configurado, omitiendo notificación")
                return
            
            logger.info(f"Enviando notificación Telegram para hora {hour}")
            
            # Extraer precios de BTC y XAU
            btc_price = prices_data.get('BTC', {}).get('price_usd')
            xau_price = prices_data.get('XAU', {}).get('price_usd')
            
            # Enviar notificación
            success = self.telegram_client.send_price_notification(
                hour=hour,
                btc_price=btc_price,
                xau_price=xau_price
            )
            
            if success:
                logger.info(f"✓ Notificación Telegram enviada exitosamente")
            else:
                logger.warning(f"⚠ No se pudo enviar notificación Telegram (ver logs del cliente)")
        
        except Exception as e:
            logger.error(f"Error al enviar notificación Telegram: {e}", exc_info=True)