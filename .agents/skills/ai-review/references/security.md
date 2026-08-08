# Security

- Input that crosses a trust boundary: where is it validated, and against what.
- Secrets: nothing in a plain variable, nothing in a log line, nothing in a fixture.
- Anything that runs a string: shell, SQL, template, deserialiser. Name the escaping.
- Permissions: does this code run with more than it needs, and can that be narrowed here.
- New dependencies: who publishes it, how often, and what it pulls in behind it.
- A fail-open path in anything that decides whether an action is allowed. Guards fail closed.
- What an attacker gets from one leaked credential in this diff's blast radius.
