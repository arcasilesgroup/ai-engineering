# Simplification

Deletion-first is already a rule of this project, so a separate skill for it would be a
second place to say the same thing. This is the pass where a diff is judged against it.

- The smaller version, in one sentence. If there is none, say that; a reviewer who never
  looks for one never finds one.
- Something added that this repository already has — a helper, a guard, a lens, a schema.
  A second copy is not reuse, and it is the most common finding of this pass.
- An abstraction with one caller. It is not an abstraction yet, it is a longer way to write
  the caller.
- A compatibility shim, a flag or a branch kept for a case nobody has. Hard rename and hard
  delete, and say it in the changelog.
- Code that could be deleted instead of fixed. Ask that before reviewing the fix.
- Configuration for a value that has never changed, and an option nobody has ever set.
- A comment explaining what the code could have said itself.
- What this diff deletes. In a repository with a line ceiling, a change that only adds has
  spent budget that somebody else now cannot.
