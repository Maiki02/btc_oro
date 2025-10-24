"""
DIAGRAMA DEL FLUJO CORREGIDO
====================================================================================

FLUJO COMPLETO: Obtención de Precios → MongoDB → GoogleSheet
====================================================================================

┌─────────────────────────────────────────────────────────────────────────────────┐
│                         ENTRADA: HTTP GET                                       │
│              /api/v1/trigger-fetch?hour=10                                      │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────────┐
│  1. HANDLER → SERVICE: fetch_and_store_prices(target_hour=10)                   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────────┐
│  2. OBTENER PRECIOS (AssetPriceRecord - formato intermedio)                     │
│                                                                                 │
│  ┌──────────────────────────┐        ┌──────────────────────────┐              │
│  │   COINGECKO API          │        │   GOLDAPI API            │              │
│  │  (BTC Price Range)       │        │  (XAU Current Price)     │              │
│  │                          │        │                          │              │
│  │  ✓ Obtiene múltiples     │        │  ✓ Obtiene precio actual │              │
│  │    puntos de precio      │        │    del oro en USD        │              │
│  │  ✓ Encuentra el más      │        │  ✓ Timestamp en UTC      │              │
│  │    cercano a la hora     │        │                          │              │
│  └──────────────────────────┘        └──────────────────────────┘              │
│         ↓                                        ↓                              │
│    Dict:                                    Dict:                              │
│    {                                        {                                  │
│      price_usd: 43250.75                      price_usd: 2738.15               │
│      timestamp_utc: datetime                  timestamp_utc: datetime          │
│      source_api: "coingecko"                  source_api: "goldapi"            │
│      collection_time_art: datetime            collection_time_art: datetime    │
│    }                                        }                                  │
│                                                                                │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────────┐
│  3. CONSOLIDAR EN DailyPriceRecord (estructura para MongoDB)                    │
│                                                                                 │
│  {                                                                              │
│    "date": "2025-10-24",                                                       │
│    "date_art": ISODate("2025-10-24T..."),                                      │
│    "prices": {                                                                 │
│      "BTC": {                                                                  │
│        "hour_10": PriceSnapshot {                                              │
│          price_usd: 43250.75,                                                  │
│          timestamp_utc: datetime,                                              │
│          source_api: "coingecko",                                              │
│          collection_time_art: datetime                                         │
│        }                                                                       │
│      },                                                                        │
│      "XAU": {                                                                  │
│        "hour_10": PriceSnapshot { ... }                                        │
│      }                                                                         │
│    }                                                                           │
│  }                                                                              │
│                                                                                │
│  ✓ Una sola estructura para ambos activos                                     │
│  ✓ Organizada por fecha y hora                                                │
│  ✓ Fácil de expandir (agregar hour_17 sin cambiar estructura)                │
│                                                                                │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────────┐
│  4. GUARDAR O ACTUALIZAR EN MONGODB (UPSERT)                                    │
│                                                                                 │
│  Repository.save_price_record(daily_record)                                    │
│                                                                                 │
│  Si existe fecha "2025-10-24":                                                 │
│    → UPDATE: Agregar/actualizar BTC y XAU en hour_10                           │
│      (preserva datos existentes de hour_17 si existen)                         │
│                                                                                 │
│  Si NO existe fecha "2025-10-24":                                              │
│    → INSERT: Crear documento nuevo                                             │
│                                                                                 │
│  ✓ Una sola operación de BD por ejecución (eficiente)                         │
│  ✓ Consolidación automática en el tiempo                                      │
│  ✓ 365 docs/año vs 2,920 docs/año (reducción del 87%)                        │
│                                                                                │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────────┐
│  5. RECUPERAR DOCUMENTO ACTUALIZADO DE MONGODB                                  │
│                                                                                 │
│  Repository.get_daily_prices("2025-10-24")                                     │
│                                                                                 │
│  ✓ Retorna el documento completo con todos los datos                          │
│  ✓ Si es primera ejecución: contiene hour_10                                  │
│  ✓ Si es segunda ejecución: contiene hour_10 + hour_17                        │
│                                                                                 │
│  Este es el MISMO DOCUMENTO que enviamos a GoogleSheet                        │
│                                                                                │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────────┐
│  6. ENVIAR A GOOGLESHEET (SIN TRANSFORMACIÓN)                                   │
│                                                                                 │
│  Service._send_to_google_sheets(daily_record)                                  │
│                                                                                 │
│  GoogleSheetClient.save_record(daily_record.model_dump())                      │
│                                                                                 │
│  ✓ Envía el DOCUMENTO COMPLETO que vino de MongoDB                            │
│  ✓ GoogleSheet es responsable de cómo lo procesa                              │
│  ✓ No hacemos transformación en el servicio                                   │
│  ✓ GoogleSheet puede extraer campos, crear filas, etc.                        │
│                                                                                │
│  El documento enviado incluye:                                                 │
│  - "date": "2025-10-24"                                                        │
│  - "prices": {BTC: {hour_10: {...}, hour_17: {...}}, XAU: {...}}              │
│  - O solo hour_10 si es la primera ejecución                                  │
│                                                                                │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         RESPUESTA HTTP 200                                      │
│  {                                                                              │
│    "success": true,                                                            │
│    "message": "Proceso completado. Precios recolectados: 2"                   │
│  }                                                                              │
└─────────────────────────────────────────────────────────────────────────────────┘


CASOS DE USO
====================================================================================

CASO 1: Primera ejecución del día (10:00 ART)
────────────────────────────────────────────────────────────────────────────────
  HTTP GET /api/v1/trigger-fetch?hour=10
    ↓
  fetch_and_store_prices(10)
    ↓
  Obtiene BTC + XAU
    ↓
  Crea DailyPriceRecord con BTC.hour_10 + XAU.hour_10
    ↓
  Repository: INSERT nueva fecha "2025-10-24"
    ↓
  Recupera: {date, prices: {BTC: {hour_10}, XAU: {hour_10}}}
    ↓
  Envía a GoogleSheet: Documento con ambos activos en hour_10


CASO 2: Segunda ejecución del día (17:00 ART)
────────────────────────────────────────────────────────────────────────────────
  HTTP GET /api/v1/trigger-fetch?hour=17
    ↓
  fetch_and_store_prices(17)
    ↓
  Obtiene BTC + XAU (nuevos precios)
    ↓
  Crea DailyPriceRecord con BTC.hour_17 + XAU.hour_17
    ↓
  Repository: UPDATE fecha "2025-10-24"
    ✓ Agrega hour_17 a BTC
    ✓ Agrega hour_17 a XAU
    ✓ Preserva hour_10 existente
    ↓
  Recupera: {date, prices: {BTC: {hour_10, hour_17}, XAU: {hour_10, hour_17}}}
    ↓
  Envía a GoogleSheet: Documento con ambos activos en AMBAS horas


BENEFICIOS DEL FLUJO CORREGIDO
====================================================================================

✅ PERSISTENCIA CORRECTA
   - MongoDB guarda datos reales (descomentado)
   - Upsert automático evita duplicados
   - Documento crece durante el día (consolidación)

✅ RESPONSABILIDAD CLARA
   - Servicio: Obtiene precios + consolida + guarda
   - GoogleSheet: Decide cómo formatear/guardar
   - No transformamos datos en el servicio

✅ EFICIENCIA
   - 1 documento/día vs 4 documentos/día
   - 365 docs/año vs 2,920 docs/año
   - 87% menos espacio en BD

✅ EXTENSIBILIDAD
   - Fácil agregar new_asset (solo nueva llave en prices)
   - Fácil agregar nueva hora (solo nuevo hour_XX)
   - No requiere cambios en estructura

✅ FACILIDAD DE DEBUGGING
   - Flujo lineal: Obtener → Consolidar → Guardar → Enviar
   - Cada paso es responsable de una cosa
   - Logs claros en cada etapa

"""
print(__doc__)
