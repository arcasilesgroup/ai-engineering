// src/ui.ts — the frame layer (cli-ux-14 work point 01). Every human verb
// presents through here; machine verbs (chain|git|wrap|spec) never import it:
// their stdout is a byte-stable contract (§07). Wraps clack 1.7.0 primitives;
import { intro, outro, log, cancel, spinner as clackSpinner, confirm } from "@clack/prompts";
import { styleText } from "node:util";
import { PassThrough } from "node:stream";
// NO_COLOR and non-TTY degrade because clack honors colors, and ui.spinner()
// covers the cursor-control codes clack emits even under NO_COLOR.

/** Open the frame: `┌  <title>` with repo/runtime context baked by the caller. */
export function frame(title: string): void {
  intro(title);
}

/** Close the frame: `└  <message>`. */
export function end(message: string): void {
  outro(message);
}

/** The mockup's line grammar (§14.2): `✓` done, `✗` bad, `▲` attention,
 *  `◆` action. clack's defaults (◆/■/▲) read as noise; the symbol option
 *  pins the mark while the frame spine stays clack's. */
export function ok(message: string): void {
  log.message(message, { symbol: styleText("green", "✓") });
}

/** `│  ◆ <message>` — the action/progress mark; neutral inside the frame. */
export function info(message: string): void {
  log.message(message, { symbol: styleText("cyan", "◆") });
}

/** `│  ▲ <message>` — attention; the frame holds, only a security or quality
 *  failure blocks the step (§12). */
export function warn(message: string): void {
  log.message(message, { symbol: styleText("yellow", "▲") });
}

/** `│  ✗ <message>` — red error; the one state that blocks. */
export function fail(message: string): void {
  log.message(message, { symbol: styleText("red", "✗") });
}

/** Cancelled prompt: print the frame-closing cancel line, no error theater. */
export function cancelled(message = "Cancelled."): void {
  cancel(message);
}

/** Scripted-pipe stdin: on a non-TTY stdin the whole pipe often arrives as one
 *  chunk, and clack's interactive prompts cannot run on it at all (no raw mode;
 *  a keypress-listener pipeline that never submits — measured 2026-09-01, G4
 *  path1). This wrapper replays the pipe as discrete keypress events on a
 *  PassThrough stream, one per tick: a prompt that opens between two keys finds
 *  the queue waiting instead of a firehose that already fired. Interactive
 *  stdin is passed through untouched. */
export function scriptedInput(): NodeJS.ReadStream | PassThrough {
  if (process.stdin.isTTY) return process.stdin;
  const script = new PassThrough();
  script.isTTY = true;
  script.setRawMode = () => script;
  const queue: Array<{ sequence: string; name: string }> = [];
  const map: Record<string, { name: string; sequence: string }> = {
    "\n": { name: "return", sequence: "\n" },
    "\r": { name: "return", sequence: "\r" },
    " ": { name: "space", sequence: " " },
    "\t": { name: "tab", sequence: "\t" },
    "\x1b[A": { name: "up", sequence: "\x1b[A" },
    "\x1b[B": { name: "down", sequence: "\x1b[B" },
    "\x03": { name: "cancel", sequence: "\x03" },
  };
  const enqueue = (chunk: Buffer) => {
    const text = chunk.toString();
    let i = 0;
    while (i < text.length) {
      const key = map[text.slice(i, i + 4)] ?? map[text.slice(i, i + 3)] ?? map[text[i] ?? ""];
      if (key) {
        queue.push(key);
        i += key.sequence.length;
        continue;
      }
      queue.push({ sequence: text[i] ?? "", name: text[i] ?? "" });
      i += 1;
    }
  };
  const drain = () => {
    if (queue.length === 0) return;
    const key = queue.shift();
    if (!key) return;
    script.emit("keypress", key.sequence, key);
    setTimeout(drain, 5);
  };
  process.stdin.on("data", (chunk) => {
    enqueue(chunk);
    setTimeout(drain, 5);
  });
  return script;
}

/** Confirmation honoring the initial value; on a scripted input stream a bare
 *  Enter means the verb's default (clack only reaches the keypress pipeline when
 *  its input emits events — the scripted wrapper supplies them). */
export async function confirmDefault(
  message: string,
  initial: boolean,
  input?: NodeJS.ReadStream | PassThrough,
): Promise<boolean> {
  const answer = await confirm({ message, initialValue: initial, input: input as never });
  if (typeof answer === "symbol") return initial;
  return answer === true;
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
    return {
      start: (_message?: string) => {},
      stop: (message?: string) => {
        if (message) info(message);
      },
    };
  }
  return clackSpinner();
}

/** The one-line version notice (§14.0): printed once, at the end, cached by caller. */
export function notice(latest: string, current: string): void {
  warn(`${latest} available → ai-eng upgrade · changelog: CHANGELOG.md (current: ${current})`);
}
