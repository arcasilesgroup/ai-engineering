import { describe, it, expect } from 'vitest';
import { parseSections, assembleSections, MARKERS } from '../../src/compiler/section-markers.js';

describe('section-markers', () => {
  describe('parseSections', () => {
    it('should extract framework and team from a file with markers', () => {
      const content = [
        '<!-- BEGIN:AI-FRAMEWORK:v0.1.0 -->',
        '',
        '# Framework Content',
        '',
        'Some standards here.',
        '',
        '<!-- END:AI-FRAMEWORK -->',
        '',
        '<!-- BEGIN:TEAM -->',
        '',
        '## Our Custom Rules',
        '',
        'Always use tabs.',
        '',
        '<!-- END:TEAM -->',
      ].join('\n');

      const result = parseSections(content);

      expect(result.frameworkContent).toBe('# Framework Content\n\nSome standards here.');
      expect(result.teamContent).toBe('## Our Custom Rules\n\nAlways use tabs.');
    });

    it('should treat legacy file (no markers) as all framework, empty team', () => {
      const content = '# Old CLAUDE.md\n\nSome legacy content.\n';

      const result = parseSections(content);

      expect(result.frameworkContent).toBe(content);
      expect(result.teamContent).toBe('');
    });

    it('should handle empty string', () => {
      const result = parseSections('');

      expect(result.frameworkContent).toBe('');
      expect(result.teamContent).toBe('');
    });

    it('should handle whitespace-only string', () => {
      const result = parseSections('   \n  \n  ');

      expect(result.frameworkContent).toBe('');
      expect(result.teamContent).toBe('');
    });

    it('should treat placeholder-only team section as empty', () => {
      const content = [
        '<!-- BEGIN:AI-FRAMEWORK:v0.1.0 -->',
        '',
        '# Content',
        '',
        '<!-- END:AI-FRAMEWORK -->',
        '',
        '<!-- BEGIN:TEAM -->',
        '',
        '<!-- Add your team-specific standards and customizations below -->',
        '',
        '<!-- END:TEAM -->',
      ].join('\n');

      const result = parseSections(content);

      expect(result.teamContent).toBe('');
    });

    it('should handle partial markers as legacy', () => {
      const content = '<!-- BEGIN:AI-FRAMEWORK:v0.1.0 -->\n\nContent without closing\n';

      const result = parseSections(content);

      expect(result.frameworkContent).toBe(content);
      expect(result.teamContent).toBe('');
    });

    it('should handle pre-release version in markers', () => {
      const content = [
        '<!-- BEGIN:AI-FRAMEWORK:v0.1.0-beta.1 -->',
        '',
        '# Content',
        '',
        '<!-- END:AI-FRAMEWORK -->',
        '',
        '<!-- BEGIN:TEAM -->',
        '',
        '## Team stuff',
        '',
        '<!-- END:TEAM -->',
      ].join('\n');

      const result = parseSections(content);

      expect(result.frameworkContent).toContain('# Content');
      expect(result.teamContent).toContain('## Team stuff');
    });
  });

  describe('assembleSections', () => {
    it('should produce well-formed output with team content', () => {
      const result = assembleSections('0.1.0', '# Framework', '## Team Rules\n\nUse tabs.');

      expect(result).toContain('<!-- BEGIN:AI-FRAMEWORK:v0.1.0 -->');
      expect(result).toContain('# Framework');
      expect(result).toContain('<!-- END:AI-FRAMEWORK -->');
      expect(result).toContain('<!-- BEGIN:TEAM -->');
      expect(result).toContain('## Team Rules');
      expect(result).toContain('Use tabs.');
      expect(result).toContain('<!-- END:TEAM -->');
      expect(result).not.toContain('Add your team-specific');
    });

    it('should include placeholder when team content is empty', () => {
      const result = assembleSections('0.1.0', '# Framework', '');

      expect(result).toContain('<!-- BEGIN:TEAM -->');
      expect(result).toContain('<!-- Add your team-specific standards and customizations below -->');
      expect(result).toContain('<!-- END:TEAM -->');
    });

    it('should include placeholder when team content is whitespace', () => {
      const result = assembleSections('0.1.0', '# Framework', '   \n  ');

      expect(result).toContain('<!-- Add your team-specific standards and customizations below -->');
    });

    it('should embed version in framework begin marker', () => {
      const result = assembleSections('1.2.3', '# Content', '');

      expect(result).toContain('<!-- BEGIN:AI-FRAMEWORK:v1.2.3 -->');
    });

    it('should produce output that round-trips through parseSections', () => {
      const framework = '# Project Standards\n\nSome rules.';
      const team = '## Our Overrides\n\nCustom stuff.';

      const assembled = assembleSections('0.1.0', framework, team);
      const parsed = parseSections(assembled);

      expect(parsed.frameworkContent).toBe(framework);
      expect(parsed.teamContent).toBe(team);
    });

    it('should produce output that round-trips with empty team', () => {
      const framework = '# Standards';

      const assembled = assembleSections('0.1.0', framework, '');
      const parsed = parseSections(assembled);

      expect(parsed.frameworkContent).toBe(framework);
      expect(parsed.teamContent).toBe('');
    });
  });

  describe('MARKERS', () => {
    it('should generate correct framework begin marker with version', () => {
      expect(MARKERS.FRAMEWORK_BEGIN('0.1.0')).toBe('<!-- BEGIN:AI-FRAMEWORK:v0.1.0 -->');
    });

    it('should have correct static markers', () => {
      expect(MARKERS.FRAMEWORK_END).toBe('<!-- END:AI-FRAMEWORK -->');
      expect(MARKERS.TEAM_BEGIN).toBe('<!-- BEGIN:TEAM -->');
      expect(MARKERS.TEAM_END).toBe('<!-- END:TEAM -->');
    });
  });
});
