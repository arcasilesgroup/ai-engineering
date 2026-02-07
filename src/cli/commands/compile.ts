import { setVerbose, logger } from "../../utils/logger.js";
import { loadConfig } from "../../utils/config.js";
import { fileExists, resolvePath } from "../../utils/filesystem.js";
import { compile } from "../../compiler/index.js";

interface CompileOptions {
  verbose?: boolean;
}

export async function compileCommand(options: CompileOptions): Promise<void> {
  if (options.verbose) setVerbose(true);

  const projectRoot = process.cwd();
  const configPath = resolvePath(projectRoot, ".ai-engineering/config.yml");

  if (!fileExists(configPath)) {
    logger.error(
      "No ai-engineering config found. Run `npx ai-engineering init` first.",
    );
    process.exit(1);
  }

  const config = loadConfig(projectRoot);

  logger.header("Recompiling Standards");
  await compile(projectRoot, config);

  logger.blank();
  logger.success("Recompilation complete");
}
