"""Main scraper for EC2 Capacity Blocks pricing."""

import json
from datetime import datetime, timezone
from pathlib import Path

import requests

from .models import PricingData, PricingMetadata
from .parser import extract_json_data, parse_pricing_data

SOURCE_URL = "https://aws.amazon.com/ec2/capacityblocks/pricing/"
VERSION = "1.0.0"
DEFAULT_OUTPUT_PATH = Path(__file__).parent.parent / "data" / "pricing.json"


def fetch_page(url: str) -> str:
    """Fetch HTML content from the given URL."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.text


def scrape_pricing() -> PricingData:
    """Scrape pricing data from the AWS pricing page."""
    html = fetch_page(SOURCE_URL)
    json_data = extract_json_data(html)

    if not json_data:
        raise ValueError("No pricing data found in the page")

    instance_types = parse_pricing_data(json_data)

    if not instance_types:
        raise ValueError("Failed to parse any instance type pricing")

    metadata = PricingMetadata(
        last_updated=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        source_url=SOURCE_URL,
        version=VERSION,
    )

    return PricingData(metadata=metadata, instance_types=instance_types)


def save_pricing(data: PricingData, output_path: Path | None = None) -> Path:
    """Save pricing data to JSON file."""
    if output_path is None:
        output_path = DEFAULT_OUTPUT_PATH

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data.model_dump(), f, indent=2, ensure_ascii=False)

    return output_path


def main() -> None:
    """Main entry point for the scraper."""
    print("Fetching EC2 Capacity Blocks pricing data...")

    try:
        data = scrape_pricing()
        output_path = save_pricing(data)

        instance_count = len(data.instance_types)
        total_entries = sum(len(it.pricing) for it in data.instance_types.values())

        print(f"Successfully scraped pricing data:")
        print(f"  - Instance types: {instance_count}")
        print(f"  - Total pricing entries: {total_entries}")
        print(f"  - Output file: {output_path}")

        print("\nInstance types found:")
        for instance_type, pricing in sorted(data.instance_types.items()):
            regions = len(pricing.pricing)
            print(f"  - {instance_type} ({pricing.instance_family}): {regions} region(s)")

    except requests.RequestException as e:
        print(f"Error fetching page: {e}")
        raise SystemExit(1)
    except ValueError as e:
        print(f"Error parsing data: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
