import { logger } from '../utils/logger.js';
import { writeFile, readFileOrNull, resolvePath } from '../utils/filesystem.js';
import { assemble } from './assembler.js';
import { parseSections, assembleSections } from './section-markers.js';
import { compileClaudeCode, writeClaudeCodeOutput } from './targets/claude-code.js';
import { compileCopilot, writeCopilotOutput } from './targets/copilot.js';
import { compileCodex, writeCodexOutput } from './targets/codex.js';
import type { Config } from '../utils/config.js';
import type { IntermediateRepresentation } from './assembler.js';

export { assemble } from './assembler.js';
export type { IntermediateRepresentation } from './assembler.js';

export function writeMarkedOutput(filePath: string, frameworkContent: string, version: string): void {
  const existing = readFileOrNull(filePath);
  let teamContent = '';

  if (existing) {
    const parsed = parseSections(existing);
    teamContent = parsed.teamContent;
  }

  const output = assembleSections(version, frameworkContent, teamContent);
  writeFile(filePath, output);
}

export async function compile(projectRoot: string, config: Config): Promise<IntermediateRepresentation> {
  // Step 1: Assemble all content
  const ir = assemble(config);

  // Step 2: Write compiled standards to .ai-engineering/standards/
  writeCompiledStandards(projectRoot, ir);

  // Step 3: Compile and write IDE-specific outputs
  for (const ide of config.ides) {
    switch (ide) {
      case 'claude-code': {
        const output = compileClaudeCode(ir, projectRoot);
        // Write CLAUDE.md with section markers
        writeMarkedOutput(resolvePath(projectRoot, 'CLAUDE.md'), output.claudeMd, config.version);
        logger.success('Generated CLAUDE.md');
        // Write commands + settings (no markers needed)
        writeClaudeCodeOutput(output, projectRoot);
        break;
      }
      case 'copilot': {
        const output = compileCopilot(ir);
        // Write copilot-instructions.md with section markers
        writeMarkedOutput(
          resolvePath(projectRoot, '.github/copilot-instructions.md'),
          output.instructionsMd,
          config.version,
        );
        writeCopilotOutput(output, projectRoot);
        break;
      }
      case 'codex': {
        const output = compileCodex(ir);
        // Write codex.md with section markers
        writeMarkedOutput(resolvePath(projectRoot, 'codex.md'), output.codexMd, config.version);
        writeCodexOutput(output, projectRoot);
        break;
      }
    }
  }

  logger.success('Compilation complete');
  return ir;
}

function writeCompiledStandards(projectRoot: string, ir: IntermediateRepresentation): void {
  const standardsDir = resolvePath(projectRoot, '.ai-engineering/standards');

  // Write base standards
  writeFile(resolvePath(standardsDir, 'base.md'), ir.assembled.standards);

  // Write per-stack compiled standards
  for (const [stack, content] of ir.stackSections) {
    writeFile(resolvePath(standardsDir, `${stack}.md`), content);
  }

  logger.success(`Wrote compiled standards to .ai-engineering/standards/`);
}
