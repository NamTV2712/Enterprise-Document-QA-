import {
  captureBrowserWorkspaceSnapshot,
  createWorkspaceBackup,
  validateWorkspaceBackup,
  type WorkspaceBackup,
} from "./workspaceBackup";

export type WorkspaceRepositoryKind = "browser" | "sqlite";
export type WorkspaceRepositoryAvailability = "available" | "unavailable" | "disconnected";

export interface WorkspaceRepositoryWriter {
  readonly kind: WorkspaceRepositoryKind;
  availability: WorkspaceRepositoryAvailability;
  write<T>(operation: string, payload: unknown): Promise<T>;
}

export interface UnsavedWorkspaceOperation {
  operation: string;
  payload: unknown;
  attemptedAt: string;
  repository: WorkspaceRepositoryKind;
}

export interface WorkspaceRepositorySessionState {
  authority: WorkspaceRepositoryKind;
  browser: WorkspaceRepositoryAvailability;
  sqlite: WorkspaceRepositoryAvailability;
  unsavedExportable: boolean;
  unsavedOperationCount: number;
}

/**
 * Session-level authority owner. It calls one writer exactly once. A failed
 * SQLite write becomes a disconnected, exportable in-memory operation and is
 * never retried against browser storage.
 */
export class WorkspaceRepositoryAuthoritySession {
  private authority: WorkspaceRepositoryKind;
  private readonly writers: Record<WorkspaceRepositoryKind, WorkspaceRepositoryWriter>;
  private readonly unsaved: UnsavedWorkspaceOperation[] = [];

  constructor(options: {
    browser: WorkspaceRepositoryWriter;
    sqlite: WorkspaceRepositoryWriter;
    authority?: WorkspaceRepositoryKind;
  }) {
    this.writers = { browser: options.browser, sqlite: options.sqlite };
    this.authority = options.authority ?? "browser";
    if (this.writers[this.authority].availability !== "available") {
      throw new Error(`The ${this.authority} repository is not available for this session.`);
    }
  }

  getState(): WorkspaceRepositorySessionState {
    return {
      authority: this.authority,
      browser: this.writers.browser.availability,
      sqlite: this.writers.sqlite.availability,
      unsavedExportable: this.unsaved.length > 0,
      unsavedOperationCount: this.unsaved.length,
    };
  }

  /** Authority changes only through this explicit session action. */
  selectAuthority(authority: WorkspaceRepositoryKind): WorkspaceRepositorySessionState {
    if (this.writers[authority].availability !== "available") {
      throw new Error(`The ${authority} repository is not available for this session.`);
    }
    this.authority = authority;
    return this.getState();
  }

  setAvailability(kind: WorkspaceRepositoryKind, availability: WorkspaceRepositoryAvailability): void {
    this.writers[kind].availability = availability;
  }

  async write<T>(operation: string, payload: unknown): Promise<T> {
    const writer = this.writers[this.authority];
    if (writer.availability !== "available") {
      throw new Error(`The authoritative ${writer.kind} repository is ${writer.availability}.`);
    }
    try {
      return await writer.write<T>(operation, payload);
    } catch (error) {
      if (writer.kind === "sqlite") writer.availability = "disconnected";
      this.unsaved.push({
        operation,
        payload: JSON.parse(JSON.stringify(payload)) as unknown,
        attemptedAt: new Date().toISOString(),
        repository: writer.kind,
      });
      throw error;
    }
  }

  exportUnsavedOperations(): UnsavedWorkspaceOperation[] {
    return this.unsaved.map((operation) => JSON.parse(JSON.stringify(operation)) as UnsavedWorkspaceOperation);
  }
}

export interface WorkspaceImportPreview {
  format: string;
  version: number;
  digest: string;
  compatibility: "compatible" | "partial";
  supported: Record<string, number>;
  unsupported: number;
  unsupported_sources: Array<Record<string, unknown>>;
  duplicates: number;
  potential_conflicts: number;
  tombstones: number;
  records_to_create: number;
  records_to_update: number;
  records_to_skip: number;
  mapping_required: number;
  mappings: Array<{ kind: string; legacy_id: string; workspace_id: string }>;
}

export interface WorkspaceImportReceipt extends WorkspaceImportPreview {
  import_id: string;
  status: "committed";
  completed_at: string;
}

export interface WorkspaceTransferClient {
  preview(backup: WorkspaceBackup): Promise<WorkspaceImportPreview>;
  importBackup(backup: WorkspaceBackup, previewDigest: string): Promise<WorkspaceImportReceipt>;
  exportBackup(): Promise<WorkspaceBackup>;
}

interface WorkspaceTransferClientOptions {
  apiBaseUrl: string;
  /** Token remains in caller-owned memory and is never read from VITE_* config. */
  getBearerToken: () => string | null;
  fetchImpl?: typeof fetch;
}

async function responseJson<T>(response: Response): Promise<T> {
  const body = await response.json().catch(() => null) as { detail?: unknown } | null;
  if (!response.ok) {
    const detail = typeof body?.detail === "string" ? body.detail : `Workspace request failed (${response.status}).`;
    throw new Error(detail);
  }
  return body as T;
}

export function createWorkspaceTransferClient(options: WorkspaceTransferClientOptions): WorkspaceTransferClient {
  const request = async <T>(path: string, init?: RequestInit): Promise<T> => {
    const token = options.getBearerToken();
    if (!token) throw new Error("Local workspace authentication is required.");
    const fetchImpl = options.fetchImpl ?? fetch;
    const response = await fetchImpl(`${options.apiBaseUrl.replace(/\/$/, "")}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
        ...(init?.headers ?? {}),
      },
    });
    return responseJson<T>(response);
  };
  return {
    async preview(backup) {
      await validateWorkspaceBackup(backup);
      return request<WorkspaceImportPreview>("/workspace/imports/preview", {
        method: "POST",
        body: JSON.stringify(backup),
      });
    },
    async importBackup(backup, previewDigest) {
      await validateWorkspaceBackup(backup);
      if (previewDigest !== backup.digest) throw new Error("Preview digest does not match the selected backup.");
      return request<WorkspaceImportReceipt>("/workspace/imports", {
        method: "POST",
        body: JSON.stringify({ backup, preview_digest: previewDigest }),
      });
    },
    async exportBackup() {
      const backup = await request<WorkspaceBackup>("/workspace/export", { method: "GET" });
      return validateWorkspaceBackup(backup);
    },
  };
}

/** Explicit browser export adapter. It reads the loaded snapshot and never mutates it. */
export async function exportBrowserWorkspaceBackup(): Promise<WorkspaceBackup> {
  return createWorkspaceBackup(captureBrowserWorkspaceSnapshot());
}
