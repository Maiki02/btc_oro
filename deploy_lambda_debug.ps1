# ============================================================================
# Script PowerShell: Crear paquete Lambda (CON MENSAJES DE ERROR)
# ============================================================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Creador de Paquete Lambda - DEBUG" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Variables
$LAMBDA_PACKAGE_DIR = "lambda_package"
$ZIP_FILE = "lambda_deployment.zip"

# Paso 1: Limpiar
Write-Host "Paso 1: Preparando carpeta..." -ForegroundColor Cyan
if (Test-Path $LAMBDA_PACKAGE_DIR) {
    Remove-Item -Recurse -Force $LAMBDA_PACKAGE_DIR
}
if (Test-Path $ZIP_FILE) {
    Remove-Item -Force $ZIP_FILE
}
Write-Host "OK" -ForegroundColor Green
Write-Host ""

# Paso 2: Crear carpeta
Write-Host "Paso 2: Creando carpeta..." -ForegroundColor Cyan
mkdir $LAMBDA_PACKAGE_DIR | Out-Null
Write-Host "OK" -ForegroundColor Green
Write-Host ""

# Paso 3: Cambiar directorio y copiar codigo
Write-Host "Paso 3: Copiando codigo fuente..." -ForegroundColor Cyan
cd $LAMBDA_PACKAGE_DIR
Copy-Item -Path "..\src" -Destination ".\src" -Recurse
Copy-Item -Path "..\lambda_handler.py" -Destination ".\lambda_handler.py"
Write-Host "OK" -ForegroundColor Green
Write-Host ""

# Paso 4: Instalar dependencias CON SALIDA VISIBLE
Write-Host "Paso 4: Instalando dependencias..." -ForegroundColor Cyan

# Determinar comando Python disponible (python o py)
$pythonCmd = 'python'
if (-not (Get-Command $pythonCmd -ErrorAction SilentlyContinue)) {
    $pythonCmd = 'py'
}

if (-not (Get-Command $pythonCmd -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: No se encontró 'python' ni 'py' en PATH. Instale Python (https://www.python.org/) o use un entorno con Python disponible." -ForegroundColor Red
    cd ..
    exit 1
}

# Ejecutar pip via módulo para evitar depender del ejecutable 'pip'
$installCmd = "$pythonCmd -m pip install -r ..\requirements.txt -t . --platform manylinux2014_x86_64 --python-version 3.11 --only-binary :all:"
Write-Host "Ejecutando: $installCmd" -ForegroundColor Yellow

& $pythonCmd -m pip install -r ..\requirements.txt -t . --platform manylinux2014_x86_64 --python-version 3.11 --only-binary :all:
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR al instalar dependencias" -ForegroundColor Red
    Write-Host "Exit code: $LASTEXITCODE" -ForegroundColor Red
    cd ..
    exit 1
}
Write-Host "OK" -ForegroundColor Green
Write-Host ""

# Verificar que las dependencias estan
Write-Host "Paso 5: Verificando dependencias..." -ForegroundColor Cyan
$packages = @("dotenv", "requests", "pymongo", "pydantic", "pytz")
foreach ($pkg in $packages) {
    if (Test-Path $pkg) {
        Write-Host "  OK: $pkg" -ForegroundColor Green
    } else {
        Write-Host "  FALTA: $pkg" -ForegroundColor Red
    }
}
Write-Host ""

# Paso 6: Listar lo que hay en la carpeta
Write-Host "Contenido de lambda_package:" -ForegroundColor Cyan
ls -Name | ForEach-Object { Write-Host "  $_" }
Write-Host ""

# Paso 7: Crear ZIP
Write-Host "Paso 6: Creando ZIP..." -ForegroundColor Cyan
Compress-Archive -Path * -DestinationPath $ZIP_FILE
Write-Host "OK" -ForegroundColor Green
Write-Host ""

# Paso 8: Mover ZIP
Write-Host "Paso 7: Moviendo ZIP..." -ForegroundColor Cyan
Move-Item -Path $ZIP_FILE -Destination "..\$ZIP_FILE" -Force
Write-Host "OK" -ForegroundColor Green
Write-Host ""

# Paso 9: Volver
cd ..

Write-Host "========================================" -ForegroundColor Green
Write-Host "LISTO! Paquete creado" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
$zip_size = (Get-Item $ZIP_FILE).Length / 1MB
Write-Host "Tamano: $([Math]::Round($zip_size, 2)) MB" -ForegroundColor Cyan
