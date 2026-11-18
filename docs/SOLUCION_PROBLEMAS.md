# Guía de instalación y resolución de problemas — Windows

## 1. El instalador no encuentra Python

Instale Python 3.11–3.13 desde https://www.python.org/downloads/windows/ incluyendo el Python Launcher (`py`) o PATH. Cierre y vuelva a abrir la ventana de Windows, y ejecute `INSTALAR_WINDOWS.cmd`. No se necesita Visual C++ Build Tools.

## 2. Fallo de PyYAML o FastMCP

Esta versión **no los instala ni los necesita**. Si ve una referencia a `fastmcp` en el proceso, puede estar instalando el paquete anterior o utilizando otra carpeta. Compruebe que el nombre del ZIP contiene `v1.3.0`.

## 3. Error de pip, red o proxy

El instalador necesita Internet para descargar `httpx`, `platformdirs`, `keyring`, `google-auth`, `google-auth-oauthlib`, `cryptography` (ruedas binarias) y `pypdf`. Obliga a utilizar distribuciones binarias, por lo que falla de forma clara si no hay una versión compatible. No desactive el antivirus para forzar la instalación. Si un proxy corporativo bloquea PyPI, consulte con su administrador o use un índice privado confiable.

## 4. No aparece el panel gráfico

Ejecute `DIAGNOSTICO_WINDOWS.cmd`. Algunas instalaciones reducidas de Python no incluyen Tkinter. Instale Python estándar de python.org con Tcl/Tk y vuelva a ejecutar. No es necesario borrar el proyecto.

## 5. Google Cloud solicita muchos pasos

Google requiere una configuración OAuth por proyecto. En https://console.cloud.google.com haga lo siguiente: (1) cree/seleccione proyecto; (2) active Gemini Notebook API `notebook.googleapis.com`; (3) configure marca y audiencia de OAuth; (4) registre el alcance `https://www.googleapis.com/auth/notebook.readonly` para lectura o `https://www.googleapis.com/auth/notebook` para escritura; (5) cree cliente OAuth **Desktop app**; (6) descargue el JSON y selecciónelo desde la interfaz. Nunca suba el JSON al repositorio GitHub. Si su aplicación está en modo pruebas, agregue su propio correo como usuario de pruebas según la configuración de Google.

## 6. Google 403 (cuenta no admitida)

En vista previa, Gemini Notebook API admite cuentas personales y no cuentas Google Workspace. Compruebe haber iniciado sesión en https://notebook.google.com al menos una vez con la cuenta autorizada. Una restricción del proveedor no puede corregirse con el cliente Python.

## 7. No aparecen los cuadernos o falla OAuth

Verifique que se abrió la cuenta Google correcta, que el proyecto tenga la API activa, que el ID de proyecto coincida y que el perfil tiene credenciales. Compruebe el consentimiento solicitado. Si el token caducó o fue revocado, vuelva a vincular la cuenta desde el panel. No copie cookies de NotebookLM.

## 8. Claude Code/Codex no reconoce Notebook Conexión

Primero instale Claude Code o Codex según sus instrucciones oficiales y confirme que el ejecutable esté en PATH. Ejecute `CONECTAR_AGENTES_WINDOWS.cmd`, elija agente y autorice modificación de configuración MCP local. Reinicie el agente y pruebe: «Usa Notebook Conexión y lista mis cuadernos». La Skill contextualiza los usos; **el acceso real viene del servidor MCP**. Si la configuración no se registra por cambio de sintaxis de su versión CLI, consulte `docs/INTEGRACION_AGENTES.md`.

## 9. No permite crear cuadernos ni modificar fuentes

Por seguridad hay tres barreras: autorización general de escritura del perfil, servidor MCP registrado con escritura y ventana temporal habilitada desde el panel durante 10 minutos. También debe reautenticarse por OAuth con alcance de escritura. Si vuelve a conectar el agente con nuevos permisos, permita explícitamente reemplazar la configuración anterior.

## 10. Mis archivos no aparecen

Los archivos exportados se guardan en la carpeta **Documentos/Notebook Conexion/Exportaciones**. En Windows puede variar según la ubicación de Documentos redirigida por OneDrive. Las herramientas devuelven la ruta concreta. No utilizan el directorio de instalación.

## 11. Cómo desinstalar

Quite el servidor `notebook-conexion` de la configuración de Claude Code/Codex si lo instaló, elimine el directorio del programa y borre manualmente su configuración/secretos de este producto a través del almacén de credenciales y el menú `logout` del CLI. El programa no elimina ni revoca los permisos del proyecto Google de forma remota; para hacerlo retire el acceso de la aplicación en su Cuenta Google. No borre archivos de otras aplicaciones.

## 12. Gemini API devuelve HTTP 404 por un modelo anterior

La nueva versión usa `gemini-3.8-flash` por defecto. El acceso a modelos de la familia 2.5 puede estar restringido para nuevas cuentas. El usuario puede escoger otro modelo disponible; esto no cambia su autenticación con Gemini Notebook.

## 13. Proyecto descomprimido en OneDrive

El instalador Windows coloca el entorno virtual en `%LOCALAPPDATA%\NotebookConexion\1.3.0\.venv`, fuera de OneDrive, para evitar sincronizar miles de archivos de dependencias. El código fuente puede permanecer en OneDrive, pero mover o borrar esa carpeta después de conectar agentes puede romper una instalación *editable*. Si necesita moverla, ejecute el instalador de nuevo desde su nueva ubicación y reconecte los agentes.

## 14. El Segundo Cerebro no encuentra respuesta aunque las fuentes aparecen

Listar una fuente solo demuestra que la cuenta ve sus **metadatos**. Pulse **Abrir Segundo Cerebro → Indexar texto desde Google**; la API puede devolver solo estado/URL para PDF o páginas web. Importe entonces el documento original o una exportación local desde **Importar archivo**. Para PDFs escaneados haga OCR fuera de esta aplicación. Use **listar documentos indexados** desde su agente para comprobar el texto realmente disponible. Si no hay evidencia, la abstención es el comportamiento correcto.

## 15. Necesito combinar dos o tres cuentas

Cada cuenta necesita un perfil nuevo y autenticación independiente. Vuelva al panel inicial, escriba otro perfil, guarde y vincule Google. Desde Segundo Cerebro pulse **Cargar cuentas** y seleccione los cuadernos deseados de todos los perfiles. No renombre un perfil existente para reutilizar el token de otro proyecto.

## 16. No se puede usar una herramienta antigua desde Claude Code/Codex

Cuando está activo el alcance estricto, las herramientas anteriores de listado global, cambios o generación independiente se bloquean deliberadamente. Emplee las nuevas herramientas del Segundo Cerebro. Para desactivar el modo, el propietario debe hacerlo localmente con el comando administrativo confirmado `scope-clear`; el agente MCP no puede hacerlo.

## 17. No puedo consultar todos los documentos grandes de una sola vez

La consulta local rechaza cargar más de 25 MB de texto descifrado por operación. Reduzca la selección de cuadernos o separe el proyecto por tema; el sistema no responde con un listado incompleto que parezca exhaustivo.
