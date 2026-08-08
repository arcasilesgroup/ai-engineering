# Azure DevOps

Yes, it works. No, `ai-eng init --ci azure` does not exist, and the reason is not effort.

On GitHub, committing a file into `.github/workflows/` is the whole act: the push that
adds it also triggers it. In Azure DevOps a YAML file is inert until a human registers a
pipeline in the project UI or runs `az pipelines create` with an org-scoped credential.
For Azure Repos Git the `pr:` block is ignored entirely — pull-request triggers come from
branch policies, not from the file. And a pipeline's UI settings can override the YAML
triggers silently, so the printed file under-determines what actually runs.

Printing a file that does nothing until three manual steps happen elsewhere is a green
nobody earned, wearing a different hat. So here is the file and here are the three steps,
and `--ci azure` becomes real when a second actual user asks for it.

```yaml
trigger: [main]
pool: { vmImage: ubuntu-latest }
steps:
  - script: curl -LsSf https://astral.sh/uv/install.sh -o uv.sh && sh uv.sh
    displayName: uv
  - script: uv tool install ai-engineering==1.0.0 && ai-eng doctor --ci
    displayName: is the system healthy
  - script: ai-eng audit verify --anchors
    displayName: the record is intact
  - script: just check
    displayName: the gate
```

1. Commit it as `azure-pipelines.yml`.
2. Pipelines → New pipeline → Azure Repos Git → Existing YAML file, and point it at that
   path. Nothing runs before this step.
3. Branch policies on `main` → Build validation → add the pipeline as required. That, not
   the `pr:` block, is what makes it run on a pull request — and it is also T0.
