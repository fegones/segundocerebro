$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

Write-Host "Notebook Conexion 1.3.0 - Preparando instalacion local" -ForegroundColor Cyan

# Busca Python compatible sin asumir qué intérprete aparece primero en PATH.
$selector = $null
$py = Get-Command py -ErrorAction SilentlyContinue
if ($py) {
    foreach ($flag in @('-3.13','-3.12','-3.11','-3')) {
        & $py.Source $flag -c "import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] <= (3,13) else 1)" 2>$null
        if ($LASTEXITCODE -eq 0) { $selector = @($py.Source, $flag); break }
    }
}
if (-not $selector) {
    foreach ($name in @('python','python3')) {
        $found = Get-Command $name -ErrorAction SilentlyContinue
        if (-not $found) { continue }
        & $found.Source -c "import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] <= (3,13) else 1)" 2>$null
        if ($LASTEXITCODE -eq 0) { $selector = @($found.Source); break }
    }
}
if (-not $selector) {
    Write-Host "No encontre Python 3.11-3.13. Instale Python desde https://www.python.org/downloads/windows/" -ForegroundColor Yellow
    Write-Host "Active la opcion 'Add python.exe to PATH' o instale el Python Launcher (py)."
    exit 2
}

$exe = $selector[0]
$arguments = @()
if ($selector.Count -gt 1) { $arguments = @($selector[1]) }
$venv = Join-Path $env:LOCALAPPDATA 'NotebookConexion\1.3.0\.venv'
if (-not (Test-Path (Join-Path $venv 'Scripts\python.exe'))) {
    Write-Host "Creando entorno aislado en AppData local (fuera de OneDrive)..."
    $parent = Split-Path -Parent $venv
    if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    & $exe @arguments -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw "No fue posible crear el entorno virtual (venv)." }
}
$localPython = Join-Path $venv 'Scripts\python.exe'
Write-Host "Instalando dependencias con ruedas binarias, sin compilar extensiones C..."
& $localPython -m pip install --disable-pip-version-check --prefer-binary --only-binary=:all: -e .
if ($LASTEXITCODE -ne 0) { throw "Fallo de dependencias. Compruebe Internet y Python, revise solucion de problemas." }

Write-Host "Comprobando arranque offline y protocolo MCP..."
& $localPython -m notebook_conexion.selftest
if ($LASTEXITCODE -ne 0) { throw "El diagnostico de Notebook Conexion ha fallado." }
Write-Host "INSTALACION FINALIZADA" -ForegroundColor Green
Write-Host "Abrire el panel para configurar una cuenta personal de Google."
Write-Host "No se recuperan credenciales o sesiones de instalaciones anteriores."
& $localPython -m notebook_conexion.desktop
if ($LASTEXITCODE -ne 0) { Write-Host "La interfaz no se abrio. Use ABRIR_WINDOWS.cmd para volver a intentar." -ForegroundColor Yellow }
