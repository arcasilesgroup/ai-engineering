# Security

- Input that crosses a trust boundary: where is it validated, and against what.
- Secrets: nothing in a plain variable, nothing in a log line, nothing in a fixture.
- Anything that runs a string: shell, SQL, template, deserialiser. Name the escaping.
- Permissions: does this code run with more than it needs, and can that be narrowed here.
- New dependencies: who publishes it, how often, and what it pulls in behind it.
- A fail-open path in anything that decides whether an action is allowed. Guards fail closed.
- What an attacker gets from one leaked credential in this diff's blast radius.

- Before filing: name the source, the sink and the missing control. If you cannot write the
  request that reaches the sink it is not a finding yet, and forty soft ones cost a reader
  what four hard ones do and leave nothing to act on.
- Not findings: a dangerous-looking call whose argument is a constant, code behind a flag
  that is off, "add rate limiting", "defence in depth", "consider validating this".
- Tracing forward from the inputs that exist misses the control that should exist and does
  not: a query with no tenant filter, a route with no authorisation, a money path that is
  not idempotent. Ask what is absent, not only what is wrong.
