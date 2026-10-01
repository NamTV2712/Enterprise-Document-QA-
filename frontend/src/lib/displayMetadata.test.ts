import { describe, expect, test } from "vitest";
import { COMPANY_DISPLAY_METADATA_VERSION, formatCompanyLabel } from "./displayMetadata";

describe("company display metadata", () => {
  test("uses expanded labels for mapped tickers and honest fallback for unknown values", () => {
    expect(COMPANY_DISPLAY_METADATA_VERSION).toBe("sec-company-display-v1");
    expect(formatCompanyLabel("aapl")).toBe("Apple Inc. (AAPL)");
    expect(formatCompanyLabel("  mystery  ")).toBe("MYSTERY");
    expect(formatCompanyLabel(null)).toBe("—");
  });
});
