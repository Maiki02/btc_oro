# 📊 Flujo de Datos y Arquitectura

## Flujo Principal de Ejecución

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      INICIO: Cron Job / HTTP Request                    │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    main.py (Servidor HTTP)                              │
│  • Inicializa todas las dependencias                                    │
│  • Crea instancias de clientes, repositorio, servicio                  │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Router (routes/routes.py)                            │
│  • GET /api/v1/trigger-fetch                                            │
│  • Enruta la petición al handler correspondiente                       │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  PriceHandler (handlers/handler.py)                     │
│  • Recibe la petición HTTP                                              │
│  • Extrae parámetros (ej: hour=10)                                     │
│  • Delega al servicio                                                   │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│             PriceDataService (services/service.py)                      │
│  LÓGICA DE NEGOCIO PRINCIPAL                                            │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │ 1. Determinar hora objetivo (10:00 o 17:00 ART)                  │ │
│  │ 2. Calcular timestamps UTC (±10 minutos)                         │ │
│  │ 3. Obtener precios de Bitcoin y Oro (en paralelo lógico)         │ │
│  │ 4. Normalizar y validar datos                                    │ │
│  │ 5. Guardar en MongoDB                                            │ │
│  │ 6. Enviar a Google Sheets                                        │ │
│  │ 7. Retornar resultado                                            │ │
│  └───────────────────────────────────────────────────────────────────┘ │
└────┬────────────────────────────────────────────────────────┬───────────┘
     │                                                         │
     │                                                         │
     ▼                                                         ▼
┌─────────────────────────────────────┐  ┌──────────────────────────────┐
│ BITCOIN FLOW                        │  │ GOLD FLOW                    │
│                                     │  │                              │
│ 1. CoinGeckoClient                  │  │ 1. MetalsApiClient          │
│    └─> get_bitcoin_price_in_range() │  │    └─> get_gold_closing()   │
│                                     │  │                              │
│ 2. time_utils                       │  │ 2. Cálculo crítico:         │
│    └─> find_closest_price()         │  │    price = 1 / xau_usd      │
│                                     │  │                              │
│ 3. AssetPriceRecord                 │  │ 3. AssetPriceRecord         │
│    └─> asset_name: "BTC"            │  │    └─> asset_name: "XAU"    │
│    └─> price_usd: $XX,XXX           │  │    └─> price_usd: $X,XXX    │
│    └─> source_api: "coingecko"      │  │    └─> source_api: "metals" │
└─────────────┬───────────────────────┘  └──────────┬───────────────────┘
              │                                      │
              └──────────────┬───────────────────────┘
                             │
                             ▼
            ┌────────────────────────────────────────────┐
            │   PERSISTENCIA (en paralelo)               │
            │                                            │
            │  ┌──────────────────────────────────────┐ │
            │  │ PriceRepository                      │ │
            │  │  └─> save_price_record()             │ │
            │  │      └─> MongoDB: btc_oro_db         │ │
            │  │          └─> Collection: asset_prices│ │
            │  └──────────────────────────────────────┘ │
            │                                            │
            │  ┌──────────────────────────────────────┐ │
            │  │ GoogleSheetClient                    │ │
            │  │  └─> save_record()                   │ │
            │  │      └─> Google Sheets API           │ │
            │  │          └─> Append to spreadsheet   │ │
            │  └──────────────────────────────────────┘ │
            └────────────────────────────────────────────┘
                             │
                             ▼
            ┌────────────────────────────────────────────┐
            │   ServiceResponse                          │
            │   {                                        │
            │     success: true,                         │
            │     message: "...",                        │
            │     records_processed: 2,                  │
            │     errors: []                             │
            │   }                                        │
            └────────────────────────────────────────────┘
                             │
                             ▼
            ┌────────────────────────────────────────────┐
            │   HTTP Response (JSON)                     │
            │   Status: 200 OK                           │
            └────────────────────────────────────────────┘
```

## Arquitectura de Capas (Cebolla)

```
┌──────────────────────────────────────────────────────────────┐
│                     CAPA DE PRESENTACIÓN                     │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  main.py (Servidor HTTP)                               │  │
│  │  • http.server.HTTPServer                              │  │
│  │  • RequestHandler                                      │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────┼───────────────────────────────┐
│                     CAPA DE ENRUTAMIENTO                     │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  routes/routes.py                                      │  │
│  │  • Router                                              │  │
│  │  • Mapeo de URLs a handlers                           │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────┼───────────────────────────────┐
│                     CAPA DE HANDLERS                         │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  handlers/handler.py                                   │  │
│  │  • PriceHandler                                        │  │
│  │  • Procesamiento de peticiones                        │  │
│  │  • NO contiene lógica de negocio                      │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────┼───────────────────────────────┐
│                     CAPA DE SERVICIOS                        │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  services/service.py                                   │  │
│  │  • PriceDataService                                    │  │
│  │  • Orquestación de lógica de negocio                  │  │
│  │  • Coordina clientes y repositorio                    │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬───────────────────────────────┘
                               │
                ┌──────────────┴──────────────┐
                │                             │
┌───────────────┼──────────────┐  ┌──────────┼────────────────┐
│    CAPA DE CLIENTES          │  │  CAPA DE REPOSITORIO      │
│  ┌─────────────────────────┐ │  │  ┌──────────────────────┐ │
│  │ clients/api_clients.py  │ │  │  │ repositories/        │ │
│  │ • CoinGeckoClient       │ │  │  │   repository.py      │ │
│  │ • MetalsApiClient       │ │  │  │ • PriceRepository    │ │
│  │ • GoogleSheetClient     │ │  │  │ • Acceso a MongoDB   │ │
│  └─────────────────────────┘ │  │  └──────────────────────┘ │
└──────────────────────────────┘  └───────────────────────────┘
                │                             │
                ▼                             ▼
┌──────────────────────────────────────────────────────────────┐
│                   CAPA DE DATOS EXTERNOS                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │  CoinGecko   │  │  Metals-API  │  │  Google Sheets   │   │
│  │     API      │  │     API      │  │      API         │   │
│  └──────────────┘  └──────────────┘  └──────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │               MongoDB Database                       │   │
│  │  Database: btc_oro_db                                │   │
│  │  Collection: asset_prices                            │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

## Capas Transversales

```
┌──────────────────────────────────────────────────────────────┐
│                    MODELOS DE DATOS                          │
│  models/schemas.py (Pydantic)                                │
│  • CoinGeckoResponse      • AssetPriceRecord                 │
│  • MetalsApiResponse      • GoogleSheetRecord                │
│  • ServiceResponse                                           │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                       UTILIDADES                             │
│  utils/time_utils.py                                         │
│  • Conversión ART ↔ UTC                                      │
│  • Cálculo de timestamps                                     │
│  • Búsqueda de precio más cercano                           │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    CONFIGURACIÓN                             │
│  config.py + .env                                            │
│  • Variables de entorno                                      │
│  • Constantes del proyecto                                   │
└──────────────────────────────────────────────────────────────┘
```

## Manejo de Zona Horaria

```
ENTRADA (Cron/User)          PROCESAMIENTO              SALIDA
─────────────────────────────────────────────────────────────────

10:00 ART                                               MongoDB:
  │                                                     timestamp_utc
  │                    ┌───────────────────┐
  ▼                    │   time_utils      │
10:00 ART ─────────> │                   │ ───────> 13:00 UTC
                       │  ART = UTC - 3   │
                       │                   │          Google Sheets:
                       │  10:00 - (-3)    │          collection_time_art
                       │  = 13:00 UTC     │ ───────> 10:00 ART
                       └───────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  CoinGecko API requiere timestamps en UTC (Unix seconds)   │
│  from: 12:50 UTC  to: 13:10 UTC  (±10 minutos)             │
│                                                             │
│  Se busca el precio más cercano a 13:00 UTC                │
└─────────────────────────────────────────────────────────────┘
```

## Estructura de Datos en MongoDB

```javascript
{
  "_id": ObjectId("..."),
  "asset_name": "BTC",              // o "XAU"
  "price_usd": 43250.75,            // Precio en USD
  "timestamp_utc": ISODate("2025-10-24T13:00:00Z"),
  "source_api": "coingecko",        // o "metals-api"
  "collection_time_art": ISODate("2025-10-24T10:00:00-03:00"),
  "target_hour_art": 10             // 10 o 17
}
```

## Flujo de Errores

```
┌─────────────────────────────────────────────────────────────┐
│  Cada capa maneja sus propios errores y los propaga        │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  Clients:  RequestException → Logged + Re-raised            │
│  Service:  Captura errores → Agrega a lista de errores     │
│  Handler:  Convierte a respuesta HTTP con código apropiado │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  ServiceResponse:                                           │
│  {                                                          │
│    success: false,                                          │
│    records_processed: 1,  // BTC OK, Oro falló             │
│    errors: ["No se pudo obtener el precio del Oro"]        │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘
```

## Inyección de Dependencias

```
main.py inicializa todo:

1. Config.validate_config()
2. CoinGeckoClient(api_key)      ──┐
3. MetalsApiClient(api_key)      ──┤
4. GoogleSheetClient(url)        ──┼──> PriceDataService()
5. PriceRepository(uri, db)      ──┘           │
                                               ▼
                                       PriceHandler()
                                               │
                                               ▼
                                           Router()
```

## Cálculo Crítico: Precio del Oro

```
API Metals-API devuelve:
{
  "rates": {
    "XAUUSD": 0.000515  // 1 USD = 0.000515 onzas de oro
  }
}

Cálculo correcto:
precio_por_onza = 1 / 0.000515 = $1,941.75 USD/onza

❌ ERROR COMÚN: Usar directamente el valor 0.000515
✅ CORRECTO: Calcular 1 / valor_recibido
```