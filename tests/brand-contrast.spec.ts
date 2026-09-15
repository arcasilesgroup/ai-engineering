/**
 * The contrast gate measures its own truth: `brand.ts contrast` computes both the
 * ratio and the threshold it must clear, so an error in the luminance maths would
 * report every colour as legible and no other check would notice. This file is the
 * independent oracle — values that come from outside this repository, not from the
 * code under test.
 *
 * Sources for the expectations below:
 * - White on black is 21:1 and the luminance of white/black is 1/0 by definition,
 *   in WCAG 2.1 as published.
 * - `#767676` on white is the canonical "darkest grey that passes AA" and `#777777`
 *   the canonical one that fails; both are the boundary every accessibility tool
 *   quotes (4.54:1 against 4.48:1).
 * - The two greys are this project's own: the border was raised from the first to the
 *   second because the first could not clear 3:1 on a raised surface, and these
 *   assertions are what stops a future change from quietly putting it back.
 */
import { describe, test, expect } from "bun:test";
import { contrast, luminance } from "../scripts/brand.ts";

describe("the contrast maths agrees with the published WCAG definition", () => {
  test("luminance is 1 for white and 0 for black", () => {
    expect(luminance("#FFFFFF")).toBeCloseTo(1, 6);
    expect(luminance("#000000")).toBeCloseTo(0, 6);
  });

  test("white on black is the definitional maximum of 21:1", () => {
    expect(contrast("#FFFFFF", "#000000")).toBeCloseTo(21, 1);
  });

  test("the published AA boundary on white lands where it should", () => {
    // The canonical pair: #767676 passes, #777777 does not.
    expect(contrast("#767676", "#FFFFFF")).toBeGreaterThanOrEqual(4.5);
    expect(contrast("#777777", "#FFFFFF")).toBeLessThan(4.5);
  });

  test("the ratio is symmetric", () => {
    expect(contrast("#00ED64", "#001E2B")).toBeCloseTo(contrast("#001E2B", "#00ED64"), 6);
  });
});

describe("the brand's own boundary stays on the safe side of 3:1", () => {
  test("the signal green on the field clears AA for large text with room to spare", () => {
    expect(contrast("#00ED64", "#001E2B")).toBeGreaterThanOrEqual(4.5);
  });

  test("the retired border grey would not have cleared a control boundary on a raised surface", () => {
    // Why `--border` is gray.base and not gray.dark1. If someone puts the darker grey
    // back, this fails and names the reason instead of shipping an invisible control.
    expect(contrast("#5C6C75", "#1C2D38")).toBeLessThan(3);
    expect(contrast("#889397", "#1C2D38")).toBeGreaterThanOrEqual(3);
  });
});
