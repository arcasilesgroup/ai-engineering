"""One scanner lane, and the five ways it can report nothing without having looked.

A missing engine, missing rules, a crash, a timeout and zero inputs all produce the same
thing on a terminal: no findings. Every one of them is a way for a green to mean the
opposite of what it says, so each one is INCOMPLETE here and each one has its own fixture.

PASS is reachable exactly one way: an engine that was there, with its rules, ran to
completion over inputs that existed, and found nothing.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from ai_engineering import outcome

MISSING_ENGINE = "LANE_ENGINE_MISSING"
MISSING_RULES = "LANE_RULES_MISSING"
TAMPERED_RULES = "LANE_RULES_TAMPERED"
CRASHED = "LANE_CRASHED"
TIMEOUT = "LANE_TIMEOUT"
NO_INPUTS = "LANE_NO_INPUTS"

DEFAULT_TIMEOUT = 120


@dataclass(frozen=True, slots=True)
class Lane:
    """One engine, its argument list, and the two things that decide how to read it: which
    exit code means "found something", and how long it may take."""

    id: str
    argv: tuple[str, ...]
    rules: Path | None = None
    rules_digest: str = ""
    findings_exit: int = 1
    timeout: int = DEFAULT_TIMEOUT
    extra: tuple[str, ...] = field(default=())
    # How this engine is asked for SARIF, with `{}` standing for the file it writes. Empty
    # means it was never asked: `report` then says so rather than reporting nothing found,
    # which is the same distinction the whole module is about, one level down.
    sarif: tuple[str, ...] = field(default=())


def _incomplete(lane: Lane, code: str, why: str, cure: str) -> outcome.Fact:
    return outcome.fact(
        f"lane-{lane.id}", "INCOMPLETE", f"The {lane.id} lane", f"{code}: {why}", cure=cure
    )


def run(lane: Lane, root: Path, inputs: list[str]) -> outcome.Fact:
    """Run one lane over one list of inputs and say what it observed.

    The order matters. Inputs are checked before the engine is started, because a lane with
    nothing to scan is not a lane that scanned; and the rules are checked before the exit
    code is read, because an engine with no rules exits zero having looked for nothing.
    """

    if not inputs:
        return _incomplete(
            lane,
            NO_INPUTS,
            "there was nothing to scan, so nothing was scanned",
            "point the lane at files that exist, or say why this stack has none",
        )
    if lane.rules is not None:
        where = Path(root) / lane.rules if not Path(lane.rules).is_absolute() else Path(lane.rules)
        if not where.is_file():
            return _incomplete(
                lane,
                MISSING_RULES,
                f"the rules at {Path(lane.rules).name} are not there",
                "restore the rules file; an engine with no rules looks for nothing",
            )
        # One byte is enough. A rule deleted from the middle of a file leaves an engine that
        # runs, exits zero, and no longer looks for the thing it was deleted for — which is
        # indistinguishable from a clean scan unless the bytes themselves are pinned.
        if lane.rules_digest:
            found = hashlib.sha256(where.read_bytes()).hexdigest()
            if found != lane.rules_digest:
                return _incomplete(
                    lane,
                    TAMPERED_RULES,
                    f"{Path(lane.rules).name} is not the file this lane was pinned to",
                    "review the change and move the pin deliberately, or restore the file",
                )

    try:
        done = subprocess.run(
            [*lane.argv, *lane.extra, *inputs],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=lane.timeout,
            check=False,
        )
    except FileNotFoundError:
        return _incomplete(
            lane,
            MISSING_ENGINE,
            f"{lane.argv[0]} is not installed here",
            "install the pinned engine, or record this lane as not applicable",
        )
    except subprocess.TimeoutExpired:
        return _incomplete(
            lane,
            TIMEOUT,
            f"it did not finish within {lane.timeout} seconds",
            "narrow the inputs or raise the bound deliberately",
        )
    except OSError as why:
        return _incomplete(
            lane, CRASHED, f"it could not be executed: {type(why).__name__}", "check the engine"
        )

    if done.returncode == lane.findings_exit:
        return outcome.fact(
            f"lane-{lane.id}",
            "FAIL",
            f"The {lane.id} lane",
            f"it ran over {len(inputs)} input(s) and found something",
            cure="read its output, fix what it found, and run it again",
        )
    if done.returncode != 0:
        return _incomplete(
            lane,
            CRASHED,
            f"it exited {done.returncode}, which has no meaning in this lane",
            "read its output; an exit code with no defined meaning is not a verdict",
        )
    return outcome.fact(
        f"lane-{lane.id}",
        "PASS",
        f"The {lane.id} lane",
        f"it ran over {len(inputs)} input(s) and found nothing",
    )


# The three lanes this repository's own baseline runs, in one place so the gate and any
# future reader of it see the same list. Each `findings_exit` is the engine's documented
# code for "I found something"; anything else it can exit is undefined and INCOMPLETE.
BASELINE = (
    Lane(
        "secrets",
        ("gitleaks", "dir"),
        extra=("--redact", "--no-banner", "--exit-code", "1"),
        sarif=("--report-format", "sarif", "--report-path", "{}"),
    ),
    Lane(
        "semantic",
        ("semgrep", "scan"),
        rules=Path("policy/semgrep.yml"),
        # Moved deliberately when the rules change, and a test says so with the command that
        # prints the new value. A pin nobody has to update is a pin nobody notices missing.
        rules_digest="81adf3bdbd24ca883bbc75d659e9a44ba0967ef4c4445628bb78f63f85a26c2a",
        extra=("--config", "policy/semgrep.yml", "--error", "--quiet"),
        sarif=("--sarif-output", "{}"),
    ),
    Lane(
        "dependencies",
        ("trivy", "fs"),
        extra=(
            "--scanners",
            "vuln,license,misconfig",
            "--exit-code",
            "1",
            "--severity",
            "CRITICAL,HIGH,MEDIUM",
            # Off by default in this engine, and measured here: with it off, the whole npm
            # tree of this repository — every package in `package-lock.json` — was excluded
            # from every scan this gate has ever run, and the lane exited zero. A build
            # dependency compiles the plugin that ships in the wheel, so "it is only a dev
            # dependency" is not a boundary this project has.
            "--include-dev-deps",
        ),
        sarif=("--format", "sarif", "--output", "{}"),
    ),
)


# The two cross-checks the proposal names by product, and the reason they are here rather
# than in `BASELINE`. Neither is required: this repository's baseline is the three lanes
# above and it passes with neither installed, which is the whole point of a cross-check —
# a second opinion an organisation may want, never a dependency this framework acquires.
#
# What was missing is that the tree said nothing at all about them. `grep` for either name
# found spec prose and no code, so a reader could not tell "we decided not to require this"
# from "nobody thought about it", and the requirement asks for exactly that distinction:
# configured and unable to run is INCOMPLETE, absent is not applicable.
# The manifests a dependency scan is about, by the file each stack keeps them in. One
# `trivy fs .` covers every repository and names none of them, so a repository whose stack
# the engine does not read passes exactly like one it read and found nothing in — which is
# the difference this whole module exists to keep. Naming what was covered is what turns
# "it ran and found nothing" into an answer somebody can check.
MANIFESTS = (
    "pyproject.toml",
    "requirements.txt",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "Gemfile",
    "pom.xml",
    "build.gradle",
    "composer.json",
)
IMAGES = ("Dockerfile", "Containerfile")

# Which file the engine actually reads for each stack, which is the half of EP-042 that a
# list of manifests cannot answer. A dependency scanner does not read the manifest a person
# edits; it reads the resolved file beside it, and where that file is absent it reads
# nothing, reports nothing and exits zero — which is indistinguishable from a clean scan.
# Measured on this repository: `pyproject.toml` with no lock produced "Not scanned", and
# `package-lock.json` was excluded entirely because its packages are all development ones.
READS = {
    "pyproject.toml": ("uv.lock", "poetry.lock", "pdm.lock", "requirements.txt"),
    "requirements.txt": ("requirements.txt",),
    "package.json": ("package-lock.json", "pnpm-lock.yaml", "yarn.lock"),
    "Cargo.toml": ("Cargo.lock",),
    "go.mod": ("go.mod", "go.sum"),
    "Gemfile": ("Gemfile.lock",),
    "pom.xml": ("pom.xml",),
    "build.gradle": ("gradle.lockfile",),
    "composer.json": ("composer.lock",),
}


def covered(root: Path, lane: Lane | None = None) -> set[str]:
    """Every file the dependency engine actually read, in its own words.

    Asked of the engine rather than inferred from the tree: what a scanner supports is the
    scanner's business and it changes between releases, so a table of ours claiming coverage
    would be a claim about somebody else's software that nothing checks. An engine that
    cannot answer returns nothing, and nothing is what makes a stack INCOMPLETE below.
    """

    import json

    engine = lane or BASELINE[-1]
    try:
        done = subprocess.run(
            # The lane's own arguments, and not a second copy of them. Built from `argv`
            # alone this asked a different question than the run that decided the verdict:
            # remove `--include-dev-deps` from the lane and the coverage line would still
            # have reported the npm tree read — a green answer about a scan that skipped it,
            # which is the defect that flag was added to close, restated one function over.
            [*engine.argv, *engine.extra, "--list-all-pkgs", "--format", "json", "."],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=engine.timeout,
            check=False,
        )
        loaded = json.loads(done.stdout)
    except (OSError, subprocess.SubprocessError, ValueError):
        return set()
    if not isinstance(loaded, dict):
        return set()
    return {
        str(row.get("Target"))
        for row in (loaded.get("Results") or [])
        if isinstance(row, dict) and row.get("Target")
    }


def unread(root: Path, lane: Lane | None = None) -> list[str]:
    """Every stack this repository has that the engine read no file for.

    This is the distinction the whole module is named after, at the level of a stack rather
    than a lane: a manifest whose resolved file is missing, or whose packages the engine
    excluded, produces the same silence as a stack with nothing wrong in it.
    """

    # By name, because the two sides speak different dialects: `stacks` returns the bare
    # file name and the engine returns the path it read it at. A repository whose package
    # lives in `api/` — the shape `stacks` descends a level to find — was therefore
    # permanently INCOMPLETE over a file the engine had read, with no cure short of hoisting
    # the lock to the root. A control somebody can only satisfy by rearranging their
    # repository is a control they learn to skip.
    read = {Path(target).name for target in covered(root, lane)}
    return [
        manifest
        for manifest in stacks(root)
        if not any(name in read for name in READS.get(manifest, ()))
    ]


def stacks(root: Path) -> list[str]:
    """Every dependency manifest in this repository, by name and sorted.

    Shallow on purpose: a manifest inside `node_modules` or a vendored copy belongs to
    somebody else's project, and walking the whole tree turns one answer into hundreds.
    """

    found = {name for name in MANIFESTS if (Path(root) / name).is_file()}
    for entry in sorted(Path(root).iterdir()) if Path(root).is_dir() else []:
        if entry.is_dir() and not entry.name.startswith((".", "node_modules")):
            found.update(name for name in MANIFESTS if (entry / name).is_file())
    return sorted(found)


def images(root: Path) -> list[str]:
    """The container definitions, if any. A container lane over a repository with no image
    is a lane scanning nothing, and this repository has none."""

    return sorted(name for name in IMAGES if (Path(root) / name).is_file())


CROSS_CHECKS = (
    Lane("skillspector", ("skillspector", "scan")),
    Lane("claude-security", ("claude-security", "review")),
)


# The seven fields `ai-security` says one finding is, and no eighth. Three of them a scanner
# can fill and four of them it cannot, which is the whole reason this record exists rather
# than a line of engine output pasted into a report: the effect, the location and the command
# are observations, and the boundary crossed, what an attacker controls, the refutation
# somebody tried and what would close it are judgements nobody has made yet.
#
# So every finding a scanner produces is INCOMPLETE by the skill's own rule — a field left
# blank makes the finding INCOMPLETE — and it names which fields are blank. A scanner hit
# presented as a completed finding is a preference with a severity attached, and a queue of
# them is how a team learns to skip the next one.
UNANSWERED = "nobody has answered this"


@dataclass(frozen=True, slots=True)
class Finding:
    """One finding in the seven fields the skill defines, and no eighth."""

    boundary: str
    attacker_controls: str
    effect: str
    state: str
    decided_by: str
    refutation: str
    closed_by: str

    def blank(self) -> tuple[str, ...]:
        return tuple(
            name
            for name in ("boundary", "attacker_controls", "refutation", "closed_by")
            if getattr(self, name) == UNANSWERED
        )


def _results(report: Path) -> list[dict]:
    """Every result in a SARIF file, or nothing if it is not one.

    SARIF is the engines' own output format and reading it is not reimplementing their
    detectors, which is what `D-014-01` refused. A file that is not SARIF, or that this
    version of the format nests differently, yields no results — and `report` turns that
    into an INCOMPLETE rather than a clean answer.
    """

    import json

    try:
        loaded = json.loads(report.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(loaded, dict):
        return []
    found: list[dict] = []
    for run_of in loaded.get("runs", []):
        if not isinstance(run_of, dict):
            continue
        for row in run_of.get("results", []):
            # Shaped, not merely present. The docstring above promises that a report this
            # code cannot read yields nothing rather than an answer, and for a while it only
            # kept that promise down to the row: `"message": "a string"` is a shape some
            # converters emit, and it left an AttributeError coming out of the security gate
            # instead of a verdict. A gate that terminates with a traceback has not decided,
            # and this module's whole rule is that an undecided lane is INCOMPLETE.
            if not isinstance(row, dict):
                continue
            message = row.get("message")
            locations = row.get("locations")
            if message is not None and not isinstance(message, dict):
                continue
            if locations is not None and not isinstance(locations, list):
                continue
            found.append(row)
    return found


def report(lane: Lane, root: Path, inputs: list[str]) -> list[Finding]:
    """Ask a lane's engine what it found, in its own words, as findings.

    Run separately and only when a lane has already failed: the gate's verdict comes from
    the exit code and nothing here may change it. The second run costs nothing on a green
    gate and, on a red one, is the difference between "it found something" and a list
    somebody can act on.
    """

    if not lane.sarif or not inputs:
        return []
    import tempfile

    with tempfile.TemporaryDirectory() as area:
        where = Path(area) / "report.sarif"
        flags = tuple(flag.format(where) for flag in lane.sarif)
        try:
            subprocess.run(
                [*lane.argv, *lane.extra, *flags, *inputs],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=lane.timeout,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return []
        rows = _results(where)

    findings = []
    for row in rows:
        first = (row.get("locations") or [{}])[0]
        physical = first.get("physicalLocation") if isinstance(first, dict) else None
        physical = physical if isinstance(physical, dict) else {}
        artifact = physical.get("artifactLocation")
        region = physical.get("region")
        at = (
            artifact.get("uri", "an unnamed file")
            if isinstance(artifact, dict)
            else "an unnamed file"
        )
        line = region.get("startLine", "?") if isinstance(region, dict) else "?"
        text = (row.get("message") or {}).get("text")
        message = str(text).strip() if text is not None else str(row.get("ruleId", ""))
        findings.append(
            Finding(
                boundary=UNANSWERED,
                attacker_controls=UNANSWERED,
                effect=" ".join(message.split())[:200],
                state="INCOMPLETE",
                decided_by=f"{' '.join(lane.argv)} — {at}:{line}",
                refutation=UNANSWERED,
                closed_by=UNANSWERED,
            )
        )
    return findings


def cross_check(lane: Lane, root: Path, inputs: list[str]) -> outcome.Fact:
    """A second opinion, or the honest answer that nobody asked for one.

    Absent means not applicable and passes: an organisation that never installed this tool
    is not failing a check, it is declining one. Present means it runs under exactly the
    contract the baseline runs under — an engine that is there and cannot answer is
    INCOMPLETE, and INCOMPLETE is not a pass. The difference between those two sentences is
    the entire requirement.
    """

    if shutil.which(lane.argv[0]) is None:
        return outcome.fact(
            f"cross-{lane.id}",
            "SKIPPED",
            f"The {lane.id} cross-check",
            f"{lane.argv[0]} is not installed here, so there is no second opinion to read",
        )
    return run(lane, root, inputs)


def baseline(root: Path) -> int:
    """Run the three lanes and return the exit code the gate should take.

    INCOMPLETE fails the gate exactly as FAIL does. A lane that could not run is a lane
    whose answer nobody has, and the whole point of this module is that nobody's answer is
    not a clean one.
    """

    worst = 0
    for lane in BASELINE:
        fact = run(lane, root, ["."])
        print(f"  {fact.status:<11} {lane.id:<13} {fact.detail}")
        if fact.status != "PASS":
            worst = 1
        if fact.status == "FAIL":
            # "It found something" is where a security gate used to stop, and the next move
            # was always to run the engine again by hand. It runs itself now, in its own
            # output format, and every finding arrives INCOMPLETE with the four fields no
            # scanner can fill named — because a scanner hit that reads as a completed
            # finding is exactly the green nobody earned, with the sign reversed.
            for finding in report(lane, root, ["."]):
                print(f"  {finding.state:<11} {lane.id:<13} {finding.effect}")
                print(f"  {'':<11} {'':<13} decided by {finding.decided_by}")
                print(f"  {'':<11} {'':<13} nobody has answered: {', '.join(finding.blank())}")
    # What the dependency answer was about, named. `trivy fs .` reads every repository and
    # names no stack, so one whose manifests the engine does not support passes exactly like
    # one it read and found nothing in. A repository with no manifest at all is declining a
    # dependency scan rather than passing one, and it says so.
    # The second opinion, asked rather than only declared. This function existed and nothing
    # in the product called it: an organisation that installs one of these engines expecting
    # the framework to read it would have got the same silence as one that installed nothing,
    # which is the distinction this whole module is named after — applied to the two engines
    # the proposal names by product. Absent is SKIPPED and passes; present and unable to
    # answer is INCOMPLETE and does not.
    for lane in CROSS_CHECKS:
        fact = cross_check(lane, root, ["."])
        print(f"  {fact.status:<11} {lane.id:<13} {fact.detail}")
        if fact.status not in ("PASS", "SKIPPED"):
            worst = 1

    present = stacks(root)
    print(
        f"  {'OBSERVED':<11} {'manifests':<13} {', '.join(present)}"
        if present
        else f"  {'SKIPPED':<11} {'manifests':<13} no dependency manifest here, so there is "
        f"nothing for a dependency scan to be about"
    )
    # And which of them the engine read a file for. A manifest it read nothing for is a
    # stack that was not scanned, reported by the lane above as nothing found — so it is
    # INCOMPLETE and it fails this gate, exactly as every other way of reporting nothing
    # without having looked does.
    if present:
        missed = unread(root)
        if missed:
            worst = 1
            print(
                f"  {'INCOMPLETE':<11} {'coverage':<13} the engine read no file for "
                f"{', '.join(missed)}: a stack it did not read reports as a stack with "
                f"nothing in it"
            )
            # And the cure, in the line, because two legitimate shapes land here — a
            # manifest whose lock file is not committed, and a stack whose lock file is
            # opt-in and rarely used. Both are genuinely unscanned, so neither is a false
            # positive; what would make this a control people skip is arriving with no way
            # forward but rearranging the repository.
            print(
                f"  {'':<11} {'':<13} commit the file the engine reads for it "
                f"({', '.join(sorted({n for m in missed for n in READS.get(m, ())}))}), "
                f"or record a dated risk acceptance with `ai-eng accept`"
            )
        else:
            print(
                f"  {'OBSERVED':<11} {'coverage':<13} the engine read a file for every "
                f"manifest here"
            )
    found = images(root)
    print(
        f"  {'OBSERVED':<11} {'images':<13} {', '.join(found)}"
        if found
        else f"  {'SKIPPED':<11} {'images':<13} no container image here, so no container lane runs"
    )
    return worst
