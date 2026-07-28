"""spec-201 D-201-18 — advisory cross-model routing replay.

Replays the committed routing corpus against two OpenAI-compatible models and
reports each one's score against the recorded reference. It NEVER blocks a
merge: the workflow that runs it is advisory by construction (a job in a
separate workflow file cannot join the ``CI Result`` aggregate), and this
script's own exit code is only a signal.

Egress posture (RK-11): the only text sent is
``.ai-engineering/evals/cross-model-replay/corpus.json`` — a committed fixture
of routing questions. Nothing derived from the working tree — no source, no
diffs, no spec bodies — is transmitted. See the ``## Data Governance`` section
of ``.ai-engineering/specs/spec.md``.

Unprovisioned is a first-class outcome, not a failure: with no credential the
script prints a ``SKIPPED`` line naming the missing variable and exits 0. Fork
pull requests never receive secrets, and a workflow that reds on a withheld
secret teaches people to ignore it.

Transport: ``POST {base}/v1/chat/completions`` only. Brief E2 measured
``/v1/messages`` and ``/anthropic/v1/messages`` as 404 on the probed endpoint,
so no other shape is attempted. Stdlib only — ``urllib.request`` — so the job
needs no dependency install and the workflow needs no unpinned runtime install.

Usage::

    python3 scripts/run_cross_model_replay.py [--json report.json]

Exit codes:
- 0 — every model matched the reference score, or the replay was skipped.
- 1 — at least one model scored below the reference (an advisory regression).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_CORPUS_DIR = _REPO_ROOT / ".ai-engineering" / "evals" / "cross-model-replay"
_CORPUS = _CORPUS_DIR / "corpus.json"
_REFERENCE = _CORPUS_DIR / "claude-reference.json"

_BASE_URL_ENV = "AIENG_REPLAY_BASE_URL"
_API_KEY_ENV = "AIENG_REPLAY_API_KEY"

# Both measured schema-valid at brief E5 and 8/8 at E10. D-201-18 asks for at
# least two so a single model's bad day is distinguishable from a regression.
_MODELS: tuple[str, ...] = ("deepseek-v4-flash", "gemma4")

# E9: a completion budget too small for the reasoning pass returns EMPTY
# content with `finish_reason: "length"` — a distinct failure class, not a
# parse error. 1024 is the floor the capability table records for the
# reasoning families.
_MAX_TOKENS = 1024
_TIMEOUT_SEC = 60
_RETRY_BACKOFF_SEC = 2.0


class TransportError(RuntimeError):
    """A connection-level failure — reported distinctly from a wrong answer.

    RK-9: a connection drop was observed during probing. Conflating it with an
    incorrect answer would turn provider intermittency into a routing
    regression, which is exactly the noise that makes an advisory signal get
    ignored.
    """


def _ask(base_url: str, api_key: str, model: str, prompt: str) -> str:
    """POST one chat completion and return the assistant message text."""
    body = json.dumps(
        {
            "model": model,
            "max_tokens": _MAX_TOKENS,
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/v1/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SEC) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise TransportError(str(exc)) from exc
    except (json.JSONDecodeError, ValueError) as exc:
        raise TransportError(f"unparseable response: {exc}") from exc

    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    message = choices[0].get("message")
    if not isinstance(message, dict):
        return ""
    # RK-4: reasoning text is a separate field; never fold it into the answer.
    content = message.get("content")
    return content if isinstance(content, str) else ""


def _ask_with_one_retry(base_url: str, api_key: str, model: str, prompt: str) -> tuple[str, bool]:
    """Return ``(answer, dropped)``. One retry with backoff on a drop."""
    try:
        return _ask(base_url, api_key, model, prompt), False
    except TransportError:
        time.sleep(_RETRY_BACKOFF_SEC)
    try:
        return _ask(base_url, api_key, model, prompt), True
    except TransportError as exc:
        print(f"  transport: {model} dropped twice — {exc}", file=sys.stderr)
        return "", True


def _graded(answer: str, expected: str) -> bool:
    return expected.lower() in (answer or "").lower()


def replay(base_url: str, api_key: str, corpus: dict) -> list[dict]:
    """Score every model against the corpus. Never writes a price table."""
    results: list[dict] = []
    for model in _MODELS:
        answers: list[dict] = []
        drops = 0
        for question in corpus["questions"]:
            answer, dropped = _ask_with_one_retry(base_url, api_key, model, question["prompt"])
            drops += int(dropped)
            answers.append(
                {
                    "id": question["id"],
                    "expected": question["expected"],
                    "answer": answer.strip()[:280],
                    "correct": _graded(answer, question["expected"]),
                }
            )
        results.append(
            {
                "model": model,
                "score": sum(1 for a in answers if a["correct"]),
                "total": len(answers),
                "connection_drops": drops,
                "answers": answers,
            }
        )
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="run_cross_model_replay",
        description="spec-201 D-201-18 advisory cross-model routing replay.",
    )
    parser.add_argument("--json", type=Path, default=None, help="Write the report to this path.")
    args = parser.parse_args(argv)

    base_url = (os.environ.get(_BASE_URL_ENV) or "").strip()
    api_key = (os.environ.get(_API_KEY_ENV) or "").strip()
    missing = [
        name for name, value in ((_BASE_URL_ENV, base_url), (_API_KEY_ENV, api_key)) if not value
    ]
    if missing:
        print(f"SKIPPED: no provider credential — {', '.join(missing)} not set.")
        print("SKIPPED: the replay is advisory; an unprovisioned run is not a failure.")
        return 0

    corpus = json.loads(_CORPUS.read_text(encoding="utf-8"))
    reference = json.loads(_REFERENCE.read_text(encoding="utf-8"))
    reference_score = int(reference["score"])

    results = replay(base_url, api_key, corpus)
    regressed = False
    for result in results:
        marker = "ok" if result["score"] >= reference_score else "REGRESSION"
        print(
            f"{marker}: {result['model']} {result['score']}/{result['total']} "
            f"(reference {reference_score}/{reference['total']}, "
            f"connection drops {result['connection_drops']})"
        )
        regressed = regressed or result["score"] < reference_score

    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(
                {"reference": reference_score, "results": results},
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    return 1 if regressed else 0


if __name__ == "__main__":
    raise SystemExit(main())
