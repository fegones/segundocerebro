# Arquitectura del producto 1.3.0

```text
Claude Code / Codex (lenguaje natural)
   | MCP stdio (solo herramientas permitidas)
   v
mcp_server.py -- validación de esquema y control de alcance
   |                           |                      |
   v                           v                      v
second_brain.py          operations.py           exports.py
   |                       [modo clásico]         archivos locales
   |                           |
   +----- brain_scope.py       +--- NotebookClient [Google Notebook API OAuth]
   +----- brain_store.py       +--- GeminiClient  [Gemini API key]
   +----- brain_import.py
   +----- brain_audit.py
   +----- brain_retrieval.py
   +----- brain_answers.py [Gemini API opcional + citas literales]
```

**Alcance:** `scope.json` bajo configuración del usuario, administrado por GUI o CLI explícito. En presencia de alcance, el servidor MCP bloquea las antiguas herramientas administrativas y expone solo las de Segundo Cerebro. Este control no se extiende al shell ni a otras herramientas instaladas en el anfitrión.

**Datos:** metadatos locales SQLite; texto y versiones cifrados AES-256-GCM con clave del keyring nativo, AAD con perfil/cuaderno/fuente/versión. Selección estricta por esos identificadores. Sin backend SaaS del desarrollador.

**Integración Google:** `GET /notebooks`, `GET /notebooks/{id}`, `GET /notebooks/{id}/sources`, `GET /notebooks/{id}/sources/{id}`, y operaciones de escritura explícitas del cliente original 1.2.3. No se llama a APIs privadas.

**Motor de evidencia:** fragmentación, búsqueda por términos con IDF y citas literales. Generación Gemini separada, con autorización temporal individual por cuenta y validación sintáctica de las citas. El modo extractivo no inventa datos, pero la búsqueda léxica no garantiza cobertura ni relevancia semántica.

Documentación detallada: `SEGUNDO_CEREBRO.md` y `SEGURIDAD.md`.
