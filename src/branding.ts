// §22 branding — the terminal identity of ai-eng. The palette is NOT declared here:
// it is generated from brand/tokens.json into src/theme.ts, so the CLI, the docs and
// the landing site can never drift into three different greens.
//
// Colours come from node:util's styleText, which degrades to plain text on a non-TTY
// stdout or under NO_COLOR — the same rule the rest of the frame follows.
//
// Deliberate restraint: the brand green is only ever the banner frame and its braces.
// The wordmark and everything else stay at the terminal's default foreground, because
// the terminal owns its background and #00ED64 on a light terminal is unreadable.

import { styleText } from "node:util";
import { BANNER_GREEN, BANNER_META } from "./theme.ts";

/** The CLI logo block. */
export function showLogo(version: string): void {
  const line = (left: string, right: string): string =>
    `${styleText(BANNER_GREEN, left)}                                  ${styleText(BANNER_GREEN, right)}`;

  process.stdout.write(
    [
      line("┌─", "─┐"),
      `    ${styleText(BANNER_GREEN, "{")} ${styleText("bold", "ai")} ${styleText(BANNER_GREEN, "}")}   e n g i n e e r i n g`,
      line("└─", "─┘"),
      styleText(BANNER_META, `v${version} · install · guard · prove`),
    ].join("\n") + "\n",
  );
}
