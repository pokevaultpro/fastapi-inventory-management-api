from starlette import status
from datetime import datetime, timedelta

from app.models import ShoppingHistory, ShoppingHistoryItem
from test.utils import *
from app.routers.cart import get_db, get_current_user
from app.main import app

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user

def test_get_cart(test_cart):
    response = client.get('/cart')
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [{'product_id': 1, 'quantity': 2,
                               'checked': False, 'id': 1, 'owner_id': 1}]

def test_get_cart_by_supermarket(test_cart):
    response = client.get('/cart?supermarket_id=1')
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [{'product_id': 1, 'quantity': 2,
                               'checked': False, 'id': 1, 'owner_id': 1}]

def test_get_cart_by_supermarket_not_found(test_cart):
    response = client.get('/cart?supermarket_id=9999')
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {'detail': 'Supermarket not found'}

def test_get_cart_by_id(test_cart):
    response = client.get(f'/cart/{test_cart[0].id}')
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {'product_id': 1, 'quantity': 2,
                               'checked': False, 'id': 1, 'owner_id': 1}

def test_get_cart_by_id_not_found(test_cart):
    response = client.get('/cart/9999')
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Cart not found"}

def test_create_cart(test_cart):
    request_data = {'product_id': 3, 'quantity': 1}
    response = client.post('/cart', json=request_data)
    assert response.status_code == status.HTTP_201_CREATED

    created_cart = response.json()
    created_cart_id = created_cart['id']
    db = TestingSessionLocal()
    cart_model = db.query(Cart).filter(Cart.id == created_cart_id).first()
    assert cart_model is not None
    assert cart_model.product_id == request_data["product_id"]
    assert cart_model.quantity == request_data["quantity"]
    assert cart_model.checked == False
    assert cart_model.owner_id == 1

def test_create_cart_duplicate_product(test_cart):
    request_data = {'product_id': 1, 'quantity': 1}
    response = client.post('/cart', json=request_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": "Product already in cart"}

def test_create_cart_product_not_found(test_cart):
    request_data = {'product_id': 9999, 'quantity': 1}
    response = client.post('/cart', json=request_data)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Product not found"}

    db = TestingSessionLocal()
    cart_model = db.query(Cart).filter(Cart.product_id == 9999).first()
    assert cart_model is None

def test_create_shopping_history(test_cart):
    # The finalize endpoint only archives checked cart items.
    # Mark the current user's cart item as checked before finalizing.
    check_response = client.put(f'/cart/{test_cart[0].id}', json={'checked': True})
    assert check_response.status_code == status.HTTP_204_NO_CONTENT

    response = client.post('/cart/finalize')
    assert response.status_code == status.HTTP_201_CREATED
    db = TestingSessionLocal()
    shopping_history_model = db.query(ShoppingHistory).filter(ShoppingHistory.id == 1).first()
    assert shopping_history_model is not None

    created_at = datetime.fromisoformat(shopping_history_model.created_at)
    now = datetime.utcnow()

    assert abs(now - created_at) < timedelta(seconds=5)
    assert shopping_history_model.total_items == 2
    assert shopping_history_model.total_price == 1.24
    assert shopping_history_model.user_id == 1

    shopping_history_item_model = db.query(ShoppingHistoryItem).filter(ShoppingHistoryItem.id == 1).first()
    assert shopping_history_item_model is not None
    assert shopping_history_item_model.id == 1
    assert shopping_history_item_model.product_id == 1
    assert shopping_history_item_model.supermarket_id == 1
    assert shopping_history_item_model.supermarket_name == "Conad"

    cart_model = db.query(Cart).filter(Cart.id == 1).first()
    assert cart_model is None

def test_update_all_cart(test_cart):
    request_data = {'quantity': 15, 'checked': True}
    response = client.put(f'/cart/{test_cart[0].id}', json=request_data)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    db = TestingSessionLocal()
    cart_model = db.query(Cart).filter(Cart.id == test_cart[0].id).first()
    assert cart_model is not None
    assert cart_model.quantity == request_data["quantity"]
    assert cart_model.checked == request_data["checked"]

def test_update_quantity_cart(test_cart):
    request_data = {'quantity': 15}
    response = client.put(f'/cart/{test_cart[0].id}', json=request_data)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    db = TestingSessionLocal()
    cart_model = db.query(Cart).filter(Cart.id == test_cart[0].id).first()
    assert cart_model is not None
    assert cart_model.quantity == request_data["quantity"]
    assert cart_model.checked == False

def test_update_checked_cart(test_cart):
    request_data = {'checked': True}
    response = client.put(f'/cart/{test_cart[0].id}', json=request_data)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    db = TestingSessionLocal()
    cart_model = db.query(Cart).filter(Cart.id == test_cart[0].id).first()
    assert cart_model is not None
    assert cart_model.quantity == 2
    assert cart_model.checked == request_data["checked"]

def test_update_nothing_cart(test_cart):
    request_data = {}
    response = client.put(f'/cart/{test_cart[0].id}', json=request_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": "You must update at least one field"}

    db = TestingSessionLocal()
    cart_model = db.query(Cart).filter(Cart.id == test_cart[0].id).first()
    assert cart_model is not None
    assert cart_model.quantity == 2
    assert cart_model.checked == False

def test_update_cart_not_found(test_cart):
    request_data = {'quantity': 15, 'checked': True}
    response = client.put('/cart/9999', json=request_data)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Cart not found"}

def test_delete_cart(test_cart):
    response = client.delete(f'/cart/{test_cart[0].id}')
    assert response.status_code == status.HTTP_204_NO_CONTENT
    db = TestingSessionLocal()
    cart_model = db.query(Cart).filter(Cart.id == test_cart[0].id).first()
    assert cart_model is None

def test_delete_cart_not_found(test_cart):
    response = client.delete('/cart/9999')
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Cart not found"}

def test_delete_all_cart(test_cart):
    response = client.delete('/cart')
    assert response.status_code == status.HTTP_204_NO_CONTENT

    db = TestingSessionLocal()
    cart_model = db.query(Cart).filter(Cart.owner_id == 1).all()
    assert cart_model == []

def test_delete_cart_by_supermarket_id(test_cart):
    db = TestingSessionLocal()
    cart_model1 = db.query(Cart).filter(Cart.owner_id == 1).all()
    assert len(cart_model1) == 1
    response = client.delete('/cart?supermarket_id=1')
    assert response.status_code == status.HTTP_204_NO_CONTENT
    cart_model2 = db.query(Cart).filter(Cart.owner_id == 1).all()
    assert len(cart_model2) == 0

def test_delete_cart_by_checked_product(test_cart):
    db = TestingSessionLocal()
    cart_model1 = db.query(Cart).filter(Cart.owner_id == 1).all()
    assert len(cart_model1) == 1
    response = client.delete('/cart?checked=False')
    assert response.status_code == status.HTTP_204_NO_CONTENT
    cart_model2 = db.query(Cart).filter(Cart.owner_id == 1).all()
    assert len(cart_model2) == 0

def test_delete_cart_by_supermarket_id_and_checked_product(test_cart):
    db = TestingSessionLocal()
    cart_model1 = db.query(Cart).filter(Cart.owner_id == 1).all()
    assert len(cart_model1) == 1
    response = client.delete('/cart?supermarket_id=1&checked=False')
    assert response.status_code == status.HTTP_204_NO_CONTENT
    cart_model2 = db.query(Cart).filter(Cart.owner_id == 1).all()
    assert len(cart_model2) == 0

def test_delete_cart_by_supermarket_id_not_found(test_cart):
    response = client.delete('/cart?supermarket_id=9999')
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Supermarket not found"}