#!/usr/bin/env bash
# Deterministic, anonymized demo fixture for the VHS recording (spec-177).
tw(){ local s="$1" i; for ((i=0;i<${#s};i++)); do printf '%s' "${s:$i:1}"; sleep 0.028; done; printf '\n'; }
prompt(){ printf '\033[38;2;0;212;170m$\033[0m '; }
teal(){ printf '\033[38;2;0;212;170m%s\033[0m' "$1"; }
dim(){ printf '\033[38;2;94;119;150m%s\033[0m\n' "$1"; }
clear; sleep 0.7
prompt; tw "uv tool install ai-engineering"; sleep 0.3
dim "  Installed ai-engineering 0.12.0"; sleep 0.5
prompt; tw "ai-eng install ."; sleep 0.3
printf '  '; teal "[PASS]"; printf ' hooks · mirrors · manifest · audit chain\n'; sleep 0.5
prompt; tw "ai-eng doctor"; sleep 0.3
printf '  '; teal "[PASS]"; printf ' 54 skills · 9 agents · 6 surfaces ready\n'; sleep 0.6
prompt; tw "# open your IDE and run /ai-start"; sleep 1.4
