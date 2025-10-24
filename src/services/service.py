"""
Capa de servicio con la lógica de negocio principal.
"""
from datetime import datetime
import logging
import pytz

from ..clients.api_clients import GoldApiClient, GoogleSheetClient  # CoinGeckoClient, MetalsApiClient (COMENTADOS)
# from ..repositories.repository import PriceRepository  # COMENTADO - MongoDB
from ..models.schemas import AssetPriceRecord, GoogleSheetRecord, ServiceResponse
from ..utils.time_utils import get_current_time_art
from ..config import Config

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PriceDataService:
    """
    Servicio principal que orquesta la obtención y almacenamiento de precios.
    VERSIÓN SIMPLIFICADA PARA PRUEBAS - Solo GoldAPI
    """
    
    def __init__(
        self,
        goldapi_client: GoldApiClient,
        google_sheet_client: GoogleSheetClient,
        # price_repository: PriceRepository  # COMENTADO - MongoDB
    ):
        """
        Inicializa el servicio con las dependencias inyectadas.
        
        Args:
            goldapi_client: Cliente para la API de GoldAPI.io
            google_sheet_client: Cliente para Google Sheets
        """
        self.goldapi_client = goldapi_client
        self.google_sheet_client = google_sheet_client
        # self.price_repository = price_repository  # COMENTADO - MongoDB
    
    def fetch_and_store_prices(self, target_hour: int = None) -> ServiceResponse:
        """
        Método principal que orquesta todo el flujo de obtención y almacenamiento de precios.
        VERSIÓN SIMPLIFICADA: Solo obtiene precio del oro.
        
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
            
            # =========================================================================
            # BITCOIN - COMENTADO PARA PRUEBAS
            # =========================================================================
            # from_ts, to_ts, target_datetime_utc = get_timestamp_range_for_bitcoin(
            #     target_hour, 
            #     Config.TIME_RANGE_MINUTES
            # )
            # btc_record = self._fetch_bitcoin_price(
            #     from_ts, to_ts, target_datetime_utc, target_hour, now_art
            # )
            # if btc_record:
            #     self.price_repository.save_price_record(btc_record)
            #     google_record = GoogleSheetRecord.from_asset_price_record(btc_record)
            #     self.google_sheet_client.save_record(google_record.model_dump())
            #     records_processed += 1
            
            # =========================================================================
            # ORO - USANDO GOLDAPI.IO
            # =========================================================================
            xau_record = self._fetch_gold_price(target_hour, now_art)
            
            if xau_record:
                # Guardar en MongoDB (COMENTADO)
                # self.price_repository.save_price_record(xau_record)
                
                # Enviar a Google Sheets
                google_record = GoogleSheetRecord.from_asset_price_record(xau_record)
                try:
                    self.google_sheet_client.save_record(google_record.model_dump())
                    logger.info("Datos enviados a Google Sheets exitosamente")
                except Exception as e:
                    logger.warning(f"No se pudo enviar a Google Sheets: {e}")
                    errors.append(f"Error al enviar a Google Sheets: {str(e)}")
                
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
    
    # =========================================================================
    # MÉTODOS PRIVADOS COMENTADOS - Bitcoin
    # =========================================================================
    # def _fetch_bitcoin_price(...):
    #     ... (comentado)
    
    def _fetch_gold_price(
        self,
        target_hour: int,
        collection_time_art: datetime
    ) -> AssetPriceRecord:
        """
        Obtiene y procesa el precio del Oro usando GoldAPI.io
        
        Args:
            target_hour: Hora objetivo en ART
            collection_time_art: Hora de recolección en ART
        
        Returns:
            AssetPriceRecord con los datos del Oro o None si falla
        """
        try:
            # Consultar API de GoldAPI.io
            response = self.goldapi_client.get_gold_price()
            
            # Obtener el precio en USD por onza
            price_usd_per_oz = response.get_price_usd()
            
            logger.info(f"Precio del Oro encontrado: ${price_usd_per_oz} por onza")
            
            # Convertir el timestamp de la API a datetime UTC
            timestamp_utc = datetime.fromtimestamp(response.timestamp, tz=pytz.utc)
            
            # Crear el registro normalizado
            record = AssetPriceRecord(
                asset_name='XAU',
                price_usd=price_usd_per_oz,
                timestamp_utc=timestamp_utc,
                source_api='goldapi',
                collection_time_art=collection_time_art,
                target_hour_art=target_hour
            )
            
            return record
            
        except Exception as e:
            logger.error(f"Error al obtener precio del Oro: {e}", exc_info=True)
            return None