import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.models.product import Product
from app.models.user import User
from app.schemas.product import ProductCreate, ProductRead
# Import your new service
from app.services.shopify import sync_product_to_shopify


router = APIRouter(prefix="/products", tags=["products"])


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProductRead:
    # 1. Local Save
    product = Product(
        name=payload.name,
        description=payload.description,
        price=payload.price,
        image_url=payload.image_url,
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    # 2. Shopify Sync
    try:
        shopify_result = await sync_product_to_shopify(
            name=product.name,
            price=float(product.price),
            description=product.description or "",
            quantity=payload.quantity
        )
        
        if isinstance(shopify_result, str) and shopify_result.startswith("gid://"):
            product.shopify_id = shopify_result
            db.add(product)
            db.commit()
            db.refresh(product)
            
    except Exception as e:
        logger.critical(f"Shopify sync failed: {e}")

    return product