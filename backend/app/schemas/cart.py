from pydantic import BaseModel, ConfigDict

from app.schemas.product import ProductRead


class CartItemBase(BaseModel):
    product_id: int
    quantity: int


class CartItemCreate(CartItemBase):
    quantity: int


class CartItemRead(CartItemBase):
    id: int
    product: ProductRead | None = None

    model_config = ConfigDict(from_attributes=True)

