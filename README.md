# Karsoogh Backend

A Django-based backend API for the Karsoogh website, built with **Django REST Framework** and managed by **PDM**. 

##  Tech Stack

* **Framework:** Django 6.0+ & Django REST Framework
* **Package Manager:** PDM
* **Authentication:** JWT (Simple JWT)
* **API Documentation:** drf-spectacular (OpenAPI/Swagger)
* **Server:** Gunicorn & WhiteNoise (for static files)
* **Code Quality:** Ruff (Linting) & Black (Formatting)


##  Local Development Setup

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/karsoogh-mehregan/karsoogh-backend.git](https://github.com/karsoogh-mehregan/karsoogh-backend.git)
    cd karsoogh-backend
    ```

2.  **Install dependencies using PDM:**
    ```bash
    pdm install --dev
    ```

3.  **Environment Configuration:**
    Copy the example environment file and configure it:
    ```bash
    cp .env.example .env
    ```
    * Update `DJANGO_SECRET_KEY` and database settings in `.env`.
    * Set `DJANGO_DEBUG=True` for local development.

4.  **Apply Migrations:**
    ```bash
    pdm run python manage.py migrate
    ```

5.  **Run the Development Server:**
    ```bash
    pdm run python manage.py runserver
    ```
