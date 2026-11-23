---
"ai-engineering": patch
---

The guards read Windows paths as Windows paths.

The write-target check decided "does this file belong to this repository" by joining every
target onto the repository root. A Windows word arrives after the shell's POSIX escaping has
eaten its separators — `C:\dir\file` reaches the guard as `C:dirfile` — so a rewrite of the
temp folder was joined onto the root, looked governed, and a command that silences nothing
was denied. On a Windows root a target that carries a drive letter is now compared by its
spelling against the root's own, and only a word without a drive letter is still resolved as
relative: a silence written into the repository stays denied however it is spelled.

The verdict cache refused a planted symlink with `O_NOFOLLOW`, which libuv defines for POSIX
only: on Windows the constant is absent, reads as 0 in the flags, and the open followed the
link quietly. The link is now tested with `lstat` where the open cannot, and it throws the
same ELOOP, so a symlinked cache is ignored on every platform and the guards decide the call
again instead of replaying what the link pointed at.
