// The four artifacts of a milestone, and the ONE list that names them.
//
// It lives alone, with no imports, because `spec` needs it and the guard used to: the
// guard cannot import the spec module — `spec/index.ts` pulls in `embed.ts`, which pulls
// in the whole embedded payload, and the guard runs on every tool call.
//
// The guard no longer reads this list. Its fence stopped being a directory literal with
// the slots carved out of it, and became a list of the four file names the chain itself
// reads; everything else under .ai-engineering/ is the session's. The list stays here for
// the one layer that still needs it — `spec open` scaffolds two of the four and
// `spec close` sweeps all of them.
//
// Copying the list instead is the trap this module exists to close: the comment on
// `protectedPaths` says it for the protected literals, and it is the same argument here
// in the other direction. Two lists drift, and the drift is invisible until a session
// cannot write the file its own skill told it to write.

/** `spec.html` and `plan.html` are scaffolded by `spec open` and filled in by the
 *  session; `brainstorm.md` and `recap.html` have no template at all. All four are the
 *  session's to write, and all four die at `spec close`. */
export const SLOT_FILES = ["spec.html", "plan.html", "brainstorm.md", "recap.html"] as const;
