import { describe, expect, it } from "vitest";
import { sanitizeSecBrowserUrl } from "./secUrls";

describe("sanitizeSecBrowserUrl", () => {
  it("allows exact HTTPS SEC archive sources", () => {
    expect(sanitizeSecBrowserUrl("https://www.sec.gov/Archives/edgar/data/1/filing.htm"))
      .toBe("https://www.sec.gov/Archives/edgar/data/1/filing.htm");
  });

  it("rejects ingestion hosts, other paths, and authority tricks", () => {
    for (const value of [
      "http://www.sec.gov/Archives/edgar/data/1/filing.htm",
      "https://sec.gov/Archives/edgar/data/1/filing.htm",
      "https://evil.sec.gov/Archives/edgar/data/1/filing.htm",
      "https://www.sec.gov.evil.test/Archives/edgar/data/1/filing.htm",
      "https://data.sec.gov/submissions/CIK0001.json",
      "https://www.sec.gov/files/company_tickers.json",
      "https://www.sec.gov/Archives/example",
      "https://user:pass@www.sec.gov/Archives/edgar/data/1/filing.htm",
      "https://www.sec.gov:8443/Archives/edgar/data/1/filing.htm",
    ]) {
      expect(sanitizeSecBrowserUrl(value)).toBeNull();
    }
  });
});
