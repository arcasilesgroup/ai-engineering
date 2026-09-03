// src/ui.ts — the frame layer (cli-ux-14 work point 01). Every human verb
// presents through here; machine verbs (chain|git|wrap|spec) never import it:
// their stdout is a byte-stable contract (§07). Wraps clack 1.7.0 primitives;
import { intro, outro, log, cancel, spinner as clackSpinner, confirm } from "@clack/prompts";
import { styleText } from "node:util";
import { PassThrough } from "node:stream";
// NO_COLOR and non-TTY degrade because clack honors colors, and ui.spinner()
// covers the cursor-control codes clack emits even under NO_COLOR.

let frameOpen = false;

/** Open the frame: `┌  <title>` with repo/runtime context baked by the caller.
 *  A no-op when a frame is already open — a verb handed off mid-story (init →
 *  update) keeps ONE frame, like §14.3's continuous mockup. */
export function frame(title: string): void {
  if (frameOpen) {
    info(title);
    return;
  }
  intro(title);
  frameOpen = true;
}

/** Close the frame: `└  <message>`. */
export function end(message: string): void {
  outro(message);
  frameOpen = false;
}

/** Cancel closes the frame too. */
export function cancelled(message = "Cancelled."): void {
  cancel(message);
  frameOpen = false;
}

/** A row inside a concept block. Marks reuse the line grammar (✓◆▲✗); `muted`
 *  dims the whole row (bulk/unchanged), `sub` is a `↳` continuation under the
 *  row above it. `dim` is the optional gray tail after the text — the "why". */
export type Row =
  | { readonly mark: "ok" | "info" | "warn" | "fail"; readonly text: string; readonly dim?: string }
  | { readonly mark: "muted"; readonly text: string }
  | { readonly mark: "sub"; readonly text: string };

const MARKS = {
  ok: styleText("green", "✓"),
  info: styleText("cyan", "◆"),
  head: styleText("cyan", "◆"),
  warn: styleText("yellow", "▲"),
  fail: styleText("red", "✗"),
  muted: styleText("dim", "·"),
  sub: "",
} as const;

function renderRow(row: Readonly<Row>): string {
  if (row.mark === "sub") return `${styleText("dim", "    ↳")} ${row.text}`;
  if (row.mark === "muted") return styleText("dim", row.text);
  const head = `${MARKS[row.mark]} ${row.text}`;
  return typeof row.dim === "string" && row.dim.length > 0 ? `${head} ${styleText("dim", `· ${row.dim}`)}` : head;
}

/** One concept, one clack block: `│ ◆ Title · note` then the whole body
 *  inside a single log.message — every row rides the same spine line, so a
 *  list of related facts reads as ONE idea, not N staccato events. The mark
 *  grammar stays §14.2: the frame's own glyphs, no emoji. */
export function section(title: string, rows: readonly Row[] = [], note?: string): void {
  const head = `${styleText("bold", title)}${typeof note === "string" && note.length > 0 ? styleText("dim", `  ·  ${note}`) : ""}`;
  log.message([head, ...rows.map(renderRow)].join("\n"), { symbol: MARKS.head });
}

/** Compact path list for sub rows: groups by directory so four hook paths
 *  read as `hooks-dir/: pre-commit · commit-msg` instead of four full lines. */
export function pathList(paths: readonly string[]): string {
  if (paths.length === 0) return "";
  const byDir = new Map<string, string[]>();
  for (const path of paths) {
    const cut = path.lastIndexOf("/");
    const dir = cut === -1 ? "." : path.slice(0, cut + 1);
    const files = byDir.get(dir) ?? [];
    files.push(path.slice(cut + 1));
    byDir.set(dir, files);
  }
  const parts: string[] = [];
  for (const [dir, files] of byDir) parts.push(`${dir}${files.join(" · ")}`);
  return parts.join("  ·  ");
}

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

/** Scripted-pipe stdin: on a non-TTY stdin the whole pipe often arrives as one
 *  chunk, and clack's interactive prompts cannot run on it at all (no raw mode;
 *  a keypress-listener pipeline that never submits — measured 2026-09-01, G4
 *  path1). This wrapper replays the pipe as discrete keypress events on a
 *  PassThrough stream, one per tick: a prompt that opens between two keys finds
 *  the queue waiting instead of a firehose that already fired. Interactive
 *  stdin is passed through untouched. */
export function scriptedInput(): NodeJS.ReadStream | PassThrough {
  if (process.stdin.isTTY) {
    // clack adds one keypress listener per prompt; a question chain can cross
    // Node's default cap of 10 and print a leak warning inside the frame.
    process.stdin.setMaxListeners(0);
    return process.stdin;
  }
  const script = new PassThrough();
  script.isTTY = true;
  script.setRawMode = () => script;
  // Every clack prompt adds a keypress listener; a long question chain (update
  // with conflicts, init with boosters) crosses the default cap of 10 and Node
  // prints a MaxListeners leak warning inside the frame. The queue drains one
  // key per tick — the listeners are real, bounded, and finished with.
  script.setMaxListeners(0);
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

export function summary(okCount: number, warnCount: number, failCount: number): void {
  const total = okCount + warnCount + failCount;
  const parts = [
    `${total} ${total === 1 ? "check" : "checks"}: ${okCount} OK`,
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
