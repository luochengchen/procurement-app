"""Application configuration."""
from __future__ import annotations

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Database
DATABASE_PATH = os.path.join(BASE_DIR, "data.db")

# Upload
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
MAX_UPLOAD_SIZE_MB = 10
ALLOWED_IMAGE_TYPES = {"png", "jpg", "jpeg", "webp", "bmp"}

# Image search (reserved for external API)
IMAGE_SEARCH_API_URL = os.environ.get("IMAGE_SEARCH_API_URL", "")
IMAGE_SEARCH_API_KEY = os.environ.get("IMAGE_SEARCH_API_KEY", "")

# Certification external API (reserved)
CERTIFICATION_API_URL = os.environ.get("CERTIFICATION_API_URL", "")
CERTIFICATION_API_KEY = os.environ.get("CERTIFICATION_API_KEY", "")

# Currency
DEFAULT_CURRENCY = "CNY"
SUPPORTED_CURRENCIES = ["CNY", "USD", "EUR", "JPY", "KRW"]
