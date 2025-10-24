# BTC-Oro Price Fetcher

Servicio de adquisición automatizada de datos de precios de Bitcoin (BTC) y Oro (XAU) en USD.

## Descripción

Este proyecto implementa un servicio en Python que consulta APIs públicas dos veces al día (10:00 y 17:00 hora de Argentina) para obtener los precios actuales de Bitcoin y Oro. Los datos se almacenan en MongoDB y se envían a Google Sheets para su análisis.

### Características

- ✅ Arquitectura en capas (cebolla) con separación clara de responsabilidades
- ✅ Gestión correcta de zonas horarias (ART ↔ UTC)
- ✅ Validación de datos con Pydantic
- ✅ Almacenamiento persistente en MongoDB
- ✅ Integración con Google Sheets
- ✅ API REST básica con endpoints HTTP
- ✅ Manejo robusto de errores y logging

## Arquitectura

```
btc_oro/
├── src/
│   ├── routes/         # Definición de rutas HTTP
│   ├── handlers/       # Procesamiento de peticiones
│   ├── services/       # Lógica de negocio
│   ├── repositories/   # Acceso a base de datos
│   ├── clients/        # Clientes de APIs externas
│   ├── models/         # Modelos de datos (Pydantic)
│   ├── utils/          # Utilidades (tiempo, conversiones)
│   └── config.py       # Configuración de la aplicación
├── main.py             # Punto de entrada del servidor
├── requirements.txt    # Dependencias
└── .env               # Variables de entorno
```

## Instalación

### Prerrequisitos

- Python 3.8 o superior
- MongoDB instalado y ejecutándose
- Cuentas y API keys para:
  - CoinGecko API
  - Metals-API
  - Google Sheets API configurada

### Pasos de instalación

1. **Clonar o navegar al directorio del proyecto:**
   ```bash
   cd btc_oro
   ```

2. **Crear un entorno virtual (recomendado):**
   ```bash
   python -m venv venv
   
   # Windows PowerShell
   .\venv\Scripts\Activate.ps1
   
   # Windows CMD
   .\venv\Scripts\activate.bat
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar variables de entorno:**
   
   Edita el archivo `.env` con tus credenciales:
   ```env
   COINGECKO_API_KEY=tu_api_key_de_coingecko
   METALS_API_KEY=tu_api_key_de_metals_api
   MONGO_URI=mongodb://localhost:27017
   MONGO_DB_NAME=btc_oro_db
   GOOGLE_SHEET_API_URL=https://tu-api-de-google-sheets.com/v1/spreadsheets
   SERVER_PORT=8080
   ```

## Uso

### Iniciar el servidor

```bash
python main.py
```

El servidor se iniciará en `http://localhost:8080` (o el puerto configurado en `.env`).

### Endpoints disponibles

#### 1. Health Check
```bash
GET /health
GET /api/v1/health
```

Verifica que el servicio esté funcionando.

**Ejemplo:**
```bash
curl http://localhost:8080/health
```

#### 2. Trigger Fetch (Obtener precios)
```bash
GET /api/v1/trigger-fetch
GET /api/v1/trigger-fetch?hour=10
```

Inicia el proceso de obtención y almacenamiento de precios.

**Parámetros opcionales:**
- `hour`: Hora objetivo (10 o 17). Si no se especifica, usa la hora actual.

**Ejemplos:**
```bash
# Obtener precios para la hora actual
curl http://localhost:8080/api/v1/trigger-fetch

# Obtener precios para las 10:00 ART
curl http://localhost:8080/api/v1/trigger-fetch?hour=10

# Obtener precios para las 17:00 ART
curl http://localhost:8080/api/v1/trigger-fetch?hour=17
```

## Configuración de Cron Job

Para ejecutar el servicio automáticamente dos veces al día, configura un cron job:

### Linux/Mac

Edita el crontab:
```bash
crontab -e
```

Agrega las siguientes líneas:
```cron
# Ejecutar a las 10:00 ART todos los días
0 10 * * * curl http://localhost:8080/api/v1/trigger-fetch?hour=10

# Ejecutar a las 17:00 ART todos los días
0 17 * * * curl http://localhost:8080/api/v1/trigger-fetch?hour=17
```

### Windows (Task Scheduler)

1. Abre el Programador de tareas
2. Crea una nueva tarea básica
3. Configura para ejecutar dos veces al día (10:00 y 17:00)
4. Acción: Iniciar un programa
5. Programa: `curl` o `powershell`
6. Argumentos: 
   ```
   -Uri "http://localhost:8080/api/v1/trigger-fetch?hour=10"
   ```

## APIs Utilizadas

### 1. CoinGecko API
- **Endpoint:** `/coins/bitcoin/market_chart/range`
- **Propósito:** Obtener precios históricos de Bitcoin
- **Plan:** Gratuito
- **Documentación:** https://www.coingecko.com/en/api

### 2. Metals-API
- **Endpoint:** `/api/YYYY-MM-DD`
- **Propósito:** Obtener precio de cierre del oro
- **Cálculo importante:** El precio se calcula como `1 / valor_recibido` para obtener USD por onza
- **Plan:** Gratuito
- **Documentación:** https://metals-api.com/documentation

### 3. Google Sheets API
- **Propósito:** Almacenar datos en planilla de Google Sheets
- **Requiere:** Configuración de OAuth2 o Service Account

## Modelos de Datos

### AssetPriceRecord
Modelo principal para almacenar precios:
```python
{
    "asset_name": "BTC" | "XAU",
    "price_usd": float,
    "timestamp_utc": datetime,
    "source_api": "coingecko" | "metals-api",
    "collection_time_art": datetime,
    "target_hour_art": 10 | 17
}
```

## Manejo de Zonas Horarias

El proyecto maneja correctamente la conversión entre:
- **ART (Argentina Time):** UTC-3
- **UTC:** Tiempo universal coordinado

Las APIs requieren timestamps en UTC, mientras que la lógica de negocio opera en hora de Argentina.

## Logging

Los logs se imprimen en la consola con el siguiente formato:
```
2025-10-24 10:00:00 - module_name - INFO - Mensaje de log
```

## Estructura de Respuestas

### Respuesta exitosa
```json
{
  "success": true,
  "message": "Proceso completado. Registros procesados: 2",
  "records_processed": 2,
  "errors": [],
  "timestamp": "2025-10-24T13:00:00.000000"
}
```

### Respuesta con errores
```json
{
  "success": false,
  "message": "Proceso completado. Registros procesados: 1. Errores: 1",
  "records_processed": 1,
  "errors": ["No se pudo obtener el precio del Oro"],
  "timestamp": "2025-10-24T13:00:00.000000"
}
```

## Desarrollo

### Ejecutar en modo desarrollo
```bash
python main.py
```

### Testing manual
Usa `curl` o Postman para probar los endpoints.

## Troubleshooting

### Error de conexión a MongoDB
- Verifica que MongoDB esté ejecutándose
- Revisa la URI en el archivo `.env`
- Comprueba los permisos de usuario

### Error de API Key
- Verifica que las API keys sean válidas
- Revisa los límites de rate limiting de cada API
- Confirma que las keys estén correctamente configuradas en `.env`

### Error de zona horaria
- Verifica que `pytz` esté instalado correctamente
- Confirma que la configuración de zona horaria sea correcta

## Contribución

Este es un proyecto privado. Para realizar cambios:
1. Crea una rama para tu feature
2. Implementa los cambios siguiendo la arquitectura en capas
3. Prueba exhaustivamente
4. Crea un pull request

## Licencia

Proyecto privado - Todos los derechos reservados

## Contacto

Para preguntas o soporte, contacta al equipo de desarrollo.