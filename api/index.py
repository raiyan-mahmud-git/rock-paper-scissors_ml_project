"""Vercel Serverless Function entrypoint for FastAPI."""

from rps.web.server import app

# Vercel looks for the `app` instance in `api/index.py`
