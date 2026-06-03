import pytest
from sqlalchemy import create_engine, StaticPool, text
from sqlalchemy.orm import sessionmaker
from starlette.testclient import TestClient
from passlib.context import CryptContext

from app.database import Base
from app.main import app
from app.models import (Products, Supermarkets, Recipes, RecipeItems, Cart,
                        Users, ShoppingHistory, ShoppingHistoryItem, Favorites)

SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={'check_same_thread': False}, poolclass=StaticPool)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(engine)

test_bcrypt = CryptContext(schemes=["bcrypt"], deprecated="auto")


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

def override_get_current_user():
    return {'username': 'myusername', 'id': 1, 'user_role': 'admin'}

client = TestClient(app)

@pytest.fixture
def test_product(test_supermarket):
    product1 = Products(
        name="Onion",
        original_price=0.62,
        supermarket_id=test_supermarket[0].id,
        aisle_order=3.2,
        unit = "pz",
        category="Frutta"

    )
    product2 = Products(
        name="Garlic",
        original_price=0.88,
        supermarket_id=test_supermarket[1].id,
        aisle_order=2.5,
        unit="100g",
        category="Verdura"
    )
    product3 = Products(
        name="Swile",
        original_price=1.24,
        discounted_price=1.10,
        supermarket_id=test_supermarket[0].id,
        aisle_order=3,
        unit = "pz",
        category = "Verdura"
    )
    db = TestingSessionLocal()
    db.add(product1)
    db.add(product2)
    db.add(product3)
    db.commit()
    yield [product1, product2, product3]
    with engine.connect() as connection:
        connection.execute(text("DELETE FROM products;"))
        connection.commit()

@pytest.fixture
def test_favorite(test_product, test_user):
    favorite1 = Favorites(
        product_id=test_product[0].id,
        owner_id=test_user[0].id,
    )
    favorite2 = Favorites(
        product_id=test_product[1].id,
        owner_id=test_user[1].id,
    )
    db = TestingSessionLocal()
    db.add(favorite1)
    db.add(favorite2)
    db.commit()
    yield [favorite1, favorite2]
    with engine.connect() as connection:
        connection.execute(text("DELETE FROM favorites;"))
        connection.commit()

@pytest.fixture
def test_supermarket():
    supermarket1 = Supermarkets(
        name="Conad",
        location="Via delle Arti 22, Matera"
    )
    supermarket2 = Supermarkets(
        name="Lidl",
        location="Via delle Arti 1, Matera",
    )
    db = TestingSessionLocal()
    db.add(supermarket1)
    db.add(supermarket2)
    db.commit()
    yield [supermarket1, supermarket2]
    with engine.connect() as connection:
        connection.execute(text("DELETE FROM supermarkets;"))
        connection.commit()

@pytest.fixture
def test_recipe(test_user):
    recipe1 = Recipes(
        name="Carbonara",
        owner_id=test_user[0].id,
    )
    recipe2 = Recipes(
        name="Risotto ai Funghi",
        owner_id=test_user[1].id,
    )
    db = TestingSessionLocal()
    db.add(recipe1)
    db.add(recipe2)
    db.commit()
    yield [recipe1, recipe2]
    with engine.connect() as connection:
        connection.execute(text("DELETE FROM recipes;"))
        connection.commit()

@pytest.fixture
def test_recipe_item(test_recipe, test_product):
    recipe_item1 = RecipeItems(
        recipe_id=test_recipe[0].id,
        product_id=test_product[0].id,
        quantity=10
    )
    recipe_item2 = RecipeItems(
        recipe_id=test_recipe[0].id,
        product_id=test_product[1].id,
        quantity=5
    )
    recipe_item3 = RecipeItems(
        recipe_id=test_recipe[1].id,
        product_id=test_product[0].id,
        quantity=1
    )
    db = TestingSessionLocal()
    db.add(recipe_item1)
    db.add(recipe_item2)
    db.add(recipe_item3)
    db.commit()
    yield [recipe_item1, recipe_item2, recipe_item3]
    with engine.connect() as connection:
        connection.execute(text("DELETE FROM recipe_items;"))
        connection.commit()

@pytest.fixture
def test_cart(test_product):
    cart1 = Cart(
        product_id=test_product[0].id,
        owner_id=1,
        quantity=2
    )
    cart2 = Cart(
        product_id=test_product[1].id,
        owner_id=2,
        quantity=10,
        checked=True
    )
    db = TestingSessionLocal()
    db.add(cart1)
    db.add(cart2)
    db.commit()
    yield [cart1, cart2]
    with engine.connect() as connection:
        # Finalizing a cart creates shopping-history rows. Clean them here so
        # later tests start from an isolated in-memory database state.
        connection.execute(text("DELETE FROM shopping_history_items;"))
        connection.execute(text("DELETE FROM shopping_history;"))
        connection.execute(text("DELETE FROM cart;"))
        connection.commit()

@pytest.fixture
def test_user():
    user1 = Users(
    email="test@email.com",
    username="myusername",
    first_name="firstname",
    last_name="lastname",
    hashed_password=test_bcrypt.hash("test"),
    role="admin"
    )
    user2 = Users(
    email="test2@email.com",
    username="myusername2",
    first_name="firstname2",
    last_name="lastname2",
    hashed_password=test_bcrypt.hash("test2"),
    role="admin"
    )
    db = TestingSessionLocal()
    db.add(user1)
    db.add(user2)
    db.commit()
    yield [user1, user2]
    with engine.connect() as connection:
        connection.execute(text("DELETE FROM users;"))
        connection.commit()

@pytest.fixture
def test_shopping_history(test_user):
    history1 = ShoppingHistory(
        user_id=1,
        total_items=3,
        total_price=5.50,
        created_at="2024-01-01T10:00:00"
    )
    history2 = ShoppingHistory(
        user_id=1,
        total_items=1,
        total_price=2.00,
        created_at="2024-01-02T10:00:00"
    )
    db = TestingSessionLocal()
    db.add(history1)
    db.add(history2)
    db.commit()
    yield [history1, history2]
    with engine.connect() as connection:
        connection.execute(text("DELETE FROM shopping_history;"))
        connection.commit()

@pytest.fixture
def test_shopping_history_item(test_shopping_history, test_product):
    history_item1 = ShoppingHistoryItem(
        history_id=1,
        product_id=1,
        name="Onion",
        price_paid=0.62,
        was_discounted=False,
        supermarket_id=1,
        supermarket_name="Conad",
        aisle_order=3.2,
        unit = "pz",
        category="Frutta",
        image="static/images/products/onion.png",
        quantity=3
    )
    history_item2 = ShoppingHistoryItem(
        history_id=1,
        product_id=2,
        name="Garlic",
        price_paid=0.88,
        was_discounted=False,
        supermarket_id=2,
        supermarket_name="Lidl",
        aisle_order=2.5,
        unit = "100g",
        category="Verdura",
        image="static/images/products/garlic.png",
        quantity=5
    )
    db = TestingSessionLocal()
    db.add(history_item1)
    db.add(history_item2)
    db.commit()
    yield [history_item1, history_item2]
    with engine.connect() as connection:
        connection.execute(text("DELETE FROM shopping_history_items;"))
        connection.commit()

