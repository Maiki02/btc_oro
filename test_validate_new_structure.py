"""
Validación de la nueva estructura array-based.
Verifica que todos los modelos se importan correctamente y la estructura funciona.
"""
import sys
import logging
from datetime import datetime
import pytz

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

sys.path.insert(0, '.')

from src.models.schemas import (
    PriceEntry,
    DailyPriceRecord,
    GoogleSheetRecord,
    AssetPriceRecord
)

def test_price_entry():
    """Test 1: Crear PriceEntry"""
    logger.info("=" * 80)
    logger.info("TEST 1: PriceEntry - Entrada individual de precio")
    logger.info("=" * 80)
    
    now_art = pytz.timezone('America/Argentina/Buenos_Aires').localize(datetime.now())
    now_utc = now_art.astimezone(pytz.utc)
    
    entry = PriceEntry(
        hour=15,
        price_usd=43300.50,
        timestamp_utc=now_utc,
        source_api='coingecko',
        collection_time_art=now_art
    )
    
    logger.info(f"✓ PriceEntry creado correctamente:")
    logger.info(f"  Hora: {entry.hour}")
    logger.info(f"  Precio: ${entry.price_usd}")
    logger.info(f"  Fuente: {entry.source_api}")
    
    return entry

def test_daily_price_record():
    """Test 2: Crear DailyPriceRecord con estructura array"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: DailyPriceRecord - Estructura consolidada diaria (array-based)")
    logger.info("=" * 80)
    
    now_art = pytz.timezone('America/Argentina/Buenos_Aires').localize(datetime.now())
    now_utc = now_art.astimezone(pytz.utc)
    
    # Crear múltiples entries (horas diferentes)
    btc_entry_10 = PriceEntry(hour=10, price_usd=43250.75, timestamp_utc=now_utc, source_api='coingecko', collection_time_art=now_art)
    btc_entry_15 = PriceEntry(hour=15, price_usd=43300.50, timestamp_utc=now_utc, source_api='coingecko', collection_time_art=now_art)
    btc_entry_17 = PriceEntry(hour=17, price_usd=43400.00, timestamp_utc=now_utc, source_api='coingecko', collection_time_art=now_art)
    
    xau_entry_10 = PriceEntry(hour=10, price_usd=2738.15, timestamp_utc=now_utc, source_api='goldapi', collection_time_art=now_art)
    xau_entry_15 = PriceEntry(hour=15, price_usd=2745.80, timestamp_utc=now_utc, source_api='goldapi', collection_time_art=now_art)
    
    # Crear documento consolidado
    daily_record = DailyPriceRecord(
        date='2025-10-24',
        date_art=now_art,
        prices={
            'BTC': [btc_entry_10, btc_entry_15, btc_entry_17],
            'XAU': [xau_entry_10, xau_entry_15]
        }
    )
    
    logger.info(f"✓ DailyPriceRecord creado correctamente:")
    logger.info(f"  Fecha: {daily_record.date}")
    logger.info(f"  Activos: {list(daily_record.prices.keys())}")
    
    for asset, entries in daily_record.prices.items():
        logger.info(f"\n  {asset}:")
        for entry in entries:
            logger.info(f"    hora {entry.hour:2d}: ${entry.price_usd:>10.2f}")
    
    return daily_record

def test_add_price_method():
    """Test 3: Usar método add_price() para agregar/actualizar entries"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: DailyPriceRecord.add_price() - Agregar/actualizar precios")
    logger.info("=" * 80)
    
    now_art = pytz.timezone('America/Argentina/Buenos_Aires').localize(datetime.now())
    now_utc = now_art.astimezone(pytz.utc)
    
    # Crear documento vacío
    daily_record = DailyPriceRecord(date='2025-10-24', date_art=now_art, prices={})
    
    # Agregar precios
    daily_record.add_price('BTC', PriceEntry(hour=10, price_usd=43250.75, timestamp_utc=now_utc, source_api='coingecko', collection_time_art=now_art))
    daily_record.add_price('BTC', PriceEntry(hour=15, price_usd=43300.50, timestamp_utc=now_utc, source_api='coingecko', collection_time_art=now_art))
    daily_record.add_price('XAU', PriceEntry(hour=10, price_usd=2738.15, timestamp_utc=now_utc, source_api='goldapi', collection_time_art=now_art))
    
    logger.info(f"✓ Precios agregados exitosamente:")
    for asset, entries in daily_record.prices.items():
        logger.info(f"\n  {asset}: {len(entries)} entries")
        for entry in entries:
            logger.info(f"    hora {entry.hour:2d}: ${entry.price_usd:>10.2f}")
    
    # Actualizar un precio
    logger.info(f"\n✓ Actualizando BTC hora 15...")
    new_entry = PriceEntry(hour=15, price_usd=43350.99, timestamp_utc=now_utc, source_api='coingecko', collection_time_art=now_art)
    daily_record.add_price('BTC', new_entry)
    
    btc_prices = daily_record.prices['BTC']
    logger.info(f"  BTC hora 15 actualizado: ${btc_prices[-1].price_usd}")
    
    return daily_record

def test_get_methods():
    """Test 4: Métodos get_price() y get_all_prices_for_asset()"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 4: Métodos de lectura - get_price() y get_all_prices_for_asset()")
    logger.info("=" * 80)
    
    now_art = pytz.timezone('America/Argentina/Buenos_Aires').localize(datetime.now())
    now_utc = now_art.astimezone(pytz.utc)
    
    daily_record = DailyPriceRecord(
        date='2025-10-24',
        date_art=now_art,
        prices={
            'BTC': [
                PriceEntry(hour=10, price_usd=43250.75, timestamp_utc=now_utc, source_api='coingecko', collection_time_art=now_art),
                PriceEntry(hour=15, price_usd=43300.50, timestamp_utc=now_utc, source_api='coingecko', collection_time_art=now_art),
                PriceEntry(hour=17, price_usd=43400.00, timestamp_utc=now_utc, source_api='coingecko', collection_time_art=now_art)
            ]
        }
    )
    
    # Buscar precio específico
    btc_15 = daily_record.get_price('BTC', 15)
    logger.info(f"✓ get_price('BTC', 15): ${btc_15.price_usd if btc_15 else 'NOT FOUND'}")
    
    # Obtener todos los precios de un activo
    btc_all = daily_record.get_all_prices_for_asset('BTC')
    logger.info(f"✓ get_all_prices_for_asset('BTC'): {len(btc_all)} entries")
    for entry in btc_all:
        logger.info(f"  hora {entry.hour:2d}: ${entry.price_usd:>10.2f}")

def test_google_sheet_conversion():
    """Test 5: Convertir a GoogleSheetRecord[]"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 5: GoogleSheetRecord.from_daily_price_record() - Conversión para export")
    logger.info("=" * 80)
    
    now_art = pytz.timezone('America/Argentina/Buenos_Aires').localize(datetime.now())
    now_utc = now_art.astimezone(pytz.utc)
    
    daily_record = DailyPriceRecord(
        date='2025-10-24',
        date_art=now_art,
        prices={
            'BTC': [
                PriceEntry(hour=10, price_usd=43250.75, timestamp_utc=now_utc, source_api='coingecko', collection_time_art=now_art),
                PriceEntry(hour=17, price_usd=43400.00, timestamp_utc=now_utc, source_api='coingecko', collection_time_art=now_art)
            ],
            'XAU': [
                PriceEntry(hour=10, price_usd=2738.15, timestamp_utc=now_utc, source_api='goldapi', collection_time_art=now_art),
                PriceEntry(hour=17, price_usd=2750.80, timestamp_utc=now_utc, source_api='goldapi', collection_time_art=now_art)
            ]
        }
    )
    
    # Convertir a GoogleSheetRecord
    sheet_records = GoogleSheetRecord.from_daily_price_record(daily_record)
    
    logger.info(f"✓ {len(sheet_records)} registros generados para Google Sheets:")
    for record in sheet_records:
        logger.info(f"  {record.date} {record.time} | {record.asset:>3} | ${record.price_usd:>10.2f} | {record.source}")

def test_json_serialization():
    """Test 6: Serialización JSON (para enviar a APIs)"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 6: Serialización JSON - model_dump() con datetimes")
    logger.info("=" * 80)
    
    now_art = pytz.timezone('America/Argentina/Buenos_Aires').localize(datetime.now())
    now_utc = now_art.astimezone(pytz.utc)
    
    daily_record = DailyPriceRecord(
        date='2025-10-24',
        date_art=now_art,
        prices={
            'BTC': [
                PriceEntry(hour=15, price_usd=43300.50, timestamp_utc=now_utc, source_api='coingecko', collection_time_art=now_art)
            ]
        }
    )
    
    # model_dump() serializa datetimes como strings
    dumped = daily_record.model_dump()
    logger.info(f"✓ model_dump() ejecutado exitosamente")
    logger.info(f"  Tipo de timestamp_utc: {type(dumped['prices']['BTC'][0]['timestamp_utc'])}")
    logger.info(f"  Valor: {dumped['prices']['BTC'][0]['timestamp_utc']}")

def main():
    logger.info("\n" + "=" * 80)
    logger.info("VALIDACIÓN DE NUEVA ESTRUCTURA ARRAY-BASED")
    logger.info("=" * 80 + "\n")
    
    try:
        test_price_entry()
        test_daily_price_record()
        test_add_price_method()
        test_get_methods()
        test_google_sheet_conversion()
        test_json_serialization()
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ TODOS LOS TESTS PASARON CORRECTAMENTE")
        logger.info("=" * 80 + "\n")
        return 0
    
    except Exception as e:
        logger.error(f"\n❌ ERROR: {e}", exc_info=True)
        return 1

if __name__ == '__main__':
    exit(main())
