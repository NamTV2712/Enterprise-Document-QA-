"""Tests for financial table extraction helpers."""

from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from src.ingestion.table_extractor import (
    extract_table_rows,
    find_table_containing_text,
    get_table_caption,
)


def test_percentage_table_without_change_column_kept() -> None:
    """
    Synthetic test: the current AAPL/MSFT/AMZN corpus does not contain a real
    percentage-primary financial table. Percent metrics in these 10-K filings
    generally appear in MD&A prose, not in tables. This protects future corpus
    expansion where a filing may include a percentage-primary table.
    """
    html = """
    <table>
      <tr><td>Metric</td><td>2025</td><td>2024</td><td>2023</td></tr>
      <tr><td>Cloud gross margin percentage</td><td>69%</td><td>72%</td><td>74%</td></tr>
    </table>
    """
    soup = BeautifulSoup(html, "lxml")
    rows = extract_table_rows(soup.find("table"))

    assert rows[0].values_by_year == {"2025": "69%", "2024": "72%", "2023": "74%"}


def test_header_cells_can_contain_dates() -> None:
    html = """
    <table>
      <tr><td>Years ended</td></tr>
      <tr><td>September 27, 2025</td><td>September 28, 2024</td><td>September 30, 2023</td></tr>
      <tr><td>Products</td><td>$</td><td>307,003</td><td>$</td><td>294,866</td><td>$</td><td>298,085</td></tr>
      <tr><td>Services</td><td>109,158</td><td>96,169</td><td>85,200</td></tr>
    </table>
    """
    soup = BeautifulSoup(html, "lxml")
    rows = extract_table_rows(soup.find("table"))

    assert rows[0].label == "Products"
    assert rows[0].values_by_year == {
        "2025": "307,003",
        "2024": "294,866",
        "2023": "298,085",
    }


def test_caption_uses_previous_text_window() -> None:
    html = """
    <div>Property and equipment, net by segment is as follows (in millions):</div>
    <table>
      <tr><td>2025</td><td>2024</td></tr>
      <tr><td>AWS</td><td>190,055</td><td>110,683</td></tr>
    </table>
    """
    soup = BeautifulSoup(html, "lxml")

    assert get_table_caption(soup.find("table")).startswith("Property and equipment")


def test_segment_header_row_prefixes_following_metrics() -> None:
    """One-cell segment headers should prefix following metric rows."""
    html = """
    <table>
      <tr><td>Year Ended December 31,</td></tr>
      <tr><td>2024</td><td>2025</td></tr>
      <tr><td>North America</td></tr>
      <tr><td>Net sales</td><td>$387,497</td><td>$426,305</td></tr>
      <tr><td>International</td></tr>
      <tr><td>Net sales</td><td>$142,906</td><td>$161,894</td></tr>
    </table>
    """
    soup = BeautifulSoup(html, "lxml")
    rows = extract_table_rows(soup.find("table"))
    labels = [row.label for row in rows]

    assert "North America - Net sales" in labels
    assert "International - Net sales" in labels


def test_non_segment_table_labels_unchanged() -> None:
    """Regular tables should not receive a synthetic segment prefix."""
    html = """
    <table>
      <tr><td>2025</td><td>2024</td></tr>
      <tr><td>Total net sales</td><td>$416,161</td><td>$391,035</td></tr>
    </table>
    """
    soup = BeautifulSoup(html, "lxml")
    rows = extract_table_rows(soup.find("table"))

    assert rows[0].label == "Total net sales"


def test_aapl_total_net_sales_table() -> None:
    raw_path = Path("data/raw/AAPL/000032019325000079.html")
    if not raw_path.exists():
        pytest.skip("Local raw AAPL filing is not available")

    html = raw_path.read_bytes()
    soup = BeautifulSoup(html, "lxml")
    table = find_table_containing_text(soup, "Total net sales")
    rows = extract_table_rows(table)

    total_net_sales = next(row for row in rows if row.label == "Total net sales")

    assert total_net_sales.values_by_year == {
        "2025": "416,161",
        "2024": "391,035",
        "2023": "383,285",
    }


def test_msft_total_revenue_table_self_consistency() -> None:
    raw_path = Path("data/raw/MSFT/000095017025100235.html")
    if not raw_path.exists():
        pytest.skip("Local raw MSFT filing is not available")

    html = raw_path.read_bytes()
    soup = BeautifulSoup(html, "lxml")
    table = find_table_containing_text(soup, "Total revenue")
    rows = extract_table_rows(table)

    product = rows[0]
    service = rows[1]
    total_revenue = next(row for row in rows if row.label == "Total revenue")

    for year in ("2025", "2024", "2023"):
        product_value = int(product.values_by_year[year].replace(",", ""))
        service_value = int(service.values_by_year[year].replace(",", ""))
        total_value = int(total_revenue.values_by_year[year].replace(",", ""))
        assert product_value + service_value == total_value
