import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mkdtempSync, rmSync, readFileSync, writeFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { execSync } from 'node:child_process';
import { createDefaultConfig, saveConfig } from '../../src/utils/config.js';
import { compile } from '../../src/compiler/index.js';
import { MARKERS, parseSections } from '../../src/compiler/section-markers.js';

describe('lifecycle e2e', () => {
  let tempDir: string;

  beforeEach(() => {
    tempDir = mkdtempSync(join(tmpdir(), 'ai-eng-lifecycle-'));
    execSync('git init', { cwd: tempDir, stdio: 'pipe' });
    execSync('git config user.email "test@test.com"', { cwd: tempDir, stdio: 'pipe' });
    execSync('git config user.name "Test"', { cwd: tempDir, stdio: 'pipe' });
  });

  afterEach(() => {
    rmSync(tempDir, { recursive: true, force: true });
  });

  it('should produce section markers on init with claude-code', async () => {
    const config = createDefaultConfig({ ides: ['claude-code'] });
    saveConfig(tempDir, config);

    await compile(tempDir, config);

    const claudeMd = readFileSync(join(tempDir, 'CLAUDE.md'), 'utf-8');

    expect(claudeMd).toContain('<!-- BEGIN:AI-FRAMEWORK:v0.1.0 -->');
    expect(claudeMd).toContain('<!-- END:AI-FRAMEWORK -->');
    expect(claudeMd).toContain('<!-- BEGIN:TEAM -->');
    expect(claudeMd).toContain('<!-- END:TEAM -->');
    expect(claudeMd).toContain('<!-- Add your team-specific standards and customizations below -->');
  });

  it('should preserve TEAM section content on recompile', async () => {
    const config = createDefaultConfig({ ides: ['claude-code'] });
    saveConfig(tempDir, config);

    // First compile
    await compile(tempDir, config);

    // Edit the TEAM section
    const claudePath = join(tempDir, 'CLAUDE.md');
    let content = readFileSync(claudePath, 'utf-8');
    content = content.replace(
      '<!-- Add your team-specific standards and customizations below -->',
      '## Our Custom Rules\n\nAlways use 2-space indentation.\nPrefer named exports.',
    );
    writeFileSync(claudePath, content, 'utf-8');

    // Recompile
    await compile(tempDir, config);

    const updated = readFileSync(claudePath, 'utf-8');
    const parsed = parseSections(updated);

    // Team content should be preserved
    expect(parsed.teamContent).toContain('Our Custom Rules');
    expect(parsed.teamContent).toContain('2-space indentation');
    expect(parsed.teamContent).toContain('named exports');

    // Framework content should still be fresh
    expect(parsed.frameworkContent).toContain('Project Standards');
    expect(parsed.frameworkContent).toContain('DANGER ZONE');
  });

  it('should handle legacy file without markers (backward compat)', async () => {
    const config = createDefaultConfig({ ides: ['claude-code'] });
    saveConfig(tempDir, config);

    // Write a legacy CLAUDE.md without markers
    const claudePath = join(tempDir, 'CLAUDE.md');
    writeFileSync(claudePath, '# Old CLAUDE.md\n\nLegacy content here.\n', 'utf-8');

    // Compile should add markers and replace framework content
    await compile(tempDir, config);

    const content = readFileSync(claudePath, 'utf-8');

    expect(content).toContain('<!-- BEGIN:AI-FRAMEWORK:v0.1.0 -->');
    expect(content).toContain('<!-- END:AI-FRAMEWORK -->');
    expect(content).toContain('<!-- BEGIN:TEAM -->');
    expect(content).toContain('<!-- END:TEAM -->');
    // Legacy content is treated as framework and replaced by new framework content
    expect(content).not.toContain('Old CLAUDE.md');
    expect(content).toContain('Project Standards');
  });

  it('should produce markers for all 3 IDEs on multi-IDE init', async () => {
    const config = createDefaultConfig({
      ides: ['claude-code', 'copilot', 'codex'],
    });
    saveConfig(tempDir, config);

    await compile(tempDir, config);

    // Check CLAUDE.md
    const claudeMd = readFileSync(join(tempDir, 'CLAUDE.md'), 'utf-8');
    expect(claudeMd).toContain(MARKERS.FRAMEWORK_BEGIN('0.1.0'));
    expect(claudeMd).toContain(MARKERS.FRAMEWORK_END);
    expect(claudeMd).toContain(MARKERS.TEAM_BEGIN);
    expect(claudeMd).toContain(MARKERS.TEAM_END);

    // Check copilot-instructions.md
    const copilotMd = readFileSync(join(tempDir, '.github/copilot-instructions.md'), 'utf-8');
    expect(copilotMd).toContain(MARKERS.FRAMEWORK_BEGIN('0.1.0'));
    expect(copilotMd).toContain(MARKERS.FRAMEWORK_END);
    expect(copilotMd).toContain(MARKERS.TEAM_BEGIN);
    expect(copilotMd).toContain(MARKERS.TEAM_END);

    // Check codex.md
    const codexMd = readFileSync(join(tempDir, 'codex.md'), 'utf-8');
    expect(codexMd).toContain(MARKERS.FRAMEWORK_BEGIN('0.1.0'));
    expect(codexMd).toContain(MARKERS.FRAMEWORK_END);
    expect(codexMd).toContain(MARKERS.TEAM_BEGIN);
    expect(codexMd).toContain(MARKERS.TEAM_END);
  });

  it('should include Multi-IDE Sync instruction in generated content', async () => {
    const config = createDefaultConfig({
      ides: ['claude-code', 'copilot', 'codex'],
    });
    saveConfig(tempDir, config);

    await compile(tempDir, config);

    const claudeMd = readFileSync(join(tempDir, 'CLAUDE.md'), 'utf-8');
    expect(claudeMd).toContain('## Multi-IDE Sync');
    expect(claudeMd).toContain('copilot-instructions.md');
    expect(claudeMd).toContain('codex.md');

    const copilotMd = readFileSync(join(tempDir, '.github/copilot-instructions.md'), 'utf-8');
    expect(copilotMd).toContain('## Multi-IDE Sync');
    expect(copilotMd).toContain('CLAUDE.md');
    expect(copilotMd).toContain('codex.md');

    const codexMd = readFileSync(join(tempDir, 'codex.md'), 'utf-8');
    expect(codexMd).toContain('## Multi-IDE Sync');
    expect(codexMd).toContain('CLAUDE.md');
    expect(codexMd).toContain('copilot-instructions.md');
  });

  it('should preserve TEAM across all IDEs independently', async () => {
    const config = createDefaultConfig({
      ides: ['claude-code', 'copilot', 'codex'],
    });
    saveConfig(tempDir, config);

    // First compile
    await compile(tempDir, config);

    // Edit TEAM in each file with different content
    const files = [
      { path: join(tempDir, 'CLAUDE.md'), team: '## Claude Team Rule\n\nCustom for Claude.' },
      { path: join(tempDir, '.github/copilot-instructions.md'), team: '## Copilot Team Rule\n\nCustom for Copilot.' },
      { path: join(tempDir, 'codex.md'), team: '## Codex Team Rule\n\nCustom for Codex.' },
    ];

    for (const file of files) {
      let content = readFileSync(file.path, 'utf-8');
      content = content.replace(
        '<!-- Add your team-specific standards and customizations below -->',
        file.team,
      );
      writeFileSync(file.path, content, 'utf-8');
    }

    // Recompile
    await compile(tempDir, config);

    // Verify each file preserved its own TEAM content
    for (const file of files) {
      const content = readFileSync(file.path, 'utf-8');
      const parsed = parseSections(content);
      expect(parsed.teamContent).toContain(file.team);
    }
  });
});
