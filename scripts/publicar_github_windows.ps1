$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$repo = 'fegones/segundocerebro'
$url = 'https://github.com/fegones/segundocerebro.git'
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

function Run([string]$program, [string[]]$arguments) {
    & $program @arguments
    if ($LASTEXITCODE -ne 0) { throw "Error en $program (codigo: $LASTEXITCODE)." }
}

foreach ($tool in @('git', 'gh', 'python')) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        throw "Falta '$tool'. Consulte docs/PUBLICACION_GITHUB.md para instalarlo de una fuente oficial."
    }
}

Write-Host 'Revisando el paquete antes de publicar...' -ForegroundColor Cyan
Run 'python' @('scripts/check_release.py')

Write-Host 'Verificando autenticacion GitHub...' -ForegroundColor Cyan
Run 'gh' @('auth', 'status')
$account = (& gh api user --jq '.login').Trim()
if ($LASTEXITCODE -ne 0 -or $account -ne 'fegones') {
    throw "GitHub CLI debe estar autenticado como fegones. Cuenta detectada: $account"
}

$answer = Read-Host 'Este codigo sera PUBLICO en GitHub. Escriba PUBLICAR para confirmar'
if ($answer -cne 'PUBLICAR') { throw 'Publicacion cancelada por el propietario.' }

if (-not (Test-Path '.git')) {
    Run 'git' @('init', '-b', 'main')
}
$remoteNames = @(& git remote)
$existingRemote = ''
if ($remoteNames -contains 'origin') {
    $existingRemote = (& git remote get-url origin).Trim()
    if ($LASTEXITCODE -ne 0) { throw 'No fue posible verificar el remoto origin.' }
}
if ($existingRemote -and $existingRemote -notin @($url, 'git@github.com:fegones/segundocerebro.git')) {
    throw 'Existe un remoto origin diferente. No se alteran remotos ni se fuerza el envio.'
}

$allowed = @(
    '.editorconfig', '.gitattributes', '.gitignore', '.github',
    'LICENSE', 'README.md', 'SECURITY.md', 'AGENTS.md', 'CHANGELOG.md', 'CONTRIBUTING.md',
    'RELEASE_VALIDATION.txt', 'SHA256SUMS.txt',
    'ABRIR_WINDOWS.cmd', 'CONECTAR_AGENTES_WINDOWS.cmd', 'DIAGNOSTICO_WINDOWS.cmd',
    'INSTALAR_WINDOWS.cmd', 'PUBLICAR_GITHUB_WINDOWS.cmd',
    'instalar_linux_mac.sh', 'pyproject.toml',
    'docs', 'scripts', 'skills', 'src', 'tests'
)
Run 'git' (@('add', '--') + $allowed)
$staged = @(& git diff --cached --name-only)
if ($LASTEXITCODE -ne 0) { throw 'No fue posible revisar la lista de archivos preparada.' }
if (-not $staged) { Write-Host 'No hay archivos nuevos por confirmar.' }
else {
    Write-Host ('Archivos preparados: ' + $staged.Count)
    $staged | ForEach-Object { Write-Host ('  ' + $_) }
    $confirm = Read-Host 'Escriba CONFIRMAR para crear el commit con estos archivos'
    if ($confirm -cne 'CONFIRMAR') { throw 'No se ha creado ningun commit.' }
    $identity = & git var GIT_AUTHOR_IDENT 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $identity) {
        throw 'Configure primero el nombre y correo del autor Git con git config user.name / user.email.'
    }
    Run 'git' @('commit', '-m', 'Publicar Segundo Cerebro v1.3.0 bajo licencia MIT')
}
Run 'git' @('branch', '-M', 'main')

$repoExists = $false
try {
    $visibilityProbe = & gh repo view $repo --json visibility --jq '.visibility' 2>$null
    $repoExists = ($LASTEXITCODE -eq 0)
} catch { $repoExists = $false }
if (-not $repoExists) {
    Write-Host 'Creando repositorio publico desde GitHub CLI...' -ForegroundColor Cyan
    # GitHub CLI utiliza la autenticacion local del propietario. No incorpora tokens al script.
    Run 'gh' @('repo', 'create', $repo, '--public', '--description',
        'Segundo Cerebro: Gemini Notebook multicuentas, MCP, auditoria de fuentes y evidencia documental',
        '--source', '.', '--remote', 'origin', '--push')
} else {
    $visibility = (& gh repo view $repo --json visibility --jq '.visibility').Trim()
    if ($visibility -ne 'PUBLIC') {
        throw 'El repositorio ya existe pero no es PUBLICO. No se cambia su visibilidad automaticamente.'
    }
    if (-not $existingRemote) { Run 'git' @('remote', 'add', 'origin', $url) }
    Write-Host 'Repositorio publico existente; enviando solo cambios mediante fast-forward...' -ForegroundColor Cyan
    Run 'git' @('push', '-u', 'origin', 'main')
}
Write-Host 'Publicacion finalizada: https://github.com/fegones/segundocerebro' -ForegroundColor Green
