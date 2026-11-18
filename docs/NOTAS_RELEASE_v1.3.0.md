# Segundo Cerebro v1.3.0 — Notas para la versión preliminar

**Estado previsto:** pre-release / versión de evaluación.

## Resumen

Segundo Cerebro (Notebook Conexión) es una aplicación local en Python para organizar información documental proveniente de cuadernos de Gemini Notebook, trabajar con varias cuentas Google y exponer herramientas mediante MCP para agentes como Claude Code y Codex.

## Funciones disponibles en el código

- Perfiles OAuth individuales para múltiples cuentas Google.
- Catálogos de cuadernos y fuentes, con selección de alcance autorizado.
- Identificación de coincidencias de fuentes y cuadernos, comparación documental y versiones localmente indexadas.
- Índice documental local cifrado; recuperación de fragmentos con referencias y abstención cuando no hay evidencia suficiente.
- MCP local por stdio y asistentes de instalación para Windows.
- Comandos CLI, exportaciones y conector independiente para Gemini API.

## Límites importantes

- **No sustituye el chat interno de NotebookLM.** No puede acceder automáticamente a conversaciones, notas, videos u otros recursos no expuestos por la API oficial.
- La consulta estricta depende del material que se haya podido obtener o importar; la mera existencia de una fuente en un catálogo no garantiza acceso a su contenido completo.
- El control de alcance del servidor MCP no restringe otros accesos o herramientas (shell, navegador, otros MCP) del agente.
- El uso con cuentas reales Google, los permisos OAuth y la interoperabilidad real de los agentes requieren pruebas adicionales.
- No garantiza ausencia de alucinaciones, ni se declara auditado de forma independiente o apto para producción.

## Calidad y seguridad

- Las pruebas automáticas, Ruff y la auditoría de dependencias se ejecutan para Python 3.11, 3.12 y 3.13.
- La rama main está protegida mediante Pull Requests y verificaciones obligatorias.
- CodeQL se incorpora como análisis de código de seguridad separado y deberá validar sus propios resultados.
- No deben distribuirse archivos de perfil, sesiones, claves API, tokens OAuth ni bases de datos personales.

## Instalación

Revisar [README](../README.md), [seguridad](../SECURITY.md) y [guía de instalación](SOLUCION_PROBLEMAS.md) antes de instalar. En Windows, usar el instalador guiado y una cuenta Google autorizada específicamente para las pruebas.

## Licencia, atribución y procedencia

Copyright (c) 2026 Felipe Carlos González Espinoza. MIT para el código distribuido bajo esa licencia. Se aplican por separado las licencias y términos de terceros; consultar [LICENSE](../LICENSE) y [procedencia](PROCEDENCIA.md).

## Cómo publicar

Crear el tag **v1.3.0** sobre la rama main después de revisar los resultados de CodeQL. Marcar la publicación como **pre-release**. No describirla como una versión certificada para producción.
