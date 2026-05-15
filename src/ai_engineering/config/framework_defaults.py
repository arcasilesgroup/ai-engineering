"""Framework-managed manifest defaults.

These sections are framework-canonical and would otherwise duplicate
into every consumer's ``.ai-engineering/manifest.yml``. They are
injected by :func:`ai_engineering.config.loader.load_manifest_config`
when absent from the user manifest so a slim user manifest (only
``providers``, ``surfaces``, ``artifact_feeds``, ``work_items``,
``quality``, ``gates``, ``documentation``, ``cicd``, ``telemetry``)
still produces a complete :class:`ManifestConfig`.

User-supplied values always win — defaults are only applied when the
corresponding key is missing or ``None``.
"""

from __future__ import annotations

from typing import Any

# --- session.context_files ---

DEFAULT_SESSION_CONTEXT_FILES: list[str] = [
    ".ai-engineering/LESSONS.md",
    "CONSTITUTION.md",
    ".ai-engineering/manifest.yml",
    ".ai-engineering/state/decision-store.json",
]


# --- contexts.precedence (spec-128 D-128-08) ---

DEFAULT_CONTEXTS_PRECEDENCE: list[str] = ["team", "stack"]


# --- control_plane authority contract ---

DEFAULT_CONTROL_PLANE: dict[str, Any] = {
    "constitutional_authority": {
        "primary": "CONSTITUTION.md",
        "compatibility_aliases": [],
    },
    "manifest_field_roles": {
        "canonical_input": [
            "providers",
            "surfaces",
            "artifact_feeds",
            "work_items",
            "quality",
            "documentation",
            "cicd",
            "contexts.precedence",
            "session.context_files",
            "ownership.framework",
            "ownership.root_entry_points",
            "telemetry",
            "gates",
            "hot_path_slos",
        ],
        "generated_projection": ["skills", "agents"],
        "descriptive_metadata": [
            "schema_version",
            "framework_version",
            "name",
            "version",
        ],
    },
}


# --- ownership ---

DEFAULT_OWNERSHIP_FRAMEWORK: list[str] = [
    ".claude/skills/**",
    ".claude/agents/**",
    ".ai-engineering/**",
    ".github/agents/**",
    ".github/skills/**",
    ".github/hooks/**",
    ".github/copilot-instructions.md",
    ".codex/**",
    ".gemini/**",
    ".opencode/**",
    ".cursor/**",
    ".agent/**",
]


DEFAULT_OWNERSHIP_ROOT_ENTRY_POINTS: dict[str, dict[str, Any]] = {
    "CLAUDE.md": {
        "owner": "framework",
        "canonical_source": "CLAUDE.md",
        "runtime_role": "ide-overlay",
        "sync": {
            "mode": "copy",
            "template_path": "src/ai_engineering/templates/project/CLAUDE.md",
            "mirror_paths": [],
        },
    },
    "AGENTS.md": {
        "owner": "framework",
        "canonical_source": "scripts/sync_command_mirrors.py:generate_agents_md",
        "runtime_role": "shared-runtime-contract",
        "sync": {
            "mode": "generate",
            "template_path": "src/ai_engineering/templates/project/AGENTS.md",
            "mirror_paths": [],
        },
    },
    "GEMINI.md": {
        "owner": "framework",
        "canonical_source": "src/ai_engineering/templates/project/GEMINI.md",
        "runtime_role": "ide-overlay",
        "sync": {
            "mode": "render",
            "template_path": "src/ai_engineering/templates/project/GEMINI.md",
            "mirror_paths": [".gemini/GEMINI.md"],
        },
    },
    ".github/copilot-instructions.md": {
        "owner": "framework",
        "canonical_source": "CLAUDE.md",
        "runtime_role": "ide-overlay",
        "sync": {
            "mode": "generate",
            "template_path": "src/ai_engineering/templates/project/copilot-instructions.md",
            "mirror_paths": [],
        },
    },
}


DEFAULT_OWNERSHIP_TEAM: list[str] = [".ai-engineering/contexts/team/**"]
DEFAULT_OWNERSHIP_SYSTEM: list[str] = [".ai-engineering/state/**"]


# --- tooling + telemetry + hot_path_slos ---

DEFAULT_TOOLING: list[str] = ["uv", "ruff", "gitleaks", "pytest", "ty", "pip-audit"]

DEFAULT_HOT_PATH_SLOS: dict[str, int] = {
    "pre_commit_p95_ms": 1000,
    "pre_push_p95_ms": 5000,
    "skill_invocation_overhead_p95_ms": 200,
    "rolling_window_events": 100,
}


# --- python_env ---

DEFAULT_PYTHON_ENV: dict[str, str] = {"mode": "uv-tool"}


# --- prereqs.uv + sdk_per_stack ---

DEFAULT_PREREQS_UV: dict[str, str] = {"version_range": ">=0.4.0,<1.0"}

DEFAULT_PREREQS_SDK_PER_STACK: dict[str, dict[str, str]] = {
    "java": {"name": "JDK", "min_version": "21", "install_link": "https://adoptium.net/"},
    "kotlin": {"name": "JDK", "min_version": "21", "install_link": "https://adoptium.net/"},
    "swift": {
        "name": "Swift toolchain",
        "install_link": "https://www.swift.org/install/",
    },
    "dart": {"name": "Dart SDK", "install_link": "https://dart.dev/get-dart"},
    "csharp": {
        "name": ".NET SDK",
        "min_version": "9",
        "install_link": "https://dotnet.microsoft.com/download",
    },
    "go": {"name": "Go toolchain", "install_link": "https://go.dev/dl/"},
    "rust": {"name": "Rust toolchain", "install_link": "https://rustup.rs/"},
    "php": {
        "name": "PHP",
        "min_version": "8.2",
        "install_link": "https://www.php.net/downloads",
    },
    "cpp": {"name": "clang/LLVM", "install_link": "https://llvm.org/builds/"},
}


# --- required_tools (per-stack tooling) ---

DEFAULT_REQUIRED_TOOLS: dict[str, Any] = {
    "baseline": [
        {"name": "gitleaks"},
        {
            "name": "semgrep",
            "platform_unsupported": ["windows"],
            "unsupported_reason": "semgrep has no Windows release",
        },
        {"name": "jq"},
        {"name": "opa", "version_range": ">=0.70.0,<2.0.0"},
    ],
    "python": [
        {"name": "ruff"},
        {"name": "ty"},
        {"name": "pip-audit"},
        {"name": "pytest", "scope": "user_global"},
    ],
    "typescript": [
        {"name": "prettier", "scope": "project_local"},
        {"name": "eslint", "scope": "project_local"},
        {"name": "tsc", "scope": "project_local"},
        {"name": "vitest", "scope": "project_local"},
    ],
    "javascript": [
        {"name": "prettier", "scope": "project_local"},
        {"name": "eslint", "scope": "project_local"},
        {"name": "vitest", "scope": "project_local"},
    ],
    "java": [{"name": "checkstyle"}, {"name": "google-java-format"}],
    "csharp": [{"name": "dotnet-format"}],
    "go": [{"name": "staticcheck"}, {"name": "govulncheck"}],
    "php": [{"name": "phpstan"}, {"name": "php-cs-fixer"}, {"name": "composer"}],
    "rust": [{"name": "cargo-audit"}],
    "kotlin": [{"name": "ktlint"}],
    "swift": {
        "platform_unsupported_stack": ["linux", "windows"],
        "unsupported_reason": "swiftlint and swift-format have no Linux/Windows binaries",
        "tools": [{"name": "swiftlint"}, {"name": "swift-format"}],
    },
    "dart": [{"name": "dart-stack-marker"}],
    "sql": [{"name": "sqlfluff"}],
    "bash": [{"name": "shellcheck"}, {"name": "shfmt"}],
    "cpp": [
        {"name": "clang-tidy"},
        {"name": "clang-format"},
        {"name": "cppcheck"},
    ],
}


# --- skills registry (48 entries, kept here so /ai-create maintains a single source) ---

DEFAULT_SKILLS_REGISTRY: dict[str, dict[str, Any]] = {
    "ai-brainstorm": {"type": "workflow", "tags": ["planning"]},
    "ai-plan": {"type": "workflow", "tags": ["planning"]},
    "ai-build": {"type": "workflow", "tags": ["execution", "implementation"]},
    "ai-test": {"type": "workflow", "tags": ["quality"]},
    "ai-debug": {"type": "workflow", "tags": ["quality"]},
    "ai-code": {"type": "workflow", "tags": ["implementation"]},
    "ai-verify": {"type": "workflow", "tags": ["quality", "release"]},
    "ai-review": {"type": "workflow", "tags": ["quality"]},
    "ai-commit": {"type": "delivery", "tags": ["git"]},
    "ai-pr": {"type": "delivery", "tags": ["git"]},
    "ai-cleanup": {"type": "delivery", "tags": ["git"]},
    "ai-security": {"type": "enterprise", "tags": ["security"]},
    "ai-governance": {"type": "enterprise", "tags": ["compliance"]},
    "ai-advise": {"type": "workflow", "tags": ["governance", "advisory", "proactive"]},
    "ai-pipeline": {"type": "enterprise", "tags": ["cicd"]},
    "ai-schema": {"type": "enterprise", "tags": ["database"]},
    "ai-docs": {"type": "enterprise", "tags": ["documentation", "architecture", "governance"]},
    "ai-explain": {"type": "teaching", "tags": ["learning"]},
    "ai-explore": {"type": "workflow", "tags": ["exploration", "codebase", "research"]},
    "ai-guide": {"type": "teaching", "tags": ["onboarding"]},
    "ai-write": {"type": "writing", "tags": ["content"]},
    "ai-gtm": {"type": "writing", "tags": ["gtm", "marketing", "go-to-market"]},
    "ai-note": {"type": "sdlc", "tags": ["knowledge"]},
    "ai-standup": {"type": "sdlc", "tags": ["reporting"]},
    "ai-sprint": {"type": "sdlc", "tags": ["planning", "presentation"]},
    "ai-postmortem": {"type": "sdlc", "tags": ["incident"]},
    "ai-support": {"type": "sdlc", "tags": ["customer"]},
    "ai-resolve-conflicts": {"type": "sdlc", "tags": ["git"]},
    "ai-create": {"type": "meta", "tags": ["framework"]},
    "ai-learn": {"type": "meta", "tags": ["improvement"]},
    "ai-prompt": {"type": "meta", "tags": ["optimization"]},
    "ai-start": {"type": "meta", "tags": ["bootstrap"]},
    "ai-analyze-permissions": {"type": "meta", "tags": ["permissions"]},
    "ai-observe": {
        "type": "meta",
        "tags": ["meta", "learning", "continuous-improvement", "observe"],
    },
    "ai-autopilot": {
        "type": "meta",
        "tags": ["orchestration", "autonomous", "multi-spec", "backlog"],
    },
    "ai-constitution": {"type": "meta", "tags": ["governance"]},
    "ai-slides": {"type": "writing", "tags": ["presentation", "html", "css"]},
    "ai-media": {"type": "writing", "tags": ["media", "generation"]},
    "ai-video-editing": {"type": "writing", "tags": ["video", "editing"]},
    "ai-board": {"type": "enterprise", "tags": ["board", "discovery", "sync", "work-items"]},
    "ai-ide-audit": {"type": "enterprise", "tags": ["audit", "ide", "governance"]},
    "ai-skill-improve": {
        "type": "meta",
        "tags": ["improvement", "skills", "optimization", "improve"],
    },
    "ai-mcp-audit": {"type": "enterprise", "tags": ["security", "mcp", "audit", "governance"]},
    "ai-design": {"type": "design", "tags": ["design", "ui", "ux", "aesthetic"]},
    "ai-animation": {"type": "design", "tags": ["animation", "motion", "interaction"]},
    "ai-visual": {"type": "design", "tags": ["visual", "art", "composition", "marketing"]},
    "ai-research": {
        "type": "workflow",
        "tags": ["research", "evidence", "citations", "multi-tier"],
    },
    "ai-simplify": {"type": "workflow", "tags": ["refactor", "complexity", "simplification"]},
    "ai-simplify-sweep": {"type": "meta", "tags": ["simplification", "scheduled", "autonomous"]},
    "ai-eval": {"type": "workflow", "tags": ["evaluation", "gate", "regression", "pass-at-k"]},
    "ai-issue": {"type": "workflow", "tags": ["work-items", "board", "issue"]},
    "ai-engineering-issue": {
        "type": "enterprise",
        "tags": ["security", "support", "upstream", "redaction"],
    },
    "ai-spec-draft": {"type": "workflow", "tags": ["planning", "brief", "research", "sdd"]},
}


# --- agents (9 first-class orchestrators) ---
# CLAUDE.md / AGENTS.md canonical contract: "Agents (9)" enumerates only
# first-class orchestrators discovered via `ai-*` glob (sync_mirrors.core
# discover_agents). Specialist reviewer-* / verifier-* / verify-* agents
# are dispatched INTERNALLY by ai-review / ai-verify and are NOT counted
# in the manifest registry — they are mirrored separately under
# discover_specialist_agents(). Names are bare (no `ai-` prefix).

DEFAULT_AGENTS_NAMES: list[str] = [
    "autopilot",
    "build",
    "explore",
    "guard",
    "guide",
    "plan",
    "review",
    "simplify",
    "verify",
]


# --- public injector ---


def _copy(value: Any) -> Any:
    """Shallow copy for lists/dicts so caller mutations stay local."""
    if isinstance(value, dict):
        return {k: _copy(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_copy(v) for v in value]
    return value


def apply_framework_defaults(data: dict[str, Any]) -> dict[str, Any]:
    """Inject framework-managed sections into a raw manifest dict.

    User-supplied values win — defaults are applied only when the key
    is absent or ``None``. The input dict is mutated in place and also
    returned for chaining.
    """
    # session.context_files
    session = data.setdefault("session", {})
    if isinstance(session, dict) and session.get("context_files") is None:
        session["context_files"] = _copy(DEFAULT_SESSION_CONTEXT_FILES)

    # contexts.precedence
    contexts = data.setdefault("contexts", {})
    if isinstance(contexts, dict) and contexts.get("precedence") is None:
        contexts["precedence"] = _copy(DEFAULT_CONTEXTS_PRECEDENCE)

    # control_plane
    if data.get("control_plane") is None:
        data["control_plane"] = _copy(DEFAULT_CONTROL_PLANE)

    # ownership
    ownership = data.setdefault("ownership", {})
    if isinstance(ownership, dict):
        if not ownership.get("framework"):
            ownership["framework"] = _copy(DEFAULT_OWNERSHIP_FRAMEWORK)
        if not ownership.get("root_entry_points"):
            ownership["root_entry_points"] = _copy(DEFAULT_OWNERSHIP_ROOT_ENTRY_POINTS)
        if not ownership.get("team"):
            ownership["team"] = _copy(DEFAULT_OWNERSHIP_TEAM)
        if not ownership.get("system"):
            ownership["system"] = _copy(DEFAULT_OWNERSHIP_SYSTEM)

    # tooling
    if not data.get("tooling"):
        data["tooling"] = _copy(DEFAULT_TOOLING)

    # hot_path_slos
    if data.get("hot_path_slos") is None:
        data["hot_path_slos"] = _copy(DEFAULT_HOT_PATH_SLOS)

    # python_env
    if data.get("python_env") is None:
        data["python_env"] = _copy(DEFAULT_PYTHON_ENV)

    # prereqs
    prereqs = data.setdefault("prereqs", {})
    if isinstance(prereqs, dict):
        if prereqs.get("uv") is None:
            prereqs["uv"] = _copy(DEFAULT_PREREQS_UV)
        if prereqs.get("sdk_per_stack") is None:
            prereqs["sdk_per_stack"] = _copy(DEFAULT_PREREQS_SDK_PER_STACK)

    # required_tools
    if data.get("required_tools") is None:
        data["required_tools"] = _copy(DEFAULT_REQUIRED_TOOLS)

    # skills registry (auto-discovery is in loader.py; here we supply
    # the canonical 48-entry default for environments without a
    # ``.claude/skills/`` tree).
    skills = data.setdefault("skills", {})
    if isinstance(skills, dict):
        if not skills.get("registry"):
            skills["registry"] = _copy(DEFAULT_SKILLS_REGISTRY)
        if "total" not in skills:
            skills["total"] = len(skills["registry"])
        skills.setdefault("prefix", "ai-")

    # agents
    agents = data.setdefault("agents", {})
    if isinstance(agents, dict):
        if not agents.get("names"):
            agents["names"] = _copy(DEFAULT_AGENTS_NAMES)
        if "total" not in agents:
            agents["total"] = len(agents["names"])

    return data
