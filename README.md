# ai-hands-on

Plan intensivo de 2 semanas (lun–vie, 45 min/día) para dominar los patrones base de un AI Engineer:
inferencia, structured outputs, embeddings, RAG desde cero, tool calling, contexto, evals y observabilidad.

**Proyecto acumulativo:** asistente de runbooks DevOps. Cada día extiende el anterior.

- Plan día a día y criterios medibles: [`docs/PLAN.md`](docs/PLAN.md)
- Conceptos por día con autopruebas: [`docs/CONCEPTOS.md`](docs/CONCEPTOS.md)
- Bitácora técnica: [`docs/bitacora/`](docs/bitacora/)
- Catálogo de fallos de inferencia: [`docs/bitacora/FALLOS.md`](docs/bitacora/FALLOS.md)
- Decisiones de arquitectura: [`docs/bitacora/DECISIONES.md`](docs/bitacora/DECISIONES.md)

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Luego edita `.env` y completa `LLM_API_KEY` y `LLM_MODEL` (el archivo trae comentarios para Groq y Ollama). Nunca subas `.env` a git.

Notas:
- Si PowerShell bloquea `Activate.ps1`, ejecuta antes `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` (solo afecta a esa ventana).
- `requirements.txt` es la base (D1–D2). Los paquetes pesados de embeddings (`sentence-transformers`, que trae torch, y `chromadb`) están aparte y se instalan recién en el D3: `pip install -r requirements-rag.txt`.

## Estructura

```
corpus/          runbooks .md (entrada del RAG)
src/aihands/     módulos reutilizables (llm, schemas, chunking, embed, retriever, rag, tools, agent, context, tracing)
scripts/         un script ejecutable por día: dXX_*.py
evals/           golden.jsonl y run_evals.py
runs/            métricas JSONL de cada ejecución (ignoradas por git salvo muestras_*.jsonl)
tests/           pruebas de regresión
docs/bitacora/   una entrada por día + FALLOS.md + DECISIONES.md
```

## Progreso

| Día | Tema | Estado |
|---|---|---|
| D1 | Inferencia bajo el capó | ✅ (con deuda: F-02 a F-04) |
| D2 | Structured outputs | 🟡 en curso |
| D3 | Chunking, embeddings y cosine pura | ⬜ |
| D4 | ChromaDB y ablación de chunking | ⬜ |
| D5 | RAG end-to-end | ⬜ |
| D6 | Tool calling manual | ⬜ |
| D7 | Tools con efectos y guardrails | ⬜ |
| D8 | Gestión de contexto | ⬜ |
| D9 | Evals | ⬜ |
| D10 | Observabilidad y cierre | ⬜ |
