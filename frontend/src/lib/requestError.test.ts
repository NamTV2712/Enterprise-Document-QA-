import { describe, expect, test } from "vitest";
import { ApiError } from "./api";
import { describeRequestError } from "./requestError";

describe("describeRequestError", () => {
  test("turns browser transport failures into a recoverable backend message", () => {
    expect(describeRequestError(new TypeError("Failed to fetch"), "Fallback").message)
      .toBe("The backend could not be reached. Check the connection and try again.");
  });

  test("preserves the action for provider quota and timeout responses", () => {
    expect(describeRequestError(new ApiError("quota", 429), "Fallback").message)
      .toMatch(/out of quota/i);
    expect(describeRequestError(new ApiError("timeout", 504), "Fallback").message)
      .toMatch(/narrower question/i);
  });
});
