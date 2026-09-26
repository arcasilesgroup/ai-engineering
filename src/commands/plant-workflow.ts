// Plant standing workflow files when absent. Never overwrites an existing path.

import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { embeddedTemplate } from "../embed.ts";

const PLANTS: Array<{ path: string; template: string }> = [
  { path: "LEARNINGS.md", template: "LEARNINGS.md.tpl" },
  { path: "FILEMAP.md", template: "FILEMAP.md.tpl" },
  { path: "PERMISSIONS.md", template: "PERMISSIONS.md.tpl" },
  { path: "CHANGELOG.md", template: "CHANGELOG.md.tpl" },
  { path: ".ai-engineering/PRD.html", template: "PRD.html.tpl" },
  { path: ".ai-engineering/workflow/checkpoints/viewer.html", template: "viewer.html.tpl" },
];

/** Write each standing workflow file only when the path is missing. */
export function plantWorkflowFiles(root: string): void {
  for (const plant of PLANTS) {
    const absolute = join(root, plant.path);
    if (existsSync(absolute)) continue;
    mkdirSync(dirname(absolute), { recursive: true });
    writeFileSync(absolute, embeddedTemplate(plant.template));
  }
}
