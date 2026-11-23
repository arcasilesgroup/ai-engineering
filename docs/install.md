# Install

The front page keeps the one-command install. This page holds the rest: building from
source, installing without administrator rights, and the Windows gitleaks fallback.

Install [Bun](https://bun.com) (>= 1.4.4) once, then the CLI, then govern a repository:

```bash
bun add -g ai-engineering@latest    # or: npm install -g ai-engineering@latest
ai-eng init
```

`ai-eng init` asks which agents to govern, installs the skills on your machine, and writes the
contract into the repository you are in. You can run it again at any time; it converges.

The npm package ships the launcher, the source, the skills, the agents and the templates.
Each GitHub release also ships compiled binaries for eight platforms.

### From source

```bash
git clone https://github.com/arcasilesgroup/ai-engineering.git
cd ai-engineering && bun install && bun run build && bun link
```

### Without administrator rights

Nothing `ai-eng` installs or writes needs administrator rights. The binary, the skills, the
hook files and the git hooks all live in your user folder or in the repository.

| Tool | Windows | macOS and Linux |
|---|---|---|
| Bun | `powershell -c "irm bun.sh/install.ps1 \| iex"` | `curl -fsSL https://bun.sh/install \| bash` |
| `ai-eng` | `bun add -g` (into `~/.bun`), or `npm install -g` (into `%APPDATA%\npm`) | `bun add -g` (into `~/.bun`), or run `npm config set prefix ~/.local` before `npm install -g` |
| gitleaks | `winget install --id Gitleaks.Gitleaks -e` | the release binary into `~/.local/bin` |

The commit floor needs gitleaks. Where your company blocks winget, use `curl.exe` and
`tar.exe`, which ship with Windows 10 and 11. In PowerShell, with the version from the
[gitleaks releases page](https://github.com/gitleaks/gitleaks/releases):

```powershell
$v = "8.30.0"; $dir = "$env:LOCALAPPDATA\Programs\gitleaks"
New-Item -ItemType Directory -Force $dir | Out-Null
curl.exe -sSfL -o "$env:TEMP\gitleaks.zip" "https://github.com/gitleaks/gitleaks/releases/download/v$v/gitleaks_${v}_windows_x64.zip"
tar -xf "$env:TEMP\gitleaks.zip" -C $dir gitleaks.exe
[Environment]::SetEnvironmentVariable("Path", [Environment]::GetEnvironmentVariable("Path", "User") + ";$dir", "User")
```

The last line adds the folder to your user `PATH` only. Open a new terminal for it to apply.
