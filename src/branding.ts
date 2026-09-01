// §22 branding — the terminal identity of ai-eng. No color library: three
// dependencies is the cap and all of them come from Clack. The palette is the
// SVG banner's teal (#00D4AA); the ASCII mark is the original v1 CLI logo, restored.
// Every helper degrades to plain text under NO_COLOR or a non-TTY stdout.

const TEAL = "\x1b[38;2;0;212;170m";
const TEAL_DIM = "\x1b[2;38;2;0;212;170m";
const DIM = "\x1b[2m";
const BOLD = "\x1b[1m";
const RESET = "\x1b[0m";

function ansiEnabled(): boolean {
  return Boolean(process.stdout.isTTY) && !process.env["NO_COLOR"];
}

/** The full logo block — the original CLI show_logo, restored. */
export function showLogo(version: string): void {
  const on = ansiEnabled();
  const lines = [
    on ? `${TEAL_DIM}┌─                                  ─┐${RESET}` : `┌─                                  ─┐`,
    on ? `    ${TEAL}{${RESET} ${BOLD}ai${RESET} ${TEAL}}${RESET}   ${TEAL}e n g i n e e r i n g${RESET}` : `    { ai }   e n g i n e e r i n g`,
    on ? `${TEAL_DIM}└─                                  ─┘${RESET}` : `└─                                  ─┘`,
    on ? `${DIM}v${version} · AI Governance Framework${RESET}` : `v${version} · AI Governance Framework`,
  ];
  process.stdout.write(`${lines.join("\n")}\n`);
}

/** The compact one-line banner — the original CLI show_banner. */
export function showBanner(version: string): void {
  const on = ansiEnabled();
  process.stdout.write(
    on
      ? `  ${TEAL}{${RESET} ${BOLD}ai${RESET} ${TEAL}}${RESET} ${TEAL}engineering${RESET}  ${DIM}· v${version}${RESET}\n`
      : `  { ai } engineering  · v${version}\n`,
  );
}

/** The ✓ line grammar of the planted checklist: `✓ <target> → <result> · <reason>`. */
export function okLine(target: string, result: string, reason?: string): string {
  const on = ansiEnabled();
  const check = on ? `${TEAL}✓${RESET}` : "✓";
  const arrow = on ? `${DIM}→${RESET}` : "→";
  const sep = reason ? ` ${on ? `${DIM}·${RESET} ${DIM}${reason}${RESET}` : `· ${reason}`}` : "";
  return `${check} ${target} ${arrow} ${result}${sep}`;
}
