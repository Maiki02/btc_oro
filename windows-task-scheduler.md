# Configuración de Windows Task Scheduler para BTC-Oro Price Fetcher
# 
# Este archivo contiene instrucciones para configurar tareas programadas en Windows

## OPCIÓN 1: Usar PowerShell (Recomendado)

### Script PowerShell para llamar al endpoint
Guarda este script como `trigger-fetch.ps1`:

```powershell
# trigger-fetch.ps1
param(
    [Parameter(Mandatory=$true)]
    [int]$Hour
)

$url = "http://localhost:8080/api/v1/trigger-fetch?hour=$Hour"
$logFile = "C:\logs\btc_oro_$Hour.log"

# Crear directorio de logs si no existe
$logDir = Split-Path $logFile -Parent
if (!(Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force
}

# Registrar inicio
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $logFile -Value "[$timestamp] Iniciando obtención de precios para hora $Hour"

try {
    $response = Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 30
    Add-Content -Path $logFile -Value "[$timestamp] Respuesta: $($response | ConvertTo-Json -Compress)"
    
    if ($response.success) {
        Add-Content -Path $logFile -Value "[$timestamp] ✓ Éxito: $($response.message)"
    } else {
        Add-Content -Path $logFile -Value "[$timestamp] ✗ Error: $($response.message)"
    }
} catch {
    Add-Content -Path $logFile -Value "[$timestamp] ✗ Excepción: $($_.Exception.Message)"
}
```

### Crear las tareas programadas con PowerShell

Ejecuta estos comandos en PowerShell como Administrador:

```powershell
# Tarea para las 10:00
$action10 = New-ScheduledTaskAction -Execute "PowerShell.exe" `
    -Argument "-File C:\ruta\a\proyecto\btc_oro\trigger-fetch.ps1 -Hour 10"

$trigger10 = New-ScheduledTaskTrigger -Daily -At 10:00AM

$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName "BTC-Oro Fetch 10AM" `
    -Action $action10 `
    -Trigger $trigger10 `
    -Settings $settings `
    -Description "Obtiene precios de BTC y Oro a las 10:00 ART"

# Tarea para las 17:00
$action17 = New-ScheduledTaskAction -Execute "PowerShell.exe" `
    -Argument "-File C:\ruta\a\proyecto\btc_oro\trigger-fetch.ps1 -Hour 17"

$trigger17 = New-ScheduledTaskTrigger -Daily -At 5:00PM

Register-ScheduledTask -TaskName "BTC-Oro Fetch 5PM" `
    -Action $action17 `
    -Trigger $trigger17 `
    -Settings $settings `
    -Description "Obtiene precios de BTC y Oro a las 17:00 ART"
```

## OPCIÓN 2: Usar la interfaz gráfica de Task Scheduler

### Paso 1: Abrir el Programador de tareas
1. Presiona `Win + R`
2. Escribe `taskschd.msc`
3. Presiona Enter

### Paso 2: Crear una nueva tarea para las 10:00 AM
1. Clic en "Crear tarea básica" en el panel derecho
2. Nombre: `BTC-Oro Fetch 10AM`
3. Descripción: `Obtiene precios de BTC y Oro a las 10:00 ART`
4. Desencadenador: Diariamente
5. Hora: `10:00:00`
6. Acción: Iniciar un programa
7. Programa/script: `powershell.exe`
8. Agregar argumentos:
   ```
   -ExecutionPolicy Bypass -File "C:\ruta\a\proyecto\btc_oro\trigger-fetch.ps1" -Hour 10
   ```
9. Finalizar

### Paso 3: Crear una nueva tarea para las 5:00 PM
Repetir el Paso 2 pero con:
- Nombre: `BTC-Oro Fetch 5PM`
- Hora: `17:00:00`
- Argumentos: `-ExecutionPolicy Bypass -File "C:\ruta\a\proyecto\btc_oro\trigger-fetch.ps1" -Hour 17`

### Paso 4: Configuraciones adicionales (Recomendado)
Para cada tarea creada:
1. Clic derecho en la tarea → Propiedades
2. En la pestaña "General":
   - ☑ Ejecutar tanto si el usuario inició sesión como si no
   - ☑ Ejecutar con los privilegios más altos
3. En la pestaña "Condiciones":
   - ☐ Desmarcar "Iniciar la tarea solo si el equipo está conectado a la CA"
   - ☑ Marcar "Activar si el equipo está en batería"
4. En la pestaña "Configuración":
   - ☑ Permitir que la tarea se ejecute a petición
   - ☑ Si la tarea no se puede ejecutar, volver a intentarlo cada: 1 minuto
   - Detener la tarea si se ejecuta más de: 1 hora

## OPCIÓN 3: Usar curl directamente (Más simple)

### Script por lotes (batch) simple
Guarda como `trigger-fetch-10.bat`:

```batch
@echo off
curl -s http://localhost:8080/api/v1/trigger-fetch?hour=10 >> C:\logs\btc_oro_10.log
echo [%date% %time%] Ejecución completada >> C:\logs\btc_oro_10.log
```

Guarda como `trigger-fetch-17.bat`:

```batch
@echo off
curl -s http://localhost:8080/api/v1/trigger-fetch?hour=17 >> C:\logs\btc_oro_17.log
echo [%date% %time%] Ejecución completada >> C:\logs\btc_oro_17.log
```

Luego crea las tareas programadas apuntando a estos archivos .bat

## IMPORTANTE: Mantener el servidor ejecutándose

El servidor debe estar ejecutándose para que los cron jobs funcionen.

### Opción A: Ejecutar como servicio de Windows

Usa NSSM (Non-Sucking Service Manager):

1. Descarga NSSM: https://nssm.cc/download
2. Extrae y abre PowerShell como Administrador
3. Navega al directorio de NSSM
4. Ejecuta:
   ```powershell
   .\nssm.exe install BTCOroService "C:\ruta\a\python\python.exe" "C:\ruta\a\proyecto\btc_oro\main.py"
   .\nssm.exe start BTCOroService
   ```

### Opción B: Ejecutar al inicio de Windows

1. Crea un acceso directo a `main.py`
2. Presiona `Win + R` y escribe `shell:startup`
3. Copia el acceso directo a la carpeta que se abre

### Opción C: Usar Task Scheduler para iniciar el servidor

Crea una tarea con:
- Desencadenador: Al iniciar el sistema
- Acción: `python.exe C:\ruta\a\proyecto\btc_oro\main.py`
- Configuración: Ejecutar en segundo plano

## Verificar las tareas

```powershell
# Listar todas las tareas relacionadas con BTC-Oro
Get-ScheduledTask | Where-Object {$_.TaskName -like "*BTC-Oro*"}

# Ver el historial de ejecución
Get-ScheduledTask -TaskName "BTC-Oro Fetch 10AM" | Get-ScheduledTaskInfo

# Ejecutar manualmente una tarea
Start-ScheduledTask -TaskName "BTC-Oro Fetch 10AM"
```

## Solución de problemas

1. **El servidor no responde:**
   - Verifica que el servidor esté ejecutándose: `curl http://localhost:8080/health`
   - Revisa los logs del servidor

2. **La tarea no se ejecuta:**
   - Verifica que la ruta a PowerShell/Python sea correcta
   - Revisa el Historial de tareas en Task Scheduler
   - Ejecuta la tarea manualmente para ver errores

3. **Problemas de permisos:**
   - Ejecuta PowerShell como Administrador
   - Verifica los permisos del directorio de logs

4. **Zona horaria incorrecta:**
   - Verifica la configuración de zona horaria de Windows
   - Panel de Control → Reloj e idioma → Fecha y hora