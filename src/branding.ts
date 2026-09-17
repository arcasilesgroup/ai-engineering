// §22 branding — the terminal identity of ai-eng. The palette is NOT declared here:
// it is generated from brand/tokens.json into src/theme.ts, so the CLI, the docs and
// the landing site can never drift into three different greens.
//
// The banner frame carries the brand hex, so it paints a truecolor SGR sequence by
// hand — styleText (node:util) only accepts named formats and a hex would crash on
// strict runtimes (Bun 1.3) and drop the colour on lenient ones (Bun 1.4, Node).
// It degrades to plain text on a non-TTY stdout or under NO_COLOR — the same rule
// the rest of the frame follows. BANNER_META and everything else go through
// styleText, which handles the named formats.
//
// Deliberate restraint: the brand green is only ever the banner frame and its braces.
// The wordmark and everything else stay at the terminal's default foreground, because
// the terminal owns its background and #00ED64 on a light terminal is unreadable.

import { styleText } from "node:util";
import { BANNER_GREEN, BANNER_META } from "./theme.ts";

/** True `#rrggbb` → SGR foreground params ("38;2;r;g;b"), or null if not a hex. */
const sgr = (hex: string): string | null => {
  if (!/^#[0-9a-fA-F]{6}$/.test(hex)) return null;
  const n = parseInt(hex.slice(1), 16);
  return `38;2;${(n >> 16) & 255};${(n >> 8) & 255};${n & 255}`;
};

/** Paint text in a raw colour value (hex → truecolor SGR, named → styleText),
 *  or return it untouched when stdout is not a TTY or NO_COLOR is set. */
const paint = (colour: string, text: string): string => {
  const params = sgr(colour);
  if (process.stdout.isTTY && !process.env["NO_COLOR"]) {
    if (params !== null) return `\u001B[${params}m${text}\u001B[39m`;
    // styleText's type advertises hex but its runtime validation (Bun 1.3) rejects
    // it; sgr() already routed every hex here, so what is left is a named format.
    const named = colour as Parameters<typeof styleText>[0];
    return styleText(named, text);
  }
  return text;
};

/** The CLI logo block. */
export function showLogo(version: string): void {
  const line = (left: string, right: string): string =>
    `${paint(BANNER_GREEN, left)}                                  ${paint(BANNER_GREEN, right)}`;

  process.stdout.write(
    [
      line("┌─", "─┐"),
      `    ${paint(BANNER_GREEN, "{")} ${styleText("bold", "ai")} ${paint(BANNER_GREEN, "}")}   e n g i n e e r i n g`,
      line("└─", "─┘"),
      styleText(BANNER_META, `v${version} · install · guard · prove`),
    ].join("\n") + "\n",
  );
}
