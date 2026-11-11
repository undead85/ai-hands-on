# D1 · Verificación y reporte sobre runs/d01.jsonl (solo lectura).
# Uso: python scripts/d01_report.py [ruta.jsonl]
import itertools
import json
import os
import re
import statistics
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(
    encoding="utf-8"
)  # evita caracteres rotos en consolas de Windows
ROOT = Path(__file__).resolve().parent.parent
PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "runs" / "d01.jsonl"

REQUIRED = [
    "run_id",
    "ts",
    "model",
    "temperature",
    "max_tokens",
    "reasoning_effort",
    "timeout_s",
    "ttft_s",
    "latency_s",
    "input_tokens",
    "output_tokens",
    "finish_reason",
    "cost_ref_usd",
    "attempts",
    "output_chars",
]
CONFIG_KEYS = ["model", "max_tokens", "reasoning_effort", "timeout_s"]
N_PROJECTION = 10_000
MAX_ATTEMPTS = 5
BACKOFF_MIN_S = 1 + 2 + 4 + 8  # espera acumulada de 5 intentos (sin jitter)
BACKOFF_MAX_S = BACKOFF_MIN_S + 0.5 * 4 + 2.0  # jitter máx. + margen de ejecución


def title(text):
    print(f"\n=== {text} ===")


def verdict(ok):
    return "OK" if ok else "FALLA"


def p50(values):
    return statistics.median(values)


# ---------------------------------------------------------------- carga
if not PATH.exists():
    sys.exit(f"No existe {PATH}")

records, bad_lines = [], []
for n, line in enumerate(PATH.read_text(encoding="utf-8").splitlines(), start=1):
    if not line.strip():
        continue
    try:
        rec = json.loads(line)
    except json.JSONDecodeError:
        bad_lines.append(n)
        continue
    rec["_line"] = n
    records.append(rec)

print(f"Archivo: {PATH}")
print(f"Líneas parseadas: {len(records)} · líneas con JSON inválido: {len(bad_lines)}")


def is_valid(r):
    """Registro válido: esquema completo, sin error y con métricas presentes."""
    if any(k not in r for k in REQUIRED):
        return False
    if r.get("error") is not None:
        return False
    metrics = ["ttft_s", "latency_s", "input_tokens", "output_tokens", "cost_ref_usd"]
    return all(r[k] is not None for k in metrics) and r["finish_reason"] is not None


valid = [r for r in records if is_valid(r)]
failed = [r for r in records if r.get("error") is not None]
incomplete = [r for r in records if r.get("error") is None and not is_valid(r)]

# ------------------------------------------- 1. registros válidos y atribución
title("1. Registros válidos atribuibles a su corrida y configuración")
run_ids = [r["run_id"] for r in records if "run_id" in r]
dup_ids = {i for i in run_ids if run_ids.count(i) > 1}
print(
    f"Válidos: {len(valid)} · con error: {len(failed)} · incompletos: {len(incomplete)}"
)
print(
    f"run_id duplicados: {len(dup_ids)} · registros sin run_id/ts: "
    f"{sum(1 for r in records if 'run_id' not in r or 'ts' not in r)}"
)

groups = defaultdict(list)
for r in valid:
    groups[tuple(r[k] for k in CONFIG_KEYS)].append(r)

print("\nConfiguraciones distintas (cada registro se asigna por su propia config):")
for cfg, rs in groups.items():
    per_temp = defaultdict(int)
    for r in rs:
        per_temp[r["temperature"]] += 1
    cfg_txt = ", ".join(f"{k}={v}" for k, v in zip(CONFIG_KEYS, cfg))
    temps = ", ".join(f"T={t}: {c}" for t, c in sorted(per_temp.items()))
    print(f"  - {cfg_txt}\n      válidos={len(rs)} ({temps})")

best = max(groups.values(), key=len, default=[])
per_temp_best = defaultdict(int)
for r in best:
    per_temp_best[r["temperature"]] += 1
ok1 = (
    len(best) >= 10
    and all(per_temp_best.get(t, 0) >= 5 for t in (0, 1.0))
    and not dup_ids
)
print(
    f"\nCriterio (>=10 válidos en una misma config, >=5 por temperatura, sin run_id "
    f"duplicados): {verdict(ok1)}"
)

# --------------------------------- 2. tabla p50 / máx de ttft y latency por T
title("2. p50 / máx de ttft y latency por temperatura (s)")
for cfg, rs in groups.items():
    print("\nConfig: " + ", ".join(f"{k}={v}" for k, v in zip(CONFIG_KEYS, cfg)))
    print(
        f"{'temp':>6} {'n':>3} | {'ttft p50':>9} {'ttft máx':>9} | "
        f"{'lat p50':>8} {'lat máx':>8}"
    )
    by_temp = defaultdict(list)
    for r in rs:
        by_temp[r["temperature"]].append(r)
    for t, trs in sorted(by_temp.items()):
        tt = [r["ttft_s"] for r in trs]
        la = [r["latency_s"] for r in trs]
        print(
            f"{t:>6} {len(trs):>3} | {p50(tt):>9.3f} {max(tt):>9.3f} | "
            f"{p50(la):>8.3f} {max(la):>8.3f}"
        )

# --------------------------------------- 3. proyección a 10.000 llamadas
title(f"3. Proyección a {N_PROJECTION:,} llamadas (media de los registros válidos)")
for cfg, rs in groups.items():
    n = len(rs)
    mean_in = sum(r["input_tokens"] for r in rs) / n
    mean_out = sum(r["output_tokens"] for r in rs) / n
    mean_lat = sum(r["latency_s"] for r in rs) / n
    mean_cost = sum(r["cost_ref_usd"] for r in rs) / n
    total_s = mean_lat * N_PROJECTION
    print(
        "\nConfig: "
        + ", ".join(f"{k}={v}" for k, v in zip(CONFIG_KEYS, cfg))
        + f"  (n={n})"
    )
    print(f"  tokens entrada : {mean_in * N_PROJECTION:>14,.0f}")
    print(f"  tokens salida  : {mean_out * N_PROJECTION:>14,.0f}")
    print(
        f"  tiempo total   : {total_s:>14,.0f} s  (~{total_s / 3600:.2f} h, en serie)"
    )
    print(f"  costo ref. USD : {mean_cost * N_PROJECTION:>14,.2f}")

# ----------------------- 4. timeout con reintento y backoff (prueba ~1 ms)
title("4. Timeout con reintento y backoff exponencial con jitter (prueba ~1 ms)")
tiny = [
    r
    for r in records
    if isinstance(r.get("timeout_s"), (int, float)) and r["timeout_s"] <= 0.01
]
tiny_fail = [r for r in tiny if r.get("error")]
print(f"Registros con timeout_s <= 10 ms: {len(tiny)} (con error: {len(tiny_fail)})")
if not tiny:
    print(
        "Sin evidencia: ejecuta d01_inference.py con TIMEOUT_S=0.001 y vuelve a correr."
    )
    ok4 = False
else:
    # Con ~1 ms el timeout suele saltar al conectar y el SDK lo reporta como
    # APIConnectionError; ambos son errores reintentables.
    all_timeouts = all(
        r["error"].startswith(("APITimeoutError", "APIConnectionError"))
        for r in tiny_fail
    )
    all_exhausted = all(r["attempts"] == MAX_ATTEMPTS for r in tiny_fail)
    kinds = sorted({r["error"].split(":")[0] for r in tiny_fail})
    print(f"Todos fallan por timeout/conexión {kinds}: {verdict(all_timeouts)}")
    print(
        f"Todos agotan {MAX_ATTEMPTS} intentos (attempts={MAX_ATTEMPTS}): "
        f"{verdict(all_exhausted)}"
    )

    # El ts es el inicio de cada corrida; el hueco hasta la siguiente incluye la
    # espera acumulada del backoff: 1+2+4+8 s (+ jitter hasta 0.5 s por espera).
    ordered = sorted(records, key=lambda r: r.get("ts", ""))
    gaps = []
    for a, b in itertools.pairwise(ordered):
        if a in tiny_fail and b in tiny_fail:  # solo corridas fallidas consecutivas
            gap = datetime.fromisoformat(b["ts"]) - datetime.fromisoformat(a["ts"])
            gaps.append(gap.total_seconds())
    in_range = [g for g in gaps if BACKOFF_MIN_S <= g <= BACKOFF_MAX_S]
    print(
        f"Espera entre corridas fallidas esperada {BACKOFF_MIN_S}-{BACKOFF_MAX_S:.1f} s: "
        f"{len(in_range)}/{len(gaps)} en rango"
        + (f" (min {min(gaps):.1f} s, máx {max(gaps):.1f} s)" if gaps else "")
    )
    if gaps:
        spread = max(gaps) - min(gaps)
        print(f"Dispersión de huecos: {spread:.2f} s (>0 indica jitter aleatorio)")
    ok4 = (
        bool(tiny_fail)
        and all_timeouts
        and all_exhausted
        and len(in_range) == len(gaps)
        and len(gaps) > 0
    )
print(f"Criterio: {verdict(ok4)}")

# --------------------------------------------- 5. finish_reason anómalo
title("5. Respuestas con finish_reason distinto de 'stop' (anómalas)")
anomalous = [
    r for r in records if r.get("error") is None and r.get("finish_reason") != "stop"
]
if anomalous:
    for r in anomalous:
        print(
            f"  ANÓMALA línea {r['_line']} run_id={r.get('run_id')} "
            f"T={r.get('temperature')} finish_reason={r.get('finish_reason')!r} "
            f"output_tokens={r.get('output_tokens')}"
        )
else:
    print("  Ninguna: todas las respuestas completadas terminaron con 'stop'.")
print(
    f"Anómalas: {len(anomalous)} de {len(records) - len(failed)} respuestas sin error"
)

# -------------------------------------------- 6. sin key ni headers en salida
title("6. Ni la key ni los headers aparecen")
raw = PATH.read_text(encoding="utf-8")
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass
key = os.environ.get("LLM_API_KEY", "")
findings = []
if key and key in raw:
    findings.append("el valor de LLM_API_KEY aparece en el archivo")
for pattern in (
    r"authorization",
    r"bearer\s",
    r"x-api-key",
    r"api[_-]?key",
    r"\bsk-[A-Za-z0-9]",
):
    hits = [
        i
        for i, ln in enumerate(raw.splitlines(), 1)
        if re.search(pattern, ln, re.IGNORECASE)
    ]
    if hits:
        findings.append(f"patrón '{pattern}' en líneas {hits[:5]}")
print("Hallazgos: " + ("; ".join(findings) if findings else "ninguno"))
print("(Este reporte nunca imprime la key, los headers ni el contenido de las líneas.)")
ok6 = not findings
print(f"Criterio: {verdict(ok6)}")

# ------------------------------------------------------------------ resumen
title("Resumen")
for name, ok in [
    ("1 registros válidos", ok1),
    ("4 reintento/backoff", ok4),
    ("5 anómalas marcadas", True),
    ("6 sin key/headers", ok6),
]:
    print(f"  {verdict(ok):>5}  {name}")
