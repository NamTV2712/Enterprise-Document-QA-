"""Safe immutable provenance for the production decision transport."""

from typing import Literal
import hashlib
import json

from pydantic import BaseModel, ConfigDict


class DecisionProviderIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    provider: Literal["groq"] = "groq"
    model_id: Literal["openai/gpt-oss-120b", "openai/gpt-oss-20b"]
    adapter_version: Literal["groq_json_schema_v1"] = "groq_json_schema_v1"
    mechanism: Literal["native_strict_json_schema"] = "native_strict_json_schema"
    credential_policy: Literal["pool", "key5_only"]

    @property
    def binding_id(self) -> str:
        encoded = json.dumps(self.model_dump(), ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False)
        return "groq_structured_" + hashlib.sha256(encoded.encode()).hexdigest()[:32]
