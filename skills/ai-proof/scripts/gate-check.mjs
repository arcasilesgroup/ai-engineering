#!/usr/bin/env node
// gate-check.mjs : run the CHECK commands in gate files, flip boxes, record evidence.
// Zero dependencies. Node 16+. Part of the unlazy skill (v2).
//
// Usage:
//   node gate-check.mjs [file ...]           run unmet gates' checks, update files
//   node gate-check.mjs --status [file ...]  report only, run nothing, change nothing
//   node gate-check.mjs --recheck [file ...] re-run EVERY gate's check, even ones
//                                           already checked with evidence
//   node gate-check.mjs --timeout 60 ...     per-check timeout in seconds (default 120)
//   node gate-check.mjs --jobs 8 ...         max concurrent checks (default: min(4, cores-1))
//
// Files default to GATES.md plus gates/*.md in the current directory. Name files
// explicitly to scope a run to one leaf instead of re-running the whole tree.
//
// Checks run concurrently across gates and files, and an identical CHECK command
// is executed once and shared by every gate that names it. A gate file whose
// checks are not parallel-safe can declare `Jobs: <n>` in its header: its checks
// then run at most n at a time, and it neither shares results with other files
// nor accepts theirs (a shared result would be a concurrent one, which is the
// thing it opted out of).
//
// --recheck is how a driver verifies a returned subagent's work: without it, a
// gate the subagent already checked and gave evidence for is taken on trust and
// its command never runs. A --recheck failure resets that gate's evidence to
// pending, which makes it UNMET and blocks the stop-hook. Checkboxes are only
// ever ticked by this tool, never unticked: the box is the author's claim, and
// withdrawing the evidence under it is enough to void the claim.
//
// Exit codes: 0 = all gates met (or honestly abandoned), 1 = unmet gates remain,
//             2 = usage or parse error.

import { readFileSync, writeFileSync, existsSync, readdirSync } from "node:fs";
import { exec } from "node:child_process";
import { cpus } from "node:os";
import { join } from "node:path";
import { promisify } from "node:util";

const execAsync = promisify(exec);

const args = process.argv.slice(2);
const statusOnly = args.includes("--status");
const recheck = args.includes("--recheck");
if (statusOnly && recheck) {
  console.error("gate-check: --status and --recheck contradict each other (--status runs nothing)");
  process.exit(2);
}
let timeoutSec = 120;
const tIdx = args.indexOf("--timeout");
if (tIdx !== -1) timeoutSec = Number(args[tIdx + 1]) || 120;
let jobs = Math.max(1, Math.min(4, (cpus().length || 2) - 1));
const jIdx = args.indexOf("--jobs");
if (jIdx !== -1) jobs = Math.max(1, Number(args[jIdx + 1]) || jobs);
const valueIdx = new Set([tIdx + 1, jIdx + 1].filter(i => i > 0));
const fileArgs = args.filter((a, i) => !a.startsWith("--") && !valueIdx.has(i));

function defaultFiles(dir) {
  const found = [];
  const top = join(dir, "GATES.md");
  if (existsSync(top)) found.push(top);
  const gdir = join(dir, "gates");
  if (existsSync(gdir)) {
    for (const f of readdirSync(gdir)) {
      if (f.endsWith(".md")) found.push(join(gdir, f));
    }
  }
  return found;
}

const files = fileArgs.length ? fileArgs : defaultFiles(process.cwd());
if (!files.length) {
  console.error("gate-check: no gate files found (GATES.md or gates/*.md)");
  process.exit(2);
}

const GATE_RE = /^- \[( |x|X)\] (.*)$/;
const ATTR_RE = /^\s+(CHECK|EXPECT|EVIDENCE):\s?(.*)$/;
const ABANDON_RE = /^ABANDON:\s*(\S+)\s*(.*)$/;
const JOBS_RE = /^\s*Jobs:\s*(.*?)\s*$/i;

function parse(lines) {
  const gates = [];
  const abandoned = new Map(); // id -> reason
  let jobsCap = null;   // per-file concurrency cap, when the file declares one
  const warnings = [];
  let cur = null;
  lines.forEach((line, i) => {
    const g = line.match(GATE_RE);
    if (g) {
      const id = (g[2].match(/^(\S+?):/) || [null, `line${i + 1}`])[1];
      cur = {
        line: i, checked: g[1].toLowerCase() === "x",
        title: g[2].trim().replace(/^\S+?:\s*/, ""),
        id,
        check: null, expect: null, evidence: null, evidenceLine: -1,
      };
      gates.push(cur);
      return;
    }
    const a = cur && line.match(ATTR_RE);
    if (a) {
      const key = a[1].toLowerCase();
      cur[key] = a[2].trim();
      if (key === "evidence") cur.evidenceLine = i;
      return;
    }
    const j = line.match(JOBS_RE);
    if (j) {
      const n = Number(j[1]);
      // Silently ignoring a Jobs line would let a file believe it is serial
      // while its checks trample each other, so say so instead.
      if (Number.isInteger(n) && n >= 1) jobsCap = jobsCap === null ? n : Math.min(jobsCap, n);
      else warnings.push(`line ${i + 1}: "Jobs: ${j[1]}" is not a positive integer, ignored`);
      return;
    }
    const ab = line.match(ABANDON_RE);
    if (ab) abandoned.set(ab[1].replace(/:$/, ""), ab[2] || "(no reason)");
    if (/^#|^- /.test(line) && !g) cur = null;
  });
  return { gates, abandoned, jobsCap, warnings };
}

function expectMatches(expect, output) {
  const rx = expect.match(/^\/(.+)\/([a-z]*)$/);
  if (rx) {
    try { return new RegExp(rx[1], rx[2]).test(output); } catch { return false; }
  }
  return output.includes(expect);
}

function tail(output, max = 200) {
  const lines = output.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
  const last = lines.slice(-2).join(" | ");
  return (last || "(no output)").slice(0, max);
}

// --- scheduler ---------------------------------------------------------------
// A bounded pool so a tree with dozens of gates does not fork dozens of builds.
function makeLimiter(max) {
  let active = 0;
  const queue = [];
  const pump = () => {
    while (active < max && queue.length) {
      const { fn, resolve, reject } = queue.shift();
      active++;
      Promise.resolve().then(fn).then(resolve, reject).finally(() => { active--; pump(); });
    }
  };
  return fn => new Promise((resolve, reject) => { queue.push({ fn, resolve, reject }); pump(); });
}

const globalLimit = makeLimiter(jobs);
const globalMemo = new Map(); // command -> Promise<{ output, status, errMessage }>

// A file declaring `Jobs: n` gets its own limiter and its own memo scope: it opted
// out of concurrency, so it must not be handed another file's in-flight result.
// Acquiring the file slot before the global one keeps the order uniform, so the
// two queues cannot deadlock against each other.
function scopeFor(state) {
  if (state.jobsCap === null) return { limit: globalLimit, memo: globalMemo };
  const fileLimit = makeLimiter(state.jobsCap);
  return { limit: fn => fileLimit(() => globalLimit(fn)), memo: new Map() };
}

function runCheck(cmd, { limit, memo }) {
  const cached = memo.get(cmd);
  if (cached) return { promise: cached, shared: true };
  const promise = limit(() =>
    execAsync(cmd, { timeout: timeoutSec * 1000, maxBuffer: 8 * 1024 * 1024, encoding: "utf8" })
      .then(({ stdout, stderr }) => ({ output: `${stdout || ""}\n${stderr || ""}`, status: 0, errMessage: null }))
      .catch(err => {
        const output = `${err.stdout || ""}\n${err.stderr || ""}`;
        const spawned = err.stdout !== undefined || err.stderr !== undefined;
        const errMessage = err.killed
          ? `timed out after ${timeoutSec}s`
          : (spawned ? null : err.message);
        return { output, status: typeof err.code === "number" ? err.code : 1, errMessage };
      })
  );
  memo.set(cmd, promise);
  return { promise, shared: false };
}

// --- pass 1: parse every file, schedule every runnable check ------------------
const states = [];
for (const file of files) {
  let text;
  try { text = readFileSync(file, "utf8"); } catch (e) {
    console.error(`gate-check: cannot read ${file}: ${e.message}`);
    process.exit(2);
  }
  const lines = text.split(/\r?\n/);
  states.push({ file, lines, ...parse(lines) });
}

for (const state of states) {
  for (const w of state.warnings) console.error(`gate-check: ${state.file}: ${w}`);
  const scope = scopeFor(state);
  for (const gate of state.gates) {
    if (state.abandoned.has(gate.id) || statusOnly || !gate.check) continue;
    const pendingEvidence = !gate.evidence || /^pending$/i.test(gate.evidence);
    // Normally a gate already checked with evidence is trusted and skipped.
    // --recheck is the driver's re-verification pass, so it trusts nothing.
    if (!recheck && gate.checked && !pendingEvidence) continue;
    const { promise, shared } = runCheck(gate.check, scope);
    gate.run = promise;
    gate.shared = shared;
  }
}

await Promise.all(states.flatMap(s => s.gates.map(g => g.run).filter(Boolean)));

// --- pass 2: apply results in file order, so output stays deterministic -------
let totalUnmet = 0;
let totalMet = 0;
let totalAbandoned = 0;

for (const state of states) {
  const { file, lines, gates, abandoned } = state;
  if (!gates.length) {
    console.log(`${file}: no gates found`);
    continue;
  }
  let changed = false;

  for (const gate of gates) {
    if (abandoned.has(gate.id)) { totalAbandoned++; continue; }

    if (gate.run) {
      const res = await gate.run;
      // With an EXPECT, the match decides (a check may exit non-zero by design);
      // without one, the exit code decides.
      const ok = gate.expect ? expectMatches(gate.expect, res.output) : res.status === 0;
      const note = gate.shared ? " (shared result)" : "";
      // Rewrite a line only when it actually differs: an unchanged file leaves
      // the stop-hook's no-progress counter meaningful, and a re-check that
      // confirms what was already recorded is not progress.
      const setLine = (i, text) => {
        if (i === -1 || lines[i] === text) return;
        lines[i] = text;
        changed = true;
      };
      const setEvidence = (text) => {
        if (gate.evidenceLine === -1) return;
        const indent = lines[gate.evidenceLine].match(/^\s*/)[0];
        setLine(gate.evidenceLine, `${indent}EVIDENCE: ${text}`);
      };
      if (ok) {
        setLine(gate.line, lines[gate.line].replace(/^- \[ \]/, "- [x]"));
        setEvidence(tail(res.output));
        gate.checked = true;
        gate.evidence = tail(res.output);
        console.log(`  PASS ${gate.id}: ${gate.title}${note}`);
      } else {
        // A box that was checked and has now failed its own check was a false
        // claim, so the proof is withdrawn: evidence goes back to pending, which
        // makes the gate UNMET by the format's second rule and blocks the
        // stop-hook. The box itself is left exactly as its author set it. This
        // tool only ever ticks boxes; unticking someone else's claim is not its
        // job, and it does not need to be, since evidence is what counts.
        if (gate.checked) {
          setEvidence("pending");
          gate.evidence = "pending";
        }
        console.log(`  FAIL ${gate.id}: ${gate.title}${note}\n       ${res.errMessage || tail(res.output)}`);
      }
    }

    const evidenceNow = gate.evidence && !/^pending$/i.test(gate.evidence);
    if (gate.checked && evidenceNow) totalMet++;
    else {
      totalUnmet++;
      if (statusOnly) {
        const why = !gate.checked ? "unchecked" : "checked but EVIDENCE pending";
        console.log(`  UNMET ${gate.id} (${why}): ${gate.title}`);
      }
    }
  }

  if (changed) writeFileSync(file, lines.join("\n"));
  console.log(`${file}: ${gates.length} gates`);
}

if (totalUnmet === 0) {
  console.log(`ALL MET (${totalMet} met${totalAbandoned ? `, ${totalAbandoned} abandoned` : ""})`);
  process.exit(0);
} else {
  console.log(`UNMET: ${totalUnmet} (met: ${totalMet}${totalAbandoned ? `, abandoned: ${totalAbandoned}` : ""})`);
  process.exit(1);
}
