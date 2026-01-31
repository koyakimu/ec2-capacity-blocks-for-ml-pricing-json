"""Parser for EC2 Capacity Blocks pricing page HTML."""

import json
import re
from html import unescape

from bs4 import BeautifulSoup

from .models import InstanceTypePricing, PricingEntry

REGION_NAME_TO_CODE = {
    "US East (N. Virginia)": "us-east-1",
    "US East (Ohio)": "us-east-2",
    "US West (N. California)": "us-west-1",
    "US West (Oregon)": "us-west-2",
    "Africa (Cape Town)": "af-south-1",
    "Asia Pacific (Hong Kong)": "ap-east-1",
    "Asia Pacific (Hyderabad)": "ap-south-2",
    "Asia Pacific (Jakarta)": "ap-southeast-3",
    "Asia Pacific (Melbourne)": "ap-southeast-4",
    "Asia Pacific (Mumbai)": "ap-south-1",
    "Asia Pacific (Osaka)": "ap-northeast-3",
    "Asia Pacific (Seoul)": "ap-northeast-2",
    "Asia Pacific (Singapore)": "ap-southeast-1",
    "Asia Pacific (Sydney)": "ap-southeast-2",
    "Asia Pacific (Tokyo)": "ap-northeast-1",
    "Canada (Central)": "ca-central-1",
    "Canada West (Calgary)": "ca-west-1",
    "Europe (Frankfurt)": "eu-central-1",
    "Europe (Ireland)": "eu-west-1",
    "Europe (London)": "eu-west-2",
    "Europe (Milan)": "eu-south-1",
    "Europe (Paris)": "eu-west-3",
    "Europe (Spain)": "eu-south-2",
    "Europe (Stockholm)": "eu-north-1",
    "Europe (Zurich)": "eu-central-2",
    "Israel (Tel Aviv)": "il-central-1",
    "Middle East (Bahrain)": "me-south-1",
    "Middle East (UAE)": "me-central-1",
    "South America (São Paulo)": "sa-east-1",
    "South America (Sao Paulo)": "sa-east-1",
    # Alternate naming conventions
    "Australia (Sydney)": "ap-southeast-2",
    "Australia (Melbourne)": "ap-southeast-4",
    # Local Zones
    "US West (Dallas Local Zone)": "us-west-2-dal-1a",
    "Dallas Local Zone\n(US East N. Virginia)": "us-east-1-dfw-2a",
}

INSTANCE_TYPE_INFO: dict[str, dict] = {
    # P6e (UltraServer) - GB200
    "u-p6e-gb200x72": {"family": "P6e", "accelerator": "GB200", "count": 72},
    "u-p6e-gb200x36": {"family": "P6e", "accelerator": "GB200", "count": 36},
    # P6-B300
    "p6-b300.48xlarge": {"family": "P6-B300", "accelerator": "B300", "count": 8},
    # P6-B200
    "p6-b200.48xlarge": {"family": "P6-B200", "accelerator": "B200", "count": 8},
    # P5
    "p5.48xlarge": {"family": "P5", "accelerator": "H100", "count": 8},
    "p5.4xlarge": {"family": "P5", "accelerator": "H100", "count": 1},
    # P5e
    "p5e.48xlarge": {"family": "P5e", "accelerator": "H200", "count": 8},
    # P5en
    "p5en.48xlarge": {"family": "P5en", "accelerator": "H200", "count": 8},
    # P4d
    "p4d.24xlarge": {"family": "P4d", "accelerator": "A100", "count": 8},
    "p4de.24xlarge": {"family": "P4de", "accelerator": "A100", "count": 8},
    # Trainium
    "trn1.32xlarge": {"family": "Trn1", "accelerator": "Trainium", "count": 16},
    "trn2.3xlarge": {"family": "Trn2", "accelerator": "Trainium2", "count": 1},
    "trn2.48xlarge": {"family": "Trn2", "accelerator": "Trainium2", "count": 16},
}


def extract_json_data(html: str) -> list[dict]:
    """Extract JSON data from the pricing page HTML.

    The page embeds pricing data in <script type="application/json"> tags.
    Each tag contains a structure like:
    {
        "data": {
            "items": [{
                "fields": {
                    "jsonData": "{...escaped JSON with table data...}"
                }
            }]
        }
    }
    """
    pattern = r'<script type="application/json">(.*?)</script>'
    script_matches = re.findall(pattern, html, re.DOTALL)

    all_rows = []

    for script_content in script_matches:
        try:
            outer_data = json.loads(script_content)
        except json.JSONDecodeError:
            continue

        items = outer_data.get("data", {}).get("items", [])
        for item in items:
            json_data_str = item.get("fields", {}).get("jsonData", "")
            if not json_data_str:
                continue

            try:
                table_data = json.loads(json_data_str)
            except json.JSONDecodeError:
                continue

            heading = table_data.get("heading", "")
            if "Pricing" not in heading:
                continue

            table = table_data.get("table", {})
            row_definitions = table.get("rowDefinitions", [])
            table_items = table.get("items", [])

            row_labels = {row["id"]: row.get("label", "") for row in row_definitions}

            for table_item in table_items:
                row_id = table_item.get("idProperty", "")
                instance_type = row_labels.get(row_id, "")

                region = table_item.get("2", "")
                price = table_item.get("3", "")

                if instance_type and region and price:
                    all_rows.append(
                        {
                            "instance_type": instance_type,
                            "region": region,
                            "price": price,
                            "heading": heading,
                        }
                    )

    return all_rows


def clean_html(text: str) -> str:
    """Remove HTML tags and unescape HTML entities."""
    if not text:
        return ""
    text = unescape(text)
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text().strip()


def parse_price_string(price_str: str) -> tuple[float, float]:
    """Parse price string like '$31.464 USD ($3.933 USD)' into (hourly, per_accelerator)."""
    price_str = clean_html(price_str)

    pattern = r"\$?([\d,]+\.?\d*)\s*USD\s*\(\$?([\d,]+\.?\d*)\s*USD\)"
    match = re.search(pattern, price_str)
    if match:
        hourly = float(match.group(1).replace(",", ""))
        per_acc = float(match.group(2).replace(",", ""))
        return hourly, per_acc

    single_pattern = r"\$?([\d,]+\.?\d*)\s*USD"
    match = re.search(single_pattern, price_str)
    if match:
        hourly = float(match.group(1).replace(",", ""))
        return hourly, 0.0

    return 0.0, 0.0


def parse_pricing_data(json_data: list[dict]) -> dict[str, InstanceTypePricing]:
    """Parse extracted JSON data into structured pricing information."""
    instance_pricing: dict[str, list[PricingEntry]] = {}

    for row in json_data:
        instance_type = row.get("instance_type", "")
        if not instance_type:
            continue

        region = clean_html(row.get("region", ""))
        if not region:
            continue

        price_str = row.get("price", "")
        if not price_str:
            continue

        hourly, per_acc = parse_price_string(price_str)
        if hourly == 0.0:
            continue

        region_code = REGION_NAME_TO_CODE.get(region, "")
        if not region_code:
            region_normalized = region.strip()
            region_code = REGION_NAME_TO_CODE.get(region_normalized, "unknown")

        entry = PricingEntry(
            region=region,
            region_code=region_code,
            hourly_rate_usd=hourly,
            accelerator_hourly_rate_usd=per_acc,
        )

        if instance_type not in instance_pricing:
            instance_pricing[instance_type] = []
        instance_pricing[instance_type].append(entry)

    result: dict[str, InstanceTypePricing] = {}
    for instance_type, entries in instance_pricing.items():
        info = INSTANCE_TYPE_INFO.get(instance_type, {})
        family = info.get("family", "Unknown")
        accelerator = info.get("accelerator", "Unknown")
        count = info.get("count", 0)

        if family == "Unknown":
            family, accelerator, count = _infer_instance_info(instance_type)

        result[instance_type] = InstanceTypePricing(
            instance_family=family,
            accelerator_type=accelerator,
            accelerator_count=count,
            pricing=entries,
        )

    return result


def _infer_instance_info(instance_type: str) -> tuple[str, str, int]:
    """Infer instance family, accelerator type, and count from instance type name."""
    if instance_type.startswith("p5en"):
        return "P5en", "H200", 8
    elif instance_type.startswith("p5e"):
        return "P5e", "H200", 8
    elif instance_type.startswith("p5"):
        count = 8 if "48xlarge" in instance_type else 1
        return "P5", "H100", count
    elif instance_type.startswith("p6-b300"):
        return "P6-B300", "B300", 8
    elif instance_type.startswith("p6-b200"):
        return "P6-B200", "B200", 8
    elif instance_type.startswith("u-p6e"):
        if "x72" in instance_type:
            return "P6e", "GB200", 72
        elif "x36" in instance_type:
            return "P6e", "GB200", 36
        return "P6e", "GB200", 0
    elif instance_type.startswith("p4de"):
        return "P4de", "A100", 8
    elif instance_type.startswith("p4d"):
        return "P4d", "A100", 8
    elif instance_type.startswith("trn2"):
        count = 16 if "48xlarge" in instance_type else 1
        return "Trn2", "Trainium2", count
    elif instance_type.startswith("trn1"):
        return "Trn1", "Trainium", 16
    return "Unknown", "Unknown", 0
