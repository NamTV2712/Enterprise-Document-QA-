import ipaddress
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _is_loopback_name(value: str | None) -> bool:
    """Return whether a hostname is exactly localhost or a loopback IP."""
    if not value:
        return False
    host = value.casefold()
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _is_local_origin(value: str) -> bool:
    """Validate an exact browser origin without paths, credentials or wildcards."""
    try:
        parsed = urlsplit(value)
        _ = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme in {"http", "https"}
        and bool(parsed.netloc)
        and parsed.path == ""
        and parsed.query == ""
        and parsed.fragment == ""
        and parsed.username is None
        and parsed.password is None
        and _is_loopback_name(parsed.hostname)
    )


def _is_local_host_entry(value: str) -> bool:
    """Validate one exact Host allowlist entry, optionally including a port."""
    try:
        parsed = urlsplit(f"//{value}")
        _ = parsed.port
    except ValueError:
        return False
    return (
        bool(parsed.netloc)
        and parsed.path == ""
        and parsed.query == ""
        and parsed.fragment == ""
        and parsed.username is None
        and parsed.password is None
        and _is_loopback_name(parsed.hostname)
    )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        hide_input_in_errors=True,
    )

    # LLM API keys
    groq_api_key: str = ""
    groq_api_key2: str = ""
    groq_api_key3: str = ""
    groq_api_key4: str = ""
    groq_api_key5: str = ""
    groq_api_key_fall_back: str = ""
    groq_api_key_fall_back2: str = ""
    # ``pool`` preserves legacy rotation; improvement/evaluation runs set
    # ``key5_only`` so every provider call is auditable against GROQ_API_KEY5.
    groq_key_policy: str = "pool"

    # Data path (relative path to run on any machine)
    data_raw_dir: Path = Path("data/raw")
    data_processed_dir: Path = Path("data/processed")
    data_public_evaluations_dir: Path = Path("data/public_evaluations")

    # Bounded, local-only normalized original viewer. These values are
    # deliberately conservative; the viewer validates them against hard
    # ceilings before serving any source content.
    viewer_raw_file_max_bytes: int = 20 * 1024 * 1024
    viewer_raw_file_hard_max_bytes: int = 32 * 1024 * 1024
    viewer_processed_file_max_bytes: int = 20 * 1024 * 1024
    viewer_processed_file_hard_max_bytes: int = 32 * 1024 * 1024
    viewer_companion_max: int = 4
    viewer_companion_hard_max: int = 8
    viewer_source_set_max_bytes: int = 40 * 1024 * 1024
    viewer_source_set_hard_max_bytes: int = 64 * 1024 * 1024
    viewer_normalized_source_max_codepoints: int = 4_000_000
    viewer_normalized_source_hard_max_codepoints: int = 8_000_000
    viewer_normalized_set_max_codepoints: int = 8_000_000
    viewer_normalized_set_hard_max_codepoints: int = 16_000_000
    viewer_window_default: int = 16_000
    viewer_window_max: int = 32_000
    viewer_find_default_limit: int = 20
    viewer_find_max_limit: int = 100
    viewer_max_pending_jobs: int = 8
    viewer_cache_entries: int = 4
    viewer_cache_max_bytes: int = 32 * 1024 * 1024

    # Qdrant configuration. Keep local as the safe default until cloud migration is verified.
    qdrant_mode: str = "local"
    qdrant_local_path: Path = Path("data/processed/qdrant")
    qdrant_index_manifest_path: Path = Path(
        "data/processed/qdrant_index_manifest.json"
    )
    qdrant_cloud_url: str = ""
    qdrant_cloud_api_key: str = ""

    # Required provenance for trusted embedding/index rebuilds.
    embedding_model_id: str = "nomic-ai/nomic-embed-text-v1.5"
    embedding_model_revision: str = ""
    reranker_model_id: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    reranker_model_revision: str = "233902d25c440f23af6f7d6e94d2946bac0bee0a"
    embedding_generations_dir: Path = Path("data/embedding_generations")
    embedding_generation_path: Path | None = None

    # Browser origins allowed to call the API. Add the deployed frontend URL via env.
    allowed_origins: str = "http://localhost:3000,http://localhost:5173"

    # Private workspace access is opt-in, loopback-only and authenticated with
    # a dedicated bearer token. The token is intentionally not a VITE setting.
    workspace_mode: Literal["public", "local"] = "public"
    local_workspace_token: SecretStr = SecretStr("")
    local_workspace_allowed_origins: str = (
        "http://localhost:3000,http://localhost:5173"
    )
    local_workspace_allowed_hosts: str = "localhost,127.0.0.1,[::1]"
    enable_workspace_execution: bool = False

    # Local workspace persistence is isolated from canonical data, evaluation,
    # PDF and Qdrant artifacts. Importing settings never creates these paths.
    workspace_db_path: Path = Path(".local/workbench/workspace.sqlite3")
    workspace_runs_dir: Path = Path(".local/workbench/runs")
    workspace_sqlite_busy_timeout_ms: int = Field(default=5000, ge=100, le=30_000)

    # Effective only in explicitly enabled local execution, never public mode.
    workspace_worker_enabled: bool = True
    workspace_worker_concurrency: int = Field(default=2, ge=1, le=16)
    workspace_worker_poll_interval_ms: int = Field(default=500, ge=100, le=5000)
    workspace_worker_shutdown_grace_ms: int = Field(default=5000, ge=100, le=60_000)

    # Public API protection. In-memory limits are appropriate for the single-worker runtime.
    llm_rate_limit_burst: str = "10/minute"
    llm_rate_limit_daily: str = "100/day"
    decomposed_rate_limit: str = "5/minute"
    cache_test_rate_limit: str = "10/minute"
    # Provider-free keyword discovery scans the in-memory corpus; the bound
    # keeps one client from monopolising a single worker.
    search_rate_limit: str = "30/minute"
    enable_cache_clear: bool = False
    enable_metrics_endpoint: bool = False

    # Derived-PDF representation storage and bounds. Artifacts live under the
    # git-ignored data tree and are bound to the verified source revision.
    pdf_artifacts_dir: Path = Path("data/generated/pdf")
    pdf_generation_enabled: bool = True
    pdf_generation_timeout_seconds: float = 60.0
    pdf_generation_concurrency: int = 2
    pdf_source_max_codepoints: int = 8_000_000
    pdf_max_blocks: int = 20_000
    pdf_max_artifact_bytes: int = 64 * 1024 * 1024

    # Comma-separated CIDR ranges of reverse proxies trusted to set
    # X-Forwarded-For (for example an ngrok tunnel or Docker gateway).
    # Empty by default: rate limits then key on the socket peer address,
    # and forwarded headers from anyone are ignored.
    trusted_proxy_cidrs: str = ""

    @property
    def allowed_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.allowed_origins.split(",")
            if origin.strip()
        ]

    @property
    def local_workspace_allowed_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.local_workspace_allowed_origins.split(",")
            if origin.strip()
        ]

    @property
    def local_workspace_allowed_hosts_list(self) -> list[str]:
        return [
            host.strip()
            for host in self.local_workspace_allowed_hosts.split(",")
            if host.strip()
        ]

    @model_validator(mode="after")
    def validate_local_workspace_boundary(self) -> "Settings":
        """Reject incomplete or non-local private-workspace configuration."""
        db_path = self.workspace_db_path
        runs_path = self.workspace_runs_dir
        if str(db_path).casefold() == ":memory:" or str(db_path).casefold().startswith("file:"):
            raise ValueError("WORKSPACE_DB_PATH must be a filesystem path")
        if db_path.suffix.casefold() != ".sqlite3":
            raise ValueError("WORKSPACE_DB_PATH must end in .sqlite3")

        for path, label in (
            (db_path, "WORKSPACE_DB_PATH"),
            (runs_path, "WORKSPACE_RUNS_DIR"),
        ):
            if not path.is_absolute():
                if ".." in path.parts or not path.parts or path.parts[0] != ".local":
                    raise ValueError(f"{label} relative paths must remain under .local")

        resolved_db = db_path.resolve()
        resolved_runs = runs_path.resolve()
        protected_roots = {
            Path("data").resolve(),
            self.data_raw_dir.resolve(),
            self.data_processed_dir.resolve(),
            self.data_public_evaluations_dir.resolve(),
            self.qdrant_local_path.resolve(),
            self.embedding_generations_dir.resolve(),
            self.pdf_artifacts_dir.resolve(),
        }
        for protected_root in protected_roots:
            if (
                resolved_db == protected_root
                or protected_root in resolved_db.parents
                or resolved_runs == protected_root
                or protected_root in resolved_runs.parents
            ):
                raise ValueError("workspace persistence paths must not use canonical data storage")
        if resolved_runs == Path(resolved_runs.anchor):
            raise ValueError("WORKSPACE_RUNS_DIR must not be a filesystem root")
        if (
            resolved_db == resolved_runs
            or resolved_db in resolved_runs.parents
            or resolved_runs in resolved_db.parents
        ):
            raise ValueError("WORKSPACE_DB_PATH and WORKSPACE_RUNS_DIR must be distinct")

        if self.workspace_mode == "public":
            return self

        token = self.local_workspace_token.get_secret_value()
        if len(token) < 32 or token != token.strip() or any(char.isspace() for char in token):
            raise ValueError(
                "LOCAL_WORKSPACE_TOKEN must be at least 32 non-whitespace characters in local mode"
            )

        local_origins = self.local_workspace_allowed_origins_list
        if not local_origins or any(not _is_local_origin(origin) for origin in local_origins):
            raise ValueError(
                "LOCAL_WORKSPACE_ALLOWED_ORIGINS must contain exact loopback HTTP(S) origins"
            )
        if not set(local_origins).issubset(self.allowed_origins_list):
            raise ValueError(
                "LOCAL_WORKSPACE_ALLOWED_ORIGINS must be included in ALLOWED_ORIGINS"
            )

        local_hosts = self.local_workspace_allowed_hosts_list
        if not local_hosts or any(not _is_local_host_entry(host) for host in local_hosts):
            raise ValueError(
                "LOCAL_WORKSPACE_ALLOWED_HOSTS must contain exact localhost or loopback entries"
            )
        return self


settings = Settings()
