# Security Review Dimension

## Scope Priority (ordered by severity)
1. **Injection vulnerabilities** — SQL, XSS, command injection, LDAP, XML, NoSQL
2. **Authentication & authorization** — broken session, privilege escalation, IDOR
3. **Sensitive data exposure** — hardcoded secrets, PII leaks, weak encryption
4. **Access control** — missing auth checks, insecure direct object references
5. **Cryptographic failures** — weak algorithms, hardcoded keys, insufficient entropy
6. **Input validation** — missing validation, unsafe deserialization
7. **Advanced attacks** — SSRF, XXE, race conditions, TOCTOU

## Self-Challenge
- Trace the concrete attack path — if you can't, drop the finding.
- Distinguish between "theoretically vulnerable" and "exploitable in this context".

## References
- OWASP controls: `standards/framework/security/owasp-top10-2025.md`
