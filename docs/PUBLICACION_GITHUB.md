# Publicación de Segundo Cerebro en GitHub

## Objetivo

Publicar el **código fuente** en `https://github.com/fegones/segundocerebro`, con visibilidad **Public**, README detallado, licencia MIT y sin ningún archivo privado de usuario.

## Preparación

1. Extraiga el ZIP del proyecto en una carpeta **nueva**. **No** copie el directorio `.git` de otro repositorio ni reutilice cookies/tokens o archivos de otras instalaciones.
2. Verifique que aparecen en la raíz `README.md`, `LICENSE`, `.gitignore`, `src/`, `tests/` y `docs/`.
3. Compruebe que no existen archivos `client_secret*.json`, `.env`, tokens, bases de datos personales ni exportaciones en la carpeta.
4. Si utiliza el script automatizado, instale **Git**, **GitHub CLI (`gh`)** y **Python 3.11–3.13**. En `gh auth login` autentíquese como `fegones` (no escriba el token en el script).

## Método 1: asistente Windows

Haga doble clic en `PUBLICAR_GITHUB_WINDOWS.cmd` y siga sus confirmaciones. El script:

- Ejecuta una comprobación de distribución y manifiesto SHA-256.
- Comprueba la identidad activa de GitHub CLI (`fegones`).
- Pide confirmación de que el proyecto se hará público.
- Crea un repositorio Git **nuevo** si no existe uno local.
- Prepara **solo** archivos explícitamente permitidos, nunca `git add .` indiscriminadamente.
- Muestra qué archivos se confirmarán y requiere una segunda confirmación.
- Crea `fegones/segundocerebro` como repositorio público si no existe, o publica en el repositorio existente cuando ya es público.
- No usa `--force`, no cambia la visibilidad de un repositorio existente y rechaza un remoto `origin` diferente.

**Importante:** la carpeta debe permanecer en una ruta estable; Git no comparte sus credenciales con Notebook Conexión. El script utiliza la sesión GitHub CLI del propietario.

## Método 2: GitHub desde navegador y Git

En la pantalla **Create a new repository**:

| Campo | Selección |
|---|---|
| Owner | `fegones` |
| Repository name | `segundocerebro` |
| Description | `Segundo Cerebro: Gemini Notebook multicuentas, MCP, auditoría de fuentes y evidencia documental` |
| Visibility | **Public** |
| Add README | **Off** |
| Add .gitignore | **No .gitignore** |
| Add license | **No license** (ya está el archivo MIT del proyecto) |

Pulse **Create repository**. A continuación, en PowerShell, **desde la carpeta extraída**:

```powershell
git init -b main
git add .editorconfig .gitattributes .gitignore .github LICENSE README.md SECURITY.md AGENTS.md CHANGELOG.md CONTRIBUTING.md RELEASE_VALIDATION.txt SHA256SUMS.txt ABRIR_WINDOWS.cmd CONECTAR_AGENTES_WINDOWS.cmd DIAGNOSTICO_WINDOWS.cmd INSTALAR_WINDOWS.cmd PUBLICAR_GITHUB_WINDOWS.cmd instalar_linux_mac.sh pyproject.toml docs scripts skills src tests
git status --short
git commit -m "Publicar Segundo Cerebro v1.3.0 bajo licencia MIT"
git remote add origin https://github.com/fegones/segundocerebro.git
git push -u origin main
```

Antes del `commit`, inspeccione `git status --short`: **ningún archivo privado** debe estar preparado. Si el repositorio remoto ya contiene un commit de GitHub, el envío podría rechazarse; no utilice `--force` para resolverlo.

## Método 3: GitHub Desktop

1. Instale y autentique GitHub Desktop en la cuenta `fegones`.
2. Seleccione **File → Add local repository**. Si la carpeta no contiene un repositorio Git, elija **Create a repository here**, sin importar historial externo.
3. Revise **Changes** antes del primer commit. Confirme que solo se incluyan los archivos del producto.
4. Cree el commit y seleccione **Publish repository** con **Keep this code private desmarcado** y nombre `segundocerebro`. Si el repositorio web ya existe, configure el remoto en lugar de crear otro.

## Comprobación después de publicar

Verifique en la web: `README.md` visible en la portada, `LICENSE` identificado como MIT, carpetas `src/`, `tests/` y `docs/`, y `Settings → General → Danger Zone` o cabecera indicando visibilidad pública. Confirme que el historial Git inicia con su commit, sin historial importado. Ejecute `git ls-files` y revise que no existan tokens, claves, bases de datos ni datos personales. Active Dependabot y, de ser posible, GitHub Secret Scanning.

La atribución del código propio al titular declarado y su distribución MIT se documenta en `LICENSE` y `docs/PROCEDENCIA.md`. **No corresponde afirmar que una licencia propia elimina derechos de terceros sobre componentes ajenos.**
