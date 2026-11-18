# Segundo Cerebro — Notebook Conexión

**Versión 1.3.0** · **Python 3.11–3.13** · **Código abierto (MIT)**  
**Autor y titular indicado para esta implementación:** Felipe Carlos González Espinoza · © 2026

Segundo Cerebro es un cliente local para organizar y consultar información procedente de **Gemini Notebook (NotebookLM)** desde herramientas de desarrollo asistidas por IA. Permite conectar **varias cuentas Google**, seleccionar uno o varios cuadernos como conjunto documental autorizado, revisar fuentes duplicadas, comparar versiones y ofrecer a **Claude Code** y **Codex** herramientas mediante **Model Context Protocol (MCP)**. La aplicación también admite archivos incorporados localmente, para construir un índice cifrado y obtener respuestas con evidencia rastreable.

> [!IMPORTANT]
> **No es una implementación del chat privado de NotebookLM.** La API oficial de Gemini Notebook utilizada por este proyecto permite operaciones sobre cuadernos y fuentes, pero no ofrece la totalidad de conversaciones, notas y artefactos generados desde la interfaz de NotebookLM. Solo es posible consultar texto efectivamente recuperado por la API o importado localmente. La existencia de una fuente en el catálogo **no significa** que su texto esté disponible.

> [!WARNING]
> **Proyecto en fase de validación (v1.3.0).** Se han ejecutado pruebas automatizadas offline, pero no se han realizado pruebas integrales sobre todas las versiones de Windows, cuentas Google y clientes MCP, ni una auditoría independiente de seguridad. No debe presentarse como una solución con cero alucinaciones o aislamiento total del sistema anfitrión.

## ¿Para qué sirve?

- **Segundo cerebro con fuentes delimitadas:** se seleccionan los cuadernos de referencia y el agente consulta únicamente el contenido indexado de esa selección a través de este MCP.
- **Multicuenta:** perfiles de OAuth independientes para cuentas Google personales distintas, sin almacenar sesiones del proveedor dentro del repositorio.
- **Auditoría de fuentes:** busca duplicados exactos de texto (SHA-256), coincidencias de URL o título y similitudes textuales aproximadas. Compara potenciales duplicados de cuadernos y documentos entre cuentas.
- **Versionado:** compara versiones de una misma fuente cuando su texto ha sido indexado varias veces bajo el mismo identificador.
- **Evidencia antes que respuesta:** en modo extractivo devuelve fragmentos y referencias. Si falta evidencia suficiente, se abstiene.
- **IA generativa opcional:** puede sintetizar fragmentos mediante una **Gemini API independiente**, con permisos temporales y validación de referencias literales. No utiliza por esta vía el motor conversacional interno de NotebookLM.
- **Exportación controlada:** inventarios y auditorías en formatos como JSON, CSV, Markdown y DOCX; los formatos dependen de la operación y se guardan en una carpeta local específica.
- **Uso por lenguaje natural:** Claude Code y Codex invocan herramientas MCP sin que el usuario deba recordar comandos de terminal.

### Qué está implementado y qué no

| Capacidad | Situación en v1.3.0 |
| --- | --- |
| Varios perfiles Google | Implementado; cada cuenta requiere su OAuth y autorización |
| Selección de 1, 2 o más cuadernos de cuentas diferentes | Implementada por panel/CLI local |
| Listado de cuadernos y fuentes | Implementado con la API oficial, sujeto a permisos y disponibilidad |
| Indexación de archivos TXT, MD, CSV, JSON, HTML, DOCX y PDF con texto | Implementada; **sin OCR para PDFs escaneados** |
| Importación de chats, notas y artefactos exportados por el usuario | Implementada como **archivos locales**, sin sincronización automática |
| Duplicados exactos por texto y coincidencias probables | Implementados sobre la información disponible |
| Comparación de fuentes de distintas cuentas | Implementada cuando ambas fuentes están indexadas y autorizadas |
| Comparación de versiones | Implementada para versiones indexadas |
| Respuestas extractivas con referencias y abstención | Implementadas; búsqueda léxica, no comprensión exhaustiva |
| Síntesis con Gemini API | Opcional; usa credencial propia y envía texto seleccionado al proveedor |
| Chat interno de NotebookLM, podcasts, vídeo o historial completo | **No implementados por esta integración** |
| Restricción de otras herramientas que tenga Claude/Codex (terminal, web, otros MCP) | **Fuera del alcance de este proyecto** |

## Arquitectura resumida

```text
Claude Code / Codex
       │ lenguaje natural
       ▼
Servidor MCP local (stdio; no abre un puerto público)
       │ validación de solicitudes y alcance de cuadernos
       ├── API oficial Gemini Notebook ── OAuth por cuenta Google
       ├── Selección permitida ────────── perfil + cuaderno
       ├── Índice cifrado local ───────── textos/fragmentos/versiones
       ├── Auditoría documental ───────── hashes, URL, similitud, diferencias
       ├── Respuesta extractiva ──────── citas y abstención
       └── Gemini API opcional ───────── síntesis basada en fragmentos
```

El índice utiliza SQLite con **cifrado AES-256-GCM del contenido**, y un secreto de cifrado obtenido del almacén seguro del sistema operativo. Algunos **metadatos** (IDs, nombres, URLs) permanecen sin cifrar en SQLite. La protección de disco y de la sesión del sistema operativo sigue siendo responsabilidad del usuario.

## Instalación rápida en Windows

**Requisitos:** Windows 10/11, Python **3.11–3.13** con `py` o `python` disponible, Internet y una cuenta Google que tenga acceso a Gemini Notebook API. Para agentes, debe instalar **Claude Code o Codex** por separado. No requiere `fastmcp`, `pyyaml` ni compilar dependencias C++.

1. Descargue el código desde **Code → Download ZIP** o clone el repositorio.
2. Extraiga los archivos a una carpeta propia, por ejemplo `Documentos\segundocerebro`.
3. Haga doble clic en **`INSTALAR_WINDOWS.cmd`**. Se crea un entorno Python separado en `%LOCALAPPDATA%\NotebookConexion\1.3.0\.venv`, fuera de carpetas sincronizadas con OneDrive.
4. En la interfaz, cree un perfil, seleccione su proyecto Google Cloud y el **JSON de un cliente OAuth de tipo Escritorio**; luego autorice la cuenta desde el navegador. **El JSON y los tokens se quedan en su equipo; no los suba a GitHub.**
5. Para otra cuenta, cree **otro perfil** y repita su autorización OAuth.
6. Entre a **Abrir Segundo Cerebro → Cargar cuentas**, seleccione los cuadernos y pulse **Guardar selección estricta**. Después use **Sincronizar metadatos / Indexar texto**, o importe los documentos locales.
7. Ejecute **`CONECTAR_AGENTES_WINDOWS.cmd`** para registrar las herramientas MCP y la Skill con Claude Code y/o Codex. Reinicie su agente.
8. Compruebe con una pregunta en lenguaje natural y, si hay problemas, abra **`DIAGNOSTICO_WINDOWS.cmd`**.

> **Configuración de Google Cloud:** habilite `notebook.googleapis.com`, configure el consentimiento OAuth y cree un cliente para **aplicación de escritorio**. El acceso depende de las cuotas y restricciones de Google y puede variar por tipo de cuenta. Instrucciones y problemas comunes: [`docs/SOLUCION_PROBLEMAS.md`](docs/SOLUCION_PROBLEMAS.md).

### Uso en Linux y macOS

Existe `instalar_linux_mac.sh` para instalar la base de la aplicación. El panel de escritorio, el proveedor de secretos y la integración concreta con los agentes deben verificarse en cada plataforma. No se afirma una paridad de instalación con Windows sin pruebas adicionales.

## Ejemplos en lenguaje natural

Una vez configurada la Skill y conectado el MCP, puede solicitar:

> Utiliza Segundo Cerebro. Muestra qué cuadernos he autorizado y qué fuentes contienen.

> Compara los cuadernos sobre musáceas de mis cuentas Google. Identifica fuentes exactas y probablemente repetidas; conserva cada fuente y presenta la evidencia de la comparación.

> Trabaja exclusivamente con los cuadernos seleccionados sobre pulpas congeladas. Encuentra evidencia sobre viscosidad y condiciones de procesamiento. Cita los fragmentos literales; si no existe evidencia suficiente, indícalo y no inventes cifras.

> Compara dos versiones indexadas del procedimiento de majado de verde, destaca diferencias y prepara una auditoría exportable. No alteres ninguna fuente en Google.

**Importante:** los agentes pueden invocar este MCP en lenguaje natural; la Skill no es un mecanismo de autorización. Para que una restricción sea efectiva fuera de este conector es necesario limitar también las demás herramientas del agente.

## Modo de evidencia estricta

El propietario selecciona localmente un conjunto de pares **(perfil Google, cuaderno)**. Durante esa selección, el servidor MCP restringe sus propias herramientas al alcance autorizado y bloquea el acceso a herramientas administrativas clásicas que pudieran evadirlo.

1. Solo considera fuentes **indexadas** de los cuadernos seleccionados.
2. La búsqueda local recupera fragmentos textuales con identificadores y hashes.
3. Por defecto devuelve evidencia extractiva, no una respuesta generada libremente.
4. Sin evidencia pertinente responde: **«No se encontró evidencia suficiente en las fuentes autorizadas»**.
5. La síntesis con Gemini API es opcional y conlleva enviar los fragmentos elegidos al proveedor conforme a sus condiciones de uso.

**Límite de seguridad:** el MCP no puede controlar por sí mismo el acceso que Claude Code, Codex u otro agente tenga a una terminal, navegador, directorios locales o conectores adicionales. Tampoco garantiza ausencia absoluta de errores semánticos: la verificación actual de citas es principalmente textual. Consulte [`docs/SEGUNDO_CEREBRO.md`](docs/SEGUNDO_CEREBRO.md).

## Datos, seguridad y privacidad

- **Sin cuentas preconfiguradas:** el repositorio público no incluye cookies, tokens, credenciales OAuth, claves Gemini, historial personal ni cuadernos de ejemplo procedentes de usuarios reales.
- **OAuth individual y keyring:** cada usuario autoriza sus propias cuentas; no comparta `client_secret.json`, tokens ni secretos.
- **Almacenamiento cifrado:** el contenido indexado se cifra localmente; los metadatos, rutas y archivos exportados requieren protección adicional.
- **Sin servidor remoto propio:** la implementación MCP usa `stdio` local. Las llamadas a las APIs oficiales de Google se realizan a sus servidores.
- **Escritura controlada:** las herramientas con efectos sobre cuadernos o envíos a Gemini requieren habilitaciones expresas. La restricción de cuadernos seleccionados bloquea las herramientas MCP antiguas.
- **Fuentes no confiables:** el contenido documental es información, no instrucciones para ejecutar acciones; aun así, existen riesgos residuales de *prompt injection*.
- **No se garantiza confidencialidad absoluta ni ausencia de vulnerabilidades.** Revise [`docs/SEGURIDAD.md`](docs/SEGURIDAD.md) y [`SECURITY.md`](SECURITY.md).

## Para desarrolladores y auditores

```bash
# Desde la raíz del repositorio, con Python compatible:
python -m venv .venv
# Active .venv según su sistema operativo.
python -m pip install -e '.[dev]'
python -m pytest
ruff check src tests
python -m notebook_conexion.selftest
python scripts/check_release.py
```

La carpeta `src/notebook_conexion/` contiene el código principal; `tests/`, las pruebas offline; `docs/`, el diseño y sus límites; `scripts/`, herramientas de instalación/verificación; `.github/workflows/ci.yml`, el CI; y `skills/notebook-conexion/SKILL.md`, las instrucciones para agentes.

Los comandos son opcionales para usuarios finales. Más información: [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md), [`docs/INTEGRACION_AGENTES.md`](docs/INTEGRACION_AGENTES.md), [`docs/INFORME_VALIDACION.md`](docs/INFORME_VALIDACION.md) y [`CONTRIBUTING.md`](CONTRIBUTING.md).

### Publicación y procedencia

Esta distribución constituye un **nuevo repositorio Git sin historial importado de otro repositorio**. No incluye archivos `.git` ni material privado de las instalaciones; el contenido se publica desde una copia revisada del código fuente de Notebook Conexión 1.3.0. El desarrollo contó con **asistencia de IA** y se fundamenta en documentación técnica pública de los proveedores. Esto se declara de forma transparente en [`docs/PROCEDENCIA.md`](docs/PROCEDENCIA.md). La ausencia de archivos idénticos o de historial Git previo **no certifica por sí sola originalidad absoluta**; cualquier reutilización futura de componentes externos debe respetar su licencia y atribuciones.

**GitHub:** repositorio previsto [`fegones/segundocerebro`](https://github.com/fegones/segundocerebro). Para crearlo y subir los archivos consulte [`docs/PUBLICACION_GITHUB.md`](docs/PUBLICACION_GITHUB.md); también se incluye un asistente opcional `PUBLICAR_GITHUB_WINDOWS.cmd` que utiliza Git y GitHub CLI autenticado.

## Documentación de Google

- [Gemini Notebook REST API](https://developers.google.com/notebook/reference/rest)
- [Autenticación de Gemini Notebook](https://developers.google.com/notebook/docs/authentication)
- [Fuentes de Gemini Notebook](https://developers.google.com/notebook/docs/sources)
- [Gemini API](https://ai.google.dev/gemini-api/docs)

Google, Gemini, NotebookLM, Claude y Codex son marcas de sus respectivos titulares. Este proyecto no implica respaldo ni afiliación oficial a esos proveedores.

## Licencia MIT

**Copyright © 2026 Felipe Carlos González Espinoza.** El código de esta distribución se ofrece bajo licencia **MIT**; consulte [`LICENSE`](LICENSE). La licencia permite usar, modificar, redistribuir y comercializar el software, conservando los avisos de copyright y licencia que correspondan. Las dependencias externas conservan sus respectivas licencias. Las condiciones de uso de las APIs de terceros siguen siendo aplicables.

---

**Versión:** 1.3.0 · **Estado:** candidato a validación técnica y de seguridad, no certificado para producción.
