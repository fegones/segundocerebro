# Changelog

## 1.3.0 — Segundo Cerebro (2026-11-18)

- Selección explícita y persistente de múltiples cuadernos de varias cuentas Google, no modificable desde MCP.
- Restricción del servidor MCP: ocultación y rechazo de herramientas antiguas cuando hay un alcance estricto activo.
- Sincronización multi-cuenta de metadatos de cuadernos y fuentes; recuperación opcional de fuentes con `textContent.content` accesible por API.
- Importación manual TXT/MD/CSV/JSON/HTML/DOCX/PDF; artefactos/chats exportados registrados como archivos locales con procedencia propia.
- Base SQLite con cifrado autenticado AES-256-GCM del contenido y versiones, manteniendo metadatos locales no cifrados.
- Auditoría de duplicados por hash, URL, título, similitud de texto; cuadernos probablemente repetidos; comparación de versiones y documentos entre cuentas.
- Recuperación extractiva con citas y abstención en ausencia de evidencia; síntesis Gemini opcional con comprobación de citas literales y permisos por cuenta.
- Asistente de selección de cuadernos en la GUI; CLI y Skill MCP extendidas; límites de memoria y validación de IDs.
- Bloqueo de reutilización accidental de perfil con otro proyecto/cliente OAuth y normalización de modelos de ejemplo.
- No se añade ninguna vía no oficial de chat de NotebookLM ni se promete sincronización automática de sus recursos internos.

## 1.2.3

- Cliente REST oficial, OAuth individual, interfaz local y MCP sin FastMCP ni PyYAML.
