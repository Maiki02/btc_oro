"""
Script de prueba del flujo completo: Obtener precios → Consolidar en DailyPriceRecord → Exportar a Google Sheets

Este test verifica:
1. BTC fetching (CoinGecko) → AssetPriceRecord
2. XAU fetching (GoldAPI) → AssetPriceRecord
3. Consolidación en DailyPriceRecord
4. Conversión a GoogleSheetRecord[] para exportar
5. Estructura de datos en MongoDB (simulada)
"""
import sys
import logging
from datetime import datetime
import pytz

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)

# Añadir el directorio actual al path
sys.path.insert(0, '.')

from src.models.schemas import (
    CoinGeckoResponse,
    GoldApiResponse,
    AssetPriceRecord,
    PriceSnapshot,
    DailyPriceRecord,
    GoogleSheetRecord
)
from src.clients.api_clients import CoinGeckoClient, GoldApiClient
from src.utils.time_utils import get_current_time_art, get_art_date_string
from src.config import Config

def test_price_fetching():
    """Prueba 1: Obtener precios de ambas APIs"""
    logger.info("=" * 80)
    logger.info("PRUEBA 1: Obtener precios de BTC y XAU")
    logger.info("=" * 80)
    
    coingecko = CoinGeckoClient(Config.COINGECKO_API_KEY)
    goldapi = GoldApiClient(Config.GOLDAPI_KEY)
    
    # Obtener BTC
    logger.info("Obteniendo precio de Bitcoin...")
    from src.utils.time_utils import get_timestamp_range_for_bitcoin
    from_ts, to_ts, target_utc = get_timestamp_range_for_bitcoin(10)
    
    btc_response = coingecko.get_bitcoin_price_in_range(from_ts, to_ts)
    btc_points = btc_response.get_price_points()
    logger.info(f"✓ Bitcoin: {len(btc_points)} puntos de precio obtenidos")
    
    if btc_points:
        closest = min(btc_points, key=lambda p: abs(p.timestamp - int(target_utc.timestamp() * 1000)))
        logger.info(f"  Precio más cercano: ${closest.price}")
    
    # Obtener XAU
    logger.info("Obteniendo precio del Oro...")
    xau_response = goldapi.get_gold_price()
    logger.info(f"✓ Oro: ${xau_response.get_price_usd()} por onza")
    
    return btc_response, xau_response


def test_asset_price_records(btc_response, xau_response):
    """Prueba 2: Crear AssetPriceRecord desde respuestas de API"""
    logger.info("=" * 80)
    logger.info("PRUEBA 2: Crear AssetPriceRecord (normalización)")
    logger.info("=" * 80)
    
    now_art = get_current_time_art()
    from src.utils.time_utils import get_timestamp_range_for_bitcoin
    from_ts, to_ts, target_utc = get_timestamp_range_for_bitcoin(10)
    
    # BTC → AssetPriceRecord
    btc_points = btc_response.get_price_points()
    closest_btc = min(btc_points, key=lambda p: abs(p.timestamp - int(target_utc.timestamp() * 1000)))
    timestamp_utc_btc = datetime.fromtimestamp(closest_btc.timestamp / 1000, tz=pytz.utc)
    
    btc_record = AssetPriceRecord(
        asset_name='BTC',
        price_usd=closest_btc.price,
        timestamp_utc=timestamp_utc_btc,
        source_api='coingecko',
        collection_time_art=now_art,
        target_hour_art=10
    )
    
    # XAU → AssetPriceRecord
    timestamp_utc_xau = datetime.fromtimestamp(xau_response.timestamp, tz=pytz.utc)
    xau_record = AssetPriceRecord(
        asset_name='XAU',
        price_usd=xau_response.get_price_usd(),
        timestamp_utc=timestamp_utc_xau,
        source_api='goldapi',
        collection_time_art=now_art,
        target_hour_art=10
    )
    
    logger.info(f"✓ BTC AssetPriceRecord: ${btc_record.price_usd}")
    logger.info(f"✓ XAU AssetPriceRecord: ${xau_record.price_usd}")
    logger.info(f"  Tipo de dato: {type(btc_record).__name__}")
    
    return btc_record, xau_record


def test_daily_consolidation(btc_record, xau_record):
    """Prueba 3: Consolidar en DailyPriceRecord (estructura MongoDB)"""
    logger.info("=" * 80)
    logger.info("PRUEBA 3: Consolidar en DailyPriceRecord")
    logger.info("=" * 80)
    
    date_str = get_art_date_string()
    now_art = get_current_time_art()
    
    # Crear PriceSnapshot desde AssetPriceRecord
    btc_snapshot = PriceSnapshot(
        price_usd=btc_record.price_usd,
        timestamp_utc=btc_record.timestamp_utc,
        source_api=btc_record.source_api,
        collection_time_art=btc_record.collection_time_art
    )
    
    xau_snapshot = PriceSnapshot(
        price_usd=xau_record.price_usd,
        timestamp_utc=xau_record.timestamp_utc,
        source_api=xau_record.source_api,
        collection_time_art=xau_record.collection_time_art
    )
    
    # Construir estructura consolidada
    prices_nested = {
        'BTC': {'hour_10': btc_snapshot},
        'XAU': {'hour_10': xau_snapshot}
    }
    
    daily_record = DailyPriceRecord(
        date=date_str,
        date_art=now_art,
        prices=prices_nested
    )
    
    logger.info(f"✓ DailyPriceRecord creado para {date_str}")
    logger.info(f"  Activos: {list(daily_record.prices.keys())}")
    logger.info(f"  Horas registradas: {list(daily_record.prices['BTC'].keys())}")
    logger.info(f"  Estructura: {daily_record.model_dump_json(indent=2)}")
    
    return daily_record


def test_google_sheet_conversion(daily_record):
    """Prueba 4: Convertir DailyPriceRecord a GoogleSheetRecord[]"""
    logger.info("=" * 80)
    logger.info("PRUEBA 4: Convertir a GoogleSheetRecord[] para exportar")
    logger.info("=" * 80)
    
    # Convertir estructura consolidada a registros para Google Sheets
    sheet_records = GoogleSheetRecord.from_daily_price_record(daily_record)
    
    logger.info(f"✓ {len(sheet_records)} registros generados para Google Sheets:")
    
    for i, record in enumerate(sheet_records, 1):
        logger.info(f"\n  Registro {i}:")
        logger.info(f"    Fecha: {record.date}")
        logger.info(f"    Hora: {record.time}")
        logger.info(f"    Activo: {record.asset}")
        logger.info(f"    Precio: ${record.price_usd}")
        logger.info(f"    Fuente: {record.source}")
    
    return sheet_records


def test_multiple_hours():
    """Prueba 5: Simular actualización con múltiples horas (hour_10 y hour_17)"""
    logger.info("=" * 80)
    logger.info("PRUEBA 5: Simular actualización con múltiples horas")
    logger.info("=" * 80)
    
    date_str = get_art_date_string()
    now_art = get_current_time_art()
    
    # Crear snapshots para ambas horas
    btc_10 = PriceSnapshot(
        price_usd=43250.75,
        timestamp_utc=now_art.astimezone(pytz.utc),
        source_api='coingecko',
        collection_time_art=now_art.replace(hour=10, minute=0, second=0)
    )
    
    btc_17 = PriceSnapshot(
        price_usd=43500.50,  # Precio diferente en la tarde
        timestamp_utc=now_art.astimezone(pytz.utc),
        source_api='coingecko',
        collection_time_art=now_art.replace(hour=17, minute=0, second=0)
    )
    
    xau_10 = PriceSnapshot(
        price_usd=2738.15,
        timestamp_utc=now_art.astimezone(pytz.utc),
        source_api='goldapi',
        collection_time_art=now_art.replace(hour=10, minute=0, second=0)
    )
    
    xau_17 = PriceSnapshot(
        price_usd=2745.80,  # Precio diferente en la tarde
        timestamp_utc=now_art.astimezone(pytz.utc),
        source_api='goldapi',
        collection_time_art=now_art.replace(hour=17, minute=0, second=0)
    )
    
    # Documento consolidado con ambas horas
    daily_record_full = DailyPriceRecord(
        date=date_str,
        date_art=now_art,
        prices={
            'BTC': {
                'hour_10': btc_10,
                'hour_17': btc_17
            },
            'XAU': {
                'hour_10': xau_10,
                'hour_17': xau_17
            }
        }
    )
    
    logger.info(f"✓ DailyPriceRecord con múltiples horas:")
    logger.info(f"  Activos: {list(daily_record_full.prices.keys())}")
    
    for asset, hours in daily_record_full.prices.items():
        logger.info(f"\n  {asset}:")
        for hour_key, snapshot in hours.items():
            logger.info(f"    {hour_key}: ${snapshot.price_usd}")
    
    # Convertir a Google Sheets
    sheet_records = GoogleSheetRecord.from_daily_price_record(daily_record_full)
    logger.info(f"\n✓ {len(sheet_records)} registros generados para Google Sheets:")
    
    for record in sheet_records:
        logger.info(f"  {record.date} {record.time:>5} | {record.asset:>3} | ${record.price_usd:>10.2f} | {record.source}")
    
    return daily_record_full, sheet_records


def main():
    """Ejecutar todas las pruebas"""
    logger.info("\n" + "=" * 80)
    logger.info("PRUEBA DE FLUJO COMPLETO: Obtención de Precios → MongoDB → Google Sheets")
    logger.info("=" * 80 + "\n")
    
    try:
        # Prueba 1
        btc_response, xau_response = test_price_fetching()
        
        # Prueba 2
        btc_record, xau_record = test_asset_price_records(btc_response, xau_response)
        
        # Prueba 3
        daily_record = test_daily_consolidation(btc_record, xau_record)
        
        # Prueba 4
        sheet_records = test_google_sheet_conversion(daily_record)
        
        # Prueba 5
        daily_record_full, sheet_records_full = test_multiple_hours()
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ TODAS LAS PRUEBAS PASARON CORRECTAMENTE")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"\n❌ ERROR EN PRUEBAS: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
