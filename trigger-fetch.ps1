# trigger-fetch.ps1
# Script de PowerShell para llamar al endpoint de obtención de precios
# Uso: .\trigger-fetch.ps1 -Hour 10

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet(10, 17)]
    [int]$Hour
)

# Configuración
$baseUrl = "http://localhost:8080"
$endpoint = "/api/v1/trigger-fetch"
$url = "$baseUrl$endpoint?hour=$Hour"
$logDir = "C:\logs\btc_oro"
$logFile = Join-Path $logDir "fetch_$Hour.log"

# Crear directorio de logs si no existe
if (!(Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    Write-Host "Directorio de logs creado: $logDir" -ForegroundColor Green
}

# Función para escribir en el log con timestamp
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    
    # Escribir en archivo
    Add-Content -Path $logFile -Value $logMessage
    
    # Escribir en consola con colores
    switch ($Level) {
        "SUCCESS" { Write-Host $logMessage -ForegroundColor Green }
        "ERROR"   { Write-Host $logMessage -ForegroundColor Red }
        "WARNING" { Write-Host $logMessage -ForegroundColor Yellow }
        default   { Write-Host $logMessage -ForegroundColor White }
    }
}

# Inicio del proceso
Write-Log "========================================" "INFO"
Write-Log "Iniciando obtención de precios para hora $Hour ART" "INFO"
Write-Log "URL: $url" "INFO"

try {
    # Verificar conectividad básica
    Write-Log "Verificando conectividad con el servidor..." "INFO"
    
    try {
        $healthCheck = Invoke-RestMethod -Uri "$baseUrl/health" -Method Get -TimeoutSec 5
        Write-Log "Servidor respondiendo correctamente" "SUCCESS"
    } catch {
        Write-Log "Advertencia: No se pudo verificar el health check" "WARNING"
        Write-Log "Error: $($_.Exception.Message)" "WARNING"
    }
    
    # Realizar la petición principal
    Write-Log "Realizando petición de obtención de precios..." "INFO"
    
    $response = Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 60
    
    # Procesar respuesta
    if ($response.success) {
        Write-Log "✓ Éxito: $($response.message)" "SUCCESS"
        Write-Log "Registros procesados: $($response.records_processed)" "SUCCESS"
        
        if ($response.errors -and $response.errors.Count -gt 0) {
            Write-Log "Advertencias encontradas:" "WARNING"
            foreach ($error in $response.errors) {
                Write-Log "  - $error" "WARNING"
            }
        }
    } else {
        Write-Log "✗ Fallo en la operación: $($response.message)" "ERROR"
        Write-Log "Registros procesados: $($response.records_processed)" "ERROR"
        
        if ($response.errors -and $response.errors.Count -gt 0) {
            Write-Log "Errores encontrados:" "ERROR"
            foreach ($error in $response.errors) {
                Write-Log "  - $error" "ERROR"
            }
        }
        
        exit 1
    }
    
    # Información adicional
    Write-Log "Timestamp de respuesta: $($response.timestamp)" "INFO"
    
} catch {
    Write-Log "✗ Excepción durante la ejecución: $($_.Exception.Message)" "ERROR"
    
    if ($_.Exception.Response) {
        $statusCode = $_.Exception.Response.StatusCode.value__
        Write-Log "Código de estado HTTP: $statusCode" "ERROR"
    }
    
    Write-Log "Stack trace: $($_.Exception.StackTrace)" "ERROR"
    exit 1
}

Write-Log "Proceso finalizado" "INFO"
Write-Log "========================================" "INFO"
Write-Host ""

exit 0