from sqlalchemy import Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # --- Shopify Integration Fields ---
    # Stored as Strings because Shopify IDs are GIDs (e.g., "gid://shopify/Product/123")
    shopify_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True, index=True)
    shopify_variant_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)

    cart_items: Mapped[list["CartItem"]] = relationship(back_populates="product")