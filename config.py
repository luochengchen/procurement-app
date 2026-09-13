"""Application configuration."""
from __future__ import annotations

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Render free tier: project directory is read-only, use /tmp for writable files.
# Local development: use project directory.
IS_RENDER = os.environ.get("RENDER", "") == "true"
_WRITABLE_DIR = "/tmp" if IS_RENDER else BASE_DIR

# Database
DATABASE_PATH = os.environ.get("DATABASE_PATH", os.path.join(_WRITABLE_DIR, "data.db"))

# Upload
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", os.path.join(_WRITABLE_DIR, "uploads"))
MAX_UPLOAD_SIZE_MB = 10
ALLOWED_IMAGE_TYPES = {"png", "jpg", "jpeg", "webp", "bmp"}

# Image search (reserved for external API)
IMAGE_SEARCH_API_URL = os.environ.get("IMAGE_SEARCH_API_URL", "")
IMAGE_SEARCH_API_KEY = os.environ.get("IMAGE_SEARCH_API_KEY", "")

# 图片识别（视觉模型）：OpenAI 兼容协议，留空则不做 AI 识图、只按用户填的关键词检索。
# 例：VISION_API_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
#     VISION_MODEL=qwen-vl-max
VISION_API_URL = os.environ.get("VISION_API_URL", "")
VISION_API_KEY = os.environ.get("VISION_API_KEY", "")
VISION_MODEL = os.environ.get("VISION_MODEL", "")

# Certification external API (reserved)
CERTIFICATION_API_URL = os.environ.get("CERTIFICATION_API_URL", "")
CERTIFICATION_API_KEY = os.environ.get("CERTIFICATION_API_KEY", "")

# Factory data API（主：天眼查；保底：Apizero）
TIANYANCHA_TOKEN = os.environ.get("TIANYANCHA_TOKEN", "")  # 天眼查开放平台 token，免费 500 次/天
APIZERO_API_KEY = os.environ.get("APIZERO_API_KEY", "")    # Apizero 可选，匿名 20 次/天保底

# Currency
DEFAULT_CURRENCY = "CNY"
SUPPORTED_CURRENCIES = ["CNY", "USD", "EUR", "JPY", "KRW"]
