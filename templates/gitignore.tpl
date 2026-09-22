# .gitignore — the ai-engineering standard (ai-eng init writes it once; it is yours after that).
# Stack-specific rules (frameworks you add later): run `npx generate-gitignore <stack>`
# and append what you need. This file keeps only what is true for every governed project.

# ── macOS ────────────────────────────────────────────────
.DS_Store
._*
.Spotlight-V100
.Trashes

# ── Windows ──────────────────────────────────────────────
Thumbs.db
ehthumbs.db
Desktop.ini
$RECYCLE.BIN/

# ── Linux ────────────────────────────────────────────────
*~
.fuse_hidden*
.directory
.Trash-*

# ── Editors / IDEs ───────────────────────────────────────
*.swp
*.swo
*.sublime-workspace
# .vscode/ and .idea/ often hold settings a team WANTS committed. Uncomment if yours are personal.
# .vscode/
# .idea/

# ── Logs / temp ──────────────────────────────────────────
logs/
*.log
tmp/
temp/

# ── Environment / secrets ────────────────────────────────
.env
.env.*
!.env.example
*.pem
*.key
id_rsa*

# ── Node / Bun ───────────────────────────────────────────
node_modules/
npm-debug.log*
yarn-error.log*
pnpm-debug.log*
coverage/
dist/
build/
*.bun-build

# ── Python ───────────────────────────────────────────────
__pycache__/
*.py[cod]
.venv/
venv/
.mypy_cache/
.ruff_cache/
.pytest_cache/
*.egg-info/

# ── Rust ─────────────────────────────────────────────────
target/

# ── Go ───────────────────────────────────────────────────
*.test

# ── ai-engineering runtime state ─────────────────────────
# Receipts and the verdict cache are local execution evidence — committing them
# commits machine paths. spec/, research/, config.toml and ai-eng.lock DO belong in git.
.ai-engineering/receipts/
.ai-engineering/cache/
.claude/reviews/
