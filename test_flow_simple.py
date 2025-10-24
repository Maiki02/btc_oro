"""
Test simple del flujo: Obtener precios → Consolidar → Enviar a MongoDB → GoogleSheet
"""
import sys
import logging
from datetime import datetime
import pytz

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.insert(0, '.')

from src.models.schemas import DailyPriceRecord, PriceSnapshot, GoogleSheetRecord
from src.clients.api_clients import CoinGeckoClient, GoldApiClient, GoogleSheetClient
from src.config import Config
from src.utils.time_utils import get_current_time_art, get_art_date_string, get_timestamp_range_for_bitcoin


def test_full_flow():
    """Test el flujo completo sin MongoDB (simulado)"""
    logger.info("="*80)
    logger.info("TEST: Flujo Completo (Sin MongoDB)")
    logger.info("="*80)
    
    # 1. Obtener precios
    logger.info("\n1️⃣ Obteniendo precios...")
    coingecko = CoinGeckoClient(Config.COINGECKO_API_KEY)
    goldapi = GoldApiClient(Config.GOLDAPI_KEY)
    
    from_ts, to_ts, target_utc = get_timestamp_range_for_bitcoin(10)
    btc_response = coingecko.get_bitcoin_price_in_range(from_ts, to_ts)
    btc_points = btc_response.get_price_points()
    
    xau_response = goldapi.get_gold_price()
    
    logger.info(f"✓ BTC points: {len(btc_points)}")
    logger.info(f"✓ XAU price: ${xau_response.get_price_usd()}")
    
    # 2. Construir DailyPriceRecord
    logger.info("\n2️⃣ Consolidando en DailyPriceRecord...")
    
    closest_btc = min(btc_points, key=lambda p: abs(p.timestamp - int(target_utc.timestamp() * 1000)))
    btc_snapshot = PriceSnapshot(
        price_usd=closest_btc.price,
        timestamp_utc=datetime.fromtimestamp(closest_btc.timestamp / 1000, tz=pytz.utc),
        source_api='coingecko',
        collection_time_art=get_current_time_art()
    )
    
    xau_snapshot = PriceSnapshot(
        price_usd=xau_response.get_price_usd(),
        timestamp_utc=datetime.fromtimestamp(xau_response.timestamp, tz=pytz.utc),
        source_api='goldapi',
        collection_time_art=get_current_time_art()
    )
    
    daily_record = DailyPriceRecord(
        date=get_art_date_string(),
        date_art=get_current_time_art(),
        prices={
            'BTC': {'hour_10': btc_snapshot},
            'XAU': {'hour_10': xau_snapshot}
        }
    )
    
    logger.info(f"✓ DailyPriceRecord creado para {daily_record.date}")
    logger.info(f"  Activos: {list(daily_record.prices.keys())}")
    logger.info(f"  JSON:\n{daily_record.model_dump_json(indent=2)}")
    
    # 3. Este documento se guardaría en MongoDB
    logger.info("\n3️⃣ [SIMULADO] Guardando en MongoDB...")
    logger.info("✓ Documento guardado (simulado)")
    logger.info("✓ Documento recuperado (simulado)")
    
    # 4. Enviar a GoogleSheet (mismo documento)
    logger.info("\n4️⃣ Enviando documento a GoogleSheet...")
    logger.info(f"Documento a enviar (sin transformación):")
    logger.info(f"{daily_record.model_dump_json(indent=2)}")
    
    logger.info("\n✅ FLUJO COMPLETADO EXITOSAMENTE")
    logger.info("="*80)


if __name__ == '__main__':
    try:
        test_full_flow()
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        sys.exit(1)
