from __future__ import annotations

import io
import json

import quality_gate


def test_live_gate_is_resolved_from_the_project_before_its_conditions_are_read(monkeypatch):
    replies = iter(
        [
            {"qualityGate": {"id": 144658, "name": "the assigned gate"}},
            {"conditions": [{"metric": "new_coverage", "op": "LT", "error": "80"}]},
        ]
    )
    urls = []

    def answer(request, timeout):
        urls.append(request.full_url)
        return io.BytesIO(json.dumps(next(replies)).encode())

    monkeypatch.setattr(quality_gate.urllib.request, "urlopen", answer)
    assert quality_gate.live("group_project", "group", "secret") == {"new_coverage": ("LT", 80.0)}
    assert urls == [
        "https://sonarcloud.io/api/qualitygates/get_by_project?project=group_project&organization=group",
        "https://sonarcloud.io/api/qualitygates/show?id=144658&organization=group",
    ]
