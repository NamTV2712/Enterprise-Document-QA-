import { describe, expect, test } from "vitest";
import { normalizeLocaleSearch } from "./i18n";

describe("locale utilities", () => {
  test("normalizes Vietnamese accents and đ for literal search", () => {
    expect(normalizeLocaleSearch("Đám mây và Tỷ lệ")).toBe("dam may va ty le");
  });
});
