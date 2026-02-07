import {
  readFile,
  listMarkdownFiles,
  fileExists,
  isDirectory,
  resolvePath,
} from "../utils/filesystem.js";
import { logger } from "../utils/logger.js";
import type { Config, Stack } from "../utils/config.js";

export interface AssembledContent {
  standards: string;
  agents: string;
  skills: string;
  security: string;
  testing: string;
  git: string;
}

export interface IntermediateRepresentation {
  config: Config;
  assembled: AssembledContent;
  stackSections: Map<Stack, string>;
  agentSections: Map<string, string>;
  skillSections: Map<string, string>;
}

let _packageRoot: string | null = null;

function getPackageRoot(): string {
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

function resolveContentPath(relativePath: string): string {
  const root = getPackageRoot();
  const fullPath = resolvePath(root, relativePath);
  if (!fileExists(fullPath) && !isDirectory(fullPath)) {
    throw new Error(
      `Content not found: ${relativePath}\n` +
        `  Resolved to: ${fullPath}\n` +
        `  Package root: ${root}`,
    );
  }
  return fullPath;
}

function readContentFile(relativePath: string): string {
  const fullPath = resolveContentPath(relativePath);
  return readFile(fullPath);
}

function assembleStackStandards(stack: Stack): string {
  const dir = resolveContentPath(`stacks/${stack}`);
  const files = listMarkdownFiles(dir);

  if (files.length === 0) {
    logger.warn(`No standards files found for stack: ${stack}`);
    return "";
  }

  const stackLabels: Record<Stack, string> = {
    "typescript-react": "TypeScript/React",
    dotnet: ".NET",
    python: "Python",
    cicd: "CI/CD",
  };

  const parts: string[] = [`## ${stackLabels[stack]} Standards\n`];

  for (const file of files.sort()) {
    const content = readFile(file);
    parts.push(content);
    parts.push("");
  }

  return parts.join("\n");
}

function assembleBase(): {
  standards: string;
  security: string;
  testing: string;
  git: string;
} {
  return {
    standards: readContentFile("stacks/_base/standards.md"),
    security: readContentFile("stacks/_base/security.md"),
    testing: readContentFile("stacks/_base/testing.md"),
    git: readContentFile("stacks/_base/git.md"),
  };
}

function assembleAgents(): Map<string, string> {
  const agents = new Map<string, string>();
  const dir = resolveContentPath("agents");
  const files = listMarkdownFiles(dir);

  for (const file of files) {
    const name = file.split("/").pop()?.replace(".md", "") ?? "";
    if (name === "_base") continue;
    agents.set(name, readFile(file));
  }

  return agents;
}

function assembleSkills(): Map<string, string> {
  const skills = new Map<string, string>();
  const dir = resolveContentPath("skills");

  const categories = ["sdlc", "git", "quality", "learning"];
  for (const category of categories) {
    const catDir = resolvePath(dir, category);
    const files = listMarkdownFiles(catDir);
    for (const file of files) {
      const name = file.split("/").pop()?.replace(".md", "") ?? "";
      skills.set(`${category}/${name}`, readFile(file));
    }
  }

  return skills;
}

export function assemble(config: Config): IntermediateRepresentation {
  logger.step(1, 3, "Assembling standards...");

  // Base standards
  const base = assembleBase();

  // Stack-specific standards
  const stackSections = new Map<Stack, string>();
  const stackParts: string[] = [];

  for (const stack of config.stacks) {
    const content = assembleStackStandards(stack);
    stackSections.set(stack, content);
    stackParts.push(content);
  }

  // Agents
  logger.step(2, 3, "Assembling agents and skills...");
  const baseAgent = readContentFile("agents/_base.md");
  const agentSections = assembleAgents();

  let agentsContent = "# Agent Definitions\n\n";
  agentsContent += "## Shared Agent Capabilities\n\n" + baseAgent + "\n\n";
  for (const [_name, content] of agentSections) {
    agentsContent += content + "\n\n";
  }

  // Skills
  const skillSections = assembleSkills();
  let skillsContent = "# Available Skills\n\n";
  for (const [_name, content] of skillSections) {
    skillsContent += content + "\n\n";
  }

  logger.step(3, 3, "Assembly complete");

  // Validate assembly produced real content
  const emptyFields: string[] = [];
  if (!base.standards.trim()) emptyFields.push("standards");
  if (!base.security.trim()) emptyFields.push("security");
  if (!base.testing.trim()) emptyFields.push("testing");
  if (!base.git.trim()) emptyFields.push("git");
  if (skillSections.size === 0) emptyFields.push("skills");
  if (agentSections.size === 0) emptyFields.push("agents");

  if (emptyFields.length > 0) {
    logger.warn(
      `Assembly produced empty content for: ${emptyFields.join(", ")}`,
    );
    logger.warn(`Package root resolved to: ${getPackageRoot()}`);
  }

  // Combine all standards
  const allStandards = [
    "# Coding Standards\n",
    "## Universal Standards\n",
    base.standards,
    "\n",
    ...stackParts,
  ].join("\n");

  return {
    config,
    assembled: {
      standards: allStandards,
      agents: agentsContent,
      skills: skillsContent,
      security: base.security,
      testing: base.testing,
      git: base.git,
    },
    stackSections,
    agentSections,
    skillSections,
  };
}
