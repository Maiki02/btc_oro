# ============================================================================
# Script PowerShell: Crear paquete Lambda automáticamente
# ============================================================================
# Uso: .\deploy_lambda.ps1
# 
# Este script automatiza todo el proceso de preparación del paquete
# para AWS Lambda:
# 1. Crea la carpeta lambda_package
# 2. Copia el código fuente
# 3. Instala las dependencias
# 4. Crea el ZIP
# 5. Limpia y organiza
# ============================================================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "📦 Creador de Paquete Lambda" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Variables
$LAMBDA_PACKAGE_DIR = "lambda_package"
$ZIP_FILE = "lambda_deployment.zip"
$REQUIREMENTS_FILE = "requirements.txt"

# Colores para mensajes
$SUCCESS = "Green"
$WARNING = "Yellow"
$ERROR = "Red"
$INFO = "Cyan"

# Función para mostrar mensajes
function Write-Status {
    param(
        [string]$Message,
        [string]$Status = "INFO"
    )
    
    $color = $INFO
    if ($Status -eq "SUCCESS") { $color = $SUCCESS }
    elseif ($Status -eq "WARNING") { $color = $WARNING }
    elseif ($Status -eq "ERROR") { $color = $ERROR }
    
    Write-Host "[$Status] $Message" -ForegroundColor $color
}

# Verificar que estamos en la carpeta correcta
if (-not (Test-Path $REQUIREMENTS_FILE)) {
    Write-Status "❌ requirements.txt no encontrado. Asegúrate de estar en la carpeta del proyecto" $ERROR
    exit 1
}

Write-Status "✓ Ubicación correcta" $SUCCESS
Write-Host ""

# Paso 1: Limpiar paquete anterior
Write-Status "Paso 1: Preparando carpeta..." "INFO"
if (Test-Path $LAMBDA_PACKAGE_DIR) {
    Write-Status "Eliminando paquete anterior..." $WARNING
    Remove-Item -Recurse -Force $LAMBDA_PACKAGE_DIR
}
if (Test-Path $ZIP_FILE) {
    Write-Status "Eliminando ZIP anterior..." $WARNING
    Remove-Item -Force $ZIP_FILE
}
Write-Status "✓ Carpeta preparada" $SUCCESS
Write-Host ""

# Paso 2: Crear carpeta
Write-Status "Paso 2: Creando carpeta lambda_package..." "INFO"
mkdir $LAMBDA_PACKAGE_DIR | Out-Null
Write-Status "✓ Carpeta creada" $SUCCESS
Write-Host ""

# Paso 3: Cambiar a la carpeta
Write-Status "Paso 3: Entrando a la carpeta..." "INFO"
Push-Location $LAMBDA_PACKAGE_DIR
Write-Status "✓ En carpeta: $(Get-Location)" $SUCCESS
Write-Host ""

# Paso 4: Copiar código fuente
Write-Status "Paso 4: Copiando código fuente..." "INFO"
try {
    Copy-Item -Path "..\src" -Destination ".\src" -Recurse -ErrorAction Stop
    Copy-Item -Path "..\lambda_handler.py" -Destination ".\lambda_handler.py" -ErrorAction Stop
    Write-Status "✓ Código fuente copiado" $SUCCESS
} catch {
    Write-Status "❌ Error al copiar: $_" $ERROR
    Pop-Location
    exit 1
}
Write-Host ""

# Paso 5: Instalar dependencias
Write-Status "Paso 5: Instalando dependencias (esto puede tardar 1-2 minutos)..." "INFO"
try {
    pip install -r ..\requirements.txt -t . --quiet --disable-pip-version-check
    Write-Status "✓ Dependencias instaladas" $SUCCESS
} catch {
    Write-Status "❌ Error al instalar dependencias: $_" $ERROR
    Pop-Location
    exit 1
}
Write-Host ""

# Paso 6: Verificar instalación
Write-Status "Paso 6: Verificando instalación..." "INFO"
$packages = @("requests", "pymongo", "pydantic", "pytz", "python_dotenv")
$missing = @()

foreach ($pkg in $packages) {
    if (Test-Path $pkg) {
        Write-Host "  ✓ $pkg" -ForegroundColor Green
    } else {
        $missing += $pkg
        Write-Host "  ❌ $pkg (FALTANTE)" -ForegroundColor Red
    }
}

if ($missing.Count -gt 0) {
    Write-Status "⚠️  Algunas dependencias pueden no estar instaladas" $WARNING
} else {
    Write-Status "✓ Todas las dependencias verificadas" $SUCCESS
}
Write-Host ""

# Paso 7: Crear ZIP
Write-Status "Paso 7: Creando archivo ZIP..." "INFO"
try {
    Compress-Archive -Path * -DestinationPath $ZIP_FILE -ErrorAction Stop
    Write-Status "✓ ZIP creado exitosamente" $SUCCESS
} catch {
    Write-Status "❌ Error al crear ZIP: $_" $ERROR
    Pop-Location
    exit 1
}
Write-Host ""

# Paso 8: Mover ZIP a la carpeta principal
Write-Status "Paso 8: Moviendo ZIP a la carpeta principal..." "INFO"
try {
    Move-Item -Path $ZIP_FILE -Destination "..\$ZIP_FILE" -Force -ErrorAction Stop
    Write-Status "✓ ZIP movido" $SUCCESS
} catch {
    Write-Status "❌ Error al mover ZIP: $_" $ERROR
    Pop-Location
    exit 1
}
Write-Host ""

# Paso 9: Volver a la carpeta principal
Pop-Location
Write-Status "✓ Volviendo a la carpeta principal" $SUCCESS
Write-Host ""

# Paso 10: Mostrar información
Write-Status "Paso 10: Información final" "INFO"
$zip_size = (Get-Item $ZIP_FILE).Length / 1MB
Write-Host "  📁 Archivo ZIP: $ZIP_FILE" -ForegroundColor Cyan
Write-Host "  📊 Tamaño: $([Math]::Round($zip_size, 2)) MB" -ForegroundColor Cyan
Write-Host "  📍 Ubicación: $(Get-Location)\$ZIP_FILE" -ForegroundColor Cyan
Write-Host ""

Write-Host "========================================" -ForegroundColor Green
Write-Host "✅ ¡Paquete Lambda creado exitosamente!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

Write-Host "Próximos pasos:" -ForegroundColor Cyan
Write-Host "1. Abre AWS Console: https://console.aws.amazon.com" -ForegroundColor White
Write-Host "2. Ve a Lambda → Funciones → Crear función" -ForegroundColor White
Write-Host "3. Nombre: btc-oro-fetcher" -ForegroundColor White
Write-Host "4. Runtime: Python 3.11" -ForegroundColor White
Write-Host "5. Cargar el archivo: $ZIP_FILE" -ForegroundColor White
Write-Host "6. Handler: lambda_handler.lambda_handler" -ForegroundColor White
Write-Host ""

Write-Host "Para más información, lee:" -ForegroundColor Cyan
Write-Host "- Docs\AWS_LAMBDA_DEPLOYMENT.md" -ForegroundColor White
Write-Host "- Docs\INSTALAR_DEPENDENCIAS.md" -ForegroundColor White
Write-Host ""

# Opción de limpiar carpeta temporal
Write-Host "¿Deseas eliminar la carpeta temporal 'lambda_package'? (S/N)" -ForegroundColor Yellow
$cleanup = Read-Host
if ($cleanup -eq "S" -or $cleanup -eq "s") {
    Remove-Item -Recurse -Force $LAMBDA_PACKAGE_DIR
    Write-Status "✓ Carpeta temporal eliminada" $SUCCESS
} else {
    Write-Status "⚠️  Carpeta temporal conservada en: .\$LAMBDA_PACKAGE_DIR" $WARNING
}

Write-Host ""
Write-Host "¡Listo! 🚀" -ForegroundColor Green
