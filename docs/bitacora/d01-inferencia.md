# D1 · Inferencia bajo el capó · 2026-11-09 (cerrado 2026-11-10)

> Las cifras salen de `runs/d01.jsonl` y del reporte `scripts/d01_report.py`. Lo marcado como
> **(propuesto)** lo redactó Claude a partir de tus datos y de tu código; revísalo y corrígelo
> con tus palabras si no lo compartes.

## Objetivo y criterio de éxito
- **Objetivo:** medir una llamada de inferencia real con streaming (TTFT, latencia, tokens, costo de referencia), con reintentos propios, y dejar cada llamada registrada en `runs/d01.jsonl`.
- **Criterio medible y resultado:**

| Criterio | Resultado |
|---|---|
| 10 registros válidos atribuibles a su configuración | ✅ 20 válidos en 2 configuraciones (timeout 0,5 s y 0,4 s), 5 por temperatura |
| Tabla p50 / máx de ttft y latencia por temperatura | ✅ ver *Métricas* |
| Proyección a 10.000 llamadas | ⚠️ calculada, pero el tiempo está subestimado (F-02) |
| Timeout con reintento y backoff con jitter, probado con ~1 ms | ✅ backoff comprobado; ⚠️ no está probado que la falla fuera un timeout (F-03) |
| `finish_reason` ≠ `stop` marcado como anómalo | ⚠️ el reporte lo detecta (0 casos), pero el chequeo del resumen es fijo (F-04) |
| Ni la key ni los headers en las salidas | ✅ verificado en el `jsonl`; la consola no está cubierta |

- **Estado:** cerrado con deuda técnica documentada (F-02 a F-04, abiertos).
- **Tiempo real (propuesto):** cercano a 4 h frente a los 45 min planificados. Inicio hacia las 16:36 del 9-nov y el último script llegó pasadas las 20:00; el cierre se hizo el 10-nov. El exceso vino del montaje del entorno (venv y activación en Windows), el cambio de proveedor por falta de presupuesto, el fallo F-01 y las iteraciones sobre qué medir. Ajusta la cifra si tu cronómetro dice otra cosa.

## Diseño
- **Proveedor:** Groq, API compatible con OpenAI (ADR-002). Modelo `qwen/qwen3.8-27b` con `reasoning_effort="none"`.
- **Llamada:** `stream=True` con `stream_options={"include_usage": True}`; los tokens salen de `usage`, no se estiman.
- **Reintentos:** cliente con `max_retries=0` y wrapper propio `run_with_retry` (ADR-003): hasta 5 intentos, espera de 1, 2, 4, 8 s más jitter de hasta 0,5 s. Se reintentan errores de conexión/timeout, 429 y 5xx; el resto falla de inmediato.
- **Fallos:** si se agotan los intentos se escribe un registro con el mismo esquema (métricas en `null`, `attempts`, `error`) en vez de abortar.
- **Registro (un JSON por línea):** `run_id`, `ts`, `model`, `temperature`, `max_tokens`, `reasoning_effort`, `timeout_s`, `ttft_s`, `latency_s`, `input_tokens`, `output_tokens`, `finish_reason`, `cost_ref_usd`, `attempts`, `output_chars`, `error`. `ts` marca el inicio de la llamada.
- **Reporte:** `d01_report.py`, solo lectura: valida esquema, agrupa por configuración, calcula p50/máx y proyección, revisa el backoff por la separación entre `ts`, detecta anomalías y busca patrones de key.

### Definiciones de las métricas (según el código)
- **Primer token (propuesto):** el primer fragmento del stream con `delta.content` no vacío. Con `reasoning_effort="none"` coincide con el primer token generado; con un modelo de razonamiento el primer contenido llegaría después del razonamiento, y el TTFT incluiría ese tiempo.
- **Latencia total (propuesto):** desde justo antes de enviar la request hasta que termina el stream.
- **Limitación:** ambas miden solo el intento exitoso. Los intentos fallidos y las esperas de backoff no entran (F-02).

## Trade-offs

| Decisión | Alternativas | Elegí | Evidencia / razón |
|---|---|---|---|
| Proveedor | Ollama local · Groq · Gemini | Groq | Sin presupuesto para APIs de pago y 8 GB de RAM con poca memoria libre para un modelo local |
| Modelo y razonamiento | modelo de razonamiento (gpt-oss) · Qwen 3.8 27B | Qwen con `reasoning_effort="none"` | Respuesta directa y métricas más simples; evita el F-01 |
| Reintentos | A: SDK (`max_retries`) · B: wrapper propio con `max_retries=0` · C: ambas capas | B | Permite registrar `attempts` y definir la política; C multiplicaría los intentos (ADR-003) |
| Timeout | 0,5 s · 0,4 s · mayor | Valores de prueba, sin decisión de producción (propuesto) | Con 0,5 s reintentó 1 de 10 llamadas sanas y con 0,4 s, 2 de 10. Ambos valores quedan cerca del TTFT p50 (~0,35 s), por eso sirven para provocar reintentos pero no para producción. Una llamada reintentada costó ~2,1 s reales frente a ~0,5 s sin reintento. Propuesta para D2 en adelante: ~2 s, a validar con una muestra mayor |

## Métricas (n = 5 por temperatura; segundos)

| Configuración | Temp. | TTFT p50 | TTFT máx | Latencia p50 | Latencia máx |
|---|---|---|---|---|---|
| timeout 0,5 s | 0 | 0,352 | 0,675 | 0,495 | 0,808 |
| timeout 0,5 s | 1,0 | 0,357 | 0,369 | 0,590 | 0,620 |
| timeout 0,4 s | 0 | 0,370 | 0,687 | 0,513 | 0,844 |
| timeout 0,4 s | 1,0 | 0,341 | 0,436 | 0,475 | 0,616 |

Con n = 5 el p95 coincide con el máximo, por eso la tabla muestra p50 y máx.

**Tokens:** `input_tokens` = 31 en todas las llamadas. Con `temperature=0`, `output_tokens` = 74 en las 10 llamadas (361 caracteres); con `temperature=1.0` varía entre 66 y 126.

**Proyección a 10.000 llamadas** (media de las válidas, en serie; precio de referencia hipotético de 0,80 / 4,00 USD por 1M de tokens entrada/salida, consultado el 2026-11-09):

| Configuración | Tokens entrada | Tokens salida | Tiempo | Costo ref. |
|---|---|---|---|---|
| timeout 0,5 s | 310.000 | 870.000 | ~1,56 h | 3,73 USD |
| timeout 0,4 s | 310.000 | 732.000 | ~1,54 h | 3,18 USD |

El tiempo está subestimado porque no incluye reintentos ni backoff (F-02). En esta muestra 3 de 20 llamadas sanas necesitaron un segundo intento.

**Prueba de reintentos (timeout ≈ 1 ms):** 10 de 10 llamadas agotaron los 5 intentos. La separación entre registros fallidos consecutivos fue de 15,8 a 17,0 s (esperado 15–19 s), coherente con el jitter. Error registrado: `APIConnectionError: Connection error.`

## Fallos de inferencia encontrados
- **F-01** (cerrado): respuesta vacía por `max_tokens` agotado en tokens de razonamiento. Detalle en `FALLOS.md`.
- **F-02** (abierto): la latencia reportada no incluye reintentos ni esperas. Una llamada con `attempts: 2` registró `latency_s` de 0,48 s, pero el siguiente registro empezó 2,05 s después; en otra, 0,49 s frente a 2,19 s. Es una subestimación de ~4× en esas llamadas.
- **F-03** (abierto): el error de la prueba de 1 ms es `Connection error.`; el SDK reserva otro mensaje y clase para los timeouts, así que no está demostrado que la falla fuera un timeout. Pendiente: inspeccionar `exc.__cause__`.
- **F-04** (abierto): el ítem "anómalas marcadas" del resumen del reporte está fijado en verdadero y nunca puede fallar.

Detalle de síntoma, causa y test en `docs/bitacora/FALLOS.md`.

## Seguridad
- La key vive en `.env` (en `.gitignore`) y nunca se imprime ni se guarda en el `jsonl`.
- El reporte busca la key y patrones de cabeceras en el `jsonl`; no revisa la salida de consola.
- El `jsonl` guarda solo el largo de la respuesta (`output_chars`), no su texto, así que no filtra contenido del modelo.
- Los reintentos sin tope de tiempo total y sin respetar `Retry-After` pueden agravar un 429 en vez de aliviarlo.

## Qué haría distinto (propuesto)
- Medir de extremo a extremo (toda la llamada, con reintentos) y registrar además el tiempo del intento exitoso.
- Registrar la causa del fallo con más detalle que el mensaje final de la excepción.
- Agregar un identificador por ejecución del script además del de cada llamada, para agrupar corridas.
- Poner `if __name__ == "__main__"`, un tope de tiempo total por llamada y respeto de `Retry-After`.
- Antes de comparar temperaturas, subir la muestra (n ≥ 20) para que el p95 signifique algo.
- Dejar escrito desde el inicio qué mide cada métrica y de dónde sale cada campo.
