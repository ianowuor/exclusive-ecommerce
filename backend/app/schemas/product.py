from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    name: str = Field(min_length=2, max_length=255, examples=["Vintage Leather Jacket"])
    description: str | None = Field(default=None, examples=["A high-quality, handcrafted leather jacket."])
    price: Decimal = Field(gt=0, examples=[120.50])
    image_url: str | None = Field(default=None, examples=["/uploads/products/jacket.jpg"])


class ProductCreate(ProductBase):
    """
    Schema for creating a product. 
    Includes Shopify-specific requirements for the 2026 sync logic.
    """
    # Required for Step C (Inventory) of the Shopify sync
    location_id: str = Field(
        description="The Shopify Global ID for the location (e.g., gid://shopify/Location/12345678)",
        examples=["gid://shopify/Location/12345678"]
    )
    # Defaulting to 1 ensures there is stock upon creation
    quantity: int = Field(default=1, ge=0, examples=[10])


class ProductRead(ProductBase):
    """
    Schema for reading product data.
    Includes database IDs and Shopify sync confirmation.
    """
    id: int
    # Shopify identifiers returned after successful sync
    shopify_id: str | None = None
    shopify_variant_id: str | None = None

    model_config = ConfigDict(from_attributes=True)