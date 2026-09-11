// The release flags are derived, not remembered: the version is the only input.
import { test, expect } from "bun:test";
import { releaseFlags } from "../scripts/release-flags.ts";

test("a prerelease version never claims Latest", () => {
  expect(releaseFlags("2.0.0-rc.1")).toEqual({ tag: "v2.0.0-rc.1", prerelease: true });
});

test("a final version is a final release", () => {
  expect(releaseFlags("2.0.0")).toEqual({ tag: "v2.0.0", prerelease: false });
});

test("a leading v is tolerated, so the tag and package.json agree", () => {
  expect(releaseFlags(" v2.1.3\n")).toEqual({ tag: "v2.1.3", prerelease: false });
});

test("anything that is not a release version is refused", () => {
  for (const bad of ["", "2.0", "latest", "v2.0.0.1", "2.0.0-"]) {
    expect(() => releaseFlags(bad), bad).toThrow();
  }
});
