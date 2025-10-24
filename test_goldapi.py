"""
Script de prueba rápida para GoldAPI.io
Ejecuta este script para probar que la API funciona correctamente.
"""
import requests
import json

def test_goldapi():
    """Prueba rápida de GoldAPI.io"""
    api_key = "goldapi-l32r3smh51f4pj-io"
    symbol = "XAU"
    curr = "USD"
    
    url = f"https://www.goldapi.io/api/{symbol}/{curr}"
    
    headers = {
        "x-access-token": api_key,
        "Content-Type": "application/json"
    }
    
    print("🧪 Probando GoldAPI.io...")
    print(f"📍 URL: {url}")
    print(f"🔑 API Key: {api_key[:20]}...")
    print("\n" + "="*60)
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        
        print("✅ RESPUESTA EXITOSA!")
        print("="*60)
        print(json.dumps(result, indent=2))
        print("="*60)
        print(f"\n💰 Precio del Oro (XAU): ${result.get('price', 'N/A')} USD/oz")
        print(f"📊 Cambio: {result.get('ch', 'N/A')} ({result.get('chp', 'N/A')}%)")
        print(f"📈 Máximo: ${result.get('high_price', 'N/A')}")
        print(f"📉 Mínimo: ${result.get('low_price', 'N/A')}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"📄 Respuesta del servidor: {e.response.text}")

if __name__ == "__main__":
    test_goldapi()
