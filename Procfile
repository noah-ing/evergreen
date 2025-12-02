# Procfile for Railway/Heroku-style deployments
release: alembic upgrade head
web: uvicorn evergreen.api.main:app --host 0.0.0.0 --port ${PORT:-8000}
