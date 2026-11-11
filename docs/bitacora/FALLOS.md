# Catálogo de fallos de inferencia

| ID | Día | Síntoma | Causa raíz | Solución | Test de regresión |
|---|---|---|---|---|---|
| F-01 | D0 (smoke) | Respuesta vacía (`content=''`) sin error de API | `max_tokens=5` se agotó en tokens de razonamiento; el modelo cortó por `length` antes de emitir texto visible | Subir `max_tokens` y/o usar modelo directo (Qwen 3.8 27B con `reasoning_effort="none"`) | Parcial: `d01_report.py` marca `finish_reason` ≠ `stop` (0 casos en D1); falta chequear contenido vacío y marcar la anomalía al escribir el registro |
| F-02 | D1 | `latency_s` de llamadas con `attempts: 2` es ~0,5 s, pero la llamada duró ~2,1 s | `t_start` se toma dentro de `run_once`, así que solo mide el intento exitoso y deja fuera intentos fallidos y backoff | Propuesta (sin implementar): medir en el wrapper toda la llamada y registrar también el tiempo del intento exitoso | Abierto: una fila con `attempts > 1` debe tener tiempo total ≥ latencia del intento + espera mínima |
| F-03 | D1 | Con timeout de 1 ms el error registrado es `Connection error.` | No concluyente: el SDK distingue timeouts de otros fallos de conexión y aquí no se registró la causa | Abierto: inspeccionar `exc.__cause__` y registrar la clase de la causa | Abierto: el test de timeout debe fallar si la causa no es un timeout |
| F-04 | D1 | El ítem "anómalas marcadas" del resumen siempre pasa | Está fijado en verdadero en el reporte | Abierto: derivarlo de los datos (anomalías detectadas vs. marcadas al escribir) | Abierto: un registro de prueba con `finish_reason='length'` debe hacerlo fallar |

## Detalle

### F-01 · Respuesta vacía por tope de tokens consumido en razonamiento
- **Fecha / contexto:** 2026-11-09, prueba de conexión (`scripts/smoke.py`), antes del D1.
- **Síntoma:** la llamada respondía sin error (HTTP OK) pero `message.content` llegaba como `''`.
- **Hipótesis descartadas:** key, URL base o nombre de modelo incorrectos (la API habría devuelto 401/404; respondió normalmente).
- **Evidencia:** `finish_reason='length'`, `completion_tokens=5` (igual a `max_tokens=5`), `reasoning_tokens=3`, `prompt_tokens=76`.
- **Modelo original:** openai/gpt-oss-120b
- **Causa raíz:** el modelo era de razonamiento y los tokens de razonamiento cuentan contra `max_tokens`. De los 5 permitidos, 3 se gastaron razonando y el resto no alcanzó para texto visible. El tope fue un error de diseño: se fijó pensando en un modelo directo.
- **Solución:** cambiar a `qwen/qwen3.8-27b` (que admite `reasoning_effort="none"`) y repetir el mismo test. Resultado: `finish_reason='stop'`, `completion_tokens=2`, `prompt_tokens=17`, `content='ok'`. Alternativa: subir `max_tokens` con un modelo de razonamiento.
- **Test de regresión:** pendiente. En el D1, registrar `stop_reason` y marcar como anómala toda respuesta con `finish_reason='length'` o contenido vacío.
- **Aprendizaje:** `max_tokens` limita razonamiento + respuesta juntos; el conteo de `prompt_tokens` depende de la plantilla de cada modelo (76 con el modelo de razonamiento original frente a 17 con Qwen para el mismo mensaje), así que se mide con `usage`, no se estima.

### F-02 · La latencia reportada excluye reintentos y esperas (abierto)
- **Fecha / contexto:** 2026-11-09, revisión del reporte de D1.
- **Síntoma:** en dos filas con `attempts: 2`, `latency_s` fue 0,477 y 0,488 s, mientras que la diferencia hasta el `ts` del registro siguiente fue 2,05 y 2,19 s. En filas con un solo intento esa diferencia fue de 0,44 a 0,85 s, coherente con su latencia.
- **Causa raíz:** el reloj arranca dentro de `run_once`, que solo ve el intento exitoso; el tiempo de los intentos fallidos y del backoff queda fuera. La proyección de tiempo a 10.000 llamadas hereda ese sesgo (y las llamadas que fallaron del todo ni entran en la media).
- **Impacto:** la latencia que vería un usuario en una llamada reintentada es ~4× la reportada; el p95 real es peor que el de la tabla.
- **Estado:** abierto.

### F-03 · Evidencia de timeout ambigua (abierto)
- **Síntoma:** las 10 llamadas con timeout de 1 ms terminaron con `APIConnectionError: Connection error.`
- **Causa raíz:** no determinada. El SDK usa otra clase y otro mensaje cuando detecta un timeout, y el criterio del reporte acepta cualquier error de conexión, de modo que no distingue entre ambos casos.
- **Estado:** abierto. Primer paso: ver `exc.__cause__` de una de esas excepciones.

### F-04 · Verificación que no puede fallar (abierto)
- **Síntoma:** en el resumen del reporte, el ítem "5 anómalas marcadas" está fijado en `True`.
- **Causa raíz:** la anomalía solo se detecta al leer el `jsonl`; al escribir el registro no se marca, así que no hay nada contra qué comparar.
- **Estado:** abierto.
