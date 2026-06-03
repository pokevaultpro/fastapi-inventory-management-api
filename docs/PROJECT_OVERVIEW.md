# Project Overview

This project is a FastAPI backend for a supermarket and grocery-management workflow. It was created as a practical backend application rather than a toy CRUD-only app.

## Domain model

The application models:

- users
- supermarkets
- products
- cart items
- favorites
- recipes
- recipe items
- shopping-history records
- shopping-history item snapshots

## Backend concepts demonstrated

- REST API design
- route grouping by domain
- JWT authentication
- password hashing
- SQLAlchemy ORM modelling
- relational database relationships
- Alembic migrations
- FastAPI dependency injection
- test dependency overrides
- in-memory test database setup
- frontend-to-backend API calls

## What I would improve next

- Add response schemas for every endpoint
- Add role-based access control for admin-only mutations
- Replace permissive CORS with environment-specific origins
- Add Docker Compose for API + database
- Add GitHub Actions CI
- Add seed data script for demo usage
- Move toward PostgreSQL as the default production-like database
