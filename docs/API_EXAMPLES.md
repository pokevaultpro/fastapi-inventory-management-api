# API Examples

The API documentation is available locally at `/docs` when the FastAPI server is running.

## Register user

```http
POST /auth
Content-Type: application/json

{
  "username": "demo_user",
  "email": "demo@example.com",
  "first_name": "Demo",
  "last_name": "User",
  "password": "demo-password"
}
```

## Login

```http
POST /auth/token
Content-Type: application/x-www-form-urlencoded

username=demo_user&password=demo-password
```

## Create supermarket

```http
POST /supermarket
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Conad",
  "location": "Matera, Italy"
}
```

## Create product

```http
POST /products
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Pasta",
  "category": "Pasta",
  "original_price": 1.49,
  "discounted_price": null,
  "unit": "500g",
  "supermarket_id": 1,
  "aisle_order": 4.0
}
```

## Add product to cart

```http
POST /cart
Authorization: Bearer <token>
Content-Type: application/json

{
  "product_id": 1,
  "quantity": 2
}
```
