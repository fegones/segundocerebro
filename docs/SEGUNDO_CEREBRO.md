# Segundo Cerebro: operación controlada y límites

## Flujo operativo

1. Dar de alta perfiles distintos. Una cuenta Google = un perfil independiente; cada perfil completa su propio OAuth.
2. El propietario selecciona un subconjunto de cuadernos en el panel. Se guarda `scope.json` en la configuración privada del usuario. Las herramientas MCP no pueden modificar este archivo mediante una operación disponible en el servidor.
3. Sincronización de metadatos desde la API oficial **solo para cuadernos seleccionados**. Si se solicita `include-text`, intentar leer las fuentes textuales con `GetSource`. Muchas fuentes web, video, PDF u otros recursos solo devolverán metadatos; se indica el número sin contenido recuperable.
4. Para incorporar documento original/archivo exportado: usar el diálogo de archivo local y seleccionar el cuaderno autorizado. El documento se indexa en una base cifrada. No se está subiendo el archivo a NotebookLM y no se sincroniza con su chat.
5. Auditar duplicados o versiones; consultar evidencias en modo extractivo. Para respuesta generativa enviar solamente fragmentos de selección a Gemini API tras permiso temporal por cuenta y exigir citas literales.

## Matriz de certeza para fuentes duplicadas

- **Igualdad exacta**: el SHA-256 de los textos disponibles coincide. No verifica si las versiones binarias, imágenes o PDF originales son iguales.
- **URL coincidente**: normaliza únicamente mayúsculas de host, barras finales y parámetros de rastreo conocidos. Un sitio puede modificar su contenido; la URL no prueba igualdad documental.
- **Título coincidente**: coincidencia de nombre normalizado, **baja confianza**.
- **Contenido similar**: similitud Jaccard por ventanas de cinco palabras, con umbral 0,80 y límites de cálculo. No es verificación semántica con embeddings ni plagio pericial.
- **Duplicidad de cuaderno**: coincidencia de nombres o superposición de fuentes, nunca borrado automático.

## Aislamiento de cuentas y cuadernos

Cada registro se identifica mediante tres componentes: `(perfil, cuaderno, fuente)`. Todos los documentos se guardan con el origen y el hash. Los datos cifrados se autentican con AES-GCM vinculando esos identificadores como datos adicionales. Un registro copiado a otro perfil/cuaderno sin su clave/identificador no se descifra correctamente.

El servidor MCP tiene una barrera: cuando existe una selección activa, las herramientas antiguas para consultar cuadernos fuera de alcance, generar sin fundamentación o administrar fuentes no se ofrecen ni se ejecutan. Las nuevas herramientas no admiten seleccionar otros cuadernos. La selección se realiza fuera del MCP mediante una acción local explícita del propietario.

**Límite de amenaza:** un agente con acceso adicional a una terminal del usuario o permiso para editar sus archivos de configuración podría modificar el estado local. No es una sandbox para procesos con privilegios del mismo usuario. Para aislamiento exigible debe deshabilitarse shell, red y otros conectores del agente, o ejecutarlo con un usuario de sistema de mínimos privilegios.

## Respuesta documental estricta

La herramienta `buscar_evidencia_segura` utiliza una búsqueda léxica local y devuelve fragmentos literales con identificadores de perfil/cuaderno/fuente y SHA-256 del contenido. `responder_segundo_cerebro` usa el modo extractivo por defecto y no redacta conclusiones no fundamentadas. Si la búsqueda no encuentra coincidencias relevantes, devuelve una abstención exacta.

Cuando el usuario selecciona Gemini, se envían los fragmentos solo si **todas** las cuentas seleccionadas tienen política local y autorización temporal vigente. Las citas deben coincidir con fragmentos textuales recuperados y la respuesta debe referenciarlas. Esto es un filtro formal, no una validación semántica de cada frase. Nunca afirmar precisión del 100 %, cero alucinaciones o equivalencia al chat interno de Google.

## Recursos exportados y memoria

Los históricos de conversación, notas, transcripciones o recursos generados en NotebookLM no están disponibles como colección íntegra por el API REST empleado. Pueden indexarse solo después de que el usuario los exporte y los incorpore con `kind=chat_export|note_export|artifact_export`. Se preservan como evidencia **local** vinculada al cuaderno, sin afirmar que son una réplica sincronizada.

No se permite borrado automático de originales. Las versiones se comparan únicamente si el usuario importa nuevamente un documento bajo el mismo identificador local `local:...` o si la API devuelve el mismo ID de fuente con un contenido distinto disponible.
