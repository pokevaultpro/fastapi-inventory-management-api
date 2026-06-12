from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Users(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True)
    username = Column(String, unique=True)
    first_name = Column(String)
    last_name = Column(String)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    role = Column(String, default="user")
    cart_items = relationship("Cart", back_populates="owner")


class Products(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    category = Column(String)
    original_price = Column(Float)
    discounted_price = Column(Float, nullable=True)
    unit = Column(String)
    supermarket_id = Column(Integer, ForeignKey('supermarkets.id'))
    aisle_order = Column(Float)
    image = Column(String, nullable=True)
    calories = Column(Float, nullable=True)
    fat = Column(Float, nullable=True)
    carbs = Column(Float, nullable=True)
    protein = Column(Float, nullable=True)
    location = Column(String, nullable=True)
    supermarket = relationship("Supermarkets", back_populates="products")
    cart_items = relationship("Cart", back_populates="product")

class Favorites(Base):
    __tablename__ = 'favorites'

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey('products.id'))
    owner_id = Column(Integer, ForeignKey('users.id'))

class Supermarkets(Base):
    __tablename__ = 'supermarkets'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    image = Column(String, nullable=True)
    location = Column(String, nullable=True)
    products = relationship("Products", back_populates="supermarket")


class Recipes(Base):
    __tablename__ = 'recipes'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    image = Column(String, nullable=True)
    owner_id = Column(Integer, ForeignKey('users.id'))


class RecipeItems(Base):
    __tablename__ = 'recipe_items'

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey('recipes.id'))
    product_id = Column(Integer, ForeignKey('products.id'))
    quantity = Column(Integer)


class Cart(Base):
    __tablename__ = 'cart'

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey('products.id'))
    quantity = Column(Integer)
    owner_id = Column(Integer, ForeignKey('users.id'))
    checked = Column(Boolean, default=False)
    product = relationship("Products", back_populates="cart_items")
    owner = relationship("Users", back_populates="cart_items")

class ShoppingHistory(Base):
    __tablename__ = "shopping_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    created_at = Column(String, nullable=False)
    total_price = Column(Float, nullable=False)
    total_items = Column(Integer, nullable=False)

    # relazione con gli item
    items = relationship("ShoppingHistoryItem", back_populates="history", cascade="all, delete")

class ShoppingHistoryItem(Base):
    __tablename__ = "shopping_history_items"

    id = Column(Integer, primary_key=True, index=True)
    history_id = Column(Integer, ForeignKey("shopping_history.id"), nullable=False)

    product_id = Column(Integer, nullable=True)

    name = Column(String, nullable=False)
    image = Column(String, nullable=True)
    unit = Column(String, nullable=True)

    price_paid = Column(Float, nullable=False)
    was_discounted = Column(Boolean, default=False)

    quantity = Column(Integer, default=1)

    category = Column(String, nullable=True)
    aisle_order = Column(Float, nullable=True)

    supermarket_id = Column(Integer, nullable=True)
    supermarket_name = Column(String, nullable=True)

    calories = Column(Float, nullable=True)
    fat = Column(Float, nullable=True)
    carbs = Column(Float, nullable=True)
    protein = Column(Float, nullable=True)

    # relazione inversa
    history = relationship("ShoppingHistory", back_populates="items")
