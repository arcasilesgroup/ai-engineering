import { writeFile, resolvePath } from "../utils/filesystem.js";
import { sha256, readFile, listFiles } from "../utils/filesystem.js";
import { logger } from "../utils/logger.js";
import { installHooks } from "./hooks-installer.js";
import { installGates } from "./gates-installer.js";
import { installKnowledge } from "./knowledge-installer.js";
import type { Config } from "../utils/config.js";

export async function install(
  projectRoot: string,
  config: Config,
): Promise<void> {
  // Install knowledge directory
  installKnowledge(projectRoot);

  // Install hooks (runtime + git)
  installHooks(projectRoot, config);

  // Install CI/CD gates
  installGates(projectRoot, config);

  // Write version file with checksums
  writeVersionFile(projectRoot, config);

  logger.success("Installation complete");
}

function writeVersionFile(projectRoot: string, config: Config): void {
  const aiEngDir = resolvePath(projectRoot, ".ai-engineering");
  const versionInfo: string[] = [config.version];

  // Compute checksums for all framework-generated files
  const frameworkFiles = collectFrameworkFiles(projectRoot, config);
  for (const filePath of frameworkFiles) {
    try {
      const content = readFile(filePath);
      const checksum = sha256(content);
      const relativePath = filePath.replace(projectRoot + "/", "");
      versionInfo.push(`${relativePath}:${checksum}`);
    } catch {
      // Skip files that can't be read
    }
  }

  writeFile(resolvePath(aiEngDir, ".version"), versionInfo.join("\n") + "\n");
  logger.debug("Written version file with checksums");
}

function collectFrameworkFiles(projectRoot: string, config: Config): string[] {
  const files: string[] = [];

  // .ai-engineering files (excluding user-owned knowledge/)
  const aiEngFiles = listFiles(
    resolvePath(projectRoot, ".ai-engineering"),
    true,
  );
  for (const f of aiEngFiles) {
    if (
      !f.includes("/knowledge/") &&
      !f.includes("/.version") &&
      !f.includes("/.update-cache")
    ) {
      files.push(f);
    }
  }

  // IDE files
  if (config.ides.includes("claude-code")) {
    const claudeFile = resolvePath(projectRoot, "CLAUDE.md");
    files.push(claudeFile);
    const commandFiles = listFiles(
      resolvePath(projectRoot, ".claude/commands"),
    );
    files.push(...commandFiles);
  }

  if (config.ides.includes("copilot")) {
    files.push(resolvePath(projectRoot, ".github/copilot-instructions.md"));
  }

  if (config.ides.includes("codex")) {
    files.push(resolvePath(projectRoot, "codex.md"));
  }

  // Hook files (always included)
  const lefthookFile = resolvePath(projectRoot, "lefthook.yml");
  const gitleaksFile = resolvePath(projectRoot, ".gitleaks.toml");
  files.push(lefthookFile, gitleaksFile);

  return files;
}
