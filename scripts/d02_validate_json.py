import sys

from d02_models import Incident
from pydantic import ValidationError

OK = '"service": "api-pagos", "severity": "SEV1", "root_cause": "x", "action_items": ["a"]'

# nombre: (texto JSON, tipos de error esperados; None si debe validar)
casos = {
    "valido": ("{" + OK + "}", None),
    "sin_campo": (
        '{"service": "api-pagos", "severity": "SEV1", "action_items": ["a"]}',
        ["missing"],
    ),
    "sev_mala": (
        '{"service": "api-pagos", "severity": "grave", "root_cause": "x", "action_items": ["a"]}',
        ["enum"],
    ),
    "campo_extra": ("{" + OK + ', "notas": "hola"}', ["extra_forbidden"]),
    # F-05: strings vacíos que cumplen la forma pero no tienen contenido
    "lista_vacia": (
        '{"service": "api-pagos", "severity": "SEV1", "root_cause": "x", "action_items": []}',
        ["too_short"],
    ),
    "accion_vacia": (
        '{"service": "api-pagos", "severity": "SEV1", "root_cause": "x", "action_items": [""]}',
        ["string_too_short"],
    ),
    "accion_espacios": (
        '{"service": "api-pagos", "severity": "SEV1", "root_cause": "x", "action_items": ["   "]}',
        ["string_too_short"],
    ),
    "service_vacio": (
        '{"service": "", "severity": "SEV1", "root_cause": "x", "action_items": ["a"]}',
        ["string_too_short"],
    ),
    "root_cause_espacios": (
        '{"service": "api-pagos", "severity": "SEV1", "root_cause": "  ", "action_items": ["a"]}',
        ["string_too_short"],
    ),
}

fallos = 0
for nombre, (texto, esperado) in casos.items():
    try:
        Incident.model_validate_json(texto)
        obtenido = None
    except ValidationError as e:
        obtenido = [x["type"] for x in e.errors()]
    estado = "PASS" if obtenido == esperado else "FAIL"
    if estado == "FAIL":
        fallos += 1
    print(estado, nombre, "->", obtenido if obtenido else "OK")

sys.exit(1 if fallos else 0)
