---
spec: spec-fixture-api
title: Endpoint for credential validation
status: approved
effort: medium
---

# Spec Fixture -- Backend Only

## Summary

Add a backend HTTP endpoint that validates credentials, issues a signed token,
and persists the session record to the database. No client-side work in scope.

## Goals

- G-1: POST /auth/login returns a signed token on valid credentials.
- G-2: rate limiting blocks brute-force attempts at the gateway.
- G-3: session records persist with a 24-hour expiry window.

## Non-Goals

- NG-1: no client SDK changes; consumers integrate via raw HTTP.
- NG-2: no token rotation strategy; out of scope for this spec.
