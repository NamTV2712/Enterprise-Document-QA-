import { SECTION_METADATA } from "./displayMetadata";

export interface SourceSectionDisplay {
  section: string;
  ticker: string;
  year: string;
}

/**
 * Derive display-only filing identity from the source facts already present
 * in an answer or catalog result. This never creates a document identity.
 */
export function getSectionDisplay(
  citation: string,
  sectionField?: string | null,
): SourceSectionDisplay {
  const citationLower = citation.toLowerCase();

  const tickerMatch = citation.match(/^([A-Z]{1,5}(?:-[A-Z])?)(?:\s|_)/i);
  const ticker = tickerMatch?.[1]?.toUpperCase() || "SEC";

  const yearMatch =
    citation.match(/_(20\d{2})_/) ||
    citation.match(/_(19\d{2})_/) ||
    citation.match(/\b(20\d{2})\b/) ||
    citation.match(/\b(19\d{2})\b/);
  const year = yearMatch ? yearMatch[1] : "";

  let matchedItem = sectionField || "";
  const explicitSection = citation.match(/Section:\s*([^,]+)/i)?.[1]?.trim();
  if (!matchedItem && explicitSection) {
    const normalizedSection = explicitSection.toLowerCase().replace(/\s+/g, "_");
    if (SECTION_METADATA[normalizedSection]) matchedItem = normalizedSection;
  }
  if (!matchedItem) {
    const itemMatch =
      citationLower.match(/item_(\d+[a-z]?)/) ||
      citationLower.match(/item\s+(\d+[a-z]?)/);
    if (itemMatch) matchedItem = "item_" + itemMatch[1];
  }

  if (!matchedItem) {
    const items = [
      "item_1a",
      "item_1b",
      "item_7a",
      "item_9a",
      "item_9b",
      "item_1",
      "item_2",
      "item_3",
      "item_4",
      "item_5",
      "item_6",
      "item_7",
      "item_8",
      "item_9",
      "item_10",
      "item_11",
      "item_12",
      "item_13",
      "item_14",
      "item_15",
    ];
    for (const item of items) {
      if (
        citationLower.includes(item) ||
        citationLower.includes(item.replace("_", " "))
      ) {
        matchedItem = item;
        break;
      }
    }
  }

  if (SECTION_METADATA[matchedItem]) {
    return {
      section: SECTION_METADATA[matchedItem].label,
      ticker,
      year,
    };
  }

  const cleanItem = matchedItem.toLowerCase().replace(/_/g, " ").trim();
  const sectionMap: Record<string, string> = {
    "item 1": "Business Overview",
    "item 1a": "Risk Factors",
    "item 1b": "Unresolved Staff Comments",
    "item 2": "Properties",
    "item 3": "Legal Proceedings",
    "item 4": "Mine Safety Disclosures",
    "item 5": "Market and Shareholder Matters",
    "item 6": "Selected Financial Data",
    "item 7": "Management Discussion & Analysis (MD&A)",
    "item 7a": "Market Risk Disclosures",
    "item 8": "Financial Statements & Supplementary Data",
    "item 9": "Accountant Disagreements",
    "item 9a": "Controls and Procedures",
    "item 9b": "Other Information",
    "item 10": "Directors & Officers",
    "item 11": "Executive Compensation",
    "item 12": "Security Ownership",
    "item 13": "Related Transactions",
    "item 14": "Accountant Fees & Services",
    "item 15": "Exhibits & Schedules",
  };

  return {
    section: sectionMap[cleanItem] || (cleanItem ? cleanItem.toUpperCase() : "General Document"),
    ticker,
    year,
  };
}

export function getSectionBadgeClass(sectionName: string): string {
  const lower = sectionName.toLowerCase();
  if (lower.includes("risk")) return "section-badge--risk";
  if (lower.includes("table") || lower.includes("financial") || lower.includes("statement")) {
    return "section-badge--financial";
  }
  if (lower.includes("md&a") || lower.includes("discussion")) return "section-badge--mdna";
  return "section-badge--business";
}
