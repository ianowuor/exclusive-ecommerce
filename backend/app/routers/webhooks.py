import hmac
import hashlib
import json
import logging
import base64
from fastapi import APIRouter, Request, HTTPException, Depends, Header
from sqlalchemy.orm import Session
from app.core.deps import get_db
from app.core.config import settings
from app.models.product import Product

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)

def verify_shopify_webhook(data: bytes, hmac_header: str) -> bool:
    """
    Verifies the integrity of the webhook using the specific Webhook Secret.
    """
    if not hmac_header:
        logger.warning("Webhook rejected: Missing HMAC header")
        return False
    
    # Use the specific Webhook Secret, not the general API Secret
    secret = settings.SHOPIFY_WEBHOOK_SECRET.encode("utf-8")
    
    hash_code = hmac.new(
        secret, 
        data, 
        hashlib.sha256
    ).digest()
    
    calculated_hmac = base64.b64encode(hash_code).decode()
    
    is_valid = hmac.compare_digest(calculated_hmac, hmac_header)
    
    if not is_valid:
        logger.warning(f"Webhook HMAC mismatch. Calculated: {calculated_hmac} | Received: {hmac_header}")
        
    return is_valid

@router.post("/shopify/product-update")
async def shopify_product_update_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_shopify_hmac_sha256: str = Header(None)
):
    # 1. Read the raw body for HMAC verification
    raw_body = await request.body()
    
    # 2. Verify the authenticity
    if not verify_shopify_webhook(raw_body, x_shopify_hmac_sha256):
        logger.warning("Unauthorized webhook attempt blocked.")
        raise HTTPException(status_code=401, detail="Invalid HMAC signature")

    # 3. Parse data
    data = json.loads(raw_body)
    shopify_id = f"gid://shopify/Product/{data.get('id')}"
    
    logger.info(f"Received Shopify update for product: {shopify_id}")

    # 4. Find the product in our local DB
    product = db.query(Product).filter(Product.shopify_id == shopify_id).first()
    
    if product:
        # Update local fields based on Shopify changes
        product.name = data.get("title", product.name)
        # Note: description is usually 'body_html' in Shopify Webhooks
        product.description = data.get("body_html", product.description)
        
        # Update price from the first variant
        variants = data.get("variants", [])
        if variants:
            product.price = float(variants[0].get("price", product.price))
        
        db.commit()
        db.refresh(product)
        logger.info(f"Local product {product.id} updated from Shopify webhook.")
    else:
        logger.info(f"Product with Shopify ID {shopify_id} not found in local DB. Skipping.")

    return {"status": "success"}


@router.post("/shopify/product-delete")
async def shopify_product_delete_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_shopify_hmac_sha256: str = Header(None)
):
    raw_body = await request.body()
    if not verify_shopify_webhook(raw_body, x_shopify_hmac_sha256):
        raise HTTPException(status_code=401, detail="Invalid HMAC")

    data = json.loads(raw_body)
    shopify_id = f"gid://shopify/Product/{data.get('id')}"

    product = db.query(Product).filter(Product.shopify_id == shopify_id).first()
    
    if not product:
        # If it's already gone, just tell Shopify "Success" so it stops retrying
        logger.info(f"Webhook received for {shopify_id}, but product already deleted locally.")
        return {"status": "already_deleted"}

    db.delete(product)
    db.commit()
    return {"status": "success"}


@router.post("/shopify/inventory-update")
async def shopify_inventory_update_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_shopify_hmac_sha256: str = Header(None)
):
    raw_body = await request.body()
    if not verify_shopify_webhook(raw_body, x_shopify_hmac_sha256):
        raise HTTPException(status_code=401)

    data = json.loads(raw_body)
    inventory_item_id = f"gid://shopify/InventoryItem/{data.get('inventory_item_id')}"
    new_quantity = data.get("available") # 'available' represents sellable stock

    product = db.query(Product).filter(Product.shopify_inventory_item_id == inventory_item_id).first()
    if product:
        product.quantity = new_quantity
        db.commit()
        logger.info(f"Inventory synced: Product {product.id} now has {new_quantity} items.")

    return {"status": "success"}