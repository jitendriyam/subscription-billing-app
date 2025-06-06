import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./subscription_billing.db")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://127.0.0.1:6379/0")

PLANS_DATA = [
    {"name": "Basic", "price": 10.00, "description": "Basic monthly plan"},
    {
        "name": "Pro",
        "price": 25.00,
        "description": "Pro monthly plan with more features",
    },
    {
        "name": "Enterprise",
        "price": 75.00,
        "description": "Enterprise plan for large teams",
    },
]

landing_page_html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Subscription Billing API</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Open Sans", "Helvetica Neue", sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 40px auto;
                padding: 20px;
                background-color: #f4f4f4;
                border-radius: 8px;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
            }
            h1 {
                color: #2c3e50;
                text-align: center;
            }
            p {
                font-size: 1.1em;
                margin-bottom: 1em;
            }
            .links {
                text-align: center;
                margin-top: 30px;
            }
            .links a {
                display: inline-block;
                background-color: #3498db;
                color: white;
                padding: 12px 25px;
                text-decoration: none;
                border-radius: 5px;
                font-size: 1.1em;
                margin: 0 10px;
                transition: background-color 0.3s ease;
            }
            .links a:hover {
                background-color: #2980b9;
            }
            .footer {
                text-align: center;
                margin-top: 40px;
                font-size: 0.9em;
                color: #777;
            }
        </style>
    </head>
    <body>
        <h1>Welcome to the Subscription Billing API!</h1>
        <p>This is the backend service for managing user subscriptions, plans, and automated invoicing.</p>
        <p>
            Our system handles user sign-ups, allows users to subscribe to predefined plans (Basic, Pro, Enterprise),
            and uses Celery for background tasks like generating monthly invoices, marking unpaid invoices,
            and sending mock payment reminders.
        </p>
        <p>To explore the available API endpoints and interact with the system, please visit our documentation pages:</p>
        <div class="links">
            <a href="/docs">API Documentation (Swagger UI)</a>
            <a href="/redoc">Alternative Documentation (ReDoc)</a>
        </div>
        <div class="footer">
            <p>Subscription Billing Backend v0.1.0</p>
        </div>
    </body>
    </html>
    """
