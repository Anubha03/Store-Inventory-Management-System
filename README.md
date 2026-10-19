# Store Inventory Management System

A course project for **COMS W4111.001: Introduction to Databases at Columbia University**, implementing a database-backed inventory management web application.

## Features

- Employee login and session-based access to inventory operations.
- Add and delete products, with category and shelf assignments.
- Update stock quantities and record the employee, timestamp, and reason for each movement.
- Search products by name, category, shelf, and low-stock threshold.
- View employee activity logs and product stock history.
- Parameterized SQL queries and form validation for inventory inputs.

## Stack

Python, Flask, SQLAlchemy, PostgreSQL, and server-rendered HTML/Jinja templates.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL='postgresql://username:password@localhost:5432/store_inventory'
python server.py 127.0.0.1 8111
```

Open http://127.0.0.1:8111 and sign in with an employee account from your database. `.env.example` documents the connection variable; the application reads it from the environment and does not automatically load `.env` files.

**Database prerequisite:** This source snapshot does not include schema migrations, table-creation SQL, or seed data. It expects an existing compatible PostgreSQL database containing `Employee`, `Product`, `Category`, `Shelf`, and `Stock_Movement` tables. Provision the original course schema and employee records before running the application.

## Repository layout

- `server.py`: Flask routes, authentication, SQL queries, and stock movement tracking.
- `templates/`: HTML views for login, inventory operations, search, and history.
- `requirements.txt`: runtime dependencies.
- `.env.example`: example database connection configuration.

## Project origin

Course project source imported from [Sans-Shej/StoreInventoryProj](https://github.com/Sans-Shej/StoreInventoryProj). This standalone repository adds documentation and environment-based database configuration, and excludes the bundled virtual environment and machine-specific files.
