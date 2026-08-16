"""WSGI entry point used by Gunicorn/Render."""

from app import create_app


application = create_app("production")
app = application
