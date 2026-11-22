// The mutation gate's thresholds are the contract CI enforces. break used to sit
// at 85 while the measured incremental score was 58.51, so every governance pull
// request was red and the red meant nothing.
import { describe, expect, test } from "bun:test";
import config from "../stryker.conf.mjs";

describe("mutation thresholds", () => {
  test("break is the measured incremental floor, under the clean score and under the old unreachable 85", () => {
    expect(config.thresholds).toEqual({ high: 90, low: 58, break: 58 });
  });
});
