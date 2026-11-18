"""Revisa una carpeta fuente sin conectarse a Internet ni ejecutar dependencias."""
from __future__ import annotations
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORED = {'.venv', 'venv', '__pycache__', '.git', '.pytest_cache', '.ruff_cache', 'dist', 'build'}
IGNORED_SUFFIX = {'.pyc', '.pyo'}
SECRETS = {'master_token.json', 'storage_state.json', '.env', 'token.json', 'credentials.json'}


def release_files() -> list[Path]:
    result = []
    for p in ROOT.rglob('*'):
        if not p.is_file() or any(x in IGNORED for x in p.relative_to(ROOT).parts) or p.suffix in IGNORED_SUFFIX:
            continue
        if p.name == 'SHA256SUMS.txt' or '.egg-info' in str(p):
            continue
        result.append(p)
    return sorted(result)


def main() -> int:
    required = ['LICENSE','README.md','pyproject.toml','INSTALAR_WINDOWS.cmd',
                'ABRIR_WINDOWS.cmd','CONECTAR_AGENTES_WINDOWS.cmd',
                'src/notebook_conexion/mcp_server.py','src/notebook_conexion/skill/SKILL.md']
    for name in required:
        if not (ROOT / name).is_file():
            raise RuntimeError('Falta archivo obligatorio: ' + name)
    paths = release_files()
    for p in paths:
        name = p.name.lower()
        if name in SECRETS or (name.startswith('client_secret') and name.endswith('.json')):
            raise RuntimeError('Posible archivo de credenciales: ' + str(p.relative_to(ROOT)))
        if p.stat().st_size > 2_000_000:
            raise RuntimeError('Archivo inesperadamente grande: ' + str(p.relative_to(ROOT)))
    manifest = []
    for p in paths:
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        manifest.append(f'{digest}  {p.relative_to(ROOT).as_posix()}')
    (ROOT / 'SHA256SUMS.txt').write_text('\n'.join(manifest) + '\n', encoding='utf-8')
    print(f'OK: {len(paths)} archivos sin material de credenciales conocido, hashes SHA256 listos.')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
