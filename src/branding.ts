// §22 branding — the terminal identity of ai-eng. Colors come from node:util's
// styleText: no palette to maintain, and it degrades to plain text on a non-TTY
// stdout or under NO_COLOR, the same rule the rest of the frame follows.

import { styleText } from "node:util";

const TEAL = "#00D4AA";

/** The full logo block — the original CLI logo. */
export function showLogo(version: string): void {
  const teal = (text: string): string => styleText(TEAL, text);
  process.stdout.write(
    [
      `${teal("┌─")}                                  ${teal("─┐")}`,
      `    ${teal("{")} ${styleText("bold", "ai")} ${teal("}")}   ${teal("e n g i n e e r i n g")}`,
      `${teal("└─")}                                  ${teal("─┘")}`,
      styleText("dim", `v${version} · AI Governance Framework`),
    ].join("\n") + "\n",
  );
}
