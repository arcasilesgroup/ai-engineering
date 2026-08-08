# Correctness

Read for what the change claims, then for what it does.

- Does it do what the pull request says it does? Say so explicitly, or say where it differs.
- Boundaries: every call that leaves this process. Timeouts, retries, partial failure, and
  what the caller sees when the other side is down.
- The empty case, the one-item case, the duplicate case. Most real bugs live in one of them.
- Concurrency: two of these at once. Which write wins, and does anybody notice.
- Behaviour that used to be true and is not any more, whether or not it was intended.
- Error paths run too. Read them as code, not as decoration.
