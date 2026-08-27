"""One exporter, OTLP over HTTP with a JSON body, and no dependency.

Everything unreachable that way is reachable through the standard collector, which is
our extension system and costs us zero lines: point the framework at the collector's
:4318 and let it fan out. That is the documented answer for Dynatrace, which rejects
JSON, and for Azure Application Insights, whose rotating identity token does not fit in
a fixed header.

Two failure modes are designed for rather than hoped about. A 200 is not a delivery —
the protocol returns the number of rejected records inside a successful response — so
`probe` requires a 2xx AND zero rejections. And nothing free-text leaves: the allow-list
below is what goes, and everything else leaves as its hash and its length.
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
import uuid

from _emit import chain_path, config, machine_id, repo_id

KEEP = ("cls", "name", "seq", "ts", "session", "repo", "machine", "hash")
# The four at the end are spec 011's field names and spec 014's export path: which surface
# an event came from, which version of it, which adapter translated it, and how a denial was
# expressed there. They are in clear because every one of them names software rather than a
# person or a place — and outside this list they would leave as a sixteen-character hash,
# which answers no question anybody exports observability to ask.
KEEP_DATA = (
    "outcome",
    "phase",
    "verb",
    "exit",
    "guard",
    "fp",
    "archived",
    "ms",
    "id",
    "surface_id",
    "surface_version",
    "adapter_version",
    "deny_protocol",
)


def opaque(value) -> dict:
    text = str(value)
    return {"sha256": hashlib.sha256(text.encode()).hexdigest()[:16], "len": len(text)}


def redact(event: dict) -> dict:
    """Everything outside the two allow-lists leaves as a hash and a length.

    `command` keeps its first token and nothing else. It used to keep the first two,
    written after the hashing pass so the prefix survived every mode including strict —
    and the second token is the argument on any command that takes one:
    `curl https://host/?token=…` is two tokens, and so is `psql --password=…`. The one
    test guarding it used `git push <canary>`, where the canary is the third token and
    falls outside the cut, so the suite agreed with the defect by choosing the input that
    could not see it. The first token is the program, which is never an argument, and it
    still answers the question the field was added for: what ran.

    A `mode` parameter was read and ignored here until its callers stopped passing it: `"none"` used to send every unlisted field verbatim and it was
    a supported value in the pin: a configuration that disables a privacy control is a
    control whoever runs the exporter can switch off, and nothing downstream could tell a
    machine that had redacted from one that had been told not to. Deleted under spec 014
    D-014-08, hard, with no shim — rule 4 — and an unrecognised value redacts like every
    other, because the safe reading of a word nobody knows is the strict one."""

    out = {k: event[k] for k in KEEP if k in event}
    data = event.get("data") or {}
    kept = {k: v for k, v in data.items() if k in KEEP_DATA}
    kept.update({k: opaque(v) for k, v in data.items() if k not in KEEP_DATA})
    if isinstance(data.get("command"), str):
        kept["command"] = data["command"].split()[:1]
        kept["command"] = kept["command"][0] if kept["command"] else ""
    out["data"] = kept
    return out


def as_logs(events: list[dict]) -> dict:
    """OTLP in JSON. The field names are lowerCamelCase, not snake_case: a destination
    that receives snake_case answers 200 and keeps nothing."""
    records = []
    for event in events:
        body = redact(event)
        records.append(
            {
                "timeUnixNano": "0",
                "severityNumber": 17 if event.get("cls") == "error" else 9,
                "severityText": "ERROR" if event.get("cls") == "error" else "INFO",
                "body": {"stringValue": json.dumps(body, separators=(",", ":"))},
                "attributes": [
                    {"key": f"aieng.{k}", "value": {"stringValue": str(body.get(k, ""))}}
                    for k in ("cls", "name", "session", "repo", "machine")
                ],
            }
        )
    return {
        "resourceLogs": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "ai-engineering"}},
                        {"key": "host.id", "value": {"stringValue": machine_id()}},
                        {"key": "vcs.repository.id", "value": {"stringValue": repo_id()}},
                    ]
                },
                "scopeLogs": [{"logRecords": records}],
            }
        ]
    }


def post(body: dict) -> tuple[int, int, str]:
    """Returns (status, rejected, detail). Rejected comes out of the successful
    response, which is where the protocol puts it. One lane exists, logs; the `signal`
    parameter was generality for a traces-and-metrics exporter nobody configured."""
    signal = "logs"
    settings = config().get("observability", {})
    endpoint = str(settings.get("endpoint", "")).rstrip("/")
    if not endpoint:
        return 0, 0, "no endpoint configured"
    # A destination with no stated retention gets nothing. This exporter can say exactly
    # what leaves — two allow-lists, everything else a hash and a length — and it cannot say
    # how long the far end keeps it, because that is the operator's system and not ours.
    # What it can refuse to do is send personal-adjacent telemetry to somewhere nobody has
    # written down a retention for. `retention_days` is a number the person configuring the
    # endpoint puts beside it; it is not validated against the destination, and it is not
    # meant to be. It is the decision, made deliberately, in the file where the endpoint is
    # chosen — and no export happens until somebody has made it.
    retention = settings.get("retention_days")
    if not isinstance(retention, int) or isinstance(retention, bool) or retention <= 0:
        return (
            0,
            0,
            "no retention_days beside the endpoint: nobody has decided how long this is kept",
        )
    headers = {"Content-Type": "application/json"}
    name, env = settings.get("auth_header"), settings.get("auth_env")
    if name and env:
        headers[str(name)] = os.environ.get(str(env), "")
    request = urllib.request.Request(
        f"{endpoint}/v1/{signal}", data=json.dumps(body).encode(), headers=headers
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read() or b"{}")
            partial = payload.get("partialSuccess") or {}
            rejected = int(partial.get(f"rejected{signal.title().rstrip('s')}Records", 0) or 0)
            return response.status, rejected, partial.get("errorMessage", "")
    except urllib.error.HTTPError as err:
        return err.code, 0, err.reason
    except (urllib.error.URLError, ValueError, TimeoutError) as err:
        return 0, 0, str(err)


def send_tail(count: int) -> tuple[int, int, str]:
    settings = config().get("observability", {})
    if "logs" not in (settings.get("signals") or []):
        return 0, 0, "logs not in the configured signals"
    try:
        lines = chain_path().read_text().splitlines()[-count:]
    except OSError:
        return 0, 0, "no chain to send"
    events = [json.loads(line) for line in lines if line.strip()]
    return post(as_logs(events))


def probe() -> tuple[bool, str]:
    """A synthetic event with an identifier we made up. If it comes back 2xx with zero
    rejections, the destination is real. Anything else and you are sending into a void
    while believing you have observability."""
    canary = uuid.uuid4().hex
    event = {
        "cls": "session",
        "name": "doctor-probe",
        "seq": 0,
        "ts": "",
        "session": canary,
        "repo": repo_id(),
        "machine": machine_id(),
        "hash": "",
        "data": {"id": canary},
    }
    body = as_logs([event])
    status, rejected, detail = post(body)
    if 200 <= status < 300 and rejected == 0:
        return True, f"{status}, 0 rejected"
    return False, f"{status or 'no response'}, {rejected} rejected {detail}".strip()
