# Prueba de conexión desechable: NO es el D1 (sin streaming ni métricas).
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(base_url=os.environ["LLM_BASE_URL"], api_key=os.environ["LLM_API_KEY"])
r = client.chat.completions.create(
    model=os.environ["LLM_MODEL"],
    messages=[{"role": "user", "content": "Responde solo: ok"}],
    max_tokens=5,
    extra_body={"reasoning_effort": "none"},
)
print(r.choices[0].message.content)
print(repr(r.choices[0].message.content))
print(r.choices[0].finish_reason, r.usage)
