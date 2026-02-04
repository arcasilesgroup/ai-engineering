# Contributing to AI Engineering Framework

## How to Contribute

### Reporting Issues

Open a GitHub issue with:
- Description of the problem or suggestion
- Steps to reproduce (if applicable)
- Expected vs actual behavior

### Adding a New Stack

1. Create `standards/{stack}.md` with coding conventions
2. Create `.github/instructions/{stack}.instructions.md` with Copilot instructions
3. Create `learnings/{stack}.md` (can be empty initially)
4. Update `CLAUDE.md` to reference the new standard
5. Update `scripts/install.sh` to include the new stack option
6. Add a pipeline template in `pipelines/templates/{stack}-build.yml`

### Adding a New Command

1. Create `.claude/commands/{command-name}.md`
2. Follow the command template (see `workshop/07-customization.md`)
3. Include: YAML frontmatter with `description`, `## Steps`, and `## Verification`
4. Update `CLAUDE.md` commands list

### Adding a New Agent

1. Create `.claude/agents/{agent-name}.md`
2. Follow the agent template (see `workshop/07-customization.md`)
3. Include: YAML frontmatter with `description` and `tools`, `## Objective`, `## Process`, `## Constraints`
4. Update `CLAUDE.md` agents list

### Modifying Standards

- Standards should be prescriptive, not aspirational
- Include code examples for every rule
- Include anti-pattern examples showing what NOT to do
- Reference authoritative sources where applicable

## File Conventions

- All instructional content is **markdown**
- Metadata uses **YAML frontmatter**
- Maximum directory depth: **3 levels**
- File names: **kebab-case**
- No registries or index files — file existence = registration

## Pull Request Process

1. Fork the repository
2. Create a branch: `feat/add-rust-stack` or `fix/dotnet-standard-typo`
3. Make your changes
4. Run `/validate` to check framework integrity
5. Submit a PR with a clear description

## Code of Conduct

Be respectful, constructive, and inclusive. Focus on technical merit.
