"""Procurement App — cross-border e-commerce procurement web application."""
from __future__ import annotations

import os

from flask import Flask, jsonify

from config import UPLOAD_DIR
from database import init_db

app = Flask(__name__)

# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Initialize database and seed data (runs on import, required for gunicorn)
init_db()
from database import get_session
from models import MaterialCategory
_session = get_session()
try:
    if _session.query(MaterialCategory).count() == 0:
        from seed_data import seed_categories, seed_materials, seed_certifications
        _cat_ids = seed_categories(_session)
        seed_materials(_session, _cat_ids)
        seed_certifications(_session)
finally:
    _session.close()


# ---------------------------------------------------------------------------
# Register blueprints
# ---------------------------------------------------------------------------
from modules.dashboard import dashboard_bp
from modules.materials import materials_bp
from modules.calculator import calculator_bp
from modules.image_search import image_search_bp
from modules.certification import certification_bp
from modules.factory import factory_bp
from modules.competitor import competitor_bp

app.register_blueprint(dashboard_bp)
app.register_blueprint(materials_bp)
app.register_blueprint(calculator_bp)
app.register_blueprint(image_search_bp)
app.register_blueprint(certification_bp)
app.register_blueprint(factory_bp)
app.register_blueprint(competitor_bp)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.route("/api/ping")
def api_ping():
    return jsonify({"status": "ok", "msg": "server is running"})


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
