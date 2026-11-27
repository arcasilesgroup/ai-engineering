// bin/ai-eng.js is plain Node JS by design (no src/ imports). This declares
// its exported test surface so TypeScript consumers and the test suite can
// import it; the file ships with the package ("files" includes bin/).
declare module "*/bin/ai-eng.js" {
  export function resolveTarget(platform: string, arch: string, musl?: boolean): string | null;
  export function targetBinaryNames(target: string | null): string[];
  export function hostTarget(): string | null;
  export function buildStampPath(binaryPath: string): string;
}
