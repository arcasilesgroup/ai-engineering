# Tool Selection Guide

How to pick the right stress testing tool for the job.

## Decision tree

1. Is there an existing test script in the repo? Use it. Do not rewrite in a different
   tool just because you can.
2. Is the team familiar with a specific tool? Use that one.
3. Default to k6 for HTTP APIs.

## k6

**Best for:** HTTP APIs, CI/CD pipelines, threshold-driven runs.

**Install:** `brew install k6` (macOS), `docker pull grafana/k6`

**Strengths:**
- Scripts in JavaScript or TypeScript.
- Built-in threshold engine: `http_req_duration: ['p(95)<200']`.
- JSON summary export: `--summary-export results.json`.
- HTML dashboard generation.
- Docker-ready for CI.
- `ramping-arrival-rate` executor for breakpoint tests.
- Low resource usage (no GUI).

**Run commands:**
```bash
k6 run script.js
k6 run script.js --vus 100 --duration 5m
k6 run script.js --out json=results.json
k6 run script.js --summary-export summary.json
```

**Output formats:** JSON summary, CSV (via extension), Prometheus remote write.

## JMeter

**Best for:** Existing `.jmx` test plans, teams with JMeter expertise, complex protocol
testing (JMS, LDAP, SOAP).

**Install:** Download from jmeter.apache.org, requires JVM.

**Strengths:**
- Mature, large ecosystem of plugins.
- GUI for test plan design (use only for design, not execution).
- Supports many protocols beyond HTTP.
- Non-GUI mode for CI: `jmeter -n -t plan.jmx`.

**Run commands:**
```bash
jmeter -n -t test_plan.jmx -l results.jtl -e -o html_report/
```

**Output formats:** JTL (XML/CSV), HTML dashboard.

**Caveats:**
- JVM memory hungry at scale. Tune `-Xmx` for large tests.
- GUI mode is for design only. Never run GUI in CI.
- Results directory must be empty before generating HTML report.

## Locust

**Best for:** Complex user behavior modeling, Python shops, distributed testing.

**Install:** `pip install locust`

**Strengths:**
- Pure Python test scripts.
- Built-in web UI at localhost:8089 for real-time monitoring.
- Master/worker distributed mode.
- Custom load shapes via Python classes.
- Headless mode for CI.

**Run commands:**
```bash
locust -f locustfile.py --host https://api.example.com
locust -f locustfile.py --host https://api.example.com --headless -u 100 -r 10 -t 5m
```

**Output formats:** CSV (request stats, response times, failures), HTML report.

**Caveats:**
- Python process per user (greenlet). Higher memory than k6 for very high concurrency.
- Web UI consumes resources. Use headless in CI.

## Decision table

| Factor | k6 | JMeter | Locust |
|--------|-----|--------|--------|
| Script language | JS/TS | XML (.jmx) | Python |
| CI friendliness | Excellent | Good (needs JVM) | Good (needs Python) |
| Threshold engine | Built-in | Plugin-based | Custom code |
| Resource usage | Low | High (JVM) | Medium (greenlets) |
| Protocol support | HTTP, WS, gRPC | Many (JMS, LDAP, SOAP) | HTTP, custom |
| Distributed | k6 Cloud, k6 Operator | Remote testing | Master/worker |
| Learning curve | Low | Medium | Low (if Python) |
| Breakpoint testing | Native (ramping-arrival-rate) | Manual ramp design | Custom shape |
