"""Provider-free API-006 registry assembly over existing authorities."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.api.catalog import build_stats
from src.api.registry_models import (
    CorpusDatasetCoverage,
    DatasetCount,
    DatasetDetail,
    DatasetKind,
    DatasetProvenance,
    DatasetSummary,
    EvaluationDatasetCoverage,
    FilingYearCoverage,
    ModelRegistryEntry,
    ModelRole,
    ModelTestCheck,
    ModelTestResponse,
)
from src.evaluation.test_set import TEST_SET, TestCase
from src.generation.generator import DEFAULT_GENERATOR_MODEL_ID
from src.generation.provider_policy import configured_groq_keys
from src.retrieval.index_manifest import compute_corpus_fingerprint, load_index_manifest


MODEL_ORDER: tuple[ModelRole, ...] = ("generator", "embedding", "reranker")
DATASET_ORDER = ("serving-corpus", "evaluation-test-set")
EVALUATION_DATASET_VERSION = "evaluation-test-set-v1"


def _text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


_PUBLIC_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+@-]{0,255}$")
_HEX_REVISION = re.compile(r"^[0-9a-fA-F]{7,64}$")
_SHA256_REVISION = re.compile(r"^sha256:[0-9a-f]{64}$")
_SECRET_PREFIXES = ("sk-", "gsk_", "ghp_", "bearer ")


def _public_identifier(value: Any) -> str | None:
    """Allow a bounded registry identifier while rejecting paths/secrets."""
    text = _text(value)
    if text is None:
        return None
    folded = text.casefold()
    if folded.startswith(_SECRET_PREFIXES):
        return None
    if text.startswith(("/", "\\", "~")) or re.match(r"^[A-Za-z]:[/\\]", text):
        return None
    if (
        folded.startswith("file:")
        or "://" in text
        or "\\" in text
        or ".." in text.split("/")
    ):
        return None
    return text if _PUBLIC_IDENTIFIER.fullmatch(text) else None


def _public_revision(value: Any) -> str | None:
    text = _text(value)
    if text is None:
        return None
    if _HEX_REVISION.fullmatch(text) or _SHA256_REVISION.fullmatch(text):
        return text
    return _public_identifier(text)


def _evaluation_revision(cases: Sequence[TestCase]) -> str:
    encoded = json.dumps(
        [asdict(case) for case in cases],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _counts(values: Sequence[str]) -> list[DatasetCount]:
    counted = Counter(values)
    return [DatasetCount(key=key, count=counted[key]) for key in sorted(counted)]


class RegistryService:
    """Build deterministic registries without constructing or invoking models."""

    def __init__(
        self,
        *,
        settings: Any,
        get_state: Callable[[], Mapping[str, Any]],
        get_catalog_rows: Callable[[], list[dict[str, Any]] | None],
        get_chunks: Callable[[], Sequence[Mapping[str, Any]] | None],
        evaluation_cases: Sequence[TestCase] = TEST_SET,
    ) -> None:
        self._settings = settings
        self._get_state = get_state
        self._get_catalog_rows = get_catalog_rows
        self._get_chunks = get_chunks
        self._evaluation_cases = tuple(evaluation_cases)

    def _credential_configured(self) -> bool:
        try:
            return bool(
                configured_groq_keys(
                    self._settings,
                    policy=getattr(self._settings, "groq_key_policy", "pool"),
                )
            )
        except ValueError:
            return False

    def _model_entries(self) -> dict[ModelRole, ModelRegistryEntry]:
        state = self._get_state()
        pipeline = state.get("pipeline")
        retriever = getattr(pipeline, "retriever", None)
        generator = getattr(pipeline, "generator", None)
        embedder = getattr(retriever, "embedder", None)

        configured_raw: dict[ModelRole, tuple[str | None, str | None]] = {
            "generator": (DEFAULT_GENERATOR_MODEL_ID, None),
            "embedding": (
                _text(getattr(self._settings, "embedding_model_id", None)),
                _text(getattr(self._settings, "embedding_model_revision", None)),
            ),
            "reranker": (
                _text(getattr(self._settings, "reranker_model_id", None)),
                _text(getattr(self._settings, "reranker_model_revision", None)),
            ),
        }
        runtime_raw: dict[ModelRole, tuple[Any, str | None, str | None]] = {
            "generator": (
                generator,
                _text(getattr(generator, "model", None)),
                None,
            ),
            "embedding": (
                getattr(embedder, "model", None),
                _text(getattr(embedder, "model_name", None)),
                _text(getattr(embedder, "model_revision", None)),
            ),
            "reranker": (
                getattr(retriever, "cross_encoder", None),
                _text(getattr(retriever, "cross_encoder_model", None)),
                _text(getattr(retriever, "cross_encoder_revision", None)),
            ),
        }

        entries: dict[ModelRole, ModelRegistryEntry] = {}
        provider_credentials = self._credential_configured()
        for role in MODEL_ORDER:
            configured_id_raw, configured_revision_raw = configured_raw[role]
            runtime_object, runtime_id_raw, runtime_revision_raw = runtime_raw[role]
            configured_id = _public_identifier(configured_id_raw)
            configured_revision = _public_revision(configured_revision_raw)
            runtime_id = _public_identifier(runtime_id_raw)
            runtime_revision = _public_revision(runtime_revision_raw)
            configuration_status = (
                "configured" if configured_id_raw else "not_configured"
            )
            load_status = "loaded" if runtime_object is not None else "not_loaded"
            credential_status = (
                ("configured" if provider_credentials else "not_configured")
                if role == "generator"
                else "not_required"
            )

            if configured_id_raw and configured_id is None:
                availability_status = "unavailable"
                reason = "The configured model identity is not safe for public disclosure."
            elif configured_id is None:
                availability_status = "unavailable"
                reason = "No model identity is configured for this role."
            elif role == "generator":
                if not provider_credentials:
                    availability_status = "unavailable"
                    reason = "The required provider credential is not configured."
                elif runtime_id_raw and runtime_id is None:
                    availability_status = "unavailable"
                    reason = "The loaded runtime identity is not safe for public disclosure."
                elif runtime_object is not None and runtime_id != configured_id:
                    availability_status = "unavailable"
                    reason = "The loaded runtime identity does not match configuration."
                else:
                    availability_status = "unknown"
                    reason = "Remote provider reachability is not probed by registry reads."
            elif runtime_object is None:
                availability_status = "unknown"
                reason = "The configured local model is not loaded in the current runtime."
            elif runtime_id_raw and runtime_id is None:
                availability_status = "unavailable"
                reason = "The loaded runtime identity is not safe for public disclosure."
            elif runtime_id != configured_id:
                availability_status = "unavailable"
                reason = "The loaded runtime identity does not match configuration."
            elif configured_revision and runtime_revision != configured_revision:
                availability_status = "unavailable"
                reason = "The loaded runtime revision does not match configuration."
            else:
                availability_status = "available"
                reason = None

            entries[role] = ModelRegistryEntry(
                id=role,
                role=role,
                provider="groq" if role == "generator" else "hugging_face",
                configured_model_id=configured_id,
                configured_revision=configured_revision,
                runtime_model_id=runtime_id,
                runtime_revision=runtime_revision,
                configuration_status=configuration_status,
                load_status=load_status,
                availability_status=availability_status,
                availability_reason=reason,
                credential_status=credential_status,
                test_capabilities=["runtime_identity"],
            )
        return entries

    def list_models(self, role: ModelRole | None = None) -> list[ModelRegistryEntry]:
        entries = self._model_entries()
        return [entries[item] for item in MODEL_ORDER if role is None or item == role]

    def get_model(self, model_id: str) -> ModelRegistryEntry | None:
        if model_id not in MODEL_ORDER:
            return None
        return self._model_entries()[model_id]  # type: ignore[index]

    def run_model_test(self, model_id: str, test_type: str) -> ModelTestResponse | None:
        """Run the bounded local identity check without inference or providers."""
        entry = self.get_model(model_id)
        if entry is None or test_type != "runtime_identity":
            return None

        checks = [
            ModelTestCheck(
                id="configured_identity",
                status="passed" if entry.configured_model_id else "failed",
                reason=None if entry.configured_model_id else "No configured model identity exists.",
            ),
            ModelTestCheck(
                id="runtime_loaded",
                status="passed" if entry.load_status == "loaded" else "unavailable",
                reason=None if entry.load_status == "loaded" else "The runtime model is not loaded.",
            ),
            ModelTestCheck(
                id="runtime_identity",
                status=(
                    "unavailable"
                    if entry.runtime_model_id is None
                    else "passed"
                    if entry.runtime_model_id == entry.configured_model_id
                    else "failed"
                ),
                reason=(
                    "The runtime identity is unavailable."
                    if entry.runtime_model_id is None
                    else None
                    if entry.runtime_model_id == entry.configured_model_id
                    else "The runtime model identity differs from configuration."
                ),
            ),
            ModelTestCheck(
                id="runtime_revision",
                status=(
                    "unavailable"
                    if entry.configured_revision is None or entry.runtime_revision is None
                    else "passed"
                    if entry.runtime_revision == entry.configured_revision
                    else "failed"
                ),
                reason=(
                    "No configured revision is recorded for this role."
                    if entry.configured_revision is None
                    else "The runtime revision is unavailable."
                    if entry.runtime_revision is None
                    else None
                    if entry.runtime_revision == entry.configured_revision
                    else "The runtime revision differs from configuration."
                ),
            ),
        ]
        required_statuses = {check.status for check in checks[:3]}
        result = (
            "failed"
            if "failed" in required_statuses
            else "unavailable"
            if "unavailable" in required_statuses
            else "passed"
        )
        return ModelTestResponse(
            model_id=entry.id,
            test_type="runtime_identity",
            result=result,
            provider_executed=False,
            checks=checks,
        )

    def _index_provenance(self, *, chunk_count: int) -> DatasetProvenance:
        path = Path(getattr(self._settings, "qdrant_index_manifest_path"))
        if not path.is_file():
            return DatasetProvenance(
                authority="qdrant_index_manifest",
                status="missing",
                reason_code="index_manifest_missing",
                reason="The serving index manifest is unavailable.",
            )
        try:
            manifest = load_index_manifest(path)
        except (OSError, UnicodeError, ValueError):
            return DatasetProvenance(
                authority="qdrant_index_manifest",
                status="invalid",
                reason_code="index_manifest_invalid",
                reason="The serving index manifest is invalid.",
            )

        safe_identifiers = {
            "collection_name": _public_identifier(manifest["collection_name"]),
            "embedding_model_id": _public_identifier(manifest["embedding_model_id"]),
            "embedding_model_revision": _public_revision(
                manifest["embedding_model_revision"]
            ),
            "build_version": _public_identifier(manifest["build_version"]),
            "distance_metric": _public_identifier(manifest["distance_metric"]),
            "embedding_generation_id": _public_identifier(
                manifest["embedding_generation_id"]
            ),
        }
        safe_hashes = {
            "corpus_fingerprint": _text(manifest["corpus_fingerprint"]),
            "snapshot_id": _text(manifest["snapshot_id"]),
            "embedding_generation_fingerprint": _text(
                manifest["embedding_generation_fingerprint"]
            ),
        }
        if any(value is None for value in safe_identifiers.values()) or any(
            value is None or _SHA256_REVISION.fullmatch(value) is None
            for value in safe_hashes.values()
        ):
            return DatasetProvenance(
                authority="qdrant_index_manifest",
                status="invalid",
                reason_code="index_manifest_invalid",
                reason="The serving index manifest contains unsafe or invalid public metadata.",
            )

        mismatches: list[str] = []
        if manifest["point_count"] != chunk_count:
            mismatches.append("point count")
        if manifest["embedding_model_id"] != getattr(
            self._settings, "embedding_model_id", None
        ):
            mismatches.append("embedding model")
        configured_revision = _text(
            getattr(self._settings, "embedding_model_revision", None)
        )
        if configured_revision and manifest["embedding_model_revision"] != configured_revision:
            mismatches.append("embedding revision")
        chunks = self._get_chunks()
        if chunks is None:
            mismatches.append("corpus fingerprint unavailable")
        else:
            try:
                corpus_fingerprint = compute_corpus_fingerprint(chunks)
            except ValueError:
                mismatches.append("corpus fingerprint unavailable")
            else:
                if manifest["corpus_fingerprint"] != corpus_fingerprint:
                    mismatches.append("corpus fingerprint")
        status = "mismatch" if mismatches else "consistent"
        return DatasetProvenance(
            authority="qdrant_index_manifest",
            status=status,
            reason_code="index_manifest_mismatch" if mismatches else None,
            reason=(
                "The serving index manifest disagrees with the loaded catalog or configured embedding binding."
                if mismatches
                else None
            ),
            schema_version=manifest["schema_version"],
            revision=safe_hashes["corpus_fingerprint"],
            build_version=safe_identifiers["build_version"],
            collection_name=safe_identifiers["collection_name"],
            point_count=manifest["point_count"],
            embedding_model_id=safe_identifiers["embedding_model_id"],
            embedding_model_revision=safe_identifiers[
                "embedding_model_revision"
            ],
            vector_dimension=manifest["vector_dimension"],
            distance_metric=safe_identifiers["distance_metric"],
            snapshot_id=safe_hashes["snapshot_id"],
            embedding_generation_id=safe_identifiers[
                "embedding_generation_id"
            ],
            embedding_generation_fingerprint=safe_hashes[
                "embedding_generation_fingerprint"
            ],
        )

    def _corpus_dataset(self) -> DatasetDetail:
        rows = self._get_catalog_rows()
        if rows is None:
            return DatasetDetail(
                id="serving-corpus",
                kind="corpus",
                name="Serving SEC filing corpus",
                description="The document corpus currently bound to retrieval.",
                availability="unavailable",
                reason_code="catalog_unavailable",
                reason="The serving catalog is unavailable.",
                record_count=None,
                record_unit="documents",
                coverage=None,
                provenance=DatasetProvenance(
                    authority="qdrant_index_manifest",
                    status="missing",
                    reason_code="catalog_unavailable",
                    reason="Index provenance cannot be reconciled without the serving catalog.",
                ),
            )

        stats = build_stats(rows)
        provenance = self._index_provenance(chunk_count=stats["chunks"])
        empty = stats["documents"] == 0
        degraded = empty or provenance.status != "consistent"
        reason_code = "empty_catalog" if empty else provenance.reason_code
        reason = "The loaded serving catalog contains no documents." if empty else provenance.reason
        coverage = CorpusDatasetCoverage(
            documents=stats["documents"],
            companies=stats["companies"],
            chunks=stats["chunks"],
            configured_companies=stats["configured_companies"],
            configured_companies_with_documents=stats[
                "configured_companies_with_documents"
            ],
            configured_companies_without_documents=stats[
                "configured_companies_without_documents"
            ],
            filing_years=FilingYearCoverage(
                availability=stats["filing_dates"]["availability"],
                earliest=stats["filing_dates"]["earliest"],
                latest=stats["filing_dates"]["latest"],
                documents_without_value=stats["filing_dates"][
                    "documents_without_value"
                ],
                reason=stats["filing_dates"]["reason"],
            ),
            sections=[
                DatasetCount(key=str(item["value"]), count=item["count"])
                for item in stats["sections"]["values"]
            ],
        )
        return DatasetDetail(
            id="serving-corpus",
            kind="corpus",
            name="Serving SEC filing corpus",
            description="The document corpus currently bound to retrieval.",
            availability="degraded" if degraded else "available",
            reason_code=reason_code,
            reason=reason,
            version=provenance.build_version,
            revision=provenance.revision,
            record_count=stats["documents"],
            record_unit="documents",
            coverage=coverage,
            provenance=provenance,
        )

    def _evaluation_dataset(self) -> DatasetDetail:
        cases = self._evaluation_cases
        revision = _evaluation_revision(cases)
        categories = _counts([case.category for case in cases])
        priorities = _counts([str(case.priority) for case in cases])
        tickers = sorted({case.ticker for case in cases if case.ticker})
        sections = sorted({case.section for case in cases if case.section})
        return DatasetDetail(
            id="evaluation-test-set",
            kind="evaluation",
            name="Built-in evaluation test set",
            description="The source-controlled cases used by the native evaluation workflow.",
            availability="available",
            version=EVALUATION_DATASET_VERSION,
            revision=revision,
            record_count=len(cases),
            record_unit="cases",
            coverage=EvaluationDatasetCoverage(
                cases=len(cases),
                categories=categories,
                priorities=priorities,
                tickers=tickers,
                sections=sections,
            ),
            provenance=DatasetProvenance(
                authority="built_in_evaluation_test_set",
                status="recorded",
                schema_version=1,
                revision=revision,
                build_version=EVALUATION_DATASET_VERSION,
            ),
        )

    def _datasets(self) -> dict[str, DatasetDetail]:
        return {
            "serving-corpus": self._corpus_dataset(),
            "evaluation-test-set": self._evaluation_dataset(),
        }

    def list_datasets(self, kind: DatasetKind | None = None) -> list[DatasetSummary]:
        datasets = self._datasets()
        return [
            DatasetSummary.model_validate(datasets[dataset_id].model_dump())
            for dataset_id in DATASET_ORDER
            if kind is None or datasets[dataset_id].kind == kind
        ]

    def get_dataset(self, dataset_id: str) -> DatasetDetail | None:
        if dataset_id not in DATASET_ORDER:
            return None
        return self._datasets()[dataset_id]
