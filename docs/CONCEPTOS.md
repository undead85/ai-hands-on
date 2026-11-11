# Conceptos por día

Cómo usar este archivo:
- Lee solo el bloque del día en curso. Máximo 10 min por concepto.
- Marca ✅ cuando respondas la autoprueba sin mirar. Si no te sale, anota la duda en *Mis notas* y sigue con el código.
- Los bloques de días futuros son un mapa, no tarea previa.

## D1 · Inferencia (ya visto)
- [x] **Token y `max_tokens`**: el tope limita razonamiento + respuesta juntos. *¿Por qué `max_tokens=5` dio contenido vacío? (F-01)*
- [x] **`finish_reason`** (`stop` / `length`): *¿qué significa `length` para la calidad de la respuesta?*
- [x] **TTFT vs latencia total**: *¿qué medía cada una en tu script y qué dejaba fuera? (F-02)*
- [x] **p50 / p95**: *¿por qué con n = 5 el p95 es el máximo?*
- [x] **Streaming**: el resultado llega en fragmentos.
- [x] **Backoff exponencial con jitter** y errores reintentables (429, 5xx, conexión): *¿por qué se añade jitter?*

Mis notas:

## D2 · Structured outputs
- [ ] **Roles de mensaje** (`system`, `user`, `assistant`). *¿Qué cambia si pones el documento dentro del `system`?*
- [ ] **JSON Schema** (`type`, `required`, `enum`, `additionalProperties`). *¿Cómo restringes `severity` a SEV1–SEV4?*
- [ ] **Pydantic**: valida forma y tipos, no intención. *¿Qué hace `extra="forbid"`? ¿Qué es la coerción y por qué importa en modo estricto?*
- [ ] **Modos de salida estructurada**: `json_object`, `json_schema` con `strict: false` y con `strict: true` (*constrained decoding*). *¿Qué garantiza cada uno y qué no?*
- [ ] **Prompt injection directa e indirecta**. *¿Por qué `inj-01` es indirecta?*
- [ ] **Separar instrucciones y datos**: rol, delimitadores, aviso explícito. *¿Un delimitador solo basta?*
- [ ] **Reintento de reparación**: reenviar el error de validación. *¿Qué riesgo hay en devolverle texto del documento?*
- [ ] **Truncado**: `finish_reason="length"` ≠ respuesta inválida. *¿Cómo los distingues sin parsear?*
- [ ] **Gold y canario**: ver `data/d02/README.md`. *¿Qué mide cada uno que Pydantic no puede medir?*
- [ ] **Higiene de logs**. *¿Qué puedes registrar para depurar sin guardar el texto del documento?*

Mis notas:

## D3 · Chunking, embeddings y coseno
- [ ] **Embedding**: vector que representa el significado de un texto. *¿Por qué dos textos parecidos quedan cerca?*
- [ ] **Similitud coseno** y normalización de vectores. *¿Qué pasa con el coseno si los vectores ya tienen norma 1?*
- [ ] **Chunking y overlap**. *¿Qué se rompe si un chunk corta una frase clave por la mitad?*
- [ ] **Top-k**.
- [ ] **hit@k y MRR**. *Si el chunk correcto sale tercero, ¿cuánto vale cada métrica?*
- [ ] **Prefijos de consulta y de pasaje** en los modelos e5. *¿Qué pasa si no los usas?*
- [ ] **Caché por hash de contenido**. *¿Qué entra al hash?*

Mis notas:

## D4 · ChromaDB y ablación
- [ ] **Base vectorial** y búsqueda aproximada (idea de HNSW). *¿Qué cambias de exactitud por velocidad?*
- [ ] **Metadatos y filtros** (`source`, `section`, `doc_hash`).
- [ ] **Indexación idempotente**. *¿Qué ocurre al indexar dos veces el mismo documento?*
- [ ] **Ablación**: variar una sola variable por experimento. *¿Por qué no cambiar tamaño y overlap a la vez?*

Mis notas:

## D5 · RAG
- [ ] **RAG**: recuperar y luego generar con ese contexto.
- [ ] **Citas y groundedness**. *¿Cómo compruebas que la respuesta sale de los chunks?*
- [ ] **Abstención** ("no lo sé"). *¿Qué señal usas para decidir abstenerte?*
- [ ] **Alucinación vs. falta de contexto**. *¿Cómo distingues una de la otra?*
- [ ] **Injection indirecta vía chunks** (lo visto en D2, ahora con tus documentos).

Mis notas:

## D6 · Tool calling y agentes
- [ ] **Tool calling**: el modelo propone la llamada, tu código la ejecuta. *¿Quién ejecuta realmente la función?*
- [ ] **Ciclo del agente** y condiciones de parada. *¿Qué evita un bucle infinito?*
- [ ] **Validar los argumentos** que propone el modelo. *¿Por qué no confiar en ellos?*
- [ ] **Crecimiento del historial**. *¿Qué pasa con los tokens en cada vuelta?*
- [ ] **Qué devolver al modelo cuando una tool falla**.

Mis notas:

## D7 · Tools con efectos y guardrails
- [ ] **Exceso de agencia** y **mínimo privilegio**.
- [ ] **Allowlist**. *¿Por qué mejor que una lista de bloqueo?*
- [ ] **Confirmación humana** y dónde vive la política (código, no prompt).
- [ ] **Límite de confianza**: qué entra por chunks, resultados de tools y usuario.
- [ ] **Audit log**.

Mis notas:

## D8 · Gestión de contexto
- [ ] **Ventana de contexto** y presupuesto de tokens.
- [ ] **"Lost in the middle"**. *¿Por qué importa la posición de un dato?*
- [ ] **Contar tokens** con el tokenizador y con `usage`.
- [ ] **Ventana deslizante y resumen**. *¿Qué se pierde al resumir?*
- [ ] **Prompt caching** (opcional).

Mis notas:

## D9 · Evals
- [ ] **Chequeos deterministas** vs **LLM-as-judge**.
- [ ] **Rúbrica** y calibración con casos etiquetados a mano.
- [ ] **Sesgos del juez**: posición, verbosidad, preferencia por su propio estilo.
- [ ] **Acuerdo entre etiquetadores** (porcentaje, kappa). *¿Por qué 80% de acuerdo puede engañar?*
- [ ] **Varianza y tests inestables**. *¿Por qué correr el eval dos veces?*
- [ ] **Umbral y exit code** para usarlo como gate en CI.

Mis notas:

## D10 · Observabilidad
- [ ] **Traza y span**; `trace_id`. *¿Qué spans tendría una consulta RAG?*
- [ ] **Atributos útiles** (modelo, tokens, latencia, costo, hash del prompt, error).
- [ ] **Cardinalidad**. *¿Por qué no usar el texto de la pregunta como etiqueta?*
- [ ] **Redacción y retención** de datos sensibles en trazas.
- [ ] **OpenTelemetry GenAI** (opcional).

Mis notas:
