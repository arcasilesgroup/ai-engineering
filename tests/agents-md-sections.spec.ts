/**
 * Workflow kit checkpoint 4 — AGENTS.md template sections and doctor ceiling.
 */
import { describe, test, expect } from "bun:test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const ROOT = join(import.meta.dir, "..");
const TEMPLATE = join(ROOT, "templates", "AGENTS.md.tpl");
const DOCTOR = join(ROOT, "src", "commands", "doctor.ts");
const SKILL = join(ROOT, "skills", "ai-agents-md", "SKILL.md");

const REQUIRED_HEADINGS = [
  "Project config",
  "Architecture rules",
  "Shared helpers",
  "Git workflow",
] as const;

describe("workflow kit — AGENTS.md sections and doctor ceiling", () => {
  test("template contains the four required headings", () => {
    const template = readFileSync(TEMPLATE, "utf8");
    for (const heading of REQUIRED_HEADINGS) {
      expect(template).toContain(`## ${heading}`);
    }
  });

  test("Where to work matches the template section", () => {
    function section(markdown: string): string | undefined {
      const sectionStart = markdown.indexOf("## Where to work\n");
      if (sectionStart === -1) return undefined;
      const contentStart = sectionStart + "## Where to work\n".length;
      const remaining = markdown.slice(contentStart);
      const nextHeading = remaining.search(/\n## /);
      return (nextHeading === -1 ? remaining : remaining.slice(0, nextHeading)).trim();
    }

    const agents = readFileSync(join(ROOT, "AGENTS.md"), "utf8");
    const template = readFileSync(TEMPLATE, "utf8");
    const agentsSection = section(agents);
    const templateSection = section(template);

    expect(agentsSection).toBeDefined();
    expect(templateSection).toBeDefined();
    expect(agentsSection).toBe(templateSection);
  });

  test("Shared helpers mentions codegraph", () => {
    const template = readFileSync(TEMPLATE, "utf8");
    const sharedHelpers = template.split("## Shared helpers")[1] ?? "";
    const nextHeading = sharedHelpers.search(/\n## /);
    const section = nextHeading === -1 ? sharedHelpers : sharedHelpers.slice(0, nextHeading);
    expect(section.toLowerCase()).toContain("codegraph");
  });

  test("doctor uses a 120-line AGENTS.md ceiling", () => {
    const doctor = readFileSync(DOCTOR, "utf8");
    expect(doctor).toContain("120");
    expect(doctor).not.toContain("lines <= 80");
  });

  test("ai-agents-md skill names the four headings in its section list", () => {
    const skill = readFileSync(SKILL, "utf8");
    for (const heading of REQUIRED_HEADINGS) {
      expect(skill).toContain(heading);
    }
  });
});
