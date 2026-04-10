from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user, get_db
from app.models.cart_item import CartItem
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.user import User
from app.schemas.order import OrderCreate, OrderRead, OrderSummary

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def create_order(
    order_data: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrderRead:
    # Get user's cart items
    cart_items = db.scalars(
        select(CartItem)
        .options(joinedload(CartItem.product))
        .where(CartItem.user_id == current_user.id)
    ).all()

    if not cart_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Cart is empty"
        )

    # Calculate total amount
    total_amount = sum(
        item.quantity * float(item.product.price) 
        for item in cart_items
    )

    try:
        # 1. Create order
        order = Order(
            user_id=current_user.id,
            total_amount=total_amount,
            shipping_address=order_data.shipping_address,
            payment_method=order_data.payment_method,
            status="processing"
        )
        db.add(order)
        db.flush() # Flush to get the order.id before commit

        # 2. Create order items from cart
        for cart_item in cart_items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=cart_item.product_id,
                quantity=cart_item.quantity,
                price=float(cart_item.product.price)
            )
            db.add(order_item)

        # 3. FIXED: Correct Delete Syntax
        # Use the delete() construct directly for bulk deletion
        db.execute(
            delete(CartItem).where(CartItem.user_id == current_user.id)
        )
        
        db.commit()
        db.refresh(order)

        # Return the complete order with items
        # Use joinedload to ensure order_items are included in the response
        return db.scalar(
            select(Order)
            .options(joinedload(Order.order_items))
            .where(Order.id == order.id)
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process order: {str(e)}"
        )


@router.get("/", response_model=list[OrderSummary])
def get_user_orders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[OrderSummary]:
    orders = db.scalars(
        select(Order)
        .where(Order.user_id == current_user.id)
        .order_by(Order.created_at.desc())
    ).all()
    return orders


@router.get("/{order_id}", response_model=OrderRead)
def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrderRead:
    order = db.scalar(
        select(Order)
        .options(joinedload(Order.order_items).joinedload(OrderItem.product))
        .where(
            Order.id == order_id,
            Order.user_id == current_user.id
        )
    )
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Order not found"
        )
    
    return order


@router.put("/{order_id}/status")
def update_order_status(
    order_id: int,
    status_data: dict, # Changed to accept body if needed
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target_status = status_data.get("status")
    
    if target_status not in ["cancelled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Only 'cancelled' status is allowed"
        )
    
    order = db.scalar(
        select(Order).where(
            Order.id == order_id,
            Order.user_id == current_user.id
        )
    )
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Order not found"
        )
    
    if order.status not in ["processing", "pending"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Order cannot be cancelled in its current state"
        )
    
    order.status = target_status
    db.commit()
    
    return {"message": f"Order status updated to {target_status}"}