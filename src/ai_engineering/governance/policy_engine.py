"""Rego-subset policy engine (spec-110 Phase 3, T-3.8).

Pure-Python evaluator for a small, well-defined subset of OPA Rego sufficient
to express the three policies shipped with spec-110:

* ``branch_protection.rego`` -- deny pushes to ``main``/``master``.
* ``commit_conventional.rego`` -- conventional-commits subject prefix.
* ``risk_acceptance_ttl.rego`` -- TTL-not-expired check.

The full OPA daemon is out of scope (see spec-110 R-4); when policy needs
outgrow this subset, the team will migrate to OPA proper. Until then, this
stdlib-only module avoids a heavyweight Go runtime in CI and Claude hooks.

Supported grammar
-----------------

A policy file is parsed line-by-line after stripping ``#``-comments. The
following constructs are recognised:

* ``package <name>`` -- informational; recorded but otherwise ignored.
* ``default allow := <bool>`` -- default verdict when no ``allow`` rule fires.
* ``allow if <expr>`` -- if ``<expr>`` evaluates truthy, the engine returns
  ``Decision(allow=True)`` and stops.
* ``deny[<msg>] if <expr>`` and ``deny if <expr>`` -- if ``<expr>`` evaluates
  truthy, the engine returns ``Decision(allow=False, reason=<msg|expr>)``.

Inside ``<expr>`` the grammar supports (with conventional precedence):

* Literals: integers, floats, ``true``, ``false``, ``null``, double-quoted
  strings (with ``\\"`` and ``\\\\`` escapes).
* Input access: ``input.<field>`` (single dotted path; nested paths
  ``input.a.b`` are supported).
* Comparisons: ``==``, ``!=``, ``<``, ``>``, ``<=``, ``>=``.
* Boolean ops: ``and``, ``or``, ``not`` (``not`` is a prefix unary).
* Built-in calls: ``regex.match(<pattern>, <value>)``,
  ``time.parse_rfc3339_ns(<value>)``.
* Parentheses for grouping.

Multi-rule semantics: rules are evaluated in source order. The *first*
``allow`` rule whose body is truthy wins. If no ``allow`` rule fires, the
*first* ``deny`` rule whose body is truthy wins (with the supplied message
or the source expression as reason). Otherwise the default applies.

Notes
-----

* String comparison with ``<`` / ``>`` is lexicographic, which makes the
  RFC-3339 timestamps used by ``risk_acceptance_ttl.rego`` chronologically
  comparable as long as they share a timezone offset (``Z`` in our case).
* Integer division and arithmetic operators are deliberately omitted -- the
  three target policies do not need them. Add support only when a future
  policy requires it (spec-110 R-4 escalation path).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = ["Decision", "PolicyError", "evaluate"]


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Decision:
    """Outcome of evaluating a policy against an ``input_data`` dict.

    Attributes
    ----------
    allow:
        ``True`` when the policy permits the action, ``False`` when it
        denies. ``default allow := false`` plus no firing ``allow`` rule
        results in ``allow=False``; an explicit ``deny if`` match also
        produces ``allow=False`` and populates :attr:`reason`.
    reason:
        Human-readable description of the deny decision. ``None`` when the
        decision is an allow, or when a deny rule did not specify a message.
    """

    allow: bool
    reason: str | None = None


class PolicyError(ValueError):
    """Raised when a policy file is malformed or contains unsupported syntax.

    The Rego subset is intentionally tight; anything outside the supported
    grammar (see module docstring) raises this rather than silently
    misbehaving. Callers in spec-110 surface the message to the operator.
    """


# ---------------------------------------------------------------------------
# Parser -- AST node types and grammar
# ---------------------------------------------------------------------------


_TOKEN_RE = re.compile(
    r"""
    \s*(
        ==|!=|<=|>=|<|>                # comparison ops
      | \(|\)|,|\.                     # punctuation
      | "(?:\\.|[^"\\])*"              # double-quoted string with escapes
      | [+-]?\d+\.\d+                  # float literal
      | [+-]?\d+                       # integer literal
      | [A-Za-z_][A-Za-z0-9_]*         # identifier (keywords + names)
    )
    """,
    re.VERBOSE,
)

_KEYWORDS_BOOL = {"and", "or", "not"}
_LITERAL_KEYWORDS = {"true": True, "false": False, "null": None}
_BUILTINS = {"regex.match", "time.parse_rfc3339_ns"}


def _tokenize(expr: str) -> list[str]:
    """Split an expression into lexical tokens.

    Multi-character operators are captured before single-char punctuation, so
    ``<=`` does not get split into ``<`` and ``=``. Identifiers may contain
    a single ``.`` (e.g. ``input.branch``, ``regex.match``) and are joined by
    a post-pass to keep the parser simple.
    """

    tokens: list[str] = []
    pos = 0
    while pos < len(expr):
        match = _TOKEN_RE.match(expr, pos)
        if match is None:
            remainder = expr[pos:].strip()
            if remainder == "":
                break
            raise PolicyError(f"unrecognised token near: {remainder!r}")
        tokens.append(match.group(1))
        pos = match.end()

    # Join dotted identifiers (input.foo, regex.match, time.parse_rfc3339_ns).
    joined: list[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if (
            tok.isidentifier()
            and i + 2 < len(tokens)
            and tokens[i + 1] == "."
            and tokens[i + 2].replace("_", "a").isalnum()
        ):
            # Greedy join: input.a.b.c becomes a single token.
            chunks = [tok]
            j = i + 1
            while j + 1 < len(tokens) and tokens[j] == "." and tokens[j + 1].isidentifier():
                chunks.append(tokens[j + 1])
                j += 2
            joined.append(".".join(chunks))
            i = j
        else:
            joined.append(tok)
            i += 1
    return joined


class _Parser:
    """Recursive-descent parser for the Rego-subset expression grammar.

    Precedence (lowest -> highest)::

        or
        and
        not
        comparisons (==, !=, <, <=, >, >=)
        primary (literals, input.<path>, calls, parenthesised exprs)
    """

    def __init__(self, tokens: list[str]):
        self._tokens = tokens
        self._pos = 0

    # -- helpers -----------------------------------------------------------

    def _peek(self) -> str | None:
        return self._tokens[self._pos] if self._pos < len(self._tokens) else None

    def _advance(self) -> str:
        if self._pos >= len(self._tokens):
            raise PolicyError("unexpected end of expression")
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def _accept(self, expected: str) -> bool:
        if self._peek() == expected:
            self._advance()
            return True
        return False

    def _expect(self, expected: str) -> None:
        if not self._accept(expected):
            raise PolicyError(f"expected {expected!r}, got {self._peek()!r}")

    # -- entry point -------------------------------------------------------

    def parse(self) -> dict:
        node = self._parse_or()
        if self._peek() is not None:
            raise PolicyError(f"trailing tokens after expression: {self._tokens[self._pos :]!r}")
        return node

    # -- precedence climbers ----------------------------------------------

    def _parse_or(self) -> dict:
        left = self._parse_and()
        while self._peek() == "or":
            self._advance()
            right = self._parse_and()
            left = {"type": "or", "left": left, "right": right}
        return left

    def _parse_and(self) -> dict:
        left = self._parse_not()
        while self._peek() == "and":
            self._advance()
            right = self._parse_not()
            left = {"type": "and", "left": left, "right": right}
        return left

    def _parse_not(self) -> dict:
        if self._peek() == "not":
            self._advance()
            operand = self._parse_not()
            return {"type": "not", "operand": operand}
        return self._parse_comparison()

    def _parse_comparison(self) -> dict:
        left = self._parse_primary()
        op = self._peek()
        if op in {"==", "!=", "<", "<=", ">", ">="}:
            self._advance()
            right = self._parse_primary()
            return {"type": "compare", "op": op, "left": left, "right": right}
        return left

    def _parse_primary(self) -> dict:
        tok = self._peek()
        if tok is None:
            raise PolicyError("unexpected end of expression")

        # Parenthesised group.
        if tok == "(":
            self._advance()
            inner = self._parse_or()
            self._expect(")")
            return inner

        # String literal.
        if tok.startswith('"') and tok.endswith('"'):
            self._advance()
            return {"type": "literal", "value": _decode_string_literal(tok)}

        # Numeric literal.
        if _looks_like_number(tok):
            self._advance()
            value: float | int = float(tok) if "." in tok else int(tok)
            return {"type": "literal", "value": value}

        # Boolean / null literals.
        if tok in _LITERAL_KEYWORDS:
            self._advance()
            return {"type": "literal", "value": _LITERAL_KEYWORDS[tok]}

        # Built-in function call: regex.match(...), time.parse_rfc3339_ns(...).
        if tok in _BUILTINS:
            self._advance()
            self._expect("(")
            args: list[dict] = []
            if self._peek() != ")":
                args.append(self._parse_or())
                while self._accept(","):
                    args.append(self._parse_or())
            self._expect(")")
            return {"type": "call", "name": tok, "args": args}

        # Input access.
        if tok.startswith("input.") or tok == "input":
            self._advance()
            path = tok.split(".")[1:]  # drop the leading "input"
            return {"type": "input", "path": path}

        raise PolicyError(f"unsupported token in expression: {tok!r}")


# ---------------------------------------------------------------------------
# Lexer helpers
# ---------------------------------------------------------------------------


def _looks_like_number(tok: str) -> bool:
    if not tok:
        return False
    head = tok.lstrip("+-")
    if not head:
        return False
    return head.replace(".", "", 1).isdigit() and head.count(".") <= 1


def _decode_string_literal(tok: str) -> str:
    """Decode a double-quoted string literal, supporting ``\\"`` and ``\\\\``."""

    inner = tok[1:-1]
    return inner.replace('\\"', '"').replace("\\\\", "\\")


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------


def _truthy(value: Any) -> bool:
    """Match Rego truthiness: only ``False`` and ``None`` are falsy.

    Numbers (including ``0``) and empty strings are *truthy* in Rego, but
    none of the spec-110 policies rely on that nuance -- they always pair a
    literal with a comparison. We follow the Rego rule for forward-compat.
    """

    return value is not False and value is not None


def _resolve_input(node: dict, input_data: dict) -> Any:
    cursor: Any = input_data
    for key in node["path"]:
        if not isinstance(cursor, dict) or key not in cursor:
            return None
        cursor = cursor[key]
    return cursor


def _call_builtin(name: str, args: list[Any]) -> Any:
    if name == "regex.match":
        if len(args) != 2:
            raise PolicyError("regex.match expects exactly 2 arguments")
        pattern, value = args
        if not isinstance(pattern, str) or not isinstance(value, str):
            raise PolicyError("regex.match arguments must be strings")
        return re.match(pattern, value) is not None

    if name == "time.parse_rfc3339_ns":
        if len(args) != 1:
            raise PolicyError("time.parse_rfc3339_ns expects exactly 1 argument")
        (value,) = args
        if not isinstance(value, str):
            raise PolicyError("time.parse_rfc3339_ns argument must be a string")
        # The full OPA helper returns nanoseconds since epoch. For spec-110
        # policies we only need a *comparable* representation -- returning the
        # original string preserves lexicographic == chronological ordering
        # for RFC-3339 timestamps with a consistent timezone (``Z``).
        return value

    raise PolicyError(f"unknown builtin: {name}")  # pragma: no cover -- guard


def _evaluate_node(node: dict, input_data: dict) -> Any:
    kind = node["type"]
    if kind == "literal":
        return node["value"]
    if kind == "input":
        return _resolve_input(node, input_data)
    if kind == "call":
        args = [_evaluate_node(arg, input_data) for arg in node["args"]]
        return _call_builtin(node["name"], args)
    if kind == "not":
        return not _truthy(_evaluate_node(node["operand"], input_data))
    if kind == "and":
        return _truthy(_evaluate_node(node["left"], input_data)) and _truthy(
            _evaluate_node(node["right"], input_data)
        )
    if kind == "or":
        return _truthy(_evaluate_node(node["left"], input_data)) or _truthy(
            _evaluate_node(node["right"], input_data)
        )
    if kind == "compare":
        return _compare(
            node["op"],
            _evaluate_node(node["left"], input_data),
            _evaluate_node(node["right"], input_data),
        )
    raise PolicyError(f"unknown AST node: {kind}")  # pragma: no cover -- guard


def _compare(op: str, left: Any, right: Any) -> bool:
    if op == "==":
        return left == right
    if op == "!=":
        return left != right
    # For ordering comparisons, both sides must be of the same comparable
    # type. Strings vs numbers raise TypeError on Python 3 -- surface that
    # as a PolicyError so the operator gets a clear remediation hint.
    try:
        if op == "<":
            return left < right
        if op == ">":
            return left > right
        if op == "<=":
            return left <= right
        if op == ">=":
            return left >= right
    except TypeError as exc:
        raise PolicyError(
            f"cannot compare {type(left).__name__} {op} {type(right).__name__}"
        ) from exc
    raise PolicyError(f"unsupported comparison operator: {op}")  # pragma: no cover


# ---------------------------------------------------------------------------
# Source -> rules
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Rule:
    """One ``allow``/``deny`` rule extracted from a policy file."""

    kind: str  # "allow" or "deny"
    body: dict  # AST returned by _Parser
    message: str | None  # explicit deny message; None when omitted


@dataclass(frozen=True)
class _Policy:
    package: str | None
    default_allow: bool
    rules: tuple[_Rule, ...]


_DEFAULT_RE = re.compile(r"^default\s+allow\s*:?=\s*(true|false)\s*$")
_PACKAGE_RE = re.compile(r"^package\s+([A-Za-z_][A-Za-z0-9_.]*)\s*$")
_ALLOW_RE = re.compile(r"^allow\s+if\s+(.+)$")
_DENY_INLINE_RE = re.compile(r'^deny\[\s*"([^"]*)"\s*\]\s+if\s+(.+)$')
_DENY_RE = re.compile(r"^deny\s+if\s+(.+)$")


def _strip_comment(line: str) -> str:
    """Remove ``#`` comments while respecting double-quoted strings."""

    in_string = False
    out: list[str] = []
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == '"' and (i == 0 or line[i - 1] != "\\"):
            in_string = not in_string
            out.append(ch)
        elif ch == "#" and not in_string:
            break
        else:
            out.append(ch)
        i += 1
    return "".join(out).rstrip()


def _parse_policy(source: str) -> _Policy:
    package: str | None = None
    default_allow = False
    rules: list[_Rule] = []

    for raw_line in source.splitlines():
        line = _strip_comment(raw_line).strip()
        if not line:
            continue

        if (match := _PACKAGE_RE.match(line)) is not None:
            package = match.group(1)
            continue

        if (match := _DEFAULT_RE.match(line)) is not None:
            default_allow = match.group(1) == "true"
            continue

        if (match := _ALLOW_RE.match(line)) is not None:
            body = _Parser(_tokenize(match.group(1))).parse()
            rules.append(_Rule(kind="allow", body=body, message=None))
            continue

        if (match := _DENY_INLINE_RE.match(line)) is not None:
            message, expr = match.group(1), match.group(2)
            body = _Parser(_tokenize(expr)).parse()
            rules.append(_Rule(kind="deny", body=body, message=message))
            continue

        if (match := _DENY_RE.match(line)) is not None:
            body = _Parser(_tokenize(match.group(1))).parse()
            rules.append(_Rule(kind="deny", body=body, message=None))
            continue

        raise PolicyError(f"unsupported policy line: {raw_line!r}")

    return _Policy(package=package, default_allow=default_allow, rules=tuple(rules))


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def evaluate(policy_path: Path, input_data: dict) -> Decision:
    """Evaluate a Rego-subset policy file against ``input_data``.

    Parameters
    ----------
    policy_path:
        Filesystem path to a ``.rego`` policy file. Read as UTF-8.
    input_data:
        Dictionary used to resolve ``input.<field>`` references inside the
        policy body. Missing fields evaluate to ``None`` (Rego ``undefined``).

    Returns
    -------
    Decision
        ``Decision(allow=True)`` when an ``allow if`` rule fires; otherwise
        ``Decision(allow=False, reason=...)`` if a ``deny if`` rule fires;
        otherwise the default verdict declared by ``default allow := ...``
        (or ``False`` when no default is declared).

    Raises
    ------
    FileNotFoundError
        If ``policy_path`` does not exist on disk.
    PolicyError
        If the policy contains syntax outside the supported subset, or an
        expression cannot be evaluated against the supplied input.
    """

    source = Path(policy_path).read_text(encoding="utf-8")
    policy = _parse_policy(source)

    # 1. First firing allow rule wins.
    for rule in policy.rules:
        if rule.kind != "allow":
            continue
        if _truthy(_evaluate_node(rule.body, input_data)):
            return Decision(allow=True)

    # 2. Otherwise, first firing deny rule wins (with a reason).
    for rule in policy.rules:
        if rule.kind != "deny":
            continue
        if _truthy(_evaluate_node(rule.body, input_data)):
            return Decision(allow=False, reason=rule.message)

    # 3. Fall back to the declared default.
    return Decision(allow=policy.default_allow)
