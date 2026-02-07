import * as p from "@clack/prompts";
import { setVerbose, logger } from "../../utils/logger.js";
import { autoDetect } from "../../utils/detect.js";
import { getGitInfo, initGitRepo } from "../../utils/git.js";
import { createDefaultConfig, saveConfig } from "../../utils/config.js";
import { fileExists, resolvePath } from "../../utils/filesystem.js";
import { runPlatformCheck } from "../../installer/platform-check.js";
import { setupBranches } from "../../installer/branch-setup.js";
import { compile } from "../../compiler/index.js";
import { install } from "../../installer/index.js";
import { promptStackSelect } from "../prompts/stack-select.js";
import { promptIDESelect } from "../prompts/ide-select.js";
import type { Stack, IDE, Config } from "../../utils/config.js";

interface InitOptions {
  stack?: string[];
  ide?: string[];
  yes?: boolean;
  force?: boolean;
  verbose?: boolean;
}

export async function initCommand(options: InitOptions): Promise<void> {
  if (options.verbose) setVerbose(true);

  const projectRoot = process.cwd();

  // Check if already initialized
  if (
    fileExists(resolvePath(projectRoot, ".ai-engineering/config.yml")) &&
    !options.force
  ) {
    logger.warn("ai-engineering is already initialized in this project.");
    logger.info(
      "Use 'npx ai-engineering compile' to recompile, or 'npx ai-engineering init --force' to re-initialize.",
    );
    return;
  }

  p.intro("ai-engineering — AI coding with enforcement");

  // Step 1: Git check
  let gitInfo = getGitInfo(projectRoot);
  if (!gitInfo.isGitRepo) {
    if (options.yes) {
      initGitRepo(projectRoot);
      gitInfo = getGitInfo(projectRoot);
    } else {
      const shouldInit = await p.confirm({
        message: "No git repository found. Initialize one?",
        initialValue: true,
      });
      if (p.isCancel(shouldInit) || !shouldInit) {
        p.cancel("ai-engineering requires a git repository.");
        process.exit(1);
      }
      initGitRepo(projectRoot);
      gitInfo = getGitInfo(projectRoot);
    }
  }

  // Step 2: Auto-detect
  const detected = autoDetect(projectRoot);
  const platform = gitInfo.platform;

  // Step 3: Gather selections (interactive or CLI flags)
  let stacks: Stack[];
  let ides: IDE[];

  if (options.yes) {
    stacks = (options.stack as Stack[]) ?? detected.stacks;
    ides = (options.ide as IDE[]) ?? detected.ides;

    if (stacks.length === 0) stacks = ["typescript-react"];
    if (ides.length === 0) ides = ["claude-code"];
  } else {
    stacks = await promptStackSelect(detected.stacks);
    ides = await promptIDESelect(detected.ides);
  }

  logger.blank();
  logger.header("Configuration");
  logger.info(`Stacks: ${stacks.join(", ")}`);
  logger.info(`IDEs: ${ides.join(", ")}`);
  logger.info(`Platform: ${platform}`);

  // Step 4: Platform check
  logger.blank();
  logger.header("Platform Check");
  const platformResult = runPlatformCheck(stacks, platform);

  // Step 5: Branch setup
  logger.blank();
  logger.header("Branch Setup");
  const branchResult = setupBranches(
    platformResult.defaultBranch,
    options.yes ?? false,
  );

  // Step 6: Create config
  const config: Config = createDefaultConfig({
    stacks,
    ides,
    platform,
    branches: branchResult.config,
  });

  saveConfig(projectRoot, config);
  logger.success("Configuration saved to .ai-engineering/config.yml");

  // Step 7: Compile standards and generate IDE files
  logger.blank();
  logger.header("Compiling Standards");
  await compile(projectRoot, config);

  // Step 8: Install hooks and gates
  logger.blank();
  logger.header("Installing Enforcement");
  await install(projectRoot, config);

  // Summary
  logger.blank();
  logger.header("Setup Complete");
  logger.success("ai-engineering is ready!");
  logger.blank();

  const generatedFiles: string[] = [];
  generatedFiles.push(".ai-engineering/config.yml");
  if (ides.includes("claude-code"))
    generatedFiles.push(
      "CLAUDE.md",
      ".claude/commands/*",
      ".claude/settings.json",
    );
  if (ides.includes("copilot"))
    generatedFiles.push(".github/copilot-instructions.md");
  if (ides.includes("codex")) generatedFiles.push("codex.md");
  generatedFiles.push("lefthook.yml", ".gitleaks.toml");

  logger.info("Generated files:");
  logger.list(generatedFiles);

  if (branchResult.warnings.length > 0 || platformResult.warnings.length > 0) {
    logger.blank();
    logger.warn("Warnings:");
    logger.list([...platformResult.warnings, ...branchResult.warnings]);
  }

  logger.blank();
  logger.info("Next steps:");
  logger.list([
    "Review the generated configuration files",
    'Commit the changes: git add . && git commit -m "feat: initialize ai-engineering"',
    "Start coding with AI enforcement active!",
  ]);

  p.outro("Happy engineering!");
}
