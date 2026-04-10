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
    location_id: str = Field(
        description="The Shopify Global ID for the location (e.g., gid://shopify/Location/12345678)",
        examples=["gid://shopify/Location/12345678"]
    )
    quantity: int = Field(default=1, ge=0, examples=[10])


class ProductUpdate(BaseModel):
    """
    Schema for updating an existing product.
    All fields are optional to allow partial updates (PATCH style).
    """
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = Field(default=None)
    price: Decimal | None = Field(default=None, gt=0)
    image_url: str | None = Field(default=None)
    quantity: int | None = Field(default=None, ge=0)


class ProductRead(ProductBase):
    """
    Schema for reading product data.
    Includes database IDs and Shopify sync confirmation.
    """
    id: int
    shopify_id: str | None = None
    shopify_variant_id: str | None = None

    model_config = ConfigDict(from_attributes=True)