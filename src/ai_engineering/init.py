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
import shutil
import subprocess
import sys
from pathlib import Path

from ai_engineering import __version__, paths, skeletons, ui, wiring

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
    if args.yes:
        return default
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


def global_step(args) -> None:
    if args.skip_global or (global_ready() and not args.do_global):
        # Whether there is anything to report is the same question the block reports on, so
        # it is asked of the disk too. It used to be "is the receipt non-empty", which is how
        # a stripped machine got the block and a wired one with a lost receipt got silence.
        if wiring.wired()[0] or wiring.linked():
            already(wiring.receipt())
        return

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
    out(
        f"\n   Writes 8 skills into {paths.home() / 'skills'}, symlinks from the roots above,\n"
        f"   and one guard entry in each found surface's own settings file.\n"
        f"   Nothing else is touched. Undo: `ai-eng uninstall`.\n"
    )

    if args.dry:
        out("   → skipped.")
        return
    if only or args.yes or not sys.stdin.isatty():
        # Named, unattended, or piped: the flags already said which surfaces, and a widget
        # with nobody in front of it is a hang.
        if not ask("Set up this machine?", True, args):
            out("   → skipped.")
            return
    else:
        found = surfaces_picked(found)
        if not found:
            out("   → skipped.")
            return

    written = wiring.install_skills(found)
    ui.step("ok", "8 skills  ", f"→ {paths.home() / 'skills'}/ai-*/")
    for row in written[1:]:
        ui.step("ok", f"{row['how']:<8}", f"→ {row['path']}")
    for name, target, detail in wiring.install_guards(found):
        # Appended and not merged means a person has to approve it before it runs, which
        # is a warning and not a tick: the difference between installed and running is the
        # whole subject of assertion 21.
        pending = "append" in detail
        ui.step("warn" if pending else "ok", "guards    ", f"→ {target or name} ({detail})")
        if pending:
            ui.note(
                "Codex will not run it until you approve it: type /hooks in Codex.\n"
                "`doctor` reports it as INERT until then."
            )
    wiring.record(
        written
        + [
            {"path": s["settings"], "kind": "guard", "how": s["writer"]}
            for s in found
            if s["writer"] != "none"
        ]
    )
    ui.step("ok", "receipt   ", f"→ {wiring.receipt_path()}")


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


def backup(path: Path, args) -> str:
    """A dated copy beside the original, before anything replaces it. Sub-second, because
    whole seconds are not resolution enough for a name whose only job is to be unique:
    two overwrites of one file inside the same second gave the same name, and the second
    copy destroyed the first backup — the recovery path, overwritten by what it recovers
    from."""
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    copy = path.with_name(f"{path.name}.bak-{stamp}")
    if not args.dry:
        shutil.copy2(path, copy)
    return copy.name


def write_offer(root: Path, name: str, args) -> None:
    path = root / name
    state, verb = marks(args)
    if path.exists():
        ui.step(state, f"{name} backup", f"→ {backup(path, args)} {verb}")
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


def project_step(args) -> int:
    if args.skip_project:
        return 0
    where = Path(args.project or ".").resolve()
    root = paths.repo_root(where)
    if root is None:
        ui.section(f"◇ Project   {where}   not a git repository")
        # A literal False, and not sys.stdin.isatty(): `ask` returns the default under -y,
        # so a terminal-shaped default would make `cd ~ && ai-eng init -y` create a
        # repository in whatever directory the person happened to be standing in.
        if args.dry or not where.is_dir() or not ask("Run `git init` here?", False, args):
            out("   → skipped. There is nothing to set up outside a repository.")
            return 0
        subprocess.run(["git", "-C", str(where), "init", "-b", "main"], check=True, timeout=10)
        ui.step("ok", "git init  ", f"→ {where}")
        root = where  # git init put .git directly here, so there is nothing to walk up to
    pinned = root / ".ai" / "config.toml"
    if pinned.exists() and args.project is None:
        out(
            f"  Project ready — {pinned.relative_to(root)}, spec chain wired\n\n  Nothing to do. "
            f"`ai-eng doctor` for the full check."
        )
        return 0

    ui.section(f"◇ Project   {root}   git repository, not set up")
    if not (args.project is not None or ask("Set up this project too?", sys.stdin.isatty(), args)):
        out("   → skipped. Nothing was written.")
        return 0

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
    if not args.dry:
        pinned.parent.mkdir(parents=True, exist_ok=True)
        for name, body in fresh.items():
            (root / name).write_text(body, encoding="utf-8")
        (root / "specs").mkdir(exist_ok=True)
        (root / "specs" / ".gitkeep").touch()
    ui.step(state, " · ".join([*fresh, "specs/"]))
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
        (row["how"] for row in wiring.receipt().get("wrote", []) if row["path"] == str(root)), None
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
            "`brew install gitleaks`,\n     or docs/tools.md for the other platforms. "
            "This installs no binaries."
        )
        waiting.append("install gitleaks, or every commit here is refused")

    # Before the loop, and that ordering is the whole of it: asked afterwards, the disk
    # answers yes for every file this run had just created, and the same screen that
    # reported writing them offers to overwrite them.
    rows = existing(root)
    files = len(fresh) + 1
    wrote = [*fresh, "specs/.gitkeep"]
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
        wiring.record(
            [
                {"path": str(root / name), "kind": "project", "how": "written"}
                for name in wrote
                if name not in PROTECTED  # yours from the second they were written
            ]
            + [{"path": str(root), "kind": "repo", "how": before}]
        )
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
            f"and build commands; the binaries are listed in docs/tools.md and this "
            f"installs none of them."
        )
    report(files, waiting, args)
    return 0


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


def main(argv: list[str]) -> int:
    args = parse(argv)
    banner()
    global_step(args)
    return project_step(args)
