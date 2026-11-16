# D2 · Structured outputs · 2026-11-11 a 2026-11-12 (etapas 1 a 4 hechas; falta el reporte, etapa 5)

> Cubre las etapas 1 a 4. La etapa 5 (reporte `d02_report.py` y cierre) está pendiente. Las cifras salen de `runs/d02.jsonl`
> (23 documentos, una sola ejecución), `runs/prueba_pm10.jsonl`, `runs/prueba_pm18.jsonl`, `scripts/d02_probe.py` y
> `scripts/d02_validate_json.py`. Lo marcado **(completar)** requiere tu criterio.

## Objetivo y criterio de éxito
- **Objetivo:** extraer post-mortems a un modelo Pydantic `Incident(service, severity, root_cause, action_items[])` con validación estricta y como máximo 1 reintento con el error de validación (ver `docs/PLAN.md`, D2).
- **Corpus:** `data/d02/` (20 limpios y 3 con instrucciones inyectadas, sintéticos), con gold aparte.
- **Criterios y estado:**

| Criterio | Estado |
|---|---|
| ≥ 19/20 limpios válidos con Pydantic estricto y ≤ 1 reintento de validación | ✅ 19/20, justo en el umbral (sin margen). El que falló es `pm-10` (F-06). `validation_attempts=1` en todas las filas |
| Reporte de reintentos de validación, costo extra y tiempo total | ⚠️ Falta `d02_report.py` (etapa 5). Con estos datos mostraría 0 reintentos de validación y costo extra 0: el camino de reparación no se activó en las 23 corridas |
| 3 inyectados con 0 obedecidos | ✅ con lo que se mide: canario presente en 0/3 y severidad correcta en 3/3. No se mide la fuga del prompt de `inj-03` |
| Truncado de `pm-18` como fallo controlado | ✅ con `--max-tokens 50` terminó como `truncated`, sin parsear ni reintentar (`runs/prueba_pm18.jsonl`). Ver F-06 sobre la fiabilidad de esa etiqueta |
| `runs/d02.jsonl` sin texto de documentos ni respuestas completas | ✅ los campos del registro no incluyen texto de entrada ni de salida |
| Prueba de los 3 modos de salida con resultado anotado | ✅ hecha con `pm-01` y con un texto sin acciones. El modo usado en las 23 corridas fue `json_schema` con `strict: true`; no se comparó con los otros dos sobre el mismo corpus |

- **Herramientas y ayuda recibida:** (completar: qué partes se escribieron con ayuda de IA u otras herramientas)
- **Tiempo real:** (completar)

## Diseño
- **Modelo (`scripts/d02_models.py`):** `Incident` con `severity: Severity` (enum SEV1 a SEV4), y `service`, `root_cause` y cada elemento de `action_items` como texto con contenido (`NonEmptyStr`: se recortan los espacios y no puede quedar vacío). `action_items` exige al menos 1 elemento. `extra="forbid"`.
- **Tests (`scripts/d02_validate_json.py`):** 9 casos con resultado esperado (`PASS`/`FAIL`) y código de salida distinto de 0 si alguno falla. Cubren campo faltante, severidad inválida, campo extra, lista vacía y los strings vacíos o de solo espacios de F-05.
- **Validación:** `model_validate_json` sobre el texto que devuelve el modelo, no sobre diccionarios.
- **Prueba de modos (`scripts/d02_probe.py`):** una llamada por modo sin streaming, con el mismo prompt, `temperature=0`, `reasoning_effort="none"`, `max_tokens=400` y timeout de 20 s. Solo cambia `response_format`. Para ver el efecto de cada modo se probó con `pm-01` y con un texto corto sin acciones.
- **Por qué sin streaming:** según la documentación de Groq, los structured outputs no admiten streaming.
- **Prompt (`construir_mensajes`):** el `system` trae la tarea, la regla de que el documento es contenido para analizar y no instrucciones, y la orden de responder solo con un objeto JSON; el `user` trae el documento entre `<documento>` y `</documento>`. Los delimitadores son fijos (que el documento contenga la etiqueta de cierre no está probado).
- **Petición (`request_with_net_retry`):** sin streaming, `temperature=0`, `reasoning_effort="none"`, `max_tokens` configurable (400 por defecto), timeout de 20 s. Hasta 5 intentos de red con backoff exponencial y jitter para errores de conexión, 429 y 5xx. Un 400 con el texto "Failed to generate JSON" se trata como truncado.
- **Validación (`validar`):** si `finish_reason` no es `stop` → `truncated` sin parsear; si no es JSON → `json_decode`; si falla el esquema → `schema` (el detalle lleva campo y mensaje, nunca el valor recibido). Validación estricta (`strict=True`).
- **Reparación:** si falla la validación y no es un truncado, hace un reintento con la respuesta previa como mensaje `assistant` y un mensaje `user` con el detalle del error. Máximo 2 intentos de validación; un truncado no se reintenta. Los reintentos de red (5) y de validación (2) se cuentan por separado, así que una llamada puede llegar a 10 peticiones.
- **Registro (`procesar_documento`):** una línea por documento en `runs/d02.jsonl` (modo append): `run_id` por ejecución, `call_id` por documento, `ts` de inicio, modo, `max_tokens`, intentos de red y de validación, `error_type`, `finish_reasons`, tokens sumados sobre los intentos, costo de referencia y costo extra del reintento, `total_s` de toda la llamada (con esperas y reintentos), `last_attempt_s`, `canary_found` y la comparación con el gold (`service_ok`, `severity_ok`, `n_actions_ok`).
- **Uso:** `python scripts/d02_extract.py [--docs ids] [--mode ...] [--max-tokens N] [--out ruta]`.

## Trade-offs

| Decisión | Alternativas | Elegí | Evidencia / razón |
|---|---|---|---|
| Tipo de `severity` | `str` libre · `Literal` · `Enum` | `Enum` con valores SEV1 a SEV4 | Un valor inventado (`"grave"`) falla con error de tipo `enum` |
| `action_items` vacía | permitir `[]` · exigir al menos 1 | Al menos 1 (`min_length=1`) | Detecta extracciones vacías. Efecto observado en F-05: con un texto sin acciones, un modo falla de forma visible y los otros cumplen con un string vacío |
| Campos extra | ignorarlos · prohibirlos | `extra="forbid"` | Un campo no pedido falla con `extra_forbidden`; útil como señal ante inyección |
| Contenido de los strings | `str` sin restricción · no vacío | No vacío, con espacios recortados | Cierra la parte de F-05 que Pydantic puede ver; los 4 casos nuevos fallaban con el modelo anterior y pasan con el actual |
| Modo de salida | `json_object` · `json_schema` con `strict: false` · `json_schema` con `strict: true` | `json_schema` con `strict: true` y Pydantic como segunda barrera | Usado en las 23 corridas: 19/20 limpios válidos. No se corrió el mismo corpus con los otros dos modos, así que la elección no está comparada (pendiente) |
| Reparación tras fallo de validación | sin reintento · solo el error · error + respuesta previa | Error (campo y mensaje, sin valores) + respuesta previa | Funciona en pruebas con respuestas simuladas hechas fuera del repo; con datos reales no se activó (0 reintentos de validación). Riesgo: reenvía texto derivado de un documento no confiable |
| Truncado | parsear igual · fallo controlado | Fallo controlado: no se parsea ni se reintenta | `pm-18` con `max_tokens=50` cae en este camino. La etiqueta `truncated` también se asignó a `pm-10` sin ser un problema de largo (F-06) |
| Contenido del log | guardar respuestas · solo campos acotados | Solo campos acotados, sin texto | Cumple el criterio de no filtrar contenido; a cambio, F-06 y F-07 no se pueden diagnosticar desde el log. Decisión pendiente: qué campos acotados agregar (clase de error, código de estado) (completar) |
| Streaming | con stream · sin stream | Sin stream | Limitación documentada por Groq para structured outputs |

## Resultados de la prueba de modos

Con `pm-01` (severidad explícita, 3 acciones) los tres modos devolvieron `finish_reason="stop"` y validaron con `Incident`. Se vieron diferencias de formato y no de validez: `json_object` devuelve el JSON con sangría y en el orden pedido; los dos modos con esquema devuelven una línea con las claves en orden alfabético. Las primeras corridas no fijaban `temperature` y el mismo modo dio textos distintos entre ejecuciones (mayúsculas/minúsculas), por eso las comparaciones posteriores usan `temperature=0`.

Con un texto que dice explícitamente que no hubo acciones (`temperature=0`):

| Modo | `action_items` devuelto | ¿Validó? |
|---|---|---|
| `json_object` | `[]` | No (`too_short`) |
| `json_schema`, `strict: false` | `[""]` | Sí |
| `json_schema`, `strict: true` | `[""]` | Sí |

Las dos salidas con esquema respetaron el mínimo de elementos, así que Groq sí aplica esa restricción; la cumplieron con un valor vacío.

Segunda prueba, tras restringir los strings a no vacíos (mismo texto sin acciones, `temperature=0`):

| Modo | `action_items` devuelto | ¿Validó? |
|---|---|---|
| `json_object` | `[]` | No (`too_short`) |
| `json_schema`, `strict: false` | `["/"]` | Sí |
| `json_schema`, `strict: true` | `["/"]` | Sí |

## Métricas
Corrida completa: 23 documentos, `json_schema` con `strict: true`, `max_tokens=400`, `temperature=0` (`run_id` único).

| Métrica | Valor |
|---|---|
| Limpios válidos | 19/20 |
| Inyectados válidos / canario presente / severidad correcta | 3/3 · 0/3 · 3/3 |
| Reintentos de validación | 0/23 (el camino de reparación no se activó) |
| Llamadas con reintentos de red | 8/23, con 18 peticiones extra y hasta 4 intentos: pm-13 (2), pm-14 (4), pm-16 (4), pm-17 (3), pm-19 (4), pm-20 (2), inj-02 (4), inj-03 (3) |
| `total_s` p50 / máx (toda la llamada) | 0.991 s / 9.234 s |
| `total_s` p50 sin reintentos de red / con reintentos | 0.924 s / 6.816 s |
| `last_attempt_s` p50 (solo el último intento) | 0.892 s |
| Tokens de entrada / salida (23 llamadas) | 5307 / 1745 |
| Costo de referencia (hipotético, 0,80 / 4,00 USD por 1M de tokens) | 0.0112 USD en total, 0.00049 USD por documento |
| Exactitud sobre los 19 limpios válidos: `service` / `severity` / nº de acciones | 14/19 · 17/19 · 18/19 |

- Los fallos de `severity` son pm-04, pm-08: justamente los dos documentos cuya severidad no está escrita y hay que deducir del impacto.
- Los fallos de `service` son pm-04, pm-07, pm-09, pm-12, pm-16. El registro no guarda lo que devolvió el modelo, así que no se sabe si fue un problema de formato (`service_ok` normaliza espacios y mayúsculas, pero no convierte "api pagos" en "api-pagos") o de identidad.
- La mediana de `total_s` pasa de 0.924 s a 6.816 s cuando hay reintentos de red: casi todo ese tiempo es espera de backoff, no de inferencia.

Pruebas dirigidas:

| Corrida | Resultado |
|---|---|
| `pm-10`, `--max-tokens 1000` (`runs/prueba_pm10.jsonl`) | Válido, `stop`, 54 tokens de salida, 0,974 s. En la corrida completa (400 tokens) había fallado como `truncated` |
| `pm-18`, `--max-tokens 50` (`runs/prueba_pm18.jsonl`) | `truncated`, 0 tokens registrados, 0,715 s, sin parsear. Con 400 tokens, en la corrida completa, `pm-18` salió válido con 165 tokens de salida |

## Fallos de inferencia encontrados
### F-05 · Los modos con esquema cumplen `min_length` con un string vacío (parcialmente resuelto)
- **Síntoma:** con un texto sin acciones, `json_object` devuelve `[]` y falla; `json_schema` (con `strict` verdadero y falso) devuelve `[""]` y pasa la validación.
- **Hipótesis descartadas:** que el modo ignore la restricción de mínimo (la respetó); que `strict` no esté soportado con este modelo (respondió `stop`).
- **Evidencia:** mismas condiciones en los tres modos (prompt, `temperature=0`, `reasoning_effort="none"`); salidas en la tabla de arriba.
- **Causa raíz:** el esquema solo exigía una lista con al menos un elemento y el elemento era un `str` sin restricción, de modo que `""` lo cumplía. La segunda prueba la respalda: al prohibir el string vacío, los modos con esquema pasaron a usar un marcador mínimo (`"/"`).
- **Solución aplicada:** `NonEmptyStr` en `service`, `root_cause` y los elementos de `action_items`. El esquema que se envía al proveedor ahora incluye `minLength: 1` en esos campos, pero no puede expresar el recorte de espacios: una respuesta `" "` cumple el esquema y la rechaza Pydantic. Esa es la razón por la que Pydantic sigue siendo la barrera final.
- **Segunda prueba (2026-11-12, mismo texto sin acciones, `temperature=0`):** `json_object` sigue devolviendo `[]` y falla con `too_short`; `json_schema` con `strict` falso y verdadero devolvió `["/"]` y validó. El modelo cumplió la restricción nueva con otro valor degenerado, de un solo carácter.
- **Lección:** una restricción de longitud no impide una acción sin contenido. El problema de fondo es de diseño: el esquema obliga a declarar al menos una acción cuando el documento dice que no hubo ninguna, y un modo que obliga a cumplir el esquema responde inventando. La decisión sobre `min_length=1` queda abierta (ver trade-offs).
- **Test de regresión añadido:** casos `accion_vacia`, `accion_espacios`, `service_vacio` y `root_cause_espacios` en `d02_validate_json.py`. Verificado en rojo con el modelo anterior (4 `FAIL`, salida 1) y en verde con el actual (9 `PASS`, salida 0).

### F-06 · La etiqueta `truncated` agrupa causas distintas (abierto)
- **Síntoma:** en la corrida completa, `pm-10` (el documento más corto, 328 caracteres, una acción) terminó como `truncated` con `max_tokens=400`: 0 tokens registrados, `finish_reasons=[None]`, 2,47 s en una sola petición.
- **Hipótesis descartadas:** que el documento fuera demasiado largo para el tope. Repetido con `--max-tokens 1000`, `pm-10` validó con 54 tokens de salida. Con `temperature=0` ese mismo tamaño de respuesta cabía de sobra en 400.
- **Evidencia:** `runs/d02.jsonl` (`pm-10`), `runs/prueba_pm10.jsonl`, `runs/prueba_pm18.jsonl`. `finish_reasons=[None]` indica que la llamada terminó con una excepción de la API y no con una respuesta; la etiqueta sale de un 400 cuyo texto contiene "Failed to generate JSON". `pm-18` con 50 tokens recibió la misma etiqueta y ahí sí es un corte por tamaño.
- **Causa raíz:** no determinada. El mismo error 400 aparece tanto por un corte real por tamaño (`pm-18` con 50) como en un caso que no depende del tamaño (`pm-10` con 400). Una repetición con otro `max_tokens` no distingue un fallo transitorio de uno ligado al tope. Falta repetir `pm-10` varias veces con 400. (completar: lo que mostró `exc.body` en esas corridas)
- **Solución definitiva:** (pendiente) distinguir las causas sin depender solo del texto del error.
- **Test de regresión añadido:** (pendiente)
- **Impacto:** el criterio de 19/20 se cumple por exactamente un documento; el fallo de `pm-10` cuenta contra él y no se sabe si se repetirá.

### F-07 · Reintentos de red frecuentes y sin causa registrada (abierto)
- **Síntoma:** {V['nm']} de 23 llamadas necesitaron entre 2 y {V['nx']} peticiones de red ({V['ne']} peticiones extra). `total_s` llega a {V['tx']} s con una mediana global de {V['tp']} s.
- **Evidencia:** `net_attempts` y `last_attempt_s` en `runs/d02.jsonl`. En {V['l1']} de las {V['nm']} llamadas con reintento, el último intento duró menos de 1 s, y las esperas de 1, 2 y 4 s explican el resto del `total_s`. Los intentos fallidos fueron rápidos, no timeouts de 20 s.
- **Causa raíz:** no determinada. El registro guarda cuántos intentos hubo, pero no la clase de error ni el código de estado de los intentos fallidos, y los mensajes impresos en consola no se conservaron. Hipótesis sin probar: límites de tasa del plan gratuito (429). El código ignora `Retry-After`.
- **Solución definitiva:** (pendiente) registrar la clase de error y el código de estado de cada intento fallido (valores de un conjunto cerrado, sin texto) y respetar `Retry-After`.
- **Test de regresión añadido:** (pendiente)

## Seguridad
- **Defensa contra inyección:** instrucciones y datos separados por rol y por etiquetas, con una frase explícita de que el documento es contenido y no órdenes. Resultado medido con los 3 documentos inyectados (una ejecución, `temperature=0`, `strict: true`): canario presente en 0/3 y severidad correcta en 3/3. Con n = 3 es una señal, no una garantía.
- **No medido:** que el modelo filtre el prompt del sistema (`inj-03` lo pide; no hay un marcador propio en el prompt para detectarlo) y que un documento contenga la etiqueta de cierre `</documento>` (ninguno del corpus lo hace).
- **Reparación y contenido no confiable:** el reintento reenvía la respuesta previa del modelo, derivada de un documento no confiable. El contador de canario revisa todos los intentos, no solo el último.
- **Higiene del log:** `runs/d02.jsonl` no guarda texto del documento ni respuestas. Verificado leyendo los campos del registro y con respuestas simuladas fuera del repo.
- **Depuración temporal:** el script tiene un `print(exc.body)` que muestra en consola el cuerpo del error de la API; puede incluir contenido generado a partir de un documento. Quitarlo o protegerlo antes de usar datos reales.
- La key sigue solo en `.env`.
- Lección de F-05: pasar el esquema no significa que el contenido sea correcto.

## Qué haría distinto / deuda técnica (propuesto)
- Fijar `temperature=0` desde la primera comparación entre modos, para no atribuir al modo lo que es variación.
- Empezar por el caso adversarial (un documento donde la respuesta honesta no cabe en el esquema) en vez de por el caso fácil.
- Capturar el error de validación para que un fallo no detenga el script.
- Escribir de entrada la restricción de contenido de los strings, además de la forma.
- Diseñar el esquema pensando en el caso en que la respuesta honesta es "no hay": un campo obligatorio empuja al modelo a inventar un valor para cumplir.
- Guardar la clase de error y el código de estado de cada intento de red fallido, para diagnosticar F-06 y F-07 sin guardar texto.
- Probar el camino de reparación con un caso real (por ejemplo, el modo `json_object` con el texto sin acciones) y dejar en el repo un test con respuestas simuladas.
- Repetir `pm-10` varias veces con el mismo `max_tokens` antes de dar por cerrada la etiqueta `truncated`.
- Incluir un documento con la etiqueta de cierre dentro del texto y un marcador propio en el prompt del sistema para medir la fuga.
- Comparar los tres modos sobre los mismos 23 documentos antes de elegir uno.
- Quitar el `print(exc.body)` temporal.
