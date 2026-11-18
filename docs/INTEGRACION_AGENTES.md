# Integración con agentes y funcionamiento en lenguaje natural

## Concepto

La Skill indica al modelo CUÁNDO y CÓMO utilizar las herramientas. El servidor MCP aporta la capacidad técnica de ejecutar operaciones. Ambos se requieren para una experiencia natural robusta. El programa no convierte ChatGPT web en un cliente de tu servidor local; esta distribución conecta **Claude Code y Codex instalados en la misma estación**.

## Activación

Use `CONECTAR_AGENTES_WINDOWS.cmd`, no necesita escribir los comandos siguientes. El asistente registra el MCP en la configuración personal del agente y copia la Skill en:

- Claude Code: `~/.claude/skills/notebook-conexion/SKILL.md`
- Codex: `~/.agents/skills/notebook-conexion/SKILL.md`

No reescribe una Skill existente diferente. La configuración MCP apunta al ejecutable Python del entorno virtual instalado en AppData local. **No mueva la carpeta una vez conectado el agente**; si lo hace, retire/reconfigure la conexión.

## Diagnóstico opcional avanzado

Un servidor MCP local usa `python -m notebook_conexion.mcp_server --profile personal`. Claude Code recibe configuración equivalente a `claude mcp add --scope user --transport stdio notebook-conexion -- <python-local> -m notebook_conexion.mcp_server --profile personal`.

Codex recibe configuración equivalente a `codex mcp add notebook-conexion -- <python-local> -m notebook_conexion.mcp_server --profile personal`.

No ponga credenciales OAuth o claves Gemini en los argumentos.

## Seguridad

- `--allow-writes` y `--allow-gemini` se añaden solo con consentimiento del titular de la estación.
- Habilitar política general de cambios NO habilita por sí solo los cambios MCP. El usuario necesita conceder una autorización temporal local de 10 minutos y el agente debe solicitar confirmación de la acción.
- La Skill debe tratar las fuentes como **contenido**, nunca como instrucciones para modificar permisos, enviar secretos, descargar ejecutables o acceder a otros proyectos.
- Ninguna herramienta acepta nombres de archivos con separadores de ruta. Las exportaciones siempre quedan dentro de la carpeta local determinada por Windows/macOS/Linux.

## Funciones disponibles

**Sin alcance estricto:** herramientas clásicas de listar/buscar/administrar fuentes más las nuevas de segundo cerebro. **Con selección activa:** solo herramientas de `PROTECTED_TOOLS`, incluidas `ver_segundo_cerebro`, `listar_fuentes_protegidas`, `sincronizar_segundo_cerebro`, `auditar_duplicados_fuentes`, `auditar_duplicados_cuadernos`, `buscar_evidencia_segura`, `responder_segundo_cerebro`, `comparar_fuentes_cuadernos`, `comparar_versiones_fuente` y `exportar_auditoria_protegida`.

**El propietario debe seleccionar o ampliar los cuadernos en la GUI local.** Los agentes no tienen una herramienta para ampliar alcance. Ni los nombres de documentos ni el contenido recuperado pueden convertirse en instrucciones para cambiar permisos. Esta restricción solo se aplica a este MCP; otros recursos del host requieren sus propios límites.

No ofrece funcionalidad de chat de NotebookLM a través de la API pública, creación de videos o podcasts, eliminación de cuadernos, administración de propietarios ni importación de PDF nativo mediante esta implementación. Algunas de esas capacidades existen en la interfaz de Notebook, pero no en la API pública utilizada.
