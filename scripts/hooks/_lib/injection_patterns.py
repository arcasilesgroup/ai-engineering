"""Prompt injection and security patterns for prompt-injection-guard.py."""

import re
from dataclasses import dataclass


@dataclass
class Pattern:
    name: str
    regex: re.Pattern
    severity: str  # 'CRITICAL' | 'HIGH'


PATTERNS: list[Pattern] = [
    # --- CRITICAL: Direct prompt injection / override ---
    Pattern(
        "ignore_previous_instructions",
        re.compile(
            r"ignore\s+(previous|all|your|above)\s+(instructions?|rules?|directives?|constraints?)",
            re.IGNORECASE,
        ),
        "CRITICAL",
    ),
    Pattern(
        "disregard_instructions",
        re.compile(
            r"disregard\s+(previous|all|your|above)\s+(instructions?|rules?|directives?)",
            re.IGNORECASE,
        ),
        "CRITICAL",
    ),
    Pattern(
        "forget_instructions",
        re.compile(
            r"forget\s+(everything|all|your)\s+(you.ve\s+been|previous|above)", re.IGNORECASE
        ),
        "CRITICAL",
    ),
    Pattern(
        "override_instructions",
        re.compile(
            r"override\s+(your|all|previous|system)\s+(instructions?|rules?|directives?|prompt)",
            re.IGNORECASE,
        ),
        "CRITICAL",
    ),
    Pattern(
        "you_are_now_different",
        re.compile(
            r"you\s+are\s+now\s+(a\s+)?(different|new|another|unrestricted|free|jailbroken)",
            re.IGNORECASE,
        ),
        "CRITICAL",
    ),
    Pattern(
        "act_as_unrestricted",
        re.compile(
            r"act\s+as\s+(if\s+you\s+(are|were)|a\s+different|an?\s+unrestricted|an?\s+unfiltered)",
            re.IGNORECASE,
        ),
        "CRITICAL",
    ),
    Pattern(
        "new_instructions_colon",
        re.compile(r"new\s+(instructions?|rules?|system\s+prompt|directive)\s*:", re.IGNORECASE),
        "CRITICAL",
    ),
    Pattern(
        "system_prompt_override",
        re.compile(r"system\s*:\s*(you\s+are|ignore|forget|override)", re.IGNORECASE),
        "CRITICAL",
    ),
    Pattern(
        "system_bracket_override",
        re.compile(r"\[SYSTEM\]\s*:?\s*(ignore|forget|override|you\s+are)", re.IGNORECASE),
        "CRITICAL",
    ),
    Pattern(
        "dan_jailbreak", re.compile(r"\bDAN\b.*\bdo\s+anything\s+now\b", re.IGNORECASE), "CRITICAL"
    ),
    Pattern("jailbreak_keyword", re.compile(r"\bjailbreak\b", re.IGNORECASE), "CRITICAL"),
    Pattern("developer_mode", re.compile(r"developer\s+mode\s+enabled", re.IGNORECASE), "CRITICAL"),
    Pattern(
        "pretend_no_restrictions",
        re.compile(
            r"pretend\s+you\s+(have\s+no\s+restrictions|are\s+an?\s+(AI|model|assistant)\s+without)",
            re.IGNORECASE,
        ),
        "CRITICAL",
    ),
    Pattern(
        "from_now_on_ignore",
        re.compile(r"from\s+now\s+on\s+(you\s+will|always|never|ignore|act)", re.IGNORECASE),
        "CRITICAL",
    ),
    # --- HIGH: Exfiltration via tool abuse ---
    Pattern(
        "curl_wget_exfil",
        re.compile(
            r"(curl|wget|nc|netcat|ncat)\s+.*(http[s]?://|[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})",
            re.IGNORECASE,
        ),
        "HIGH",
    ),
    Pattern(
        "base64_pipe_shell",
        re.compile(r"base64\s+-d\s*\|\s*(bash|sh|python|node|perl|ruby)", re.IGNORECASE),
        "HIGH",
    ),
    Pattern(
        "eval_encoded",
        re.compile(r"eval\s*\(\s*(base64|atob|decode|exec|compile)", re.IGNORECASE),
        "HIGH",
    ),
    Pattern(
        "env_dump_pipe",
        re.compile(r"(printenv|env\s*\||set\s*\|)\s*(grep|awk|sed|curl|wget)", re.IGNORECASE),
        "HIGH",
    ),
    Pattern(
        "proc_environ_read",
        re.compile(r"cat\s+/proc/(environ|self/environ|version|meminfo)", re.IGNORECASE),
        "HIGH",
    ),
    # --- HIGH: Credential exposure ---
    Pattern(
        "credential_exposure",
        re.compile(
            r"(?i)(api[_-]?key|token|secret|password|authorization|credentials?|auth)"
            r"""([\"'\s:=]+)"""
            r"([A-Za-z]+\s+)?"
            r"([A-Za-z0-9_\-/.+=]{20,})",
        ),
        "HIGH",
    ),
    # --- HIGH: Hidden instructions in file content ---
    Pattern(
        "hidden_html_comment",
        re.compile(r"<!--\s*(ignore|system|instructions?)\s*:", re.IGNORECASE),
        "HIGH",
    ),
    Pattern(
        "hidden_hash_comment",
        re.compile(r"#\s*(SYSTEM|IGNORE|OVERRIDE)\s*:", re.IGNORECASE),
        "HIGH",
    ),
    Pattern(
        "hidden_block_comment",
        re.compile(r"/\*\s*(SYSTEM|IGNORE|OVERRIDE)\s*:", re.IGNORECASE),
        "HIGH",
    ),
]

CRITICAL_PATTERNS = [p for p in PATTERNS if p.severity == "CRITICAL"]
HIGH_PATTERNS = [p for p in PATTERNS if p.severity == "HIGH"]
