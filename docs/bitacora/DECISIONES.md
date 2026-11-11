# Decisiones de arquitectura (mini-ADR)

Formato por decisión: contexto · opciones (pros/contras) · decisión · consecuencias.

## ADR-001 · Embeddings locales (multilingual-e5-small)
- Fecha: 2026-11-07
- Contexto: corpus en español, sin depender de un segundo proveedor ni enviar datos fuera.
- Opciones: A local (sentence-transformers) · B API (Voyage/OpenAI) · C Ollama.
- Decisión: A.
- Consecuencias: descarga inicial del modelo y primera ejecución más lenta en CPU; reproducible y sin costo por llamada.

## ADR-002 · Proveedor de LLM sin presupuesto: adaptador OpenAI-compatible
- Fecha: 2026-11-09 · Estado: aceptada tras el D1 (30 llamadas a Groq; los únicos errores fueron los provocados con timeout de 1 ms, sin 429 ni 5xx)
- Contexto: sin presupuesto para APIs de pago; PC con 8 GB de RAM y poca memoria libre en uso normal.
- Opciones: A Ollama local (gratis, sin rate limits; riesgo de swap con modelos > ~1–2B) · B Groq free tier (sin costo, rápido; rate limits por organización y por modelo) · C Gemini free tier (límites cambiantes; las requests pueden usarse para mejorar productos de Google).
- Decisión: código contra la API de chat completions compatible con OpenAI; proveedor por variables de entorno. Base: B. A como comparación opcional con un modelo muy pequeño.
- Consecuencias: el costo real es $0, por eso se reporta costo de referencia, tokens y tiempo. Los rate limits (429) son reales y se vuelven parte del diseño (backoff, caché de respuestas en evals).

## ADR-003 · Reintentos con wrapper propio y `max_retries=0`
- Fecha: 2026-11-09 · Estado: aceptada (con mejoras pendientes)
- Contexto: el SDK de OpenAI reintenta por defecto 2 veces con su propio backoff; se necesitaba registrar cuántos intentos hizo cada llamada y controlar la política (qué errores, cuántos intentos, qué espera).
- Opciones:
  - A. Usar el reintento del SDK. ✅ Menos código, probado. ❌ No expone `attempts`, la política es la del SDK y no queda en el registro.
  - B. `max_retries=0` y wrapper propio. ✅ Registra `attempts`, define errores reintentables y backoff con jitter. ❌ Más código que mantener, y hay que cubrir `Retry-After` y un tope de tiempo total.
  - C. Ambas capas. ❌ Los intentos se multiplican (hasta 3 × 5 por llamada) y las métricas se vuelven ininterpretables.
- Decisión: B.
- Consecuencias: cada registro lleva `attempts` y `error`. Quedan abiertos F-02 (medir la llamada completa) y las mejoras de tope de tiempo total y `Retry-After`. La política de timeouts de producción queda por decidir con una muestra mayor (propuesta: ~2 s).
