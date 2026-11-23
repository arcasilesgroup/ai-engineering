import { afterAll, describe, expect, test } from "bun:test";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { runSelfProtect } from "../src/guards/self-protect.ts";

const tempDirs: string[] = [];

function repo(): string {
  const dir = mkdtempSync(join(tmpdir(), "ai-eng-hardening-"));
  tempDirs.push(dir);
  mkdirSync(join(dir, ".ai-engineering"), { recursive: true });
  writeFileSync(join(dir, ".ai-engineering", "config.toml"), "[surfaces]\nenabled = [\"claude-code\"]\n");
  return dir;
}

afterAll(() => {
  for (const dir of tempDirs.splice(0)) rmSync(dir, { recursive: true, force: true });
});

const bash = (command: string) => ({ tool_name: "Bash", tool_input: { command } });

describe("self-protect closes the traced bypasses and still allows ordinary commands", () => {
  const root = repo();
  const denied = (command: string) => expect(runSelfProtect(bash(command), root)?.deny, command).toBe(true);
  const allowed = (command: string) => expect(runSelfProtect(bash(command), root), command).toBeUndefined();

  test("a later assignment does not hide the path already used", () => {
    denied("f=.ai-engineering/config.toml; rm \"$f\"; f=safe.txt");
    denied("f=.ai-engineering/config.toml; echo x > \"$f\"; f=safe.txt");
    denied("f=.git/hooks/pre-commit; echo x > \"$f\"; f=safe.txt");
    denied("f=.ai-engineering/config.toml; echo x | tee \"$f\"; f=safe.txt");
    denied("f=.ai-engineering/config.toml; cp /dev/null \"$f\"; f=safe.txt");
    denied("export f=.ai-engineering/config.toml; rm \"$f\"; f=safe.txt");
    allowed("f=safe.txt; rm \"$f\"; f=.ai-engineering/config.toml");
    allowed("f=\"my safe file.txt\"; rm \"$f\"");
  });

  test("printf -v and read mutations are visible to the next command", () => {
    denied("f=safe.txt; printf -v f %s/%s .ai-engineering config.toml; echo x > \"$f\"");
    denied("f=safe.txt; printf -v f \"%b\" \".ai-engineering/config.toml\"; echo x > \"$f\"");
    denied("f=safe.txt; read f <<< .ai-engineering/config.toml; rm \"$f\"");
    allowed("printf -v name %s hello; echo \"$name\"");
  });

  test("xargs into env, sed, or an interpreter is denied; xargs into a reader is not", () => {
    denied("printf '%s\\n' rm .ai-engineering/config.toml | xargs env");
    denied("printf 'rm\\0.ai-engineering/config.toml' | xargs -0 env");
    denied("printf '%s\\n' -i '' s/a/b/ .ai-engineering/config.toml | xargs sed");
    denied("printf '%s\\n' -i .ai-engineering/config.toml | xargs sed -e 's/a/b/'");
    denied("echo .ai-engineering/config.toml | xargs python3 -c \"import sys; open(sys.argv[1],'w').write('')\"");
    denied("echo 'rm .ai-engineering/config.toml' | xargs sh -c");
    allowed("echo README.md | xargs grep -n guard");
    allowed("echo README.md | xargs sed -n '1p'");
    allowed("python3 -c \"print(1)\"");
  });

  test("env -S is the command it carries", () => {
    denied("env -S \"rm .ai-engineering/config.toml\"");
    denied("env --split-string=\"rm .ai-engineering/config.toml\"");
    allowed("env LANG=C echo hello");
  });

  test("a path split across string literals is still that path across all six interpreters", () => {
    denied("python3 -c \"open('.ai-' + 'engineering/config.toml','w').write('')\"");
    denied("node -e \"require('fs').writeFileSync('.git/' + 'hooks/pre-commit','')\"");
    denied("bun -e \"Bun.write('.ai-' + 'engineering/config.toml','')\"");
    denied("perl -e \"unlink q(.ai-) . q(engineering/config.toml)\"");
    denied("ruby -e \"File.write('.ai-' + 'engineering/config.toml','')\"");
    denied("awk \"BEGIN { print \\\"\\\" > ('.ai-' 'engineering/config.toml') }\"");
    allowed("node -e \"console.log('hello' + ' world')\"");
    allowed("perl -e \"print q(hello) . q( world)\"");
    allowed("awk \"BEGIN { print 'hello' ' world' }\"");
  });
});
