"""
Capa de servicio con la lógica de negocio principal.
"""
from datetime import datetime
import logging
from typing import List

from ..clients.api_clients import CoinGeckoClient, MetalsApiClient, GoogleSheetClient
from ..repositories.repository import PriceRepository
from ..models.schemas import AssetPriceRecord, GoogleSheetRecord, ServiceResponse
from ..utils.time_utils import (
    get_current_time_art,
    get_timestamp_range_for_bitcoin,
    get_date_string_for_metals_api,
    find_closest_price,
    convert_utc_to_art
)
from ..config import Config

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PriceDataService:
    """
    Servicio principal que orquesta la obtención y almacenamiento de precios.
    """
    
    def __init__(
        self,
        coingecko_client: CoinGeckoClient,
        metals_api_client: MetalsApiClient,
        google_sheet_client: GoogleSheetClient,
        price_repository: PriceRepository
    ):
        """
        Inicializa el servicio con las dependencias inyectadas.
        
        Args:
            coingecko_client: Cliente para la API de CoinGecko
            metals_api_client: Cliente para la API de Metals-API
            google_sheet_client: Cliente para Google Sheets
            price_repository: Repositorio para MongoDB
        """
        self.coingecko_client = coingecko_client
        self.metals_api_client = metals_api_client
        self.google_sheet_client = google_sheet_client
        self.price_repository = price_repository
    
    def fetch_and_store_prices(self, target_hour: int = None) -> ServiceResponse:
        """
        Método principal que orquesta todo el flujo de obtención y almacenamiento de precios.
        
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
                # Si no se especifica, usar la hora actual si es 10 o 17
                current_hour = now_art.hour
                if current_hour in Config.TARGET_HOURS:
                    target_hour = current_hour
                else:
                    # Por defecto, usar la hora más cercana
                    target_hour = min(Config.TARGET_HOURS, key=lambda h: abs(h - current_hour))
            
            if target_hour not in Config.TARGET_HOURS:
                return ServiceResponse(
                    success=False,
                    message=f"Hora objetivo inválida: {target_hour}. Debe ser 10 o 17.",
                    errors=[f"target_hour debe ser 10 o 17, recibido: {target_hour}"]
                )
            
            logger.info(f"Hora objetivo: {target_hour}:00 ART")
            
            # 3. Obtener timestamps para la consulta de Bitcoin
            from_ts, to_ts, target_datetime_utc = get_timestamp_range_for_bitcoin(
                target_hour, 
                Config.TIME_RANGE_MINUTES
            )
            
            # 4. Obtener precio de Bitcoin
            btc_record = self._fetch_bitcoin_price(
                from_ts, to_ts, target_datetime_utc, target_hour, now_art
            )
            
            if btc_record:
                # Guardar en MongoDB
                self.price_repository.save_price_record(btc_record)
                
                # Enviar a Google Sheets
                google_record = GoogleSheetRecord.from_asset_price_record(btc_record)
                self.google_sheet_client.save_record(google_record.model_dump())
                
                records_processed += 1
                logger.info(f"Precio de Bitcoin procesado exitosamente: ${btc_record.price_usd}")
            else:
                errors.append("No se pudo obtener el precio de Bitcoin")
            
            # 5. Obtener precio del Oro
            date_str = get_date_string_for_metals_api()
            xau_record = self._fetch_gold_price(date_str, target_hour, now_art, target_datetime_utc)
            
            if xau_record:
                # Guardar en MongoDB
                self.price_repository.save_price_record(xau_record)
                
                # Enviar a Google Sheets
                google_record = GoogleSheetRecord.from_asset_price_record(xau_record)
                self.google_sheet_client.save_record(google_record.model_dump())
                
                records_processed += 1
                logger.info(f"Precio del Oro procesado exitosamente: ${xau_record.price_usd}")
            else:
                errors.append("No se pudo obtener el precio del Oro")
            
            # 6. Preparar respuesta
            success = records_processed > 0
            message = f"Proceso completado. Registros procesados: {records_processed}"
            
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
    
    def _fetch_bitcoin_price(
        self,
        from_ts: int,
        to_ts: int,
        target_datetime_utc: datetime,
        target_hour: int,
        collection_time_art: datetime
    ) -> AssetPriceRecord:
        """
        Obtiene y procesa el precio de Bitcoin.
        
        Args:
            from_ts: Timestamp de inicio
            to_ts: Timestamp de fin
            target_datetime_utc: Datetime objetivo en UTC
            target_hour: Hora objetivo en ART
            collection_time_art: Hora de recolección en ART
        
        Returns:
            AssetPriceRecord con los datos de Bitcoin o None si falla
        """
        try:
            # Consultar API de CoinGecko
            response = self.coingecko_client.get_bitcoin_price_in_range(from_ts, to_ts)
            
            # Obtener los puntos de precio
            price_points = response.get_price_points()
            
            if not price_points:
                logger.error("No se obtuvieron puntos de precio de CoinGecko")
                return None
            
            # Encontrar el precio más cercano al timestamp objetivo
            closest_price, price_datetime = find_closest_price(price_points, target_datetime_utc)
            
            logger.info(
                f"Precio de Bitcoin encontrado: ${closest_price} "
                f"(timestamp: {price_datetime})"
            )
            
            # Crear el registro normalizado
            record = AssetPriceRecord(
                asset_name='BTC',
                price_usd=closest_price,
                timestamp_utc=price_datetime,
                source_api='coingecko',
                collection_time_art=collection_time_art,
                target_hour_art=target_hour
            )
            
            return record
            
        except Exception as e:
            logger.error(f"Error al obtener precio de Bitcoin: {e}", exc_info=True)
            return None
    
    def _fetch_gold_price(
        self,
        date_str: str,
        target_hour: int,
        collection_time_art: datetime,
        target_datetime_utc: datetime
    ) -> AssetPriceRecord:
        """
        Obtiene y procesa el precio del Oro.
        
        Args:
            date_str: Fecha en formato YYYY-MM-DD
            target_hour: Hora objetivo en ART
            collection_time_art: Hora de recolección en ART
            target_datetime_utc: Datetime objetivo en UTC
        
        Returns:
            AssetPriceRecord con los datos del Oro o None si falla
        """
        try:
            # Consultar API de Metals-API
            response = self.metals_api_client.get_gold_closing_price(date_str)
            
            # Obtener el precio en USD por onza (aplicando el cálculo crítico)
            price_usd_per_oz = response.get_xau_usd_rate()
            
            logger.info(f"Precio del Oro encontrado: ${price_usd_per_oz} por onza")
            
            # Crear el registro normalizado
            record = AssetPriceRecord(
                asset_name='XAU',
                price_usd=price_usd_per_oz,
                timestamp_utc=target_datetime_utc,
                source_api='metals-api',
                collection_time_art=collection_time_art,
                target_hour_art=target_hour
            )
            
            return record
            
        except Exception as e:
            logger.error(f"Error al obtener precio del Oro: {e}", exc_info=True)
            return None