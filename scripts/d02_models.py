from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError  # noqa: F401


class Severity(str, Enum):
    SEV1 = "SEV1"
    SEV2 = "SEV2"
    SEV3 = "SEV3"
    SEV4 = "SEV4"


# Texto con contenido: se recortan los espacios y no puede quedar vacío.
NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Incident(BaseModel):
    model_config = ConfigDict(extra="forbid")
    service: NonEmptyStr
    severity: Severity
    root_cause: NonEmptyStr
    action_items: list[NonEmptyStr] = Field(..., min_length=1)
