"""Pydantic data models for EC2 Capacity Blocks pricing."""

from pydantic import BaseModel


class PricingEntry(BaseModel):
    """Pricing information for a specific region."""

    region: str
    region_code: str
    hourly_rate_usd: float
    accelerator_hourly_rate_usd: float


class InstanceTypePricing(BaseModel):
    """Pricing information for a specific instance type."""

    instance_family: str
    accelerator_type: str
    accelerator_count: int
    pricing: list[PricingEntry]


class PricingMetadata(BaseModel):
    """Metadata about the pricing data."""

    last_updated: str
    source_url: str
    version: str


class PricingData(BaseModel):
    """Complete pricing data structure."""

    metadata: PricingMetadata
    instance_types: dict[str, InstanceTypePricing]
