"""
Script de prueba manual para verificar el funcionamiento del servicio.
Ejecuta este script con el servidor en funcionamiento.
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8080"

def print_separator():
    print("\n" + "="*70 + "\n")

def test_health_check():
    """Prueba el endpoint de health check."""
    print("🔍 Probando Health Check...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_trigger_fetch_default():
    """Prueba el endpoint trigger-fetch sin parámetros."""
    print("🔍 Probando Trigger Fetch (sin parámetros)...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/trigger-fetch", timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, default=str)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_trigger_fetch_with_hour(hour: int):
    """Prueba el endpoint trigger-fetch con un parámetro de hora."""
    print(f"🔍 Probando Trigger Fetch (hour={hour})...")
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/trigger-fetch",
            params={'hour': hour},
            timeout=30
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, default=str)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_invalid_route():
    """Prueba una ruta que no existe."""
    print("🔍 Probando ruta inválida...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/invalid", timeout=5)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 404
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Ejecuta todas las pruebas."""
    print("\n" + "🚀 INICIANDO PRUEBAS DEL SERVICIO BTC-ORO")
    print(f"Hora actual: {datetime.now()}")
    print_separator()
    
    results = {}
    
    # Test 1: Health Check
    results['health_check'] = test_health_check()
    print_separator()
    
    # Test 2: Trigger Fetch sin parámetros
    results['trigger_default'] = test_trigger_fetch_default()
    print_separator()
    
    # Test 3: Trigger Fetch con hour=10
    results['trigger_hour_10'] = test_trigger_fetch_with_hour(10)
    print_separator()
    
    # Test 4: Trigger Fetch con hour=17
    results['trigger_hour_17'] = test_trigger_fetch_with_hour(17)
    print_separator()
    
    # Test 5: Ruta inválida
    results['invalid_route'] = test_invalid_route()
    print_separator()
    
    # Resumen
    print("📊 RESUMEN DE PRUEBAS")
    print_separator()
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    total = len(results)
    passed = sum(1 for r in results.values() if r)
    
    print_separator()
    print(f"Total: {passed}/{total} pruebas pasaron")
    
    if passed == total:
        print("\n🎉 ¡Todas las pruebas pasaron exitosamente!")
    else:
        print(f"\n⚠️  {total - passed} prueba(s) fallaron")

if __name__ == "__main__":
    print("\n⚠️  ASEGÚRATE DE QUE EL SERVIDOR ESTÉ EJECUTÁNDOSE")
    print("Ejecuta: python main.py")
    input("\nPresiona Enter para continuar con las pruebas...")
    
    main()