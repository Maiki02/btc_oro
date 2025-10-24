"""
Test para validar el flujo de envío a Google Sheets.
Verifica que la estructura se serializa correctamente.
"""
import json
from datetime import datetime
import pytz

from src.models.schemas import (
    PriceEntry, DailyPriceRecord
)
from src.utils.time_utils import get_art_timezone

def test_daily_price_record_serialization():
    """
    Verifica que DailyPriceRecord se serializa correctamente con mode='json'
    para envío a Google Sheets.
    """
    art_tz = get_art_timezone()
    
    # Crear datos de prueba
    now_art = datetime.now(art_tz)
    
    # Crear entradas de precio
    btc_entry = PriceEntry(
        hour=17,
        price_usd=110340.829253726,
        timestamp_utc=datetime(2025, 10, 24, 17, 55, 52, 341000, tzinfo=pytz.utc),
        source_api="coingecko",
        collection_time_art=now_art
    )
    
    xau_entry = PriceEntry(
        hour=17,
        price_usd=4500,
        timestamp_utc=datetime(2025, 10, 24, 18, 55, 53, 125396, tzinfo=pytz.utc),
        source_api="goldapi",
        collection_time_art=now_art
    )
    
    # Crear documento consolidado
    daily_record = DailyPriceRecord(
        date="2025-10-25",
        date_art=now_art,
        prices={
            "BTC": [btc_entry],
            "XAU": [xau_entry]
        }
    )
    
    # Serializar con mode='json' (como se envía a Google Sheets)
    serialized = daily_record.model_dump(mode='json')
    
    # Validaciones
    print("\n" + "="*80)
    print("TEST: DailyPriceRecord Serialization para Google Sheets")
    print("="*80)
    
    # 1. Verificar estructura JSON
    print("\n✓ Estructura serializada:")
    print(json.dumps(serialized, indent=2))
    
    # 2. Verificar que date está presente
    assert "date" in serialized, "Falta 'date' en serialized"
    assert serialized["date"] == "2025-10-25", "Date incorrecto"
    print(f"\n✓ Date correcto: {serialized['date']}")
    
    # 3. Verificar que date_art está presente y es string
    assert "date_art" in serialized, "Falta 'date_art' en serialized"
    assert isinstance(serialized["date_art"], str), "date_art debe ser string"
    print(f"✓ Date_art (ISO 8601): {serialized['date_art']}")
    
    # 4. Verificar estructura de precios
    assert "prices" in serialized, "Falta 'prices' en serialized"
    assert "BTC" in serialized["prices"], "Falta 'BTC' en prices"
    assert "XAU" in serialized["prices"], "Falta 'XAU' en prices"
    print(f"✓ Activos presentes: {list(serialized['prices'].keys())}")
    
    # 5. Verificar que BTC es array
    assert isinstance(serialized["prices"]["BTC"], list), "BTC debe ser array"
    assert len(serialized["prices"]["BTC"]) == 1, "BTC debe tener 1 entrada"
    btc_data = serialized["prices"]["BTC"][0]
    print(f"\n✓ BTC[0]:")
    print(f"    - hour: {btc_data['hour']}")
    print(f"    - price_usd: {btc_data['price_usd']}")
    print(f"    - source_api: {btc_data['source_api']}")
    print(f"    - timestamp_utc (ISO 8601): {btc_data['timestamp_utc']}")
    print(f"    - collection_time_art (ISO 8601): {btc_data['collection_time_art']}")
    
    # 6. Verificar tipos en BTC entry
    assert btc_data["hour"] == 17, f"Hour debe ser 17, recibido {btc_data['hour']}"
    assert btc_data["price_usd"] == 110340.829253726, "Price incorrecto"
    assert btc_data["source_api"] == "coingecko", "Source API incorrecto"
    assert isinstance(btc_data["timestamp_utc"], str), "timestamp_utc debe ser string (ISO 8601)"
    assert isinstance(btc_data["collection_time_art"], str), "collection_time_art debe ser string (ISO 8601)"
    print(f"\n✓ Todos los campos de BTC[0] son válidos")
    
    # 7. Verificar que XAU también es array
    assert isinstance(serialized["prices"]["XAU"], list), "XAU debe ser array"
    assert len(serialized["prices"]["XAU"]) == 1, "XAU debe tener 1 entrada"
    xau_data = serialized["prices"]["XAU"][0]
    print(f"\n✓ XAU[0]:")
    print(f"    - hour: {xau_data['hour']}")
    print(f"    - price_usd: {xau_data['price_usd']}")
    print(f"    - source_api: {xau_data['source_api']}")
    
    # 8. Verificar JSON-serializable (puede ser convertido a string sin errores)
    json_str = json.dumps(serialized)
    assert len(json_str) > 0, "JSON string debe ser no-vacío"
    print(f"\n✓ Serializable a JSON: {len(json_str)} caracteres")
    
    # 9. Puede ser parseado de vuelta
    parsed = json.loads(json_str)
    assert parsed["date"] == "2025-10-25", "Parse fallido"
    print(f"✓ Parseado correctamente de JSON")
    
    print("\n" + "="*80)
    print("✅ TODOS LOS TESTS PASARON CORRECTAMENTE")
    print("="*80)
    print("\nEstructura lista para envío a Google Sheets:")
    print(f"  - date: {serialized['date']}")
    print(f"  - date_art: {serialized['date_art']}")
    print(f"  - prices: {list(serialized['prices'].keys())}")
    print(f"  - Total entries: {sum(len(v) for v in serialized['prices'].values())}")
    print()

if __name__ == "__main__":
    test_daily_price_record_serialization()
