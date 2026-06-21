# Project State

## Current Milestone

Step 3 is complete: SEC 10-K section extraction is now robust enough for the MVP pipeline.

Latest Step 3 commit:

```text
6b2f599 Robust SEC filing section extraction
```

## Implemented So Far

- SEC EDGAR client for ticker-to-CIK lookup, filing metadata retrieval, and filing download.
- HTML-to-text conversion for downloaded SEC filings.
- Robust extraction for 10-K sections:
  - `business`
  - `risk_factors`
  - `mdna`
  - `financial_statements`
- Section extraction now handles:
  - table-of-contents false matches
  - self-reference text such as `Risk Factors of this Annual Report`
  - split headings such as `RIS\nK FACTORS`
  - intermediate section boundaries such as `Item 1B`, `Item 1C`, `Item 7A`
  - MSFT-specific management responsibility section before `Item 7A`
  - trailing page/header noise at section ends
- Processed data regenerated for:
  - AAPL
  - MSFT
  - AMZN
- Generalization check performed with GOOGL latest 10-K: passed with no warnings.

## Validation Summary

Validated section starts and ends for all 12 sections across AAPL, MSFT, and AMZN.

Current processed section token counts using `cl100k_base`:

| Ticker | Section | Characters | Tokens |
|---|---:|---:|---:|
| AAPL | business | 16,071 | 2,941 |
| AAPL | risk_factors | 68,050 | 11,631 |
| AAPL | mdna | 18,110 | 4,137 |
| AAPL | financial_statements | 62,127 | 15,401 |
| MSFT | business | 48,751 | 8,553 |
| MSFT | risk_factors | 69,024 | 11,933 |
| MSFT | mdna | 46,316 | 9,128 |
| MSFT | financial_statements | 103,782 | 24,506 |
| AMZN | business | 13,545 | 2,684 |
| AMZN | risk_factors | 60,765 | 10,655 |
| AMZN | mdna | 46,462 | 9,011 |
| AMZN | financial_statements | 124,074 | 28,459 |

## Step 4 Status: Chunking Strategy

Step 4 has started.

Completed initial analysis:

- Installed and verified `tiktoken`.
- Updated `requirements.txt` with `tiktoken==0.13.0`.
- Inspected MSFT balance sheet text inside `financial_statements`.
- Confirmed table text is usable for MVP retrieval, but formatting is verticalized.

Decision direction for MVP chunking:

- Chunk by paragraph, not fixed character count.
- Measure chunk size by token count, not character count.
- Use small overlap between adjacent chunks.
- Attach metadata to every chunk:
  - `ticker`
  - `section`
  - `accession_number`
  - `filing_date`
  - `report_date`
  - `chunk_index`
  - `token_count`

Important note for financial statements:

- Do not use chunks that are too small, because table labels and values may be split across lines.
- Chunking must keep nearby financial labels and numbers together as much as possible.

## Next Steps

1. Finalize chunk size and overlap based on token count data.
2. Implement a paragraph-aware chunker.
3. Generate chunk JSON files under `data/processed` or `data/chunks`.
4. Validate sample chunks manually, especially financial statement chunks.
5. Move to retrieval/vector store after chunk validation.
