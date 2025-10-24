"""
Capa de servicio con la lógica de negocio principal.
Orquesta la obtención, consolidación y almacenamiento de precios en la estructura
de documento diario unificado.
"""
from datetime import datetime
import logging
import pytz

from ..clients.api_clients import CoinGeckoClient, GoldApiClient, GoogleSheetClient
# from ..repositories.repository import PriceRepository  # COMENTADO - MongoDB
from ..models.schemas import (
    PriceSnapshot, DailyPriceRecord, GoogleSheetRecord, ServiceResponse, AssetPriceRecord
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
        price_repository=None  # INYECTADO - MongoDB (opcional para testing)
    ):
        """
        Inicializa el servicio con las dependencias inyectadas.
        
        Args:
            coingecko_client: Cliente para la API de CoinGecko
            goldapi_client: Cliente para la API de GoldAPI.io
            google_sheet_client: Cliente para Google Sheets
            price_repository: Repository para MongoDB (opcional)
        """
        self.coingecko_client = coingecko_client
        self.goldapi_client = goldapi_client
        self.google_sheet_client = google_sheet_client
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
            if target_hour is None:
                current_hour = now_art.hour
                if current_hour in Config.TARGET_HOURS:
                    target_hour = current_hour
                else:
                    target_hour = min(Config.TARGET_HOURS, key=lambda h: abs(h - current_hour))
            
            if target_hour not in Config.TARGET_HOURS:
                return ServiceResponse(
                    success=False,
                    message=f"Hora objetivo inválida: {target_hour}. Debe ser 10 o 17.",
                    errors=[f"target_hour debe ser 10 o 17, recibido: {target_hour}"]
                )
            
            logger.info(f"Hora objetivo: {target_hour}:00 ART")
            
            # 3. Obtener fecha actual en formato YYYY-MM-DD (ART)
            date_str = get_art_date_string()
            logger.info(f"Fecha para documento consolidado: {date_str}")
            
            # 4. Recolectar precios de ambos activos
            prices_data = {}
            
            # =========================================================================
            # BITCOIN - COINGECKO API
            # =========================================================================
            btc_price = self._fetch_bitcoin_price(target_hour, now_art)
            if btc_price:
                prices_data['BTC'] = btc_price
                records_processed += 1
                logger.info(f"Precio de Bitcoin recolectado: ${btc_price['price_usd']}")
            else:
                errors.append("No se pudo obtener el precio de Bitcoin")
            
            # =========================================================================
            # ORO - GOLDAPI.IO
            # =========================================================================
            xau_price = self._fetch_gold_price(target_hour, now_art)
            if xau_price:
                prices_data['XAU'] = xau_price
                records_processed += 1
                logger.info(f"Precio del Oro recolectado: ${xau_price['price_usd']}")
            else:
                errors.append("No se pudo obtener el precio del Oro")
            
            # 5. Construir documento consolidado
            if prices_data:
                daily_record = self._build_daily_record(
                    date_str, target_hour, prices_data, now_art
                )
                
                logger.info(f"Documento consolidado preparado para {date_str}")
                
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
                            self._send_to_google_sheets(daily_record_from_db)
                        else:
                            logger.warning(f"No se pudo recuperar documento de MongoDB")
                    else:
                        logger.error(f"Error al guardar documento en MongoDB")
                else:
                    # Si no hay repository (testing), enviar directamente
                    logger.warning("Repository no disponible, enviando documento directamente")
                    self._send_to_google_sheets(daily_record)
            
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
        
        Args:
            target_hour: Hora objetivo en ART
            collection_time_art: Hora de recolección en ART
        
        Returns:
            Dict con los datos del precio o None si falla
        """
        try:
            from_ts, to_ts, target_datetime_utc = get_timestamp_range_for_bitcoin(
                target_hour,
                Config.TIME_RANGE_MINUTES
            )
            
            response = self.coingecko_client.get_bitcoin_price_in_range(
                from_ts, to_ts
            )
            
            price_points = response.get_price_points()
            
            if not price_points:
                logger.error("No se encontraron precios de Bitcoin en el rango especificado")
                return None
            
            target_timestamp_ms = int(target_datetime_utc.timestamp() * 1000)
            
            closest_point = min(
                price_points,
                key=lambda p: abs(p.timestamp - target_timestamp_ms)
            )
            
            timestamp_utc = datetime.fromtimestamp(
                closest_point.timestamp / 1000, tz=pytz.utc
            )
            
            logger.info(f"Precio de Bitcoin encontrado: ${closest_point.price}")
            
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
        Construye un documento consolidado de precios diarios.
        
        Estructura:
        {
            "date": "2025-10-24",
            "prices": {
                "BTC": {
                    "hour_10": { snapshot },
                    "hour_17": { snapshot }
                },
                "XAU": { ... }
            }
        }
        
        Args:
            date_str: Fecha en formato YYYY-MM-DD
            target_hour: Hora objetivo (10 o 17)
            prices_data: Dict con {asset: {price, timestamp, source, collection_time}}
            collection_time_art: Hora de recolección en ART
        
        Returns:
            DailyPriceRecord listo para almacenar
        """
        hour_key = f"hour_{target_hour}"
        prices_nested = {}
        
        for asset, price_info in prices_data.items():
            # Crear snapshot para este activo/hora
            snapshot = PriceSnapshot(
                price_usd=price_info['price_usd'],
                timestamp_utc=price_info['timestamp_utc'],
                source_api=price_info['source_api'],
                collection_time_art=price_info['collection_time_art']
            )
            
            # Estructurar: {asset: {hour_X: snapshot}}
            if asset not in prices_nested:
                prices_nested[asset] = {}
            
            prices_nested[asset][hour_key] = snapshot
        
        # Crear documento consolidado
        daily_record = DailyPriceRecord(
            date=date_str,
            date_art=collection_time_art,
            prices=prices_nested
        )
        
        return daily_record
    
    def _send_to_google_sheets(
        self,
        daily_record: DailyPriceRecord
    ):
        """
        Envía el documento consolidado diario completo a Google Sheets.
        
        GoogleSheet recibe el mismo documento que se almacenó en MongoDB.
        GoogleSheet es responsable de transformar/formatear los datos como sea necesario.
        
        Args:
            daily_record: DailyPriceRecord consolidado (desde MongoDB o local)
        """
        try:
            logger.info(f"Enviando DailyPriceRecord a GoogleSheet: {daily_record.date}")
            
            # Enviar documento completo a GoogleSheet (sin transformación)
            # GoogleSheet decidirá cómo procesarlo
            self.google_sheet_client.save_record(daily_record.model_dump())
            
            logger.info(f"Documento enviado a GoogleSheet exitosamente")
        
        except Exception as e:
            logger.error(f"Error al enviar documento a GoogleSheet: {e}", exc_info=True)