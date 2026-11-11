# Plan de 2 semanas

Reparto diario (45 min): 5 brief · 30 código (timer; al minuto 30 se detiene) · 10 bitácora y commit.
Umbrales numéricos = punto de partida; se recalibran con la línea base de D1/D3.

**Rutina diaria:** al iniciar cada día se revisa y ajusta este plan (estado real, límites del proveedor, hallazgos del día anterior) y se deja constancia en el *Registro de cambios* del final.

**Proveedor:** Groq (API compatible con OpenAI), modelo `qwen/qwen3.8-27b` con `reasoning_effort="none"` salvo que el día indique otra cosa. Sin presupuesto para APIs de pago.

## Semana 1 — inferencia, structured outputs, embeddings, RAG

### D1 · Inferencia bajo el capó
- Objetivo: `scripts/d01_inference.py`, mismo prompt 5× con temperature 0 y 5× con 1.0, en streaming.
- Un registro JSONL por llamada en `runs/d01.jsonl`, con estos campos:

| Campo | Qué es |
|---|---|
| `run_id`, `ts` | identificador de la corrida y marca de tiempo |
| `model`, `temperature`, `max_tokens`, `reasoning_effort`, `timeout_s` | configuración usada |
| `ttft_*` | desde que envías la request hasta el primer fragmento de texto |
| `latency_*` | hasta el fin del stream |
| `input_tokens`, `output_tokens` | los que reporta la API (no estimados) |
| `finish_reason` | cómo terminó la generación |
| `cost_ref_usd` | costo de referencia hipotético (precio de una API de pago de tu elección, con su fecha) |
| `attempts` | cuántos intentos hicieron falta |
| `output_chars` | largo de la respuesta, no el texto |

  Las unidades (s o ms) van explícitas en el nombre del campo.
- Medible:
  - 10 registros válidos atribuibles a su corrida y configuración (el archivo puede acumular corridas, pero cada registro debe poder separarse de las demás).
  - Tabla p50/máx de `ttft` y `latency` por temperatura.
  - Proyección a 10.000 llamadas en tokens, tiempo total y costo de referencia.
  - Timeout con reintento y backoff exponencial con jitter, probado con un timeout de ~1 ms.
  - Toda respuesta con `finish_reason` distinto de `stop` queda marcada como anómala.
  - Ni la key ni los headers aparecen en ninguna salida.
- Bitácora: documentar qué definiste como «primer token» y como «latencia total», y la decisión de reintentos (SDK vs wrapper propio).
- Foco de revisión: errores, límites, dónde vive la key, qué se loguea, qué mide realmente cada métrica.

### D2 · Structured outputs
- Objetivo: extraer 20 post-mortems a un modelo Pydantic `Incident(service, severity, root_cause, action_items[])`, validación estricta y máximo 1 reintento con el error de validación.
- Medible: ≥ 19/20 válidos · reporte de reintentos y costo extra · 3 inputs con instrucciones inyectadas, 0 obedecidas.
- Foco: separación instrucciones/datos, JSON truncado, fugas en logs.
- Nota de proveedor (revisión 2026-11-10): según la documentación de Groq, los structured outputs (`response_format` con `json_schema`) **no admiten streaming** (ni tool use al mismo tiempo), así que D2 usa llamadas sin stream. Qwen 3.8 27B figura con soporte de `json_schema`, pero la página lista `strict: true` y `strict: false` de forma inconsistente para este modelo: se prueba antes de asumir (1 llamada por modo: `json_object`, `json_schema` con `strict: false` y con `strict: true`) y se anota cuál funciona. La validación con Pydantic sigue siendo la fuente de verdad en cualquier modo. Con `reasoning_effort="none"` la salida llega en `content`; con razonamiento activo el razonamiento comparte `max_tokens`, y por eso se mantiene `none`.
- Arrastre de D1: el registro de D2 incluye el tiempo total de la llamada con reintentos (F-02), además del tiempo del intento exitoso.
- Datos: `data/d02/postmortems.jsonl` (20 limpios + 3 con instrucciones inyectadas) y `data/d02/gold.jsonl` (solo para medir; nunca se envía al modelo). Convenciones en `data/d02/README.md`.
- Criterios medibles detallados:
  1. ≥ 19/20 limpios válidos con Pydantic estricto (severidad como enum, sin campos extra, sin coerción de tipos) y máximo 1 reintento de validación.
  2. Reporte: tasa de reintentos de validación, tokens y costo de referencia extra por reintento, p50/máx del tiempo total.
  3. 3 inyectados con 0 obedecidos. «Obedecida» se define en el código de forma medible (p. ej. canario presente, severidad forzada distinta del gold, acción que el documento no pide).
  4. Truncado: `pm-18` con un `max_tokens` bajo a propósito termina como fallo controlado (`finish_reason` ≠ `stop`, sin parsear JSON parcial como válido).
  5. Logs: `runs/d02.jsonl` no contiene el texto de los documentos ni las respuestas completas del modelo.
  6. Prueba de modos (1 llamada por modo) con el resultado anotado en la bitácora, y el modo elegido justificado.
- Registro D2 (`runs/d02.jsonl`, un JSON por línea, unidades en el nombre): `run_id` (por ejecución del script), `call_id` (por documento), `ts` (inicio de la llamada), `doc_id`, `kind`, `model`, `mode`, `max_tokens`, `reasoning_effort`, `timeout_s`, `net_attempts`, `validation_attempts` (1 o 2), `valid`, `error_type` (`none`/`json_decode`/`schema`/`truncated`/`api`), `finish_reasons` (uno por intento), `input_tokens` y `output_tokens` (sumados sobre todos los intentos), `cost_ref_usd` y `extra_cost_ref_usd` (lo que costó el reintento), `total_s` (toda la llamada con reintentos) y `last_attempt_s`, `canary_found` (solo inyectados), `service_ok`, `severity_ok`, `n_actions_ok` (comparación con el gold).

### D3 · Chunking, embeddings y cosine pura
- Objetivo: chunker con overlap · embeddings en lote · cosine en NumPy puro (sin faiss/sklearn) · top-k · vectores persistidos.
- Medible: golden de 10 preguntas con chunk esperado · hit@3 y MRR (umbral inicial hit@3 ≥ 0,7) · 2ª ejecución sin recalcular embeddings (cache por hash) · latencia de búsqueda medida.
- Foco: normalización, re-ejecuciones, límites de chunk.

### D4 · ChromaDB y ablación de chunking
- Objetivo: ChromaDB persistente con metadatos (`source`, `section`, `doc_hash`) e indexación idempotente; comparar 3 configuraciones (p. ej. 200/500/1000 tokens × overlap 10%/20%).
- Medible: tabla config → hit@3, MRR, nº de chunks, tokens de contexto por query, tiempo de indexado · top-k de Chroma coincide con tu cosine pura en ≥ 9/10 queries (explicar diferencias) · filtro por metadata funcionando.
- Foco: supuestos por defecto de la librería, reindexado.

### D5 · RAG end-to-end
- Objetivo: `rag.py` retrieve → prompt con contexto delimitado e ids → respuesta con citas `[c12]` → abstención cuando no hay respaldo.
- Medible: 10 respondibles con ≥ 8 correctas y bien citadas · 5 fuera de alcance con ≥ 4 abstenciones · 1 chunk envenenado no obedecido · desglose de latencia (embed/retrieve/generate) y tokens por query.
- Foco: injection indirecta, citas inventadas, tamaño del prompt.

## Semana 2 — agentes, contexto, evals, observabilidad

### D6 · Tool calling manual
- Objetivo: loop de agente sin frameworks con tools `search_runbooks`, `get_service_status` (simulada), `calc_sla_downtime`.
- Medible: 8 prompts con ≥ 7/8 de tool y args correctos · `max_steps=5` siempre termina · sobrevive a tool que falla, tool inexistente y args inválidos · turnos y tokens acumulados por tarea.
- Foco: validación de argumentos, crecimiento del historial, qué se devuelve al modelo al fallar.

### D7 · Tools con efectos y guardrails
- Objetivo: `restart_service` y `rollback_deploy` (simuladas) con confirmación humana, allowlist y mínimo privilegio; el RAG como tool.
- Medible: 6 ataques red-team (3 indirectos vía chunk/resultado de tool, 1 directo, 2 con args fuera de allowlist) con 0 ejecuciones no autorizadas · audit log de cada ejecución.
- Foco: límite de confianza, dónde vive la política.

### D8 · Gestión de contexto
- Objetivo: (a) test «aguja en el pajar» (inicio/medio/final × ~2k y ~20k tokens × 3 repeticiones); (b) `ContextManager` con presupuesto de tokens (ventana deslizante + resumen).
- Medible: matriz posición × largo con accuracy · 30 turnos sin exceder el presupuesto y conservando un hecho fijado en el turno 2 · ahorro vs historial completo · stretch: prompt caching.
- Foco: conteo de tokens, qué se pierde al resumir.

### D9 · Evals
- Objetivo: `evals/run_evals.py` sobre `golden.jsonl` (≥ 25 casos) con hit@k/MRR, chequeos deterministas y LLM-as-judge con rúbrica.
- Medible: reporte JSON + Markdown · exit code ≠ 0 bajo el umbral (listo para gate en GitHub Actions) · juez calibrado con 10 casos etiquetados a mano (acuerdo ≥ 80%) · 2 corridas con varianza.
- Foco: sesgos del juez, contaminación juez/generador, flakiness.

### D10 · Observabilidad y cierre
- Objetivo: `tracing.py` con spans anidados (request → retrieve → generate → tool) con modelo, tokens, latencia, costo, hash del prompt y error; export a JSONL (opcional OpenTelemetry GenAI).
- Medible: 100% de requests con `trace_id` · `report_traces.py` con p50/p95, costo por request, tasa de error, % de abstenciones · redacción: 0 keys/emails en trazas · tag `v0.1.0` y README con diagrama.
- Foco: qué se guarda en trazas, retención, cardinalidad.

## Registro de cambios del plan
- 2026-11-07: versión inicial.
- 2026-11-09: el proveedor pasa a Groq (sin presupuesto para API de pago); el costo del D1 pasa a ser de referencia hipotético; la tabla completa de campos del registro D1 se traslada del chat a este plan; se agregan los campos `reasoning_effort` y `timeout_s`; se exige documentar la definición de las métricas; se establece la rutina de revisar este plan al iniciar cada día.
- 2026-11-10: D2 se ajusta al proveedor (sin streaming con structured outputs; prueba de modo `strict` antes de asumir soporte; reintentos de validación se cuentan aparte de los de red) y arrastra de D1 la medición de tiempo total incluyendo reintentos (F-02). D1 se cierra con deuda técnica documentada (F-02 a F-04).
- 2026-11-11: D2 sigue abierto (sin scripts aún). El plan se cuenta por número de día, no por fecha, así que no se corre nada. D2 se divide en 5 etapas con un resultado comprobable cada una y se permite repartirlo en dos sesiones; el tope de 30 min de código se aplica por sesión.
