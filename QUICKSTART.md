# 🚀 Guía de Inicio Rápido - BTC-Oro Price Fetcher

## Pasos para comenzar (5 minutos)

### 1. Instalar dependencias

```powershell
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual (PowerShell)
.\venv\Scripts\Activate.ps1

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

Edita el archivo `.env`:

```env
# Reemplaza estos valores con tus API keys reales
COINGECKO_API_KEY=tu_api_key_aqui
METALS_API_KEY=tu_api_key_aqui
GOOGLE_SHEET_API_URL=https://tu-api-url.com

# MongoDB (usar valores por defecto si MongoDB está en local)
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=btc_oro_db

# Puerto del servidor
SERVER_PORT=8080
```

### 3. Verificar MongoDB

```powershell
# Verificar que MongoDB esté ejecutándose
# Si no tienes MongoDB instalado, descárgalo de:
# https://www.mongodb.com/try/download/community

# Verificar conexión
mongo --eval "db.version()"
```

### 4. Iniciar el servidor

```powershell
python main.py
```

Deberías ver algo como:

```
============================================================
🚀 Servidor BTC-Oro ejecutándose en puerto 8080
============================================================

Endpoints disponibles:
  • GET /health
  • GET /api/v1/health
  • GET /api/v1/trigger-fetch

Ejemplos de uso:
  curl http://localhost:8080/api/v1/health
  curl http://localhost:8080/api/v1/trigger-fetch
  curl http://localhost:8080/api/v1/trigger-fetch?hour=10
============================================================
```

### 5. Probar el servidor

Abre otra terminal y ejecuta:

```powershell
# Test 1: Health check
curl http://localhost:8080/health

# Test 2: Obtener precios (hora actual)
curl http://localhost:8080/api/v1/trigger-fetch

# Test 3: Obtener precios para las 10:00 ART
curl http://localhost:8080/api/v1/trigger-fetch?hour=10
```

### 6. (Opcional) Ejecutar tests automáticos

```powershell
python test_manual.py
```

## Solución rápida de problemas

### ❌ Error: "Variables de entorno faltantes"
**Solución:** Edita el archivo `.env` y agrega las API keys faltantes.

### ❌ Error: "Error al conectar con MongoDB"
**Solución:** 
1. Verifica que MongoDB esté ejecutándose
2. Verifica la URI en el archivo `.env`
3. Intenta: `mongo --eval "db.version()"`

### ❌ Error: "Module not found"
**Solución:** 
```powershell
pip install -r requirements.txt
```

### ❌ Error: "Port 8080 already in use"
**Solución:** 
1. Cambia el puerto en `.env`: `SERVER_PORT=8081`
2. O detén el proceso que está usando el puerto 8080

### ❌ Error al activar entorno virtual en PowerShell
**Solución:**
```powershell
# Ejecuta esto primero (como Administrador)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Luego activa el entorno virtual
.\venv\Scripts\Activate.ps1
```

## Estructura del proyecto

```
btc_oro/
├── src/                    # Código fuente
│   ├── clients/           # Clientes de APIs externas
│   ├── handlers/          # Procesadores de peticiones HTTP
│   ├── models/            # Modelos de datos (Pydantic)
│   ├── repositories/      # Acceso a base de datos
│   ├── routes/            # Definición de rutas
│   ├── services/          # Lógica de negocio
│   ├── utils/             # Utilidades (tiempo, etc.)
│   └── config.py          # Configuración
├── main.py                # Servidor HTTP
├── requirements.txt       # Dependencias
├── .env                   # Variables de entorno
└── README.md             # Documentación completa
```

## Próximos pasos

1. ✅ **Configurar cron jobs:** Ver `windows-task-scheduler.md`
2. ✅ **Revisar logs:** El servidor imprime logs en la consola
3. ✅ **Verificar MongoDB:** Usa MongoDB Compass para ver los datos
4. ✅ **Configurar Google Sheets:** Sigue la documentación de Google Sheets API

## Comandos útiles

```powershell
# Ver logs en tiempo real (si redirigiste a archivo)
Get-Content -Path "server.log" -Wait -Tail 50

# Listar datos en MongoDB
mongo btc_oro_db --eval "db.asset_prices.find().pretty()"

# Verificar tareas programadas
Get-ScheduledTask | Where-Object {$_.TaskName -like "*BTC-Oro*"}

# Detener el servidor
# Presiona Ctrl+C en la terminal donde se está ejecutando
```

## Contacto y soporte

Para preguntas o problemas, consulta:
- 📖 README.md (documentación completa)
- 🔧 windows-task-scheduler.md (configuración de tareas)
- 🧪 test_manual.py (scripts de prueba)

## ¡Listo! 🎉

El servidor está configurado y listo para usar. 

Para configurar las ejecuciones automáticas a las 10:00 y 17:00, 
consulta el archivo `windows-task-scheduler.md`.