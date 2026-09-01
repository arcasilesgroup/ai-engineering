#!/usr/bin/env python3
"""Score review reports against a planted-bug manifest.

Recall is computed automatically: every planted defect is either found or it is
not. Precision is not — deciding whether an *unplanted* finding is real is a
judgment call, so this prints a triage list for you to adjudicate and then
computes precision from your answers.

Usage:
    score.py --run ~/.claude/evals/myrepo-20260728-101500/manifest.json
    score.py --run MANIFEST --reports .claude/reviews --window 8
    score.py --run MANIFEST --adjudicate   # recompute after editing triage.json

Stdlib only. Python 3.8+.
"""

import argparse
import json
import pathlib
import re
import sys
from datetime import datetime

SEV = "CRITICAL|HIGH|MEDIUM|LOW"
HEADING_FINDING = re.compile(r"^#{2,5}\s*\[(" + SEV + r")\]\s*(.+)$", re.I)
LIST_FINDING = re.compile(r"^\s*\d+\.\s*\*\*\[(" + SEV + r")\]\s*(.+?)\*\*", re.I)
SECTION = re.compile(r"^#{1,5}\s+\S")
REF = re.compile(r"([A-Za-z0-9_@./\\-]+\.[A-Za-z0-9]+):(\d+)")
LANE_FROM_NAME = re.compile(r"^(.*?)-\d{8}-\d{6}\.md$")


def die(msg):
    print("error: " + msg, file=sys.stderr)
    sys.exit(1)


def lane_of(path):
    m = LANE_FROM_NAME.match(path.name)
    return m.group(1) if m else path.stem


def parse_report(path):
    """Split a report into findings: severity, claim, body text, file:line refs."""
    findings = []
    current = None
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = HEADING_FINDING.match(raw) or LIST_FINDING.match(raw)
        if m:
            if current:
                findings.append(current)
            current = {
                "severity": m.group(1).upper(),
                "claim": m.group(2).strip().strip("*"),
                "body": [raw],
                "lane": lane_of(path),
                "report": path.name,
            }
            continue
        if current is not None:
            # A new non-finding section ends the current finding block.
            if SECTION.match(raw) and not HEADING_FINDING.match(raw):
                findings.append(current)
                current = None
                continue
            current["body"].append(raw)
    if current:
        findings.append(current)

    for f in findings:
        text = "\n".join(f["body"])
        f["text"] = text
        f["refs"] = [(p.replace("\\", "/"), int(n)) for p, n in REF.findall(text)]
    return findings


def path_matches(ref_path, bug_path):
    a = ref_path.strip("./").split("/")
    b = bug_path.strip("./").split("/")
    n = min(len(a), len(b))
    return n > 0 and a[-n:] == b[-n:]


def match_bug(bug, findings, window):
    """Return (finding, quality) for the best match, or (None, None)."""
    lines = bug.get("line_candidates") or [bug["line"]]
    patterns = [re.compile(p, re.I) for p in bug.get("match", [])]
    best = None
    for f in findings:
        near = any(
            path_matches(rp, bug["file"]) and any(abs(rl - bl) <= window for bl in lines)
            for rp, rl in f["refs"]
        )
        if not near:
            continue
        if patterns and not all(p.search(f["text"]) for p in patterns):
            best = best or (f, "WEAK")
            continue
        return f, "FOUND"
    return best or (None, None)


def load_triage(run_dir):
    p = run_dir / "triage.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True, help="path to manifest.json from plant.py")
    ap.add_argument("--reports", default=".claude/reviews", help="report dir or single .md")
    ap.add_argument("--window", type=int, default=8, help="line tolerance (default 8)")
    ap.add_argument("--adjudicate", action="store_true", help="use triage.json verdicts")
    args = ap.parse_args()

    manifest_path = pathlib.Path(args.run).expanduser().resolve()
    if not manifest_path.exists():
        die("no manifest at {}".format(manifest_path))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    run_dir = manifest_path.parent
    bugs = manifest["bugs"]

    rp = pathlib.Path(args.reports)
    if not rp.is_absolute():
        rp = pathlib.Path(manifest["repo"]) / rp
    report_files = [rp] if rp.is_file() else sorted(rp.glob("*.md"))
    if not report_files:
        die("no reports found at {} — did the review write its report?".format(rp))

    findings = []
    for f in report_files:
        findings.extend(parse_report(f))
    if not findings:
        die(
            "parsed 0 findings from {} report file(s). Either the review found "
            "nothing (recall 0 — that is a result) or it did not follow the "
            "output contract in CONVENTIONS.md §6.".format(len(report_files))
        )

    triage = load_triage(run_dir) if args.adjudicate else {}

    rows, matched_ids = [], set()
    for bug in bugs:
        f, quality = match_bug(bug, findings, args.window)
        if f:
            matched_ids.add(id(f))
            right_lane = bug.get("lane") in (None, f["lane"])
            rows.append((bug, quality, f, right_lane))
        else:
            rows.append((bug, "MISSED", None, False))

    found = [r for r in rows if r[1] == "FOUND"]
    weak = [r for r in rows if r[1] == "WEAK"]
    missed = [r for r in rows if r[1] == "MISSED"]
    wrong_lane = [r for r in found if not r[3]]
    extra = [f for f in findings if id(f) not in matched_ids]

    verdicts = {}
    for f in extra:
        # Keyed on lane + claim, not on position, so a triage verdict survives
        # a re-run that adds or reorders findings.
        key = "{}::{}".format(f["lane"], re.sub(r"\s+", " ", f["claim"])[:70])
        f["key"] = key
        verdicts[key] = triage.get(key, "unknown")
    real_extra = sum(1 for v in verdicts.values() if v == "real")
    noise = sum(1 for v in verdicts.values() if v == "noise")
    unknown = sum(1 for v in verdicts.values() if v == "unknown")

    recall = len(found) / len(bugs) if bugs else 0.0
    true_pos = len(found) + real_extra
    # Precision is undefined while any unplanted finding is unjudged. Treating
    # `unknown` as real is exactly the flattery this harness exists to prevent.
    precision = None
    if unknown == 0 and (true_pos + noise):
        precision = true_pos / (true_pos + noise)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = [
        "# Eval score — {}".format(manifest.get("pack")),
        "",
        "**Run:** `{}` · planted {} · scored {}".format(
            manifest["branch"], manifest["planted_at"], stamp
        ),
        "**Reports:** {}".format(", ".join(f.name for f in report_files)),
        "**Findings parsed:** {} · line tolerance ±{}".format(len(findings), args.window),
        "",
        "| Metric | Value |",
        "|---|---|",
        "| **Recall** | **{:.0%}** ({}/{} planted defects found) |".format(
            recall, len(found), len(bugs)
        ),
        "| Weak matches | {} (right location, claim does not describe the defect) |".format(
            len(weak)
        ),
        "| Wrong lane | {} (found, but by a lane that does not own it) |".format(
            len(wrong_lane)
        ),
        "| **Precision** | {} |".format(
            "**{:.0%}** ({} real / {} judged)".format(precision, true_pos, true_pos + noise)
            if precision is not None
            else "pending — {} unplanted findings need adjudication".format(unknown)
        ),
        "",
        "## Planted defects",
        "",
        "| ID | Class | Expected lane | Where | Result | Found by |",
        "|---|---|---|---|---|---|",
    ]
    mark = {"FOUND": "✅ found", "WEAK": "⚠️ weak", "MISSED": "❌ missed"}
    for bug, quality, f, right_lane in rows:
        by = f["lane"] if f else "—"
        if f and not right_lane:
            by += " ⚠️"
        out.append(
            "| {} | {} | {} | `{}:{}` | {} | {} |".format(
                bug["id"], bug["class"], bug.get("lane", "—"),
                bug["file"], bug["line"], mark[quality], by,
            )
        )

    if missed or weak:
        out += ["", "## Misses — read these, they are the point", ""]
        for bug, quality, _f, _rl in rows:
            if quality in ("MISSED", "WEAK"):
                out.append(
                    "- **{} ({})** — {} — `{}:{}`{}".format(
                        bug["id"], mark[quality].split()[-1], bug.get("expect", bug["class"]),
                        bug["file"], bug["line"],
                        "" if quality == "MISSED" else "  ← flagged the line, described it wrong",
                    )
                )

    out += [
        "",
        "## Unplanted findings — adjudicate these",
        "",
        "Mark each `real` or `noise` in `triage.json`, then re-run with "
        "`--adjudicate`. A finding you cannot decide about is noise: if the "
        "report did not make it decidable, it would not have been actioned either.",
        "",
    ]
    if not extra:
        out.append("_None. Every finding mapped to a planted defect._")
    for f in extra:
        out.append(
            '- `"{}"` — **[{}]** {} _(from {})_'.format(
                f["key"], f["severity"], f["claim"], f["lane"]
            )
        )

    report_md = run_dir / "score-{}.md".format(stamp)
    report_md.write_text("\n".join(out) + "\n", encoding="utf-8")

    triage_path = run_dir / "triage.json"
    if extra and not triage_path.exists():
        triage_path.write_text(
            json.dumps({f["key"]: "unknown" for f in extra}, indent=2), encoding="utf-8"
        )

    print("recall    {:.0%}  ({}/{} found, {} weak, {} missed)".format(
        recall, len(found), len(bugs), len(weak), len(missed)))
    if precision is not None:
        print("precision {:.0%}  ({} real / {} judged)".format(precision, true_pos, true_pos + noise))
    else:
        print("precision pending — adjudicate {} findings in {}".format(unknown, triage_path))
    print(report_md)


if __name__ == "__main__":
    main()
