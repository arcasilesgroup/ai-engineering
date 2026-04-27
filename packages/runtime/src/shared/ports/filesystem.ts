import type { Result } from "../kernel/result.ts";
import type { IOError } from "../kernel/errors.ts";

/**
 * FilesystemPort — driven port for filesystem operations.
 *
 * The domain never imports node:fs / Bun.file directly. All FS access goes
 * through this port so we can swap real FS, in-memory FS (testing), or
 * remote attestation-locked FS (regulated tier control plane).
 */
export interface FilesystemPort {
  read(path: string): Promise<Result<string, IOError>>;
  write(path: string, content: string): Promise<Result<void, IOError>>;
  exists(path: string): Promise<boolean>;
  list(path: string): Promise<Result<string[], IOError>>;
  remove(path: string): Promise<Result<void, IOError>>;
  hash(path: string): Promise<Result<string, IOError>>;
}
