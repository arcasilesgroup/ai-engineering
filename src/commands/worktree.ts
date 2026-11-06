// The `ai-eng worktree` parser is thin; git merge transactions live in src/git/merge.ts.

import {
  worktreeList,
  worktreeNew,
  worktreeRequestChanges,
  worktreeRm,
} from "../shared-worktree.ts";
import { worktreeMerge } from "../git/merge.ts";

const USAGE =
  "usage: ai-eng worktree new <branch> | list [<slug>] | merge <slug> | request-changes <slug> <pending-checkpoint-commit-sha> | " +
  "rm <slug> [--force] (force also permanently deletes ignored files)\n";

export function worktreeMain(args: string[], force = false): number {
  const [action, slug, ...files] = args;
  let result;
  switch (action) {
    case "new":
      if (!slug || force) {
        process.stderr.write(USAGE);
        return 2;
      }
      if (files.length > 0) {
        process.stderr.write(USAGE);
        return 2;
      }
      result = worktreeNew(slug);
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
    case "merge":
      if (!slug || files.length > 0 || force) {
        process.stderr.write(USAGE);
        return 2;
      }
      result = worktreeMerge(slug);
      break;
    case "list":
      if (files.length > 0 || force) {
        process.stderr.write(USAGE);
        return 2;
      }
      result = worktreeList(slug);
      break;
    case "request-changes":
      if (!slug || files.length !== 1 || force) {
        process.stderr.write(USAGE);
        return 2;
      }
      result = worktreeRequestChanges(slug, files[0] ?? "");
      break;
    default:
      process.stderr.write(USAGE);
      return 2;
  }
  if (result.out) process.stdout.write(result.out);
  if (result.err) process.stderr.write(result.err);
  return result.code;
}
