---
spec: spec-fixture-ui
title: Build a dashboard component with responsive layout
status: approved
effort: medium
---

# Spec Fixture -- UI Keywords

## Summary

Build a dashboard component with responsive layout. The dashboard hosts a primary
page that lists recent activity. The page includes a form with multiple fields,
a modal for confirmation, and follows the project's design system tokens for
typography and color palette.

## Goals

- G-1: dashboard renders all widgets above the fold on desktop and mobile screen.
- G-2: form fields meet accessibility AA contrast and 44x44 touch targets.
- G-3: modal dismiss honors keyboard escape and reduced-motion preference.

## Non-Goals

- NG-1: no custom design system extensions; reuse existing tokens.
