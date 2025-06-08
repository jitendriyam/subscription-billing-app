# Subscription Billing Backend

This project implements a basic subscription billing backend using FastAPI and Celery. It supports user sign-up, predefined subscription plans, automatic monthly invoice generation, billing lifecycle tracking, and mock integrations for email reminders and Stripe payments.

## 🌟 Objective

To design and build a foundational backend system capable of managing user subscriptions to various service plans and automating the core billing processes like invoicing and overdue payment handling.

## 🛠️ Features

*   **User Management:** Sign-up and basic user profiles.
*   **Subscription Plans:** Predefined plans (Basic, Pro, Enterprise) with different pricing.
*   **Subscription Lifecycle:** Users can subscribe to and unsubscribe from plans. Subscriptions track start/end dates and status (active, cancelled, expired).
*   **Automated Invoice Generation:** Celery tasks generate monthly invoices for active subscriptions.
*   **Invoice Management:** Invoices track user, plan, amount, issue/due dates, and payment status (pending, paid, overdue).
*   **Celery for Background Tasks:**
    *   Generates initial invoices upon new subscriptions.
    *   Periodically generates renewal invoices.
    *   Periodically marks unpaid invoices as overdue.
    *   Periodically sends mock payment reminders for pending/overdue invoices.
*   **API Endpoints:**
    *   User registration.
    *   Subscribing/unsubscribing from plans.
    *   Viewing user subscriptions.
    *   Viewing user invoices and their payment status.
    *   Mock payment processing for invoices.
*   **Database:** SQLite for simplicity.
*   **Mock Integrations:**
    *   Console-printed mock email reminders.
    *   Mock Stripe payment processing.

## ⚙️ Tech Stack

*   **Backend Framework:** FastAPI
*   **Asynchronous Task Queue:** Celery
*   **Message Broker (for Celery):** Redis
*   **Database ORM:** SQLAlchemy
*   **Database:** SQLite
*   **Environment & Dependency Management:** `uv`
*   **Containerization:** Docker

## 🚀 Getting Started

### Prerequisites

*   **Python 3.10+**
*   **`uv` (Python package installer and resolver)**: If not installed, see [uv installation guide](https://github.com/astral-sh/uv#installation).
*   **Redis:** Running and accessible (default `redis://127.0.0.1:6379/0`).
    *   If using WSL on Windows, ensure Redis is running within WSL and accessible from Windows.
*   **Docker :** For containerized deployment.

### Local Development Setup (using `uv`)

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/jitendriyam/subscription-billing-app.git
    cd subscription-billing-backend # Or your project's root directory
    ```

2.  **Create and Activate Virtual Environment with `uv`:**
    ```bash
    uv venv  # Creates a virtual environment 
    source .venv/bin/activate  # On Linux/macOS
    .venv\Scripts\activate    # On Windows (Command Prompt)
    .venv\Scripts\Activate.ps1 # On Windows (PowerShell)
    ```

3.  **Install Dependencies using `uv sync`:**
    This command installs dependencies exactly as specified in `uv.lock`, ensuring a reproducible environment.
    ```bash
    uv sync --frozen
    ```

4.  **Set up Environment Variables (Optional but Recommended):**
    Create a `.env` file in the project root directory (same level as `pyproject.toml`):
    ```env
    DATABASE_URL="sqlite:///./subscription_billing.db"
    CELERY_BROKER_URL="redis://127.0.0.1:6379/0"
    CELERY_RESULT_BACKEND="redis://127.0.0.1:6379/0"
    ```
    The application will use default values if this file is not present.

5.  **Run Database Migrations (Table Creation):**
    The application creates tables on startup if they don't exist. The first time you run the FastAPI app, tables will be created based on `app/models.py`.

6.  **Seed Initial Data (Plans):**
    Once the FastAPI application is running (see next step), you can seed the predefined subscription plans:
    *   Open your browser or Postman to `http://127.0.0.1:8000/docs`.
    *   Execute the `POST /seed-plans/` endpoint.

7.  **Run the Services:**
    You need to run three separate processes, typically in different terminal windows/tabs (ensure your virtual environment is activated in each).

    *   **Start Redis Server (if not already running globally):**
        ```bash
        sudo service redis-server start
        redis-cli
        ```
        (Command might vary based on your Redis installation)

    *   **Start Celery Worker:**
        (From the project root directory)
        ```bash
        celery -A app.celery_worker.celery_app worker -l info
        celery -A app.celery_worker.celery_app worker -l info --pool=solo #only try if you face any issue with above command
        ```

    *   **Start Celery Beat (Scheduler for periodic tasks):**
        (From the project root directory)
        ```bash
        celery -A app.celery_worker.celery_app beat -l info
        ```

    *   **Start FastAPI Application:**
        (From the project root directory)
        ```bash
        uvicorn app.main:app --reload
        ```

8.  **Access the API:**
    The API will be available at `http://127.0.0.1:8000`.
    Interactive API documentation (Swagger UI) is at `http://120.0.0.1:8000/docs`.
    Alternative API documentation (ReDoc) is at `http://120.0.0.1:8000/redoc`.

### Docker Setup 

If you want to use `Dockerfile` :

1.  **Build the Docker Image:**
    ```bash
    docker build -t subscription-billing-app .
    ```

2.  **Run using Docker :**
    If running the app container standalone, you'll need to ensure it can connect to Redis.
    ```bash
    docker run -d -p 8000:8000 subscription-billing-app
    ```
    *(You would also need to run Celery worker and beat containers similarly, configured to connect to the same Redis instance.)*

    ```bash
    docker run -e SERVICE=celery-combined subscription-billing-app
    ```

    

## 🌊 Business Flow Overview

This system simulates a typical subscription model:

1.  **User Onboarding:**
    *   A potential customer signs up for an account (`POST /users/`).

2.  **Plan Selection & Subscription:**
    *   The user browses available subscription plans (`GET /plans/`).
    *   The user chooses a plan and subscribes (`POST /users/{user_id}/subscribe/`).
    *   Upon successful subscription:
        *   A `Subscription` record is created with `status: active` and a `start_date`.
        *   The `next_billing_date` is set to the `start_date` (for immediate first billing).
        *   A Celery task (`generate_initial_invoice_task`) is triggered **asynchronously** to create the first `Invoice`.

3.  **Initial Invoice Generation (Async):**
    *   The Celery worker picks up the task.
    *   An `Invoice` is generated with `status: pending`, an `issue_date` (today), and a `due_date` (e.g., 15 days from issue).
    *   The `Subscription`'s `next_billing_date` is updated to one month from the current billing date.

4.  **Recurring Billing Cycle (Automated by Celery Beat & Worker):**
    *   **Daily Invoice Generation:** A periodic Celery task (`generate_renewal_invoices_task`) runs daily (e.g., at 1:00 AM UTC).
        *   It queries for active subscriptions whose `next_billing_date` is today.
        *   For each such subscription, a new `Invoice` is created (status: `pending`).
        *   The subscription's `next_billing_date` is advanced by one month.
    *   **Overdue Invoice Marking:** Another periodic Celery task (`mark_overdue_invoices_task`) runs daily (e.g., at 2:00 AM UTC).
        *   It finds `pending` invoices whose `due_date` has passed.
        *   It updates their status to `overdue`.
    *   **Payment Reminders:** A third periodic Celery task (`send_payment_reminders_task`) runs daily (e.g., at 3:00 AM UTC).
        *   It finds `pending` invoices nearing their `due_date` or `overdue` invoices.
        *   It sends a mock email reminder (prints to console).

5.  **Invoice Viewing & Payment:**
    *   Users can view their invoices and payment statuses (`GET /users/{user_id}/invoices/`).
    *   Users can "pay" an invoice (`POST /invoices/{invoice_id}/pay/`). This uses a mock Stripe integration.
        *   If mock payment is successful, the invoice status is updated to `paid` and `paid_at` is recorded.

6.  **Subscription Management:**
    *   Users can view their active subscriptions (`GET /users/{user_id}/subscriptions/`).
    *   Users can cancel their subscriptions (`PUT /subscriptions/{subscription_id}/cancel/`).
        *   The subscription status is set to `cancelled`.
        *   The `end_date` is recorded.
        *   Future invoice generation for this subscription stops.

## 📂 Project Structure


    subscription_billing/
    ├── app/
    │ ├── __init__.py
    │ ├── main.py # FastAPI app setup, routers, main API logic
    │ ├── models.py # SQLAlchemy database models
    │ ├── schemas.py # Pydantic schemas for data validation & serialization
    │ ├── crud.py # CRUD (Create, Read, Update, Delete) database operations
    │ ├── database.py # Database engine and session setup
    │ ├── celery_worker.py # Celery application setup and task definitions
    │ ├── config.py # Configuration settings (DB URLs, Celery URLs, Plan data)
    │ └── utils.py # Utility functions (password hashing, date calculations, mocks)
    ├── .env.example # Example environment variables file
    ├── pyproject.toml # Project metadata and dependencies for uv
    ├── uv.lock # Pinned versions of all dependencies by uv
    ├── requirements.txt 
    ├── Dockerfile
    └── README.md # This file

## 🧪 Testing

1.  **Unit/Integration Tests:** (Placeholder - To be added. Frameworks like `pytest` would be suitable).
2.  **Manual API Testing:**
    *   Use the Swagger UI at `http://127.0.0.1:8000/docs`.
    *   Use tools like Postman or `curl`.
3.  **Celery Task Testing:**
    *   To test periodic tasks more rapidly, you can adjust the `crontab` schedules in `app/celery_worker.py` to run every minute (e.g., `crontab()`).
    *   **Remember to restart Celery Beat and Worker after changing schedules.**
    *   Monitor the console output of the Celery worker for task execution logs.

---
