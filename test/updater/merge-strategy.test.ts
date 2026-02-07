import { describe, it, expect } from 'vitest';
import { classifyFile, parseVersionFile, threeWayMerge } from '../../src/updater/merge-strategy.js';
import { sha256 } from '../../src/utils/filesystem.js';

describe('merge-strategy', () => {
  describe('classifyFile', () => {
    it('should classify knowledge files as user-owned', () => {
      expect(classifyFile('.ai-engineering/knowledge/learnings.md')).toBe('user-owned');
      expect(classifyFile('.ai-engineering/knowledge/patterns.md')).toBe('user-owned');
      expect(classifyFile('.ai-engineering/knowledge/decisions/001-api-design.md')).toBe('user-owned');
    });

    it('should classify hooks as framework-only', () => {
      expect(classifyFile('.ai-engineering/hooks/pre-tool.sh')).toBe('framework-only');
      expect(classifyFile('.ai-engineering/hooks/post-tool.sh')).toBe('framework-only');
    });

    it('should classify CLAUDE.md as compiled-output', () => {
      expect(classifyFile('CLAUDE.md')).toBe('compiled-output');
    });

    it('should classify copilot instructions as compiled-output', () => {
      expect(classifyFile('.github/copilot-instructions.md')).toBe('compiled-output');
    });

    it('should classify codex.md as compiled-output', () => {
      expect(classifyFile('codex.md')).toBe('compiled-output');
    });

    it('should classify config as user-customizable', () => {
      expect(classifyFile('.ai-engineering/config.yml')).toBe('user-customizable');
    });

    it('should classify lefthook as user-customizable', () => {
      expect(classifyFile('lefthook.yml')).toBe('user-customizable');
    });

    it('should classify commands as compiled-output', () => {
      expect(classifyFile('.claude/commands/ai-commit.md')).toBe('compiled-output');
    });

    it('should classify standards as compiled-output', () => {
      expect(classifyFile('.ai-engineering/standards/base.md')).toBe('compiled-output');
    });
  });

  describe('parseVersionFile', () => {
    it('should parse version and checksums', () => {
      const content = '0.1.0\nfile1.txt:abc123\nfile2.txt:def456\n';
      const checksums = parseVersionFile(content);

      expect(checksums.get('file1.txt')).toBe('abc123');
      expect(checksums.get('file2.txt')).toBe('def456');
    });

    it('should handle version-only content', () => {
      const checksums = parseVersionFile('0.1.0\n');
      expect(checksums.size).toBe(0);
    });

    it('should handle empty content', () => {
      const checksums = parseVersionFile('');
      expect(checksums.size).toBe(0);
    });
  });

  describe('threeWayMerge', () => {
    it('should replace if file unchanged from original', () => {
      const original = 'original content';
      const current = 'original content';
      const incoming = 'new content';
      const originalChecksum = sha256(original);

      const result = threeWayMerge(originalChecksum, current, incoming);
      expect(result.action).toBe('replace');
      expect(result.hasConflict).toBe(false);
      expect(result.content).toBe(incoming);
    });

    it('should skip if current matches new', () => {
      const current = 'same content';
      const incoming = 'same content';

      const result = threeWayMerge('different-checksum', current, incoming);
      expect(result.action).toBe('skip');
      expect(result.hasConflict).toBe(false);
    });

    it('should detect conflict when file was customized', () => {
      const original = 'original';
      const current = 'customized by user';
      const incoming = 'updated by framework';
      const originalChecksum = sha256(original);

      const result = threeWayMerge(originalChecksum, current, incoming);
      // Either merge or conflict
      expect(['merge', 'conflict']).toContain(result.action);
    });

    it('should generate conflict markers when cannot auto-merge', () => {
      const original = 'line1\nline2\nline3';
      const current = 'line1\nUSER CHANGE\nline3';
      const incoming = 'FRAMEWORK CHANGE\nline2\nline3';
      const originalChecksum = sha256(original);

      const result = threeWayMerge(originalChecksum, current, incoming);

      if (result.hasConflict && result.content) {
        expect(result.content).toContain('<<<<<<< CURRENT');
        expect(result.content).toContain('>>>>>>> INCOMING');
      }
    });
  });
});
