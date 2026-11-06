// A suite that drives prompts by emitting keys on `process.stdin` must not use the
// runner's real stdin for it: src/ui.ts's scriptedInput() listens to that stream, so the
// first `data` listener puts it in flowing mode and any byte the runner's parent writes
// (a newline from the shell that launched `bun test`) is replayed into whichever prompt
// is open — a confirm whose default is No then answers itself and nothing is removed.
// The swap gives the suite a stream only it writes to; scriptedInput() reads
// `process.stdin` at call time, so every prompt in the file gets the private one.

import { PassThrough } from "node:stream";

export function usePrivateStdin(): { runnerStdin: NodeJS.ReadStream; restore: () => void } {
  const runnerStdin = process.stdin;
  const descriptor = Object.getOwnPropertyDescriptor(process, "stdin");
  const privateStdin = new PassThrough();
  // The piped shape tests/preload.ts pins on the real stream: not a TTY, so scriptedInput() wraps it.
  Object.defineProperty(privateStdin, "isTTY", { value: false, configurable: true });
  privateStdin.setMaxListeners(0);
  Object.defineProperty(process, "stdin", { value: privateStdin, configurable: true, writable: true });
  return {
    runnerStdin,
    restore: () => {
      if (descriptor) Object.defineProperty(process, "stdin", descriptor);
      else Reflect.deleteProperty(process, "stdin");
    },
  };
}
