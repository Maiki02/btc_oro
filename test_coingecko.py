"""
Script de prueba para verificar la integración con CoinGecko API.
"""
import os
from datetime import datetime
import pytz
from dotenv import load_dotenv

from src.clients.api_clients import CoinGeckoClient
from src.utils.time_utils import get_timestamp_range_for_bitcoin

# Cargar variables de entorno
load_dotenv()

def main():
    print("="*70)
    print("🧪 TEST: CoinGecko API - Precio de Bitcoin")
    print("="*70)
    
    # Obtener la API key
    api_key = os.getenv('COINGECKO_API_KEY')
    print(f"\n🔑 API Key: {api_key[:10]}..." if api_key else "\n❌ API Key no encontrada")
    
    if not api_key:
        print("\n❌ ERROR: No se encontró COINGECKO_API_KEY en el archivo .env")
        return
    
    try:
        # Crear cliente
        client = CoinGeckoClient(api_key)
        print("✅ Cliente de CoinGecko creado exitosamente")
        
        # Obtener timestamps para buscar BTC (hora 10:00 ART, ±10 minutos)
        target_hour = 10
        time_range_minutes = 10
        
        from_ts, to_ts, target_datetime_utc = get_timestamp_range_for_bitcoin(
            target_hour, 
            time_range_minutes
        )
        
        # Convertir timestamps a fechas legibles
        from_date = datetime.fromtimestamp(from_ts, tz=pytz.utc)
        to_date = datetime.fromtimestamp(to_ts, tz=pytz.utc)
        
        print(f"\n📅 Buscando precio de Bitcoin:")
        print(f"   • Hora objetivo: {target_hour}:00 ART")
        print(f"   • Rango: {from_date.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"         a {to_date.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"   • From timestamp: {from_ts}")
        print(f"   • To timestamp: {to_ts}")
        
        # Hacer la petición
        print("\n🔄 Consultando CoinGecko API...")
        response = client.get_bitcoin_price_in_range(from_ts, to_ts)
        
        # Procesar respuesta
        price_points = response.get_price_points()
        
        if not price_points:
            print("\n❌ No se encontraron precios en el rango especificado")
            return
        
        print(f"\n✅ RESPUESTA EXITOSA!")
        print(f"📊 Puntos de precio recibidos: {len(price_points)}")
        
        # Encontrar el precio más cercano a la hora objetivo
        target_timestamp_ms = int(target_datetime_utc.timestamp() * 1000)
        
        closest_point = min(
            price_points,
            key=lambda p: abs(p.timestamp - target_timestamp_ms)
        )
        
        # Convertir timestamp a fecha legible
        closest_date = datetime.fromtimestamp(closest_point.timestamp / 1000, tz=pytz.utc)
        time_diff = abs(closest_point.timestamp - target_timestamp_ms) / 1000 / 60  # diferencia en minutos
        
        print(f"\n💰 Precio de Bitcoin (BTC):")
        print(f"   • Precio: ${closest_point.price:,.2f} USD")
        print(f"   • Timestamp: {closest_date.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"   • Diferencia con hora objetivo: {time_diff:.1f} minutos")
        
        # Mostrar algunos precios adicionales
        print(f"\n📈 Primeros 5 precios del rango:")
        for i, point in enumerate(price_points[:5]):
            date = datetime.fromtimestamp(point.timestamp / 1000, tz=pytz.utc)
            print(f"   {i+1}. ${point.price:,.2f} - {date.strftime('%H:%M:%S')} UTC")
        
        print(f"\n{'='*70}")
        print("✅ TEST COMPLETADO EXITOSAMENTE")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ ERROR durante la prueba:")
        print(f"   {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
