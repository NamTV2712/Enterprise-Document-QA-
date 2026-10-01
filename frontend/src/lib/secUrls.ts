const SEC_BROWSER_HOST = "www.sec.gov";
const SEC_ARCHIVE_PREFIX = "/Archives/edgar/data/";

/** Return only exact first-party SEC archive URLs suitable for browser links. */
export function sanitizeSecBrowserUrl(value: unknown): string | null {
  if (typeof value !== "string" || !value.trim()) return null;
  try {
    const url = new URL(value.trim());
    if (
      url.protocol !== "https:" ||
      url.hostname !== SEC_BROWSER_HOST ||
      (url.port !== "" && url.port !== "443") ||
      url.username !== "" ||
      url.password !== "" ||
      !url.pathname.startsWith(SEC_ARCHIVE_PREFIX) ||
      url.pathname.length <= SEC_ARCHIVE_PREFIX.length
    ) {
      return null;
    }
    return url.href;
  } catch {
    return null;
  }
}
