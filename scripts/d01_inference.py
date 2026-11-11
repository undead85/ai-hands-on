# D1 · Etapa 1: llamadas con streaming, medición básica y registro en JSONL.
import json
import os
import random
import time
import uuid
from datetime import UTC, datetime

from dotenv import load_dotenv
from openai import APIConnectionError, APIStatusError, OpenAI

load_dotenv()

TIMEOUT_S = 0.4
client = OpenAI(
    base_url=os.environ["LLM_BASE_URL"],
    api_key=os.environ["LLM_API_KEY"],
    max_retries=0,
    timeout=TIMEOUT_S,
)

MODEL = os.environ["LLM_MODEL"]
PROMPT = "Explica en un párrafo corto qué es la inferencia de un LLM."
MAX_TOKENS = 200
REASONING_EFFORT = "none"  # none, minimal, low, medium, high, xhigh, and max
TEMPERATURES = [0, 1.0]
RUNS_PER_TEMPERATURE = 5
OUT_PATH = "runs/d01.jsonl"
MAX_ATTEMPTS = 5
BASE_DELAY_S = 1.0  # espera: 1, 2, 4, 8 s... + jitter
JITTER_S = 0.5

# Precio de referencia (hipotético): Qwen/Qwen3.8-27B, USD por 1M de tokens.
# Fuente: tabla de precios del proveedor, consultada el 2026-11-09.
PRICE_IN_PER_M = 0.80
PRICE_OUT_PER_M = 4.00


def cost_ref_usd(input_tokens, output_tokens):
    if input_tokens is None or output_tokens is None:
        return None
    cost = input_tokens * PRICE_IN_PER_M + output_tokens * PRICE_OUT_PER_M
    return round(cost / 1_000_000, 8)


def run_once(temperature):
    usage = None
    finish_reason = None
    t_first = None
    output_chars = 0

    t_start = time.perf_counter()
    stream = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT}],
        max_tokens=MAX_TOKENS,
        temperature=temperature,
        extra_body={"reasoning_effort": REASONING_EFFORT},
        stream=True,
        stream_options={"include_usage": True},
    )

    for chunk in stream:
        # El último fragmento trae el usage y choices vacío.
        if chunk.usage is not None:
            usage = chunk.usage
        if not chunk.choices:
            continue
        choice = chunk.choices[0]
        if choice.finish_reason:
            finish_reason = choice.finish_reason
        text = choice.delta.content
        if text:
            if t_first is None:
                t_first = time.perf_counter()
            output_chars += len(text)
            print(text, end="", flush=True)
    t_end = time.perf_counter()
    print()

    input_tokens = usage.prompt_tokens if usage else None
    output_tokens = usage.completion_tokens if usage else None
    return {
        "ttft_s": round(t_first - t_start, 3) if t_first is not None else None,
        "latency_s": round(t_end - t_start, 3),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "finish_reason": finish_reason,
        "cost_ref_usd": cost_ref_usd(input_tokens, output_tokens),
        "output_chars": output_chars,
    }


def is_retryable(exc):
    # Timeout y error de conexión (APITimeoutError hereda de APIConnectionError).
    if isinstance(exc, APIConnectionError):
        return True
    # 429 y 5xx son pasajeros; 400/401/403/404 y el resto no se reintentan.
    if isinstance(exc, APIStatusError):
        return exc.status_code == 429 or exc.status_code >= 500
    return False


def run_with_retry(temperature):
    # Campos comunes a éxito y fallo; run_id y ts se fijan una vez por corrida.
    base = {
        "run_id": uuid.uuid4().hex[:8],
        "ts": datetime.now(UTC).isoformat(),
        "model": MODEL,
        "temperature": temperature,
        "max_tokens": MAX_TOKENS,
        "reasoning_effort": REASONING_EFFORT,
        "timeout_s": TIMEOUT_S,
    }
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            metrics = run_once(temperature)
            return {**base, **metrics, "attempts": attempt, "error": None}
        except Exception as exc:  # noqa: BLE001
            if not is_retryable(exc) or attempt == MAX_ATTEMPTS:
                # Intentos agotados (o error no reintentable): registro de
                # fallo con el mismo esquema, en vez de abortar.
                return {
                    **base,
                    "ttft_s": None,
                    "latency_s": None,
                    "input_tokens": None,
                    "output_tokens": None,
                    "finish_reason": None,
                    "cost_ref_usd": None,
                    "output_chars": None,
                    "attempts": attempt,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            delay = BASE_DELAY_S * 2 ** (attempt - 1) + random.uniform(0, JITTER_S)
            print(
                f"\n[intento {attempt}/{MAX_ATTEMPTS} falló: {type(exc).__name__}: {exc}] "
                f"reintentando en {delay:.2f} s"
            )
            time.sleep(delay)


os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

for temperature in TEMPERATURES:
    for i in range(RUNS_PER_TEMPERATURE):
        print(f"--- temperature={temperature} · corrida {i + 1}/{RUNS_PER_TEMPERATURE}")
        result = run_with_retry(temperature)
        print(result)
        with open(OUT_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
