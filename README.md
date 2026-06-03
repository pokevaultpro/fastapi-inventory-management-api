# FastAPI Inventory Management API

A backend portfolio project for managing supermarket products, grocery lists, favorites, recipes, carts, users, and shopping-history workflows.

The project is built around a Python/FastAPI REST API with SQLAlchemy models, Alembic migrations, JWT authentication, automated tests, and a small static frontend used to exercise the backend from the browser.

## Why this project matters

This project demonstrates the kind of backend work I enjoy: designing API endpoints, modelling relational data, validating requests, connecting application logic to a database, handling authentication, and testing business workflows.

## Features

- User registration and JWT login
- Product and supermarket management
- Cart and shopping-list workflows
- Favorites
- Recipes and recipe items
- Shopping-history creation, item snapshots, and cart restoration
- SQLAlchemy ORM models
- Alembic database migrations
- Pytest-based API tests
- Static HTML/CSS/JavaScript frontend for manual testing

## Tech stack

- Python
- FastAPI
- SQLAlchemy
- Alembic
- Pydantic
- SQLite for local development
- JWT authentication with `python-jose`
- Password hashing with `passlib[bcrypt]`
- Pytest
- HTML/CSS/JavaScript basics

## Repository structure

```text
app/
  main.py              FastAPI application setup and router registration
  database.py          SQLAlchemy engine/session configuration
  models.py            ORM models
  routers/             API routes grouped by domain
alembic/               Database migration setup and versions
frontend/              Lightweight static frontend for manual API usage
test/                  Automated API tests and fixtures
main.py                ASGI entrypoint for uvicorn
```

## Local setup

### 1. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

For normal app usage:

```bash
pip install -r requirements.txt
```

For running the automated tests as well:

```bash
pip install -r requirements-dev.txt
```

### 3. Create environment file

```bash
cp .env.example .env
```

The default `.env.example` uses SQLite:

```env
DATABASE_URL=sqlite:///./shoppinglist.db
SECRET_KEY=change-me-in-production
```

### 4. Run database migrations

```bash
alembic upgrade head
```

### 5. Run the API

```bash
uvicorn main:app --reload
```

Open the interactive API docs at:

```text
http://127.0.0.1:8000/docs
```

## Running tests

Install the development dependencies first:

```bash
pip install -r requirements-dev.txt
```

Then run:

```bash
pytest
```

The tests use an in-memory SQLite database and FastAPI dependency overrides, so they do not require your local `shoppinglist.db`.

## Example API flow

1. Register a user with `POST /auth`
2. Login with `POST /auth/token`
3. Use the bearer token to call protected endpoints
4. Create supermarkets and products
5. Add products to cart
6. Finalize checked cart items into shopping history
7. Restore a previous shopping history back into the cart

## Security and portfolio notes

- `.env`, local SQLite databases, virtual environments, IDE files, and Python caches are intentionally excluded from version control.
- The JWT secret is read from the `SECRET_KEY` environment variable.
- Large product image assets were omitted from this portfolio-ready snapshot to keep the repository lightweight.
- The frontend is intentionally simple; the focus of this project is backend/API development.

## Suggested CV description

**FastAPI Inventory Management API**

Built a FastAPI backend for supermarket/product, cart, recipe, favorites, user-authentication, and shopping-history workflows. Implemented REST endpoints, SQLAlchemy models, Alembic migrations, JWT authentication, database persistence, and automated API tests.

## Troubleshooting

### `ModuleNotFoundError: No module named 'dotenv'`

The import name is `dotenv`, but the package name is `python-dotenv`. Make sure your virtual environment is active and reinstall the project dependencies:

```powershell
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

Or install the missing package directly:

```powershell
pip install python-dotenv
```

### `MissingBackendError: bcrypt: no backends available`

If tests fail with a bcrypt backend error, install dependencies again inside the active virtual environment:

```powershell
python -m pip install -r requirements-dev.txt
python -m pip show bcrypt
python -m pytest -v
```

Expected result after installing the dev requirements: `104 passed`.

```bash
```

The important package is `bcrypt`; `passlib[bcrypt]` uses it as the hashing backend.
