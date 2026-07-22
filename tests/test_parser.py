"""Tests for the pricing page parser."""

import json

from src.parser import extract_json_data, parse_price_string, parse_pricing_data


def _page_with_fields(fields: dict) -> str:
    """Wrap item fields in the page's <script type="application/json"> structure."""
    payload = {"data": {"items": [{"fields": fields}]}}
    return f'<html><script type="application/json">{json.dumps(payload)}</script></html>'


# --- New format (2026-04 onwards): itemHeading / itemTableRowGroups / itemTableData ---

NEW_FORMAT_FIELDS = {
    "itemHeading": "P6e Pricing",
    "itemRegionProperty": "region",
    "itemTableColumns": json.dumps(
        [
            {"Heading": "UltraServer Type", "accessor": "1"},
            {"Heading": "Region", "accessor": "2"},
            {"Heading": "Effective Hourly Rate", "accessor": "3"},
            {"Heading": "ACCELERATOR", "accessor": "4"},
        ]
    ),
    "itemTableRowGroups": json.dumps(
        [
            {"id": "row1", "idProperty": "idProperty", "label": "u-p6e-gb200x72"},
            {"id": "row3", "idProperty": "idProperty", "label": "u-p6e-gb200x36"},
        ]
    ),
    "itemTableData": json.dumps(
        [
            {
                "id": 0,
                "idProperty": "row1",
                "2": "<p>US East (Dallas) Local Zone</p>\r\n",
                "3": "<p>$761.904 ($10.582 USD)<br /></p>\r\n",
                "4": "<p>72 x B200</p>\r\n",
            },
            {
                "id": 1,
                "idProperty": "row3",
                "2": "<p>US East (Dallas) Local Zone</p>\r\n",
                "3": "<p>$380.952 ($10.582 USD)<br /></p>\r\n",
                "4": "<p>36 x B200</p>\r\n",
            },
        ]
    ),
}


def test_extract_new_format_rows():
    html = _page_with_fields(NEW_FORMAT_FIELDS)
    rows = extract_json_data(html)
    assert len(rows) == 2
    assert rows[0]["instance_type"] == "u-p6e-gb200x72"
    assert "Dallas" in rows[0]["region"]
    assert "$761.904" in rows[0]["price"]


def test_extract_new_format_skips_non_pricing_tables():
    fields = dict(NEW_FORMAT_FIELDS)
    fields["itemHeading"] = "OS pricing across Instance Types"
    html = _page_with_fields(fields)
    assert extract_json_data(html) == []


# --- Old format (pre 2026-04): fields.jsonData escaped JSON string ---

OLD_FORMAT_FIELDS = {
    "jsonData": json.dumps(
        {
            "heading": "P5 Pricing",
            "table": {
                "rowDefinitions": [
                    {"id": "row1", "label": "p5.48xlarge"},
                ],
                "items": [
                    {
                        "idProperty": "row1",
                        "2": "<p>US East (N. Virginia)</p>",
                        "3": "<p>$31.464 USD ($3.933 USD)</p>",
                    }
                ],
            },
        }
    )
}


def test_extract_old_format_still_supported():
    html = _page_with_fields(OLD_FORMAT_FIELDS)
    rows = extract_json_data(html)
    assert len(rows) == 1
    assert rows[0]["instance_type"] == "p5.48xlarge"


# --- Price string parsing ---

def test_parse_price_with_usd_suffix():
    assert parse_price_string("$31.464 USD ($3.933 USD)") == (31.464, 3.933)


def test_parse_price_without_first_usd_suffix():
    assert parse_price_string("$761.904 ($10.582 USD)") == (761.904, 10.582)


def test_parse_price_single_value():
    assert parse_price_string("$11.8 USD") == (11.8, 0.0)


# --- Region code mapping for regions introduced with the new page ---

def _rows_for_region(region: str) -> list[dict]:
    return [
        {
            "instance_type": "p5e.48xlarge",
            "region": region,
            "price": "$47.76 USD ($5.97 USD)",
            "heading": "P5e Pricing",
        }
    ]


def test_new_region_names_are_mapped():
    expected = {
        "US East (Dallas) Local Zone": "us-east-1-dfw-2a",
        "US East (Atlanta) Local Zone": "us-east-1-atl-2a",
        "US West (Phoenix) Local Zone": "us-west-2-phx-2a",
        "AWS GovCloud (US-East)": "us-gov-east-1",
        "AWS GovCloud (US-West)": "us-gov-west-1",
    }
    for region, code in expected.items():
        result = parse_pricing_data(_rows_for_region(region))
        assert result["p5e.48xlarge"].pricing[0].region_code == code, region
