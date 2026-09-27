// The suite is written for a piped runner, and an interactive shell leaks its TTY-ness
// into every test: ui.ts replays stdin as keypresses only off a TTY, wraps rendered rows
// only on a TTY stdout, and its frame module keeps one `frameOpen` flag per process —
// so a prompt that hangs on real stdin leaves the frame open for the tests after it.
// `columns` too: on a TTY stream Bun reports 0 once isTTY is pinned, and clack's
// getColumns prefers a numeric `columns` over its 80 fallback — width 0 wraps every
// prompt to one character per line. Piping reports `columns` absent; pin that shape.
// The TTY branches exercise themselves by redefining isTTY inside their own tests
// (config-command, cli-ux).
Object.defineProperty(process.stdin, "isTTY", { value: false, configurable: true });
Object.defineProperty(process.stdout, "isTTY", { value: false, configurable: true });
Object.defineProperty(process.stdout, "columns", { value: undefined, configurable: true });
