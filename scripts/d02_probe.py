import os

from d02_models import Incident, ValidationError
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(
    base_url=os.environ["LLM_BASE_URL"],
    api_key=os.environ["LLM_API_KEY"],
    max_retries=0,
    timeout=20,
)

EFFORT = "none"  # none, low, medium, high, xhigh, and max

# with open("data/d02/postmortems.jsonl", encoding="utf-8") as f:
#     docs = [json.loads(l) for l in f]
# pm01 = next(d for d in docs if d["id"] == "pm-01")

texto = """Post-mortem breve de web-frontend. El sitio estuvo 5 minutos con una página
de error por una configuración equivocada. Severidad: SEV4. No se definieron acciones."""

resp = client.chat.completions.create(
    model=os.environ["LLM_MODEL"],
    messages=[
        {
            "role": "system",
            "content": "Extrae del post-mortem: service, severity (SEV1 a SEV4), root_cause y action_items. Responde en JSON.",
        },
        {"role": "user", "content": texto},
    ],
    max_tokens=400,
    temperature=0.0,
    extra_body={"reasoning_effort": EFFORT},
    response_format={"type": "json_object"},
)

print(resp.choices[0].finish_reason)
print(resp.choices[0].message.content)
try:
    Incident.model_validate_json(resp.choices[0].message.content)
    print("validó")
except ValidationError as e:
    print([x["type"] for x in e.errors()])

print("--------------------------------------------------")

resp2 = client.chat.completions.create(
    model=os.environ["LLM_MODEL"],
    messages=[
        {
            "role": "system",
            "content": "Extrae del post-mortem: service, severity (SEV1 a SEV4), root_cause y action_items. Responde en JSON.",
        },
        {"role": "user", "content": texto},
    ],
    max_tokens=400,
    temperature=0.0,
    extra_body={"reasoning_effort": EFFORT},
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "incident",
            "strict": False,
            "schema": Incident.model_json_schema(),
        },
    },
)

print(resp2.choices[0].finish_reason)
print(resp2.choices[0].message.content)
try:
    Incident.model_validate_json(resp2.choices[0].message.content)
    print("validó")
except ValidationError as e:
    print([x["type"] for x in e.errors()])

print("--------------------------------------------------")

resp3 = client.chat.completions.create(
    model=os.environ["LLM_MODEL"],
    messages=[
        {
            "role": "system",
            "content": "Extrae del post-mortem: service, severity (SEV1 a SEV4), root_cause y action_items. Responde en JSON.",
        },
        {"role": "user", "content": texto},
    ],
    max_tokens=400,
    temperature=0.0,
    extra_body={"reasoning_effort": EFFORT},
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "incident",
            "strict": True,
            "schema": Incident.model_json_schema(),
        },
    },
)

print(resp3.choices[0].finish_reason)
print(resp3.choices[0].message.content)
try:
    Incident.model_validate_json(resp3.choices[0].message.content)
    print("validó")
except ValidationError as e:
    print([x["type"] for x in e.errors()])

print("--------------------------------------------------")
