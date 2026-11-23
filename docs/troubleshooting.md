# Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Hooks do not fire | The folder is not trusted in your agent | Trust it, then check the `chain test` line of `ai-eng doctor` |
| A legitimate command was denied | No guard can tell your intent | Only the loop guard takes an override: an entry in `.ai-engineering/overrides.toml` with a `reason` and an `until` date. For any other guard, run the call another way or ask a person to change the rule in a reviewed diff |
| `ai-eng: bun not found` | The launcher runs the source under Bun | Install Bun (>= 1.4.4) |
| `ai-eng.ps1 cannot be loaded` on Windows | npm wrote the `.ps1` again, and PowerShell's default policy refuses it | Run `ai-eng.cmd update` once: it removes that file |
| `ai-eng doctor` reports canon drift | The installed skills differ from this version's | Run `ai-eng update` |
| You want no update notice | The notice is on by default | Set `AI_ENG_NO_UPDATE_NOTICES=1` |
| You want it gone | | Run `ai-eng uninstall`: it removes what it wrote and keeps your contract files |
