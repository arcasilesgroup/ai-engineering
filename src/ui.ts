// src/ui.ts — the frame layer (cli-ux-14 work point 01). Every human verb
// presents through here; machine verbs (chain|git|wrap|spec) never import it:
// their stdout is a byte-stable contract (§07). Wraps clack 1.7.0 primitives;
// NO_COLOR and non-TTY degrade because clack honors colors, and ui.spinner()
// covers the cursor-control codes clack emits even under NO_COLOR.
import { intro, outro, log, cancel, spinner as clackSpinner } from "@clack/prompts";

/** Open the frame: `┌  <title>` with repo/runtime context baked by the caller. */
export function frame(title: string): void {
  intro(title);
}

/** Close the frame: `└  <message>`. */
export function end(message: string): void {
  outro(message);
}

/** `│  ✓ <message>` */
export function ok(message: string): void {
  log.success(message);
}

/** `│  ◆ <message>` — neutral progress or informational line inside the frame. */
export function info(message: string): void {
  log.info(message);
}

/** `│  ▲ <message>` */
export function warn(message: string): void {
  log.warn(message);
}

/** `│  ■ <message>` */
export function fail(message: string): void {
  log.error(message);
}

/** Cancelled prompt: print the frame-closing cancel line, no error theater. */
export function cancelled(message = "Cancelled."): void {
  cancel(message);
}

/** Colored final tally: `12 checks: 9 OK · 3 WARN · 0 FAIL` with state colors. */
export function summary(okCount: number, warnCount: number, failCount: number): void {
  const parts = [
    `${okCount} ${okCount === 1 ? "check" : "checks"}: ${okCount} OK`,
    `${warnCount} WARN`,
    `${failCount} FAIL`,
  ];
  info(parts.join(" · "));
}

/** Spinner that fully degrades off-TTY: clack's emits cursor hide/show ANSI
 *  codes even under NO_COLOR (cursor control is not a color), so a piped or
 *  CI stdout gets a silent no-op instead. */
export function spinner() {
  if (!process.stdout.isTTY) {
    return { start: (_message?: string) => {}, stop: (_message?: string) => {} };
  }
  return clackSpinner();
}

/** The one-line version notice (§14.0): printed once, at the end, cached by caller. */
export function notice(latest: string, current: string): void {
  warn(`${latest} available → ai-eng upgrade · changelog: CHANGELOG.md (current: ${current})`);
}
