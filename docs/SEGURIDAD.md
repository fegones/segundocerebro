# Modelo de seguridad y amenazas — Notebook Conexión 1.3.0

## Política de mínimo privilegio

- Al conectar Claude/Codex se usa MCP `stdio`, sin puertos escuchando en red.
- El usuario define fuera del MCP el conjunto de perfiles y cuadernos autorizado; las operaciones del segundo cerebro son **solo lectura remota**. No hay herramienta MCP para abrir más cuadernos, borrar contenido, cambiar ACL o autorizar nuevos scopes.
- Si hay selección estricta, las herramientas clásicas se excluyen de `tools/list` **y** se deniegan en el dispatcher de `tools/call`. No equivale a controlar otras herramientas del agente.
- La autorización para enviar a Gemini es explícita y por perfil; solo se comparte el texto recuperado, no las claves de otras cuentas.

## Protección de secretos y datos

- OAuth y clave Gemini permanecen en un backend nativo aprobado por `keyring`.
- La clave AES de los documentos locales vive en ese gestor. El índice almacena ciphertext autenticado con `AES-256-GCM` (nonce aleatorio, AAD con perfil/cuaderno/fuente/versión).
- IDs de fuente, título, nombre de cuaderno, fechas, URLs y hashes permanecen **en texto claro en SQLite**. Use BitLocker/FileVault/LUKS para privacidad completa del dispositivo.
- Eliminar los archivos de índice no revoca permisos OAuth. Para revocar una sesión, hágalo desde la cuenta Google. Perder la clave AES del gestor del sistema hace irrecuperable el archivo cifrado.
- Los exportes de auditoría pueden incluir nombres/URLs privados y son archivos en claro en la carpeta de exportación; compartirlos requiere evaluación de privacidad.

## Entrada documental no confiable

- No se ejecutan macros, JavaScript, comandos desde documentos ni descargas de URLs externas en el módulo de importación.
- Importación TXT/MD/CSV/JSON/HTML/DOCX/PDF con límites por tamaño, páginas, XML comprimido y extensiones; prohíbe symlinks para archivos y carpetas privadas. La extracción PDF está restringida al texto; OCR no está integrado.
- Recuperación léxica sin embeddings remotos ni navegación por fuentes; límite de 25 MB de texto descifrado por operación, 10.000 fragmentos y comparaciones de similitud acotadas.
- Las instrucciones de sistema del modelo y las habilidades indican que el contenido de las fuentes son datos no instrucciones. Pese a ello, un LLM puede ser vulnerable a prompt injection. No utilizar como sustituto de políticas host o revisión humana.

## Superficie de red

- Acceso HTTPS sin redirecciones a endpoints Google permitidos en el cliente original.
- La creación de URLs fuente usa comprobaciones de URLs HTTPS y excluye destinos privados evidentes, pero la API de Google resuelve la URL remota. Nunca se descargan directamente URLs arbitrarias al indexador.
- La API oficial limita sus recursos en vista previa; no se realizan llamadas a endpoints no documentados ni ingeniería inversa de cookies.

## Riesgos residuales para un auditor externo

1. **Sin sandbox del agente:** Claude Code y Codex pueden tener shell, red u otros conectores. El MCP no controla esos canales ni impide que un agente ignore las instrucciones de la Skill.
2. **Identidad local:** el perfil es una etiqueta de sesión; el propietario debe comprobar que autorizó la cuenta Google correcta en OAuth. Dos perfiles pueden apuntar a la misma cuenta, de forma explícita.
3. **Metadatos sin cifrar:** pueden revelar el tema de documentos y URLs; el cifrado de disco complementa el cifrado de contenidos.
4. **Privacidad en cloud:** Google procesa la información enviada a Notebook/Gemini según sus condiciones. Las respuestas del agente anfitrión pueden registrarse en sus propios servicios.
5. **Auditoría limitada:** las pruebas offline no son pruebas de integración real, fuzzing, SAST/SCA continuo ni certificación forense.
6. **Dependencias:** las versiones se resuelven desde PyPI por rangos; se recomienda publicar lockfile/requirements por plataforma y SBOM antes de distribución comercial.
7. **Control lógico, no criptográfico de alcance:** un proceso local del mismo usuario con permisos sobre scope.json puede cambiar el alcance. El host debe restringir filesystem y shell si esto es inadmisible.

## Pruebas recomendadas para liberación general

Pytest offline; integración OAuth con 2-3 cuentas de prueba; ACL Windows con usuarios locales diferentes; `pip-audit`; análisis CodeQL, Bandit y Semgrep; SBOM; cifrado en reposo; fuzzer MCP; revisión de OAuth revocación y scopes; revisión Windows Credential Manager; escáner de secretos; ejecución en entorno de permisos reducidos; y pruebas con documentos maliciosos que contengan prompt injection.
