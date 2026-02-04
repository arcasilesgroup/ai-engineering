---
applyTo: "**/*.{env,key,pem,secret,credentials}"
---

# Security-Sensitive File Instructions for Copilot

## WARNING: This file matches a security-sensitive pattern

Files matching `.env`, `.key`, `.pem`, `.secret`, and `.credentials` extensions contain or are intended to contain sensitive data. Exercise extreme caution.

## Critical Rules

### NEVER

1. **Never commit secrets to version control.** This includes API keys, passwords, tokens, private keys, certificates, and connection strings.
2. **Never hardcode credentials** in any file, even temporarily. There is no such thing as a "temporary" secret in Git history.
3. **Never generate real secrets** in code suggestions. Use placeholder values that are clearly fake (e.g., `YOUR_API_KEY_HERE`, `<replace-with-secret>`).
4. **Never log or print secret values.** Even in debug output, secrets must be masked.
5. **Never include secret files in Docker images** or build artifacts.

### ALWAYS

1. **Use environment variables** for configuration secrets at runtime.
2. **Use a secret manager** (Azure Key Vault, AWS Secrets Manager, HashiCorp Vault) for production secrets.
3. **Add secret files to `.gitignore`** to prevent accidental commits.
4. **Use `.env.example` files** with placeholder values to document required variables.
5. **Run `gitleaks`** before every commit to detect accidentally staged secrets.
6. **Rotate secrets immediately** if they are ever committed to version control, even to a private repository.

## .env File Patterns

### .env.example (Safe to Commit)

This template documents required environment variables without real values:

```env
# Application
APP_NAME=my-app
APP_ENVIRONMENT=development

# Database
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=mydb
DATABASE_USER=<replace-with-username>
DATABASE_PASSWORD=<replace-with-password>

# External Services
API_KEY=<replace-with-api-key>
AUTH_CLIENT_SECRET=<replace-with-client-secret>

# Azure
AZURE_STORAGE_CONNECTION_STRING=<replace-with-connection-string>
AZURE_KEY_VAULT_URL=https://<your-vault>.vault.azure.net/
```

### .env (Never Commit)

The actual `.env` file with real values must be in `.gitignore`:

```gitignore
# Secret files -- NEVER commit
.env
.env.local
.env.*.local
*.key
*.pem
*.secret
*.credentials
```

## Secret Management Hierarchy

Use the appropriate mechanism based on the environment:

| Environment   | Mechanism                                     |
|--------------|-----------------------------------------------|
| Local dev     | `.env` file (in `.gitignore`)                 |
| CI/CD         | Pipeline secrets / GitHub Secrets             |
| Staging/Prod  | Azure Key Vault or equivalent secret manager  |

## Key and Certificate Files

- `.key` and `.pem` files must never be committed
- Store private keys in a secret manager or certificate store
- Use managed identities (Azure Managed Identity) where possible to avoid key management entirely
- If a key file is required locally, add the path to `.gitignore`

## If a Secret is Accidentally Committed

1. **Rotate the secret immediately** -- consider it compromised
2. Remove the secret from the current code
3. Use `git filter-branch` or BFG Repo Cleaner to purge it from history
4. Force push the cleaned history (coordinate with team)
5. Verify with `gitleaks` that the secret is no longer in any commit
6. Document the incident

## Scanning Tools

- **gitleaks**: Pre-commit hook and CI pipeline secret scanning
- **Snyk**: Dependency vulnerability scanning
- **CodeQL**: Static analysis for security patterns
- **OWASP Dependency-Check**: Known vulnerability database scanning

## Reminders

- Secrets in Git history live forever, even after deletion
- Automated scanners (GitHub Secret Scanning, gitleaks) will flag committed secrets
- All team members are responsible for secret hygiene
- When in doubt, treat the value as a secret
