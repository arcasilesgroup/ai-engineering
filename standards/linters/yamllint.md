# YAML Linting Standard

> yamllint configuration for YAML files including Azure Pipelines.

---

## Installation

```bash
pip install yamllint
```

---

## Configuration Template

```yaml
# .yamllint.yml
---
extends: default

yaml-files:
  - '*.yaml'
  - '*.yml'
  - '.yamllint'
  - '.yamllint.yml'

ignore: |
  node_modules/
  .venv/
  venv/
  .git/
  dist/
  build/

rules:
  # ==========================================================================
  # LINE LENGTH
  # ==========================================================================
  line-length:
    max: 120
    level: warning
    allow-non-breakable-words: true
    allow-non-breakable-inline-mappings: true

  # ==========================================================================
  # INDENTATION
  # ==========================================================================
  indentation:
    spaces: 2
    indent-sequences: true
    check-multi-line-strings: false

  # ==========================================================================
  # BRACES AND BRACKETS
  # ==========================================================================
  braces:
    forbid: false
    min-spaces-inside: 0
    max-spaces-inside: 1
    min-spaces-inside-empty: 0
    max-spaces-inside-empty: 0

  brackets:
    forbid: false
    min-spaces-inside: 0
    max-spaces-inside: 1
    min-spaces-inside-empty: 0
    max-spaces-inside-empty: 0

  # ==========================================================================
  # COLONS AND COMMAS
  # ==========================================================================
  colons:
    max-spaces-before: 0
    max-spaces-after: 1

  commas:
    max-spaces-before: 0
    min-spaces-after: 1
    max-spaces-after: 1

  # ==========================================================================
  # COMMENTS
  # ==========================================================================
  comments:
    require-starting-space: true
    ignore-shebangs: true
    min-spaces-from-content: 2

  comments-indentation: enable

  # ==========================================================================
  # DOCUMENT MARKERS
  # ==========================================================================
  # Disabled: Azure Pipelines don't typically use document markers
  document-start: disable
  document-end: disable

  # ==========================================================================
  # EMPTY LINES AND VALUES
  # ==========================================================================
  empty-lines:
    max: 2
    max-start: 0
    max-end: 1

  empty-values:
    forbid-in-block-mappings: false
    forbid-in-flow-mappings: true

  # ==========================================================================
  # HYPHENS
  # ==========================================================================
  hyphens:
    max-spaces-after: 1

  # ==========================================================================
  # KEY HANDLING
  # ==========================================================================
  key-duplicates: enable

  key-ordering: disable

  # ==========================================================================
  # NEWLINES
  # ==========================================================================
  new-line-at-end-of-file: enable

  new-lines:
    type: unix

  # ==========================================================================
  # OCTAL VALUES
  # ==========================================================================
  octal-values:
    forbid-implicit-octal: true
    forbid-explicit-octal: false

  # ==========================================================================
  # QUOTED STRINGS
  # ==========================================================================
  quoted-strings:
    quote-type: any
    required: only-when-needed
    extra-required: []
    extra-allowed: []
    allow-quoted-quotes: true

  # ==========================================================================
  # TRAILING SPACES
  # ==========================================================================
  trailing-spaces: enable

  # ==========================================================================
  # TRUTHY VALUES
  # ==========================================================================
  # Critical: Prevent yes/no/on/off confusion
  truthy:
    allowed-values: ['true', 'false']
    check-keys: true
    level: error

  # ==========================================================================
  # ANCHORS
  # ==========================================================================
  anchors:
    forbid-undeclared-aliases: true
    forbid-duplicated-anchors: true
    forbid-unused-anchors: false
```

---

## Azure Pipelines Specific Config

For stricter Azure Pipelines validation:

```yaml
# .yamllint-pipelines.yml
---
extends: default

yaml-files:
  - 'azure-pipelines*.yml'
  - 'pipelines/**/*.yml'
  - 'templates/**/*.yml'

rules:
  line-length:
    max: 150  # Pipelines often have long expressions
    level: warning

  indentation:
    spaces: 2
    indent-sequences: true

  truthy:
    allowed-values: ['true', 'false', 'yes', 'no']  # Azure uses yes/no for some values
    check-keys: false  # Azure uses boolean keys

  document-start: disable
  document-end: disable

  comments:
    require-starting-space: true
    min-spaces-from-content: 1  # More lenient for inline comments
```

---

## Verification Commands

```bash
# Lint all YAML files
yamllint .

# Lint with specific config
yamllint -c .yamllint.yml .

# Lint specific directory
yamllint pipelines/

# Strict mode (warnings as errors)
yamllint --strict .

# Output format for CI
yamllint -f parsable .
```

---

## Integration with Pre-commit

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/adrienverge/yamllint
    rev: v1.35.0
    hooks:
      - id: yamllint
        args: [-c=.yamllint.yml]
```

---

## VS Code Integration

```json
// .vscode/settings.json
{
  "yaml.validate": true,
  "yaml.customTags": [
    "!reference sequence"  // Azure Pipelines
  ],
  "yaml.schemas": {
    "https://raw.githubusercontent.com/microsoft/azure-pipelines-vscode/master/service-schema.json": [
      "azure-pipelines*.yml",
      "pipelines/**/*.yml"
    ]
  }
}
```
