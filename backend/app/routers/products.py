import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.models.product import Product
from app.models.user import User
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate
# Import your new service
from app.services.shopify import sync_product_to_shopify, update_shopify_product


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


@router.get("", response_model=list[ProductRead])
async def get_products(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    products = db.query(Product).offset(skip).limit(limit).all()
    return products


@router.put("/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: int,
    product_update: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Find the local product
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    # 2. Update local database fields
    update_data = product_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_product, key, value)

    db.commit()
    db.refresh(db_product)

    # 3. If the product is linked to Shopify, push the changes
    if db_product.shopify_id:
        try:
            shopify_response = await update_shopify_product(
                shopify_id=db_product.shopify_id,
                name=db_product.name,
                description=db_product.description,
                price=db_product.price
            )
            
            # Check for Shopify-specific errors
            if shopify_response.get("data", {}).get("productUpdate", {}).get("userErrors"):
                logger.error(f"Shopify Sync Error: {shopify_response['data']['productUpdate']['userErrors']}")
        except Exception as e:
            logger.error(f"Failed to sync update to Shopify: {str(e)}")
            # We don't raise an error here because the local save was successful,
            # but in production, you'd mark this for a retry.

    return db_product