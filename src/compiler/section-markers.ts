export const MARKERS = {
  FRAMEWORK_BEGIN: (version: string) => `<!-- BEGIN:AI-FRAMEWORK:v${version} -->`,
  FRAMEWORK_END: '<!-- END:AI-FRAMEWORK -->',
  TEAM_BEGIN: '<!-- BEGIN:TEAM -->',
  TEAM_END: '<!-- END:TEAM -->',
} as const;

const FRAMEWORK_BEGIN_PATTERN = /^<!-- BEGIN:AI-FRAMEWORK:v[\d.]+[\w.-]* -->$/m;
const FRAMEWORK_END_PATTERN = /^<!-- END:AI-FRAMEWORK -->$/m;
const TEAM_BEGIN_PATTERN = /^<!-- BEGIN:TEAM -->$/m;
const TEAM_END_PATTERN = /^<!-- END:TEAM -->$/m;

export interface ParsedSections {
  frameworkContent: string;
  teamContent: string;
}

const TEAM_PLACEHOLDER = '<!-- Add your team-specific standards and customizations below -->';

export function parseSections(fileContent: string): ParsedSections {
  if (!fileContent || fileContent.trim() === '') {
    return { frameworkContent: '', teamContent: '' };
  }

  const hasFrameworkBegin = FRAMEWORK_BEGIN_PATTERN.test(fileContent);
  const hasFrameworkEnd = FRAMEWORK_END_PATTERN.test(fileContent);
  const hasTeamBegin = TEAM_BEGIN_PATTERN.test(fileContent);
  const hasTeamEnd = TEAM_END_PATTERN.test(fileContent);

  // Legacy file without markers — treat entire content as framework, team empty
  if (!hasFrameworkBegin || !hasFrameworkEnd || !hasTeamBegin || !hasTeamEnd) {
    return { frameworkContent: fileContent, teamContent: '' };
  }

  // Extract framework content (between BEGIN and END markers)
  const fwBeginMatch = FRAMEWORK_BEGIN_PATTERN.exec(fileContent);
  const fwEndMatch = FRAMEWORK_END_PATTERN.exec(fileContent);
  const frameworkContent = fileContent
    .slice(fwBeginMatch!.index + fwBeginMatch![0].length, fwEndMatch!.index)
    .trim();

  // Extract team content (between TEAM BEGIN and TEAM END markers)
  const teamBeginMatch = TEAM_BEGIN_PATTERN.exec(fileContent);
  const teamEndMatch = TEAM_END_PATTERN.exec(fileContent);
  let teamContent = fileContent
    .slice(teamBeginMatch!.index + teamBeginMatch![0].length, teamEndMatch!.index)
    .trim();

  // If team section only contains the placeholder, treat as empty
  if (teamContent.trim() === TEAM_PLACEHOLDER) {
    teamContent = '';
  }

  return { frameworkContent, teamContent };
}

export function assembleSections(version: string, frameworkContent: string, teamContent: string): string {
  const lines: string[] = [];

  lines.push(MARKERS.FRAMEWORK_BEGIN(version));
  lines.push('');
  lines.push(frameworkContent);
  lines.push('');
  lines.push(MARKERS.FRAMEWORK_END);
  lines.push('');
  lines.push(MARKERS.TEAM_BEGIN);
  lines.push('');

  if (teamContent.trim()) {
    lines.push(teamContent);
  } else {
    lines.push(TEAM_PLACEHOLDER);
  }

  lines.push('');
  lines.push(MARKERS.TEAM_END);
  lines.push('');

  return lines.join('\n');
}
