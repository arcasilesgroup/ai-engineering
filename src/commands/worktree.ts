// `ai-eng worktree new|rm|list` — the thin parser. The root resolution, the git
// argv and the design-slot list live in src/shared-worktree.ts; this file only
// reads argv, prints the result and returns its exit code.

import { worktreeList, worktreeNew, worktreeRm } from "../shared-worktree.ts";

const USAGE = "usage: ai-eng worktree new <slug> [files...] | rm <slug> [--force] | list\n";

export function worktreeMain(args: string[], force = false): number {
  const [action, slug, ...files] = args;
  let result;
  switch (action) {
    case "new":
      if (!slug) {
        process.stderr.write(USAGE);
        return 2;
      }
      result = worktreeNew(slug, files);
      break;
    case "rm": {
      // A trailing positional is a typo the caller cannot see — `rm alpha typo`
      // deleting `alpha` would be silent data loss, so the shape is exact:
      // one slug, nothing else.
      if (!slug || files.length > 0) {
        process.stderr.write(USAGE);
        return 2;
      }
      result = worktreeRm(slug, force);
      break;
    }
    case "list":
      result = worktreeList();
      break;
    default:
      process.stderr.write(USAGE);
      return 2;
  }
  if (result.out) process.stdout.write(result.out);
  if (result.err) process.stderr.write(result.err);
  return result.code;
}
