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
from app.services.shopify import sync_product_to_shopify, update_shopify_product, delete_shopify_product, update_shopify_product_image


router = APIRouter(prefix="/products", tags=["products"])


router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
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
            db.commit() # Save the GID first

            # 3. Image Sync (If URL provided)
            if product.image_url:
                await update_shopify_product_image(
                    shopify_id=product.shopify_id,
                    image_url=product.image_url
                )
            
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
            # Update basic info
            await update_shopify_product(
                shopify_id=db_product.shopify_id,
                name=db_product.name,
                description=db_product.description,
                price=float(db_product.price)
            )
            
            # Update image if it was part of this request
            if "image_url" in update_data and db_product.image_url:
                await update_shopify_product_image(
                    shopify_id=db_product.shopify_id,
                    image_url=db_product.image_url
                )

        except Exception as e:
            logger.error(f"Failed to sync update to Shopify: {str(e)}")

    return db_product


@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Fetch product
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # 2. Sync deletion to Shopify if linked
    if product.shopify_id:
        try:
            response = await delete_shopify_product(product.shopify_id)
            errors = response.get("data", {}).get("productDelete", {}).get("userErrors")
            if errors:
                logger.error(f"Shopify Delete Error: {errors}")
        except Exception as e:
            logger.error(f"Network error during Shopify deletion: {e}")

    # 3. Remove from local DB
    db.delete(product)
    db.commit()
    return None