# Validación de Notebook Conexión 1.3.0

## Comprobaciones efectuadas en el entorno de construcción

- Pruebas unitarias/offline existentes de v1.2.3 más tests específicos de Segundo Cerebro.
- Pruebas de aislamiento de perfiles/cuadernos, rechazo de IDs inválidos, selección persistente, versión de documentos, recuperación extractiva, abstención, detección de coincidencias, importación TXT/DOCX/HTML, cifrado autenticado y rechazo de clave equivocada.
- Pruebas para denegar herramientas MCP heredadas bajo alcance estricto, ocultarlas del catálogo y rechazar argumentos de tipos inválidos.
- Compilación sintáctica de módulos Python y diagnóstico MCP sin conectarse a Google.

El número exacto de pruebas y los resultados finales figurarán en el manifiesto `RELEASE_VALIDATION.txt` del ZIP.

## No verificado

- Ejecución del instalador real en Windows 11 con cuentas reales.
- Operaciones con Gemini Notebook API real, ni la disponibilidad de `textContent.content` para cada tipo de fuente.
- Gestión de permisos y firma de binarios en estaciones Windows ajenas.
- Cumplimiento de requisitos regulatorios empresariales, certificación independiente, ausencia absoluta de vulnerabilidades o de alucinaciones.
- Compatibilidad de todas las variantes/ediciones de Claude Code/Codex.

## Criterio de cierre

Las funcionalidades documentadas corresponden al código entregado, no a una promesa de compatibilidad completa con NotebookLM. No se incluirá ningún archivo de perfiles, sesión, cookie, certificado privado ni clave API en el ZIP. El código está diseñado para auditoría estática y pruebas adversariales independientes.
