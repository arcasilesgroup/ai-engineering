"""The only install verb: this machine, and then this repository if you say yes.

It is stateful and it is safe to run a thousand times. Every question has a default
that destroys nothing, so pressing Enter without reading never breaks a file — and
every file that already exists and is not ours lands on one checklist, on one screen,
with nothing selected, because a queue of yes/no prompts shows you the blast radius one
file at a time and prompt fatigue does the rest.

What it never does: render a template tree, copy a guard, install a binary, commit
anything, or own any file after it exits.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

from ai_engineering import __version__, capability, intent, outcome, paths, skeletons, ui, wiring

# Each body is asked for with the repository root, because two of the five depend on what
# is in it: the justfile on which stacks were detected, and the workflow on the version
# this wheel pins. The workflow used to be printed at the reader with "paste these lines
# into" above it — the one file this product asked a person to install by hand, and the
# one step of the install nothing could verify afterwards.
OFFERS = {
    "CLAUDE.md": ("one line: @./AGENTS.md", lambda root: skeletons.CLAUDE_MD),
    "AGENTS.md": ("skeleton, ~48 lines, TODO marker per section", lambda root: skeletons.AGENTS_MD),
    "CONSTITUTION.md": ("skeleton, ~40 lines, MANDATORY", lambda root: skeletons.CONSTITUTION_MD),
    "justfile": (
        "5 recipes, filled in for the stacks found here",
        lambda root: skeletons.justfile(stacks(root)),
    ),
    ".github/workflows/check.yml": (
        "the check job, pinned to this version",
        lambda root: skeletons.CHECK_YML.format(version=__version__),
    ),
}


def out(text: str = "") -> None:
    """Messaging, and this verb is nothing else: every line it prints is chrome around a
    write, so all of it goes to stderr. It had a `data` parameter for the one caller that
    printed the workflow at the reader; that caller writes a file now, and a parameter with
    no caller left is a second way for this to behave that nothing exercises."""
    ui.write(text)


banner = ui.banner  # one drawing of the product's face, and it lives with the rest of it


def ask(question: str, default: bool, args) -> bool:
    from ai_engineering import accept

    if args.yes:
        return default
    if accept.NON_INTERACTIVE:
        # Not the default, and not the safe-looking one either: the question goes
        # unanswered and the run stops. A mode that answers for you is a mode that sets a
        # machine up on nobody's word, and this question's default is yes.
        out(f"   {accept.DECISION_REQUIRED}: {question}")
        out("   Pass the flag that decides it, or -y, or run without --non-interactive.")
        return False
    if not sys.stdin.isatty():
        return default
    reply = input(f"◆ {question} ({'Y/n' if default else 'y/N'}) › ").strip().lower()
    return default if not reply else reply.startswith("y")


def parse(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser("ai-eng init", description=__doc__.splitlines()[0])
    p.add_argument("--global", dest="do_global", action="store_true", help="set up this machine")
    p.add_argument("--no-global", dest="skip_global", action="store_true")
    p.add_argument("--project", nargs="?", const=".", help="set up this repository")
    # The half that was missing. --no-global existed and its opposite did not, so the only
    # way to ask for the machine and nothing else was to answer a question, which is not
    # something `doctor --fix` can do. A repair that rewires this machine must not also
    # decide to set up whatever repository the person happened to be standing in.
    p.add_argument("--no-project", dest="skip_project", action="store_true")
    p.add_argument(
        "--harness", default="", help="comma-separated surface ids; default is all found"
    )
    p.add_argument("--overwrite", default="", help="comma-separated file names, or all")
    p.add_argument(
        "--dry-run", dest="dry", action="store_true", help="print the checklist, write nothing"
    )
    p.add_argument("-y", "--yes", action="store_true", help="take every default")
    return p.parse_args(argv)


def global_ready() -> bool:
    """Ready when every surface here that takes a guard has one, and at least one does.

    It used to be `the receipt is not empty and its version matches` — a log of writes read
    as the state of the machine. So `ai-eng uninstall` followed by `ai-eng init` printed
    `Global ready · 4 links, 4 guards` over a machine measured at zero of both, and then
    declined to rewire it, because only `--global` forces past this. The receipt shrinking
    fixes that one sequence; asking the machine fixes every other way it can go stale, and
    a settings file edited by hand is not a rare one.

    The version still has to match, because an entry pointing at an older install is wired
    and is not ready — that is assertion 12, and this must not disagree with it either."""
    on, off = wiring.wired()
    return bool(on) and not off and wiring.receipt().get("version") == __version__


def already(data: dict) -> None:
    """What the machine half left behind on the run that did it, for the runs that have
    nothing left to do. It was one sentence at a hundred columns — `Global ready — 8
    skills, 9 entries, v1.0.0 (/…/machine.json)` — with the skill count written into it as
    the literal 8, a number that could not be wrong when it was typed and cannot be right
    after a ninth skill ships.

    Every number here is counted from what is on the disk, and spec 007 said so a version
    before it was true: skills was read from the store and links and guards were read off
    the receipt, so this block reported `links 4 · guards 4` over a machine with none of
    either. The receipt is named on its own row and no longer counted."""
    real = paths.home() / "skills"
    on, _ = wiring.wired()
    ui.section(f"◇ Global   ready · v{data.get('version')}")
    ui.facts(
        [
            ("skills", str(len(list(real.glob("ai-*")))), str(real)),
            ("links", str(len(wiring.linked())), "one skills root per surface found"),
            ("guards", str(len(on)), "one entry in each surface's own settings file"),
            ("receipt", "", str(wiring.receipt_path())),
        ]
    )


def global_step(args) -> outcome.Result:
    if args.skip_global or (global_ready() and not args.do_global):
        # Whether there is anything to report is the same question the block reports on, so
        # it is asked of the disk too. It used to be "is the receipt non-empty", which is how
        # a stripped machine got the block and a wired one with a lost receipt got silence.
        if wiring.wired()[0] or wiring.linked():
            already(wiring.receipt())
        return outcome.result("READY")

    only = [s for s in args.harness.split(",") if s] or None
    found = wiring.detect(only)
    ui.section("◇ Global")
    rows = []
    for surface in wiring.table()["surface"]:
        if surface in found:
            mark, style = "found", "ok"
        elif surface["detect"]:
            mark, style = "not installed — skipped", "muted"
        else:
            # A row with no detect path is not absent, it is unanswerable: the only
            # candidate was a file we write ourselves, so it is wired on your word.
            mark, style = "wired by name only", "warn"
        rows.append((surface["name"], surface["detect"] or "—", mark, style))
    ui.survey(rows)
    # Counted from what this wheel carries, not written into the sentence. `already` below
    # says the same thing about the line it replaced; these two were the same literal, in
    # the same file, four lines apart.
    shipped = len(list(paths.skills().glob("ai-*")))
    out(
        f"\n   Writes {shipped} skills into {paths.home() / 'skills'}, symlinks from the "
        f"roots above,\n"
        f"   and one guard entry in each found surface's own settings file.\n"
        f"   Nothing else is touched. Undo: `ai-eng uninstall`.\n"
    )

    if args.dry:
        out("   → skipped.")
        return outcome.dry_run(exact_changes=True)
    if only or args.yes or not sys.stdin.isatty():
        # Named, unattended, or piped: the flags already said which surfaces, and a widget
        # with nobody in front of it is a hang.
        if not ask("Set up this machine?", True, args):
            out("   → skipped.")
            return outcome.result("CANCELLED")
    else:
        found = surfaces_picked(found)
        if not found:
            out("   → skipped.")
            return outcome.result("CANCELLED")

    written = wiring.install_skills(found)
    # Counted off the store after the copy, so this row reports what landed rather than what
    # was intended. The line above counts the wheel; a receipt that reads the same number as
    # the plan cannot contradict it, and contradicting it is the only reason to print one.
    landed = len(list((paths.home() / "skills").glob("ai-*")))
    ui.step("ok", f"{landed} skills".ljust(10), f"→ {paths.home() / 'skills'}/ai-*/")
    # And what they are for, grouped the way the catalogue is meant to be read. `EP-135` asks
    # that the surfaces show the skills by the five phases, and the map existed only inside a
    # gate runner — so the field was declared for a person meeting thirteen unfamiliar commands
    # and the only person who ever saw it was a developer watching CI. This is the moment that
    # person exists: they have just been given the thirteen.
    for phase, names in wiring.phase_map():
        ui.step("would", f"{phase:<8}".ljust(10), ", ".join(names) or "nothing declared")
    for row in written[1:]:
        ui.step("ok", f"{row['how']:<8}", f"→ {row['path']}")
    # The routers, and the count of surfaces that could not have one. A surface with no
    # declared command root is not a failure and is not silence either: it is the reason
    # `/ai-spec` works on one surface and not on the next, and a person deciding whether
    # they are set up deserves the number rather than the discovery.
    routers = wiring.install_routers(found)
    written.extend(routers)
    without = [s["id"] for s in found if not s.get("commands")]
    if routers:
        ui.step("ok", f"{len(routers)} routers".ljust(10), f"→ /{'ai-*'} on 1 surface")
    if without:
        ui.step("would", "routers".ljust(10), f"no command root declared: {', '.join(without)}")
    pending_approval = False
    for name, target, detail in wiring.install_guards(found):
        # Appended and not merged means a person has to approve it before it runs, which
        # is a warning and not a tick: the difference between installed and running is the
        # whole subject of assertion 21.
        pending = "append" in detail
        pending_approval = pending_approval or pending
        ui.step("warn" if pending else "ok", "guards    ", f"→ {target or name} ({detail})")
        if pending:
            ui.note(
                "Codex will not run it until you approve it: type /hooks in Codex.\n"
                "`doctor` reports it as INERT until then."
            )
    _record(
        written
        + [
            {"path": s["settings"], "kind": "guard", "how": s["writer"]}
            for s in found
            if s["writer"] != "none"
        ]
    )
    ui.step("ok", "receipt   ", f"→ {wiring.receipt_path()}")
    return outcome.result("WARN" if pending_approval else "PASS")


def surfaces_picked(found: list[dict]) -> list[dict]:
    """The machine question, as a list you move a cursor over rather than a yes to a table
    you have just read. Every surface is offered and only the ones actually detected here
    arrive ticked — a widget that pre-ticks all eight is a widget whose default writes into
    eight places.

    Ctrl-C is not the empty selection. One means stop, the other means "none of these", and
    `cli.main` already turns the interrupt into exit 130 and one honest line."""
    rows = wiring.table()["surface"]
    chosen = ui.pick(
        "Set up which surfaces?",
        [(row["id"], row["detect"] or "wired by name only") for row in rows],
        {row["id"] for row in found},
    )
    if chosen is None:
        raise KeyboardInterrupt
    return [row for row in rows if row["id"] in chosen]


# Written once and never offered again. The constitution says these two are not to be
# touched after they exist, and a prompt that offers a forbidden action is a rule that only
# holds while somebody reads carefully. They stay in OFFERS, which is also the create set:
# dropping them from that would stop them ever being written at all.
PROTECTED = ("AGENTS.md", "CONSTITUTION.md")


def managed_paths(root: Path) -> frozenset[Path]:
    """The finite set of repository files an install may later remove.

    The receipt remembers which subset was actually written. This set is the other half of
    that decision: editing the receipt cannot expand ownership to an arbitrary file merely
    because it lives below the repository root."""
    offered = {root / name for name in OFFERS if name not in PROTECTED}
    framework = {
        root / ".ai" / "config.toml",
        root / ".ai" / ".gitignore",
        root / "specs" / ".gitkeep",
    }
    return frozenset(offered | framework)


def existing(root: Path) -> list[tuple[str, int, str]]:
    """What is here, is not ours, and is ours to offer to replace. A file whose content is
    already exactly what we would render is not offered either: a second `init` over an
    unchanged repository has nothing to write, and offering to overwrite a file with itself
    is a screen reporting work that would not happen."""
    rows = []
    for name, (becomes, render) in OFFERS.items():
        path = root / name
        if not path.exists() or name in PROTECTED:
            continue
        body = path.read_text(errors="replace")
        if body != render(root):
            rows.append((name, len(body.splitlines()), becomes))
    return rows


def select(reply: str, rows: list[tuple[str, int, str]]) -> tuple[set[str], list[str]]:
    """One parser for the typed reply and for `--overwrite`, because they are one intent.
    Two of them five lines apart is how a comma came to select one file in silence in the
    prompt and two on the command line. Numbers and names both, separated by commas or
    spaces or both, and `all` in either spelling. Whatever it could not use comes back to
    be named, because a selection prompt that drops half of what you typed and says
    nothing is worse than one that refuses."""
    names = [name for name, _, _ in rows]
    picked: set[str] = set()
    ignored: list[str] = []
    for token in reply.replace(",", " ").split():
        if token.lower() == "all":
            picked.update(names)
        elif token.isdigit() and 0 < int(token) <= len(names):
            picked.add(names[int(token) - 1])
        elif token in names:
            picked.add(token)
        else:
            ignored.append(token)
    return picked, ignored


def choose(rows: list[tuple[str, int, str]], args) -> set[str]:
    """Which of your own files to overwrite. At a keyboard that is a list you move a cursor
    over, with nothing ticked; everywhere else it is the parser, which is what `--overwrite`
    and `-y` and every piped run go through."""
    if not rows:
        return set()
    if not (args.overwrite.strip() or args.yes or not sys.stdin.isatty()):
        ui.section(f"◇ {len(rows)} files already exist and are not ours")
        chosen = ui.pick(
            "Overwrite which? Each one is copied to a dated backup first.",
            [(name, f"{lines:>4} lines  →  {becomes}") for name, lines, becomes in rows],
            set(),
        )
        if chosen is None:
            raise KeyboardInterrupt
        return set(chosen)
    picked, ignored = select(args.overwrite, rows)
    if ignored:
        out(f"   → ignored, nothing on the list matches: {', '.join(ignored)}")
    return picked


def marks(args) -> tuple[str, str]:
    """The state and the verb, in the tense the run is actually in. The writes were guarded
    by --dry-run and the printing was not, so a preview reported a backup written and a
    file written having written neither, and the test that covered it asserted the files
    were absent rather than that the output had stopped saying otherwise.

    A state and not a glyph: which character stands for "this happened" is the renderer's
    business, and this file no longer spells one."""
    return ("would", "would be created") if args.dry else ("ok", "written")


def backup(root: Path, path: Path, args) -> str:
    """A dated copy under `.ai/backups/`, before anything replaces it. Sub-second, because
    whole seconds are not resolution enough for a name whose only job is to be unique:
    two overwrites of one file inside the same second gave the same name, and the second
    copy destroyed the first backup — the recovery path, overwritten by what it recovers
    from.

    Under `.ai/` and no longer beside the original, because the managed `.ai/.gitignore`
    ignores everything there and a `.gitignore` cannot reach out of its own directory: at
    the repository root these accumulated, nothing ignored them and `git add -A` committed
    them. `uninstall` does not touch `.ai/`, so the recovery path outlives the framework."""
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    copy = root / ".ai" / "backups" / f"{path.name}.bak-{stamp}"
    if not args.dry:
        copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, copy)
    return str(copy.relative_to(root))


def write_offer(root: Path, name: str, args) -> None:
    path = root / name
    state, verb = marks(args)
    if path.exists():
        ui.step(state, f"{name} backup", f"→ {backup(root, path, args)} {verb}")
    if not args.dry:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(OFFERS[name][1](root), encoding="utf-8")


def stacks(root: Path) -> list[str]:
    """A short detection, not a table of 29 binaries: the full list is documentation,
    where it costs no lines and cannot go stale inside a release."""
    markers = {
        "pyproject.toml": "python",
        "package.json": "node",
        "go.mod": "go",
        "Cargo.toml": "rust",
        "pom.xml": "java",
        "Gemfile": "ruby",
        # Two markers, one stack, and neither of them is a fixed name — which is why this
        # asks the directory rather than the path: `glob` answers for a literal too.
        "*.csproj": "dotnet",
        "*.sln": "dotnet",
    }
    return sorted({name for marker, name in markers.items() if any(root.glob(marker))})


def _lexical_path(path: Path) -> Path:
    return Path(os.path.abspath(path))


def _safe_path(path: Path, kind: str | None = None) -> bool:
    """Reject aliases and special files before a bounded install can follow them."""
    try:
        lexical = _lexical_path(path)
        if lexical.resolve(strict=False) != lexical:
            return False
        if not os.path.lexists(lexical):
            return True
        info = lexical.lstat()
        if stat.S_ISLNK(info.st_mode):
            return False
        if kind == "directory" and not stat.S_ISDIR(info.st_mode):
            return False
        if kind == "file" and not stat.S_ISREG(info.st_mode):
            return False
        required = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
        if not info.st_mode & required:
            return False
        if stat.S_ISDIR(info.st_mode):
            searchable = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
            return bool(info.st_mode & searchable)
        if stat.S_ISREG(info.st_mode):
            with lexical.open("rb") as stream:
                stream.read(1)
            return True
        # Neither a directory nor a regular file: a socket, a device, a named pipe. This
        # used to answer `kind is None`, so a caller that asked for no particular kind was
        # told a named pipe was safe — while the line above this function says it rejects
        # special files. Every caller in the product passes a kind, so nothing changes for
        # anybody; what changes is that the sentence is now true.
        return False
    except OSError:
        return False


def _receipt_state() -> dict | None:
    try:
        data = wiring.receipt()
        rows = data.get("wrote", [])
        if not isinstance(rows, list):
            return None
        legacy = data.get("version") not in {None, __version__}
        identities = []
        for row in rows:
            if (
                not isinstance(row, dict)
                or not all(isinstance(row.get(field), str) for field in ("path", "kind"))
                or (not legacy and not isinstance(row.get("how"), str))
            ):
                return None
            identities.append((row["path"], row["kind"]))
        if len(identities) != len(set(identities)):
            return None
        return data
    except (AttributeError, wiring.Unreadable):
        return None


def _record(entries: list[dict]) -> None:
    """Hard-migrate incomplete legacy ownership before recording current writes."""
    data = wiring.receipt()
    if data.get("version") not in {None, __version__}:
        replaced = {(row["path"], row["kind"]) for row in entries}
        kept = [
            row
            for row in data.get("wrote", [])
            if (row["path"], row["kind"]) in replaced or isinstance(row.get("how"), str)
        ]
        if len(kept) != len(data.get("wrote", [])):
            data["wrote"] = kept
            wiring.write_json(wiring.receipt_path(), data)
    wiring.record(entries)


def _project_paths_safe(root: Path) -> bool:
    directories = {
        root,
        root / ".ai",
        root / ".ai" / "backups",
        root / ".github",
        root / ".github" / "workflows",
        root / "specs",
    }
    files = {
        *managed_paths(root),
        *(root / name for name in PROTECTED),
        root / ".ai" / "intent.md",
        root / ".git" / "config",
    }
    if not all(_safe_path(path, "directory") for path in directories):
        return False
    if not all(_safe_path(path, "file") for path in files):
        return False
    receipt = wiring.receipt_path()
    if not _safe_path(receipt.parent, "directory") or not _safe_path(receipt, "file"):
        return False
    return _receipt_state() is not None


def _global_paths_safe(args) -> list[Path] | None:
    """`None` when this machine's install paths are not ours to write. Otherwise the skill
    directories we found belonging to somebody else, which are skipped and named.

    It returned a bare `False` for both, and one foreign folder under one of our sixteen
    names refused every surface on the machine over a message that named no path. A name
    collision in a root we share is not a reason to install nothing."""

    only = [surface for surface in args.harness.split(",") if surface] or None
    theirs: list[Path] = []
    try:
        receipt = wiring.receipt_path()
        if not _safe_path(receipt.parent, "directory") or not _safe_path(receipt, "file"):
            return None
        installed = _receipt_state()
        if installed is None:
            return None
        found = wiring.detect(only)
        store = paths.home() / "skills"
        if not _safe_path(paths.home(), "directory") or not _safe_path(store, "directory"):
            return None
        store_owned = any(
            row.get("path") == str(store)
            and row.get("kind") == "skills"
            and row.get("how") == "wheel"
            for row in installed.get("wrote", [])
        )
        if not store_owned and any(store.glob("ai-*")):
            return None
        for surface in found:
            settings = wiring.expand(surface["settings"]) if surface.get("settings") else None
            if settings is not None:
                if not _safe_path(settings.parent, "directory") or not _safe_path(settings, "file"):
                    return None
                if settings.exists() and surface["writer"].startswith("json_"):
                    wiring.read_json(settings)
                if (
                    settings.exists()
                    and surface["writer"] == "ts_opencode"
                    and wiring.SIGNATURE not in settings.read_text(encoding="utf-8")
                ):
                    return None
            if not surface.get("skills"):
                continue
            skills_root = wiring.expand(surface["skills"])
            if not _safe_path(skills_root, "directory"):
                return None
            # Named, not refused. `wiring.foreign` answers the one question the disk can:
            # a non-empty real directory at a name we ship, in a root the receipt does not
            # record us copying into, is somebody else's. It is skipped at the write site
            # and printed here, and the other fifteen skills install.
            ours = [source.name for source in paths.skills().glob("ai-*")]
            theirs.extend(wiring.foreign(skills_root, ours))
    except (KeyError, OSError, UnicodeError, wiring.Unreadable):
        return None
    return sorted(set(theirs))


def _project_preflight(args) -> tuple[Path | None, intent.Validation | None] | None:
    if args.skip_project:
        return None, None
    where = _lexical_path(Path(args.project or "."))
    if not _safe_path(where, "directory"):
        return None
    root = paths.repo_root(where)
    if root is None:
        return None, None
    root = _lexical_path(root)
    if not _safe_path(root, "directory") or not _project_paths_safe(root):
        return None
    return root, intent.validate(root / ".ai" / "intent.md", root)


def project_step(args, prepared_root: Path | None = None) -> outcome.Result:
    if args.skip_project:
        return outcome.result("READY")
    where = _lexical_path(Path(args.project or "."))
    root = prepared_root or paths.repo_root(where)
    if root is None:
        ui.section(f"◇ Project   {where}   not a git repository")
        # A literal False, and not sys.stdin.isatty(): `ask` returns the default under -y,
        # so a terminal-shaped default would make `cd ~ && ai-eng init -y` create a
        # repository in whatever directory the person happened to be standing in.
        if args.dry or not where.is_dir() or not ask("Run `git init` here?", False, args):
            out("   → skipped. There is nothing to set up outside a repository.")
            status = "INCOMPLETE" if args.project is not None or args.dry else "READY"
            return outcome.result(status)
        subprocess.run(["git", "-C", str(where), "init", "-b", "main"], check=True, timeout=10)
        ui.step("ok", "git init  ", f"→ {where}")
        root = where  # git init put .git directly here, so there is nothing to walk up to
    root = _lexical_path(root)
    if not _safe_path(root, "directory") or not _project_paths_safe(root):
        return outcome.result("INCOMPLETE")
    pinned = root / ".ai" / "config.toml"
    if pinned.exists() and args.project is None:
        out(
            f"  Project ready — {pinned.relative_to(root)}, spec chain wired\n\n  Nothing to do. "
            f"`ai-eng doctor` for the full check."
        )
        return outcome.result("READY")

    ui.section(f"◇ Project   {root}   git repository, not set up")
    if not (args.project is not None or ask("Set up this project too?", sys.stdin.isatty(), args)):
        out("   → skipped. Nothing was written.")
        return outcome.result("READY")

    state, verb = marks(args)
    # Written when they are absent, and never rewritten. `.ai/config.toml` is the pin: it
    # names which version of the framework governs this repository, and `ai-eng update` is
    # the verb that changes it — refusing on a dirty tree, refusing without a keyboard, and
    # asking for a typed y. This used to rewrite it on every run, taking a dated backup and
    # printing a line, which is that verb with all three gates removed and a receipt handed
    # over afterwards. It also reset every tuned value in it: the guard windows, and the
    # observability endpoint somebody's alerts point at.
    pins = {
        ".ai/config.toml": skeletons.CONFIG_TOML.format(version=__version__),
        ".ai/.gitignore": skeletons.AI_GITIGNORE,
    }
    fresh = {name: body for name, body in pins.items() if not (root / name).exists()}
    keep = root / "specs" / ".gitkeep"
    keep_is_fresh = not keep.exists()
    if not args.dry:
        pinned.parent.mkdir(parents=True, exist_ok=True)
        for name, body in fresh.items():
            (root / name).write_text(body, encoding="utf-8")
        (root / "specs").mkdir(exist_ok=True)
        if keep_is_fresh:
            keep.touch()
    framework_changes = [*fresh, *(["specs/.gitkeep"] if keep_is_fresh else [])]
    if framework_changes:
        ui.step(state, " · ".join(framework_changes))
    if len(fresh) != len(pins):
        ui.note(
            f"{', '.join(name for name in pins if name not in fresh)} was already here and "
            f"is untouched. `ai-eng update` is the only verb that changes the pin."
        )
    # Read before it is overwritten, and recorded, because uninstall has to put back what
    # was here rather than unset a setting somebody else configured.
    #
    # Recorded once, and never again: the second run reads our own hooks directory as "what
    # was here before us" and stores that, so `uninstall` restored the repository to the
    # very thing it was asked to remove. Same rule spec 007 applied to the pin, one row over
    # — the first write is the one that knows what was there.
    kept = next(
        (
            row["how"]
            for row in wiring.receipt().get("wrote", [])
            if row.get("path") == str(root) and isinstance(row.get("how"), str)
        ),
        None,
    )
    before = kept if kept is not None else ("" if args.dry else wiring.prior_hooks_path(root))
    hooks = str(paths.git_hooks()) if args.dry else wiring.wire_git(root)
    ui.step(state, "core.hooksPath", f"→ {hooks}")
    # One `which`, at the moment the wall is built rather than at the person's next
    # commit. Wiring sets ai.managed, and the shipped pre-commit exits 1 when that flag is
    # set and gitleaks is absent, so this used to leave a repository that refused every
    # commit and said nothing about it. It observes one thing and claims nothing else:
    # guessing between brew, apt, winget and scoop is four branches no job here executes.
    waiting = []
    if shutil.which("gitleaks") is None:
        out(
            "   ⚠ gitleaks is not on your PATH. While this repository is managed the "
            "shipped\n     pre-commit hook exits 1 on every commit until it is there: "
            "`brew install gitleaks`,\n     or your platform's package manager. "
            "This installs no binaries."
        )
        waiting.append("install gitleaks, or every commit here is refused")

    # Before the loop, and that ordering is the whole of it: asked afterwards, the disk
    # answers yes for every file this run had just created, and the same screen that
    # reported writing them offers to overwrite them.
    rows = existing(root)
    files = len(fresh) + int(keep_is_fresh)
    wrote = [*fresh, *(["specs/.gitkeep"] if keep_is_fresh else [])]
    for name in OFFERS:
        if not (root / name).exists():
            write_offer(root, name, args)
            files += 1
            wrote.append(name)
            ui.step(state, name, f"{verb} ({OFFERS[name][0]})")
    picked = choose(rows, args)
    for name in sorted(picked):
        write_offer(root, name, args)
        files += 1
        wrote.append(name)
    # What we wrote here, in the one place that already answers "did we create this?".
    # Uninstall used to delete four files by name from a hardcoded tuple with no record
    # that we had ever written them, so a project instruction file somebody wrote by hand
    # was removed by the verb whose whole pitch is that it is safe.
    if not args.dry:
        _record(
            [
                {"path": str(root / name), "kind": "project", "how": "written"}
                for name in wrote
                if root / name in managed_paths(root)
            ]
            + [{"path": str(root), "kind": "repo", "how": before}]
        )
    ui.step(state, "receipt   ", f"→ {wiring.receipt_path()}")
    left = [name for name, _, _ in rows if name not in picked]
    if left:
        out(
            f"   → left as is: {', '.join(left)}. Nothing was written to them and "
            f"nothing recorded that they were skipped."
        )
        waiting.append(f"{len(left)} of your own files were left alone: {', '.join(left)}")

    found = stacks(root)
    if found:
        out(
            f"\n   Stacks detected: {', '.join(found)}. The justfile carries their lint, test "
            f"and build commands; it installs none of the binaries they need."
        )
    report(files, waiting, args)
    if args.dry:
        return outcome.dry_run(exact_changes=True)
    return outcome.result("WARN" if waiting else "PASS")


def opened(guards: int) -> tuple[str, str]:
    """Where to go, and whether the guards are actually waiting there. The surfaces are
    named rather than described — "open your editor" is advice and "open Claude Code" is an
    instruction — and they are read from the wiring, so a surface added to the table arrives
    on this line without anybody remembering to.

    The second half is why this takes the guard count. `--no-global` writes no entry
    anywhere, and the panel above this line says so in its first row; a next step promising
    the guards are already loaded is that same panel contradicting itself two lines later."""
    names = [surface["name"] for surface in wiring.detect() if surface["writer"] != "none"]
    # Two at most. This is one line inside a panel, and a machine with six surfaces on it
    # would wrap the line, lose its indent and read as an item of its own.
    where = "open " + (" or ".join(names[:2]) if names else "the agent you work in") + " here"
    if guards:
        return where, "the guards are already loaded there — nothing else to start"
    return where, "run `ai-eng init --global`: no guard is registered here yet"


def report(files: int, waiting: list[str], args) -> None:
    """The last screen, and the only thing the version people remember as nicer actually
    had that this one did not. That one asked one question and this asks three, so what
    was being missed was never the picker: it was a panel saying how many files were
    written, how many guard entries were placed, what is still on a person, and what to
    run next. This ended by pasting a block of YAML at the reader and stopping."""
    _, verb = marks(args)
    # Counted off the settings files, like every other number this verb prints. Read from
    # the receipt, this row said `4 guard entries on this machine` on a machine with none,
    # and the step below it then promised the guards were already loaded there.
    guards = len(wiring.wired()[0])
    entries = "entry" if guards == 1 else "entries"
    ui.report(
        f"{files} files {verb} · {guards} guard {entries} on this machine",
        waiting,
        [
            # First, because the alternative is a stranger pushing the workflow that was
            # just written and watching a first build go red for a reason nobody named.
            # Kept inside the panel's width on purpose: a line that wraps loses its indent
            # and reads as an item of its own.
            (
                "fill in the TODO: markers",
                "on purpose; `ai-eng doctor` fails until CONSTITUTION.md has none",
            ),
            ("ai-eng doctor", "every assertion, and the coverage line under it"),
            # Nothing above this line is the product. The guards are loaded in that surface
            # already and the install used to end without once saying where to go and use
            # them, which is the difference between a thing installed and a thing adopted.
            opened(guards),
            ("ai-eng spec new <slug>", "or ask that agent for /ai-spec; the chain starts here"),
        ],
    )


def _terminal(*results: outcome.Result) -> outcome.Result:
    statuses = [result.outcome for result in results]
    if "INCOMPLETE" in statuses or (
        "CANCELLED" in statuses and any(status not in {"READY", "CANCELLED"} for status in statuses)
    ):
        return outcome.result("INCOMPLETE")
    for status in ("CANCELLED", "FAIL", "WARN", "WOULD_CHANGE", "PASS", "READY"):
        if status in statuses:
            return outcome.result(status)
    return outcome.result("INCOMPLETE")


def _refused(why: str, cure: str) -> outcome.Result:
    """An INCOMPLETE that says which one it is.

    Three refusals in `main` printed nothing at all: the will, the four stage lines and
    then INCOMPLETE with no surface table, no reason and no cure. A person meeting that has
    no move, and it is the first verb anybody runs. Measured on a CI runner, where a skills
    root already held directories with our names and this verb refused every install on that
    machine in silence."""

    out(f"\n   INCOMPLETE: {why}")
    out(f"   {cure}")
    return outcome.result("INCOMPLETE")


def main(argv: list[str]) -> outcome.Result:
    args = parse(argv)
    # Invocation authorizes this verb's deterministic install scope. The manifest check
    # proves only that the declarations we install are canonical; metadata grants nothing.
    declared = capability.validate()
    if declared.outcome != "PASS":
        return _refused(
            f"the capability manifest this wheel ships is not canonical: {declared.code}",
            "reinstall the wheel; this is a defect in the package rather than in your machine",
        )

    try:
        prepared = _project_preflight(args)
        if prepared is None:
            return _refused(
                "this repository's path cannot be followed safely",
                "check that no directory in the path is a symlink, and that it is readable",
            )
        root, intent_state = prepared
        theirs: list[Path] = []
        if not args.skip_global:
            collided = _global_paths_safe(args)
            if collided is None:
                return _refused(
                    "something in this machine's install paths is not this installer's to write",
                    "run `ai-eng doctor` to see which surface, or move that file aside",
                )
            theirs = collided

        banner()
        # Before anything is written, because it changes what the counts below mean. A
        # skills root is shared with the person and with every other publisher, and the
        # reader has to be able to tell "we skipped one of yours" from "one is missing".
        if theirs:
            out(f"\n   {len(theirs)} skill folder(s) here are somebody else's.")
            out("   Skipped, not touched:")
            for path in theirs:
                out(f"     {path}")
            out("   Rename ours, or move theirs aside, if you want ours in that surface.")
        machine = global_step(args)
        if machine.outcome == "CANCELLED":
            return machine
        project = project_step(args, root)

        project_ran = args.project is not None or project.outcome in {
            "PASS",
            "WARN",
            "WOULD_CHANGE",
            "INCOMPLETE",
        }
        if project_ran and intent_state is None:
            active_root = paths.repo_root(_lexical_path(Path(args.project or ".")))
            if active_root is not None:
                active_root = _lexical_path(active_root)
                intent_state = intent.validate(active_root / ".ai" / "intent.md", active_root)
        # INCOMPLETE while the Intent is missing or unreadable, which is a decision this
        # repository already took and `test_init_keeps_missing_or_invalid_intent_incomplete`
        # holds: a repository without its canonical Intent is not a governed one, and the
        # honest word for "I cannot prove this is governed" is not PASS.
        #
        # What changed is what the person is told. `intent.validate` reported
        # INTENT_SCHEMA_INVALID over a file nobody had written, which sends a reader looking
        # for a mistake in a document that does not exist; a missing Intent says
        # INTENT_MISSING now, and the two states stop being one answer.
        if project_ran and (intent_state is None or intent_state.outcome != "PASS"):
            project = outcome.result("INCOMPLETE")
        return _terminal(machine, project)
    except KeyboardInterrupt:
        return outcome.result("CANCELLED")
    except (OSError, subprocess.SubprocessError, wiring.Unreadable) as why:
        # Said, not swallowed. The anchor check exists to name a broken install, and a
        # generic "cannot decide" tells the person nothing they can act on.
        print(f"  INCOMPLETE  {why}")
        return outcome.result("INCOMPLETE")
