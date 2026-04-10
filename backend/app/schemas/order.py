from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int
    price: float


class OrderItemRead(BaseModel):
    id: int
    product_id: int
    quantity: int
    price: float
    
    class Config:
        from_attributes = True


class OrderCreate(BaseModel):
    shipping_address: str = Field(..., min_length=10, description="Shipping address")
    payment_method: str = Field(default="credit_card", description="Payment method")


class OrderRead(BaseModel):
    id: int
    user_id: int
    total_amount: float
    status: str
    shipping_address: str
    payment_method: str
    created_at: datetime
    updated_at: datetime
    order_items: List[OrderItemRead] = []
    
    class Config:
        from_attributes = True


class OrderSummary(BaseModel):
    id: int
    total_amount: float
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True
