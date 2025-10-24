# 📦 Guía Completa: Despliegue en AWS Lambda

## 🎯 Objetivo

Convertir tu aplicación Python de un servidor HTTP tradicional a una función serverless en AWS Lambda que se ejecuta automáticamente a las 10:00 y 17:00 (hora Argentina).

---

## 📋 Requisitos Previos

- ✅ Cuenta de AWS
- ✅ AWS CLI instalado (opcional, pero recomendado)
- ✅ Python 3.11+ en tu PC
- ✅ El código fuente del proyecto (`lambda_handler.py` ya incluido)
- ✅ Las variables de entorno configuradas en `.env`

---

## Parte 1: Preparar el Código Local

### Paso 1.1: Verificar que tienes `lambda_handler.py`

El archivo `lambda_handler.py` ya está creado en la carpeta principal del proyecto. Este archivo:

- ✅ Es el punto de entrada para Lambda
- ✅ Convierte eventos de Lambda a llamadas de tu servicio
- ✅ Mantiene las mismas dependencias que el servidor local
- ✅ Compatible con API Gateway y CloudWatch Events

**Ubicación:** `c:\Users\miqui\Proyectos\btc_oro\lambda_handler.py`

### Paso 1.2: Verificar `requirements.txt`

Ya ha sido actualizado con comentarios sobre Lambda. Las dependencias son:

```
python-dotenv==1.0.0
requests==2.31.0
pytz==2023.3
pymongo==4.6.0
pydantic==2.5.0
```

### Paso 1.3: Variables de entorno

El archivo `.env` ya ha sido actualizado con explicaciones. Valores necesarios:

```
COINGECKO_API_KEY=CG-XuoBZisyuhhjYKCfLTFkJVUc
GOLDAPI_KEY=goldapi-l32r3smh51f4pj-io
MONGO_URI=mongodb+srv://gentiledev:RZCRhLLZVQiChpNl@...
MONGO_DB_NAME=btc_oro_db
GOOGLE_SHEET_API_URL=https://script.google.com/macros/s/AKfycbx...
```

---

## Parte 2: Crear el Paquete de Despliegue (Paso a Paso Detallado)

### Paso 2.1: Preparar la carpeta

En PowerShell, en la carpeta `c:\Users\miqui\Proyectos\btc_oro`:

```powershell
# Crear carpeta para el paquete
mkdir lambda_package
cd lambda_package
```

### Paso 2.2: Copiar el código fuente

```powershell
# Copiar carpeta src
Copy-Item -Path "..\src" -Destination ".\src" -Recurse

# Copiar handler de Lambda
Copy-Item -Path "..\lambda_handler.py" -Destination ".\lambda_handler.py"

# Verificar que se copió todo
ls
# Deberías ver: src/ y lambda_handler.py
```

### Paso 2.3: Instalar dependencias

```powershell
# Instalar todas las librerías EN esta carpeta (importante: -t .)
pip install -r ..\requirements.txt -t .

# Esto descarga:
# - python-dotenv/
# - requests/
# - pytz/
# - pymongo/
# - pydantic/
# ... y todas sus dependencias
```

### Paso 2.4: Crear el archivo ZIP

```powershell
# Comprimir TODO lo que está en esta carpeta
Compress-Archive -Path * -DestinationPath lambda_deployment.zip

# Verificar que se creó (debería mostrar tamaño en KB/MB)
ls -Name lambda_deployment.zip
```

### Paso 2.5: Mover el ZIP a la carpeta principal

```powershell
# Mover el ZIP fuera de lambda_package
Move-Item -Path lambda_deployment.zip -Destination "..\lambda_deployment.zip"

# Volver a la carpeta principal
cd ..

# Verificar
ls -Name lambda_deployment.zip
```

### ✅ Resultado esperado

En `c:\Users\miqui\Proyectos\btc_oro\` deberías tener:

```
lambda_deployment.zip  (5-20 MB aproximadamente)
lambda_handler.py
main.py
requirements.txt
.env
src/
Docs/
...
```

---

## Parte 3: Crear la Función en AWS

### Paso 3.1: Abrir AWS Console

1. Abre tu navegador
2. Ve a https://console.aws.amazon.com
3. Inicia sesión con tu cuenta
4. Busca "Lambda" en la barra de búsqueda
5. Haz clic en **Lambda**

### Paso 3.2: Crear una nueva función

1. Clic en **Crear función**
2. Selecciona **"Crear desde cero"**
3. **Nombre de la función:** `btc-oro-fetcher`
4. **Runtime:** `Python 3.11` (o superior)
5. **Arquitectura:** `x86_64` (recomendado)
6. **Rol de ejecución:** 
   - Selecciona **"Crear un nuevo rol con permisos Lambda básicos"**
   - AWS creará automáticamente uno
7. Clic en **Crear función**

### Paso 3.3: Subir el código

1. En la página de la función, ve a la sección **Código fuente**
2. Haz clic en **Cargar desde** → **Archivo .zip**
3. Selecciona `lambda_deployment.zip` de tu PC
4. Clic en **Guardar**

⏳ Esto puede tardar 30-60 segundos. Espera a que salga el mensaje de éxito.

### Paso 3.4: Configurar el Handler

1. En la misma página, ve a **Configuración** → **General**
2. Busca el campo **Handler**
3. Borra lo que dice y escribe exactamente: `lambda_handler.lambda_handler`
4. Clic en **Guardar** (arriba a la derecha)

### Paso 3.5: Añadir variables de entorno

1. En **Configuración** → **Variables de entorno**
2. Clic en **Editar**
3. Clic en **Añadir variable de entorno**
4. Para cada una, añade:

```
Clave                       Valor
────────────────────────────────────────────────────────────
COINGECKO_API_KEY          CG-XuoBZisyuhhjYKCfLTFkJVUc
GOLDAPI_KEY                goldapi-l32r3smh51f4pj-io
MONGO_URI                  mongodb+srv://gentiledev:RZ...
MONGO_DB_NAME              btc_oro_db
GOOGLE_SHEET_API_URL       https://script.google.com/macros/...
```

5. Clic en **Guardar**

### Paso 3.6: Aumentar timeout (opcional pero recomendado)

1. En **Configuración** → **General**
2. Ve a **Configuración general**
3. **Timeout:** Cambia a `60` segundos
4. **Memoria:** `512 MB` (o 256 si prefieres ahorrar costes)
5. Clic en **Guardar**

---

## Parte 4: Configurar la Ejecución Automática (CloudWatch)

### Opción A: Ejecutar a horas específicas (10:00 y 17:00)

#### Paso 4A.1: Crear trigger para las 10:00

1. En la función Lambda, clic en **Agregar trigger**
2. **Origen del trigger:** EventBridge (CloudWatch Events)
3. Selecciona **"Crear nueva regla"**
4. **Nombre de la regla:** `btc-oro-10am`
5. **Tipo de regla:** Expresión de programación
6. **Expresión de programación:** `cron(0 10 * * ? *)`
   - Esto significa: Cada día a las 10:00 UTC
   - ⚠️ IMPORTANTE: CloudWatch usa UTC, no ART
   - Para 10:00 ART, usa: `cron(13 * * * ? *)` (UTC-3)
   - Para 17:00 ART, usa: `cron(20 * * * ? *)` (UTC-3)
7. Clic en **Agregar**

#### Paso 4A.2: Crear trigger para las 17:00

Repite el proceso anterior:

1. Clic en **Agregar trigger**
2. **Nombre de la regla:** `btc-oro-5pm`
3. **Expresión de programación:** `cron(20 * * * ? *)`
4. Clic en **Agregar**

---

### Opción B: Ejecutar manualmente vía HTTP (API Gateway)

#### Paso 4B.1: Crear API Gateway

1. Busca **API Gateway** en AWS Console
2. Haz clic en **Crear API**
3. Selecciona **API REST**
4. **Nombre:** `btc-oro-api`
5. Clic en **Crear API**

#### Paso 4B.2: Crear endpoint

1. En la API, clic en **Métodos** → **NUEVO MÉTODO**
2. Selecciona **GET**
3. **Tipo de integración:** Función Lambda
4. **Función Lambda:** `btc-oro-fetcher`
5. Clic en **Guardar**

#### Paso 4B.3: Desplegar la API

1. Clic en **Desplegar API**
2. **Nombre de la fase:** `prod`
3. Clic en **Desplegar**
4. AWS te mostrará una URL pública como: `https://abc123.execute-api.us-east-1.amazonaws.com/prod/`

#### Paso 4B.4: Usar la API

Ahora puedes llamarla desde PowerShell:

```powershell
# Ejecutar para las 10:00
curl "https://abc123.execute-api.us-east-1.amazonaws.com/prod/?hour=10"

# Ejecutar para las 17:00
curl "https://abc123.execute-api.us-east-1.amazonaws.com/prod/?hour=17"
```

---

## Parte 5: Probar la Función

### Test desde AWS Console

1. En la función Lambda, ve a la pestaña **Código**
2. Haz clic en **Prueba**
3. **Nombre de la ejecución de prueba:** `test-trigger-fetch`
4. En **JSON de la prueba**, pega esto:

```json
{
  "queryStringParameters": {
    "hour": "10"
  },
  "path": "/api/v1/trigger-fetch"
}
```

5. Clic en **Invocar**
6. Debajo verás:
   - ✅ **Resultado:** Debería mostrar `statusCode: 200` y los datos de precios
   - ❌ **Error:** Si falla, revisa los logs

### Ver logs

1. Clic en **Monitor** → **Logs**
2. Haz clic en el evento más reciente
3. Verás toda la salida de ejecución, incluyendo errores

---

## Parte 6: Costos Estimados

### Precios de AWS Lambda (aproximados)

| Concepto | Precio |
|----------|--------|
| Primero millón de invocaciones/mes | **GRATIS** |
| Cada millón adicional | $0.20 |
| Tiempo de ejecución (1 MB-segundo) | $0.0000166667 |
| **Total estimado para 60 invocaciones/mes** | **< €1** |

### Ejemplo de coste mensual

- 60 invocaciones (2x al día × 30 días)
- 10 segundos cada invocación
- 512 MB de memoria
- **Coste total: ~€0.05-0.10/mes**

---

## 🔧 Troubleshooting

### ❌ "Handler not found: lambda_handler.lambda_handler"

**Causa:** El archivo no está en el ZIP o el nombre es incorrecto

**Solución:**
```powershell
# Verificar contenido del ZIP
Expand-Archive -Path lambda_deployment.zip -DestinationPath temp_check
ls temp_check/lambda_handler.py
Remove-Item -Recurse temp_check
```

### ❌ "Cannot import module 'src'"

**Causa:** La carpeta `src` no está en el ZIP

**Solución:**
```powershell
cd lambda_package
ls src
# Si no existe, crear de nuevo el paquete
```

### ❌ "pymongo.errors.ServerSelectionTimeoutError"

**Causa:** MongoDB no es accesible desde Lambda

**Solución:**
- Usa MongoDB Atlas (en la nube)
- Configura firewall: Network Access → ADD IP ADDRESS → 0.0.0.0/0
- Verifica MONGO_URI

### ❌ "Task timed out"

**Causa:** Función tardó más de lo permitido

**Solución:**
1. Ve a **Configuración** → **General**
2. Aumenta **Timeout** a 60 segundos
3. Si sigue fallando, aumenta **Memoria**

### ✅ Verificar que funciona

1. Ve a **Monitor** → **Logs**
2. Deberías ver:
   - ✅ "Inicializando dependencias..."
   - ✅ "Clientes de API inicializados"
   - ✅ "Repositorio MongoDB inicializado"
   - ✅ "Respuesta: status_code=200"

---

## 📊 Resumen: Comparación Local vs Lambda

| Aspecto | Local | Lambda |
|---------|:---:|:---:|
| Costo | Servidor 24/7 | ~€0.10/mes |
| Inicio rápido | Sí | No (Cold Start ~3s) |
| Escalabilidad | Manual | Automática |
| Mantenimiento | Completo | AWS lo gestiona |
| ¿Siempre ejecutándose? | Sí | No (solo cuando se invoca) |

---

## 📚 Próximos pasos

1. ✅ Seguir los pasos de esta guía
2. ✅ Probar con el event de prueba
3. ✅ Verificar los logs
4. ✅ Monitorear la primera ejecución automática
5. ✅ (Opcional) Configurar alertas de fallos

---

## 🆘 ¿Necesitas ayuda?

Consulta:
- `Docs/INSTALAR_DEPENDENCIAS.md` - Instalación de librerías
- `Docs/ARCHITECTURE.md` - Arquitectura del proyecto
- `Docs/README.md` - Documentación general
- `lambda_handler.py` - El código específico de Lambda

---

**¡Listo para deployar en AWS! 🚀**
