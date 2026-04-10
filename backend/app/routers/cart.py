from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user, get_db
from app.models.cart_item import CartItem
from app.models.product import Product
from app.models.user import User
from app.schemas.cart import CartItemCreate, CartItemRead


router = APIRouter(prefix="/cart", tags=["cart"])


@router.post("/items", response_model=CartItemRead, status_code=status.HTTP_201_CREATED)
@router.post("/items/", response_model=CartItemRead, status_code=status.HTTP_201_CREATED)
def add_to_cart(
    payload: CartItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CartItemRead:
    if payload.quantity < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="quantity must be >= 1")

    product = db.get(Product, payload.product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    existing = db.scalar(
        select(CartItem).where(
            CartItem.user_id == current_user.id,
            CartItem.product_id == payload.product_id,
        )
    )

    if existing:
        existing.quantity += payload.quantity
        db.add(existing)
        db.commit()
        db.refresh(existing)
        existing = db.scalar(select(CartItem).options(joinedload(CartItem.product)).where(CartItem.id == existing.id))
        return existing

    item = CartItem(user_id=current_user.id, product_id=payload.product_id, quantity=payload.quantity)
    db.add(item)
    db.commit()
    db.refresh(item)
    item = db.scalar(select(CartItem).options(joinedload(CartItem.product)).where(CartItem.id == item.id))
    return item


@router.get("/items", response_model=list[CartItemRead])
@router.get("/items/", response_model=list[CartItemRead])
def list_cart_items(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CartItemRead]:
    items = db.scalars(
        select(CartItem)
        .options(joinedload(CartItem.product))
        .where(CartItem.user_id == current_user.id)
    ).all()
    return items


@router.delete("/items/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_cart(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.scalar(
        select(CartItem).where(
            CartItem.user_id == current_user.id,
            CartItem.product_id == product_id,
        )
    )
    
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")
    
    db.delete(item)
    db.commit()

