"""Explicit provenance for answer postprocessing semantics.

Checkpoint identity must distinguish provider-only answers from runs that may
replace a provider draft with a deterministic renderer.  The profile is kept
outside the provider code so every evaluation runner can bind the same policy.
"""

from __future__ import annotations

import hashlib
import json

from src.generation.answer_completion import ANSWER_COMPLETION_FINGERPRINT
from src.generation.enumeration_answer_renderer import (
    ENUMERATION_ANSWER_RENDERER_FINGERPRINT,
)
from src.generation.evidence_fact_renderer import EVIDENCE_FACT_RENDERER_FINGERPRINT
from src.generation.comparative_answer_renderer import (
    COMPARATIVE_ANSWER_RENDERER_FINGERPRINT,
)
from src.generation.risk_answer_shape import RISK_ANSWER_SHAPE_FINGERPRINT


ANSWER_POSTPROCESSOR_PROFILE_VERSION = 1


def _sha256_payload(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def build_answer_postprocessor_profile(
    *,
    deterministic_risk_renderer: bool = False,
    deterministic_fact_renderer: bool = False,
    deterministic_revenue_renderer: bool = False,
    deterministic_comparative_renderer: bool = False,
) -> str:
    """Return a stable profile fingerprint for the enabled postprocessors."""
    return _sha256_payload(
        {
            "version": ANSWER_POSTPROCESSOR_PROFILE_VERSION,
            "answer_completion": ANSWER_COMPLETION_FINGERPRINT,
            "risk_renderer": RISK_ANSWER_SHAPE_FINGERPRINT,
            "fact_renderer": EVIDENCE_FACT_RENDERER_FINGERPRINT,
            "revenue_renderer": ENUMERATION_ANSWER_RENDERER_FINGERPRINT,
            "comparative_renderer": COMPARATIVE_ANSWER_RENDERER_FINGERPRINT,
            "deterministic_risk_renderer": deterministic_risk_renderer,
            "deterministic_fact_renderer": deterministic_fact_renderer,
            "deterministic_revenue_renderer": deterministic_revenue_renderer,
            "deterministic_comparative_renderer": deterministic_comparative_renderer,
        }
    )


ANSWER_POSTPROCESSOR_PROFILE_PROVIDER_DRAFT = build_answer_postprocessor_profile()
