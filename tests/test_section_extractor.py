from src.ingestion.section_extractor import extract_sections, extract_sections_from_html


def _section(name: str, body: str) -> str:
    return f'<div id="{name}"><h2>{name}</h2><p>{body}</p></div>'


def test_annual_report_toc_anchors_recover_sections_without_item_headings() -> None:
    body = "Evidence " * 200
    html = f"""
    <html><body>
      <nav>
        <a href="#business">Business</a>
        <a href="#risk">Risk Factors</a>
        <a href="#mdna">Management's Discussion and Analysis</a>
        <a href="#financial">Financial Statements and Supplementary Data</a>
      </nav>
      {_section("business", body + " Business evidence")}
      {_section("risk", body + " Risk evidence")}
      {_section("mdna", body + " MD&A evidence")}
      {_section("financial", body + " Financial evidence")}
    </body></html>
    """.encode()

    result = extract_sections_from_html(html)

    assert set(result.sections) == {
        "business",
        "risk_factors",
        "mdna",
        "financial_statements",
    }
    assert "Business evidence" in result.sections["business"]
    assert "Risk evidence" in result.sections["risk_factors"]
    assert "MD&A evidence" in result.sections["mdna"]
    assert "Financial evidence" in result.sections["financial_statements"]
    assert any("layout adapter" in warning for warning in result.warnings)


def test_annual_report_body_headings_skip_short_toc_intervals() -> None:
    body = "Evidence " * 200
    html = f"""
    <html><body>
      <p>Our Business</p><p>Risk Factors</p><p>Management's Discussion and Analysis</p>
      <p>Financial Statements and Supplementary Data</p>
      <h2>Our Business</h2><p>Business body {body}</p>
      <h2>Risk Factors</h2><p>Risk body {body}</p>
      <h2>Management's Discussion and Analysis</h2><p>Discussion body {body}</p>
      <h2>Financial Statements and Supplementary Data</h2><p>Financial statement body {body}</p>
    </body></html>
    """.encode()

    result = extract_sections_from_html(html)

    assert "Business body" in result.sections["business"]
    assert "Risk body" in result.sections["risk_factors"]
    assert "Discussion body" in result.sections["mdna"]


def test_annual_report_anchor_does_not_replace_item_boundary_section() -> None:
    body = "Evidence " * 200
    html = f"""
    <html><body>
      Item 1 Business {body}
      Item 1A Risk Factors {body}
      <a href="#business">Business</a>
      {_section("business", body + " Anchor-only business evidence")}
    </body></html>
    """.encode()

    result = extract_sections_from_html(html)

    assert "business" in result.sections
    assert "Anchor-only business evidence" not in result.sections["business"]


def test_mdna_end_skips_inline_item_cross_reference() -> None:
    """PFE regression: a mid-sentence 'Item 8' cross-reference inside the
    MD&A intro must not terminate the section; extraction advances to the
    next real end boundary instead of keeping a too-short slice."""
    filler = "Discussion " * 400
    text = (
        # Table-of-contents block: both entries are short page references.
        "ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION "
        "AND RESULTS OF OPERATIONS 30\n"
        "ITEM 7A. QUANTITATIVE AND QUALITATIVE DISCLOSURES ABOUT MARKET RISK 49\n"
        "ITEM 8. FINANCIAL STATEMENTS AND SUPPLEMENTARY DATA 50\n"
        # Body heading with an inline Item 8 cross-reference in the intro.
        "ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION "
        "AND RESULTS OF OPERATIONS\n"
        "The following discussion should be read in conjunction with the "
        "consolidated financial statements and related notes in Item 8. "
        f"{filler}\n"
        "ITEM 7A. QUANTITATIVE AND QUALITATIVE DISCLOSURES ABOUT MARKET RISK\n"
        + ("Market risk body " + "Risk " * 300 + "\n")
        + "ITEM 8. FINANCIAL STATEMENTS AND SUPPLEMENTARY DATA\n"
        + "Statement " * 300 + "\n"
        "ITEM 9. CHANGES IN AND DISAGREEMENTS WITH ACCOUNTANTS\n"
    )

    result = extract_sections(text)

    mdna = result.sections["mdna"]
    assert len(mdna) > 4000
    # The slice starts at the real body heading, not the TOC reference.
    assert mdna.startswith(
        "ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION"
    )
    assert "OPERATIONS 30" not in mdna
    assert "read in conjunction" in mdna
    assert filler.strip() in mdna
