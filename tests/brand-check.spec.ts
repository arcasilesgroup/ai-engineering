/**
 * The validator's own oracle.
 *
 * `bun scripts/brand.ts check` is the one gate in this system that had only ever been
 * observed *passing*. Every other gate here has been seen failing — `parity` on a
 * tampered artifact, `legacy` on the file the guard protects, `contrast` on a border that
 * measured 2.76:1, `artifact` on a drifted block. A validator that had quietly stopped
 * validating would have produced exactly the same output as a healthy one, and criterion
 * 1 would have looked satisfied either way.
 *
 * So each rule gets a declaration that breaks it, and the validator has to say so. The
 * mutations run against a copy of the real declaration, so a rule that stops being
 * enforced fails here immediately.
 */
import { describe, test, expect } from "bun:test";
import { loadTokens, validate, type Tokens } from "../scripts/brand.ts";

/** A deep copy of the real declaration, so each case breaks exactly one thing. */
const broken = async (mutate: (t: Tokens) => void): Promise<string[]> => {
  const tokens = JSON.parse(JSON.stringify(await loadTokens())) as Tokens;
  mutate(tokens);
  return validate(tokens);
};

describe("the validator accepts the declaration it ships", () => {
  test("the real brand/tokens.json has no problems", async () => {
    expect(validate(await loadTokens())).toEqual([]);
  });
});

describe("the validator refuses a declaration that breaks a rule", () => {
  test("a colour family that is not a hex", async () => {
    const problems = await broken((t) => {
      (t.families as Record<string, Record<string, string>>).gray!.dark4 = "#11273";
    });
    expect(problems.join("\n")).toContain("families.gray.dark4");
  });

  test("a tone scale that does not run dark to light", async () => {
    const problems = await broken((t) => {
      const gray = (t.families as Record<string, Record<string, string>>).gray!;
      // dark4 lighter than dark3: the ramp now goes light-to-dark somewhere in the middle,
      // which means the "tonal ramp" the design record publishes would be a lie.
      [gray.dark4, gray.dark3] = [gray.dark3!, gray.dark4!];
    });
    expect(problems.join("\n")).toContain("not lighter than");
  });

  test("a semantic token pointing at a family that does not exist", async () => {
    const problems = await broken((t) => {
      (t.semantic.surface as Record<string, { ref: string }>).bg = { ref: "chartreuse.base" };
    });
    expect(problems.join("\n")).toContain('unknown ref "chartreuse.base"');
  });

  test("a contrast pair whose text token was never declared", async () => {
    const problems = await broken((t) => {
      (t.pairs as { text: string; surface: string; min: number }[]).push({
        text: "readable",
        surface: "bg",
        min: 4.5,
      });
    });
    expect(problems.join("\n")).toContain('"readable" is not a declared text token');
  });

  test("a type step that names a font family the system does not have", async () => {
    const problems = await broken((t) => {
      (t.typography.scale as Record<string, { family: string }>).body = { family: "comic" };
    });
    expect(problems.join("\n")).toContain('unknown family "comic"');
  });

  test("a missing type step the stylesheet reads", async () => {
    const problems = await broken((t) => {
      delete (t.typography.scale as Record<string, unknown>)["stat"];
    });
    expect(problems.join("\n")).toContain('"stat" is required by the stylesheet');
  });

  test("a radius map pointing at a step that does not exist", async () => {
    const problems = await broken((t) => {
      (t.radius.map as Record<string, string>).card = "xl";
    });
    expect(problems.join("\n")).toContain('radius.map.card: points at unknown radius "xl"');
  });

  test("an alpha outside (0, 1]", async () => {
    const problems = await broken((t) => {
      const surface = t.semantic.surface as Record<
        string,
        { ref: string; alpha?: number; displayName: string; purpose: string }
      >;
      surface["surface-1"] = { ref: "gray.dark4", alpha: 1.5, displayName: "x", purpose: "y" };
    });
    expect(problems.join("\n")).toContain("alpha must be within (0, 1]");
  });

  test("a type step whose size is a number, which would emit a declaration the browser drops", async () => {
    const problems = await broken((t) => {
      (t.typography.scale as Record<string, { size: unknown }>).code = { size: 13 } as unknown as {
        size: string;
      };
    });
    expect(problems.join("\n")).toContain("typography.scale.code.size: must be a string");
  });

  test("a motion token that is a number, not a duration", async () => {
    const problems = await broken((t) => {
      (t.motion as Record<string, unknown>)["dur-fast"] = 160;
    });
    expect(problems.join("\n")).toContain("motion.dur-fast: must be a string");
  });

  test("a spacing token that is a number, not a length", async () => {
    const problems = await broken((t) => {
      (t.space as Record<string, unknown>).gutter = 24;
    });
    expect(problems.join("\n")).toContain("space.gutter: must be a string");
  });

  test("a radius step that is a number, not a length", async () => {
    const problems = await broken((t) => {
      (t.radius as Record<string, unknown>).lg = 24;
    });
    expect(problems.join("\n")).toContain("radius.lg: must be a string");
  });
});
