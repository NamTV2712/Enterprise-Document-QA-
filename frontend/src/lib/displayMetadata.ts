export const COMPANY_NAMES: Record<string, string> = {
  AAPL: "Apple Inc.",
  MSFT: "Microsoft Corporation",
  AMZN: "Amazon.com, Inc.",
  GOOGL: "Alphabet Inc. (Google)",
  META: "Meta Platforms, Inc.",
  NVDA: "NVIDIA Corporation",
  TSLA: "Tesla, Inc.",
  JPM: "JPMorgan Chase & Co.",
  BAC: "Bank of America Corporation",
  GS: "The Goldman Sachs Group, Inc.",
  MS: "Morgan Stanley",
  "BRK-B": "Berkshire Hathaway Inc.",
  JNJ: "Johnson & Johnson",
  UNH: "UnitedHealth Group Incorporated",
  PFE: "Pfizer Inc.",
  WMT: "Walmart Inc.",
  HD: "The Home Depot, Inc.",
  MCD: "McDonald's Corporation",
  XOM: "Exxon Mobil Corporation",
  CVX: "Chevron Corporation",
  AMD: "Advanced Micro Devices, Inc.",
  INTC: "Intel Corporation",
  QCOM: "QUALCOMM Incorporated",
  AVGO: "Broadcom Inc.",
  TXN: "Texas Instruments Incorporated",
  CRM: "Salesforce, Inc.",
  ORCL: "Oracle Corporation",
  NOW: "ServiceNow, Inc.",
  IBM: "International Business Machines Corporation",
  V: "Visa Inc.",
  MA: "Mastercard Incorporated",
  AXP: "American Express Company",
  LLY: "Eli Lilly and Company",
  MRK: "Merck & Co., Inc.",
  ABBV: "AbbVie Inc.",
  TMO: "Thermo Fisher Scientific Inc.",
  PG: "The Procter & Gamble Company",
  KO: "The Coca-Cola Company",
  PEP: "PepsiCo, Inc.",
  COST: "Costco Wholesale Corporation",
  NKE: "NIKE, Inc.",
  CAT: "Caterpillar Inc.",
  GE: "GE Aerospace",
  BA: "The Boeing Company",
  LMT: "Lockheed Martin Corporation",
  HON: "Honeywell International Inc.",
  UPS: "United Parcel Service, Inc.",
  RTX: "RTX Corporation",
  VZ: "Verizon Communications Inc.",
  T: "AT&T Inc.",
};

export function formatCompanyLabel(ticker: string): string {
  const companyName = COMPANY_NAMES[ticker];
  return companyName ? `${companyName} (${ticker})` : ticker;
}

export interface SectionMetadata {
  label: string;
  shortLabel: string;
  description: string;
}

export const SECTION_METADATA: Record<string, SectionMetadata> = {
  business: {
    label: "Business Overview",
    shortLabel: "Business Overview",
    description: "Operations, products, markets, customers, and strategy.",
  },
  risk_factors: {
    label: "Risk Factors",
    shortLabel: "Risk Factors",
    description: "Material risks disclosed by company management.",
  },
  mdna: {
    label: "Management Discussion & Analysis (MD&A)",
    shortLabel: "MD&A",
    description: "Results, liquidity, trends, and management commentary.",
  },
  financial_statements: {
    label: "Financial Statements & Notes",
    shortLabel: "Financial Statements & Notes",
    description: "Statement-related filing text, notes, and auditor material.",
  },
  financial_table: {
    label: "Structured Financial Tables",
    shortLabel: "Financial Tables",
    description: "Extracted rows optimized for exact numeric retrieval.",
  },
};

export const ALL_SECTIONS_DESCRIPTION =
  "Search every available 10-K section and structured table.";
