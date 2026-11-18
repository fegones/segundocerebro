# Política de seguridad — Segundo Cerebro

## Estado y alcance

La versión 1.3.0 es un proyecto abierto en etapa de validación. Las pruebas unitarias offline y las revisiones estáticas no equivalen a una auditoría forense independiente ni certifican ausencia de vulnerabilidades.

## Reporte responsable

No publique credenciales, tokens, datos personales ni ejemplos de explotación contra cuentas reales en Issues públicos. Para un reporte de seguridad, utilice **GitHub → Security → Advisories → Report a vulnerability**, si está habilitado por el propietario del repositorio. Si no está disponible, solicite por un canal privado al mantenedor un medio de contacto seguro antes de compartir detalles sensibles.

## Modelo de amenazas resumido

- Credenciales OAuth y claves API: se gestionan localmente con el almacén seguro del sistema. La cuenta de Windows/macOS/Linux sigue siendo un límite de seguridad fundamental.
- Datos indexados: cifrado AES-GCM de los textos; algunos metadatos permanecen sin cifrar; las exportaciones pueden almacenarse sin cifrar.
- MCP: comunicación local por `stdio` y restricciones por selección de cuadernos. El conector **no aísla otras herramientas** del agente (shell, navegador, otros MCP).
- Documentos de terceros: tratar como datos potencialmente maliciosos. Mitigaciones contra *prompt injection* no garantizan protección completa.
- Servicios externos: las políticas y cuotas de Google y demás proveedores son independientes de este software.

## Comprobaciones mínimas antes de distribuir

1. Ejecutar `python -m pytest`, `ruff check src tests` y `python scripts/check_release.py`.
2. Actualizar y auditar dependencias instaladas con `pip-audit`.
3. Revisar archivos rastreados: `git ls-files`; comprobar que no existan `.env`, `client_secret*.json`, tokens, certificados privados, bases de datos, historiales o caches.
4. Validar operaciones OAuth y MCP en un entorno de prueba con cuentas separadas.
5. Revisar permisos del sistema operativo y protección de las carpetas de datos/exportación.

No se aceptan garantías de «cero alucinaciones», «seguridad absoluta» ni «ausencia completa de rastreo».
