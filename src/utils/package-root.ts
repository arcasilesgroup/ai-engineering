import {
  readFile,
  fileExists,
  isDirectory,
  resolvePath,
} from "./filesystem.js";

let _packageRoot: string | null = null;

/**
 * Finds the ai-engineering package root by walking up from import.meta.dirname.
 *
 * This is the single source of truth for resolving the package root directory.
 * All modules that need to locate package-relative files (templates, hooks,
 * content, schemas) should use this function instead of fragile
 * import.meta.dirname + relative path patterns.
 *
 * @throws {Error} If the package root cannot be found.
 */
export function getPackageRoot(): string {
  if (_packageRoot) return _packageRoot;

  let dir = import.meta.dirname ?? process.cwd();
  while (dir !== "/" && dir !== ".") {
    const pkgPath = resolvePath(dir, "package.json");
    if (fileExists(pkgPath)) {
      try {
        const pkg = JSON.parse(readFile(pkgPath));
        if (pkg.name === "ai-engineering") {
          _packageRoot = dir;
          return dir;
        }
      } catch {
        /* continue searching */
      }
    }
    dir = resolvePath(dir, "..");
  }

  // Fallback: try from cwd (npx / global install)
  const cwdPkg = resolvePath(process.cwd(), "node_modules/ai-engineering");
  if (isDirectory(cwdPkg)) {
    _packageRoot = cwdPkg;
    return cwdPkg;
  }

  throw new Error(
    `Could not find ai-engineering package root.\n` +
      `  import.meta.dirname: ${import.meta.dirname ?? "undefined"}\n` +
      `  cwd: ${process.cwd()}`,
  );
}

/** Reset the cached package root. Useful for testing. */
export function resetPackageRootCache(): void {
  _packageRoot = null;
}
