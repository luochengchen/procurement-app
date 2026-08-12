"""Dashboard module — home page with featured material prices."""
from __future__ import annotations

from flask import Blueprint, jsonify, render_template
from database import get_session
from models import Material

dashboard_bp = Blueprint("dashboard", __name__, template_folder="../../templates")


@dashboard_bp.route("/")
def index() -> str:
    """Render the main dashboard page."""
    return render_template("index.html")


@dashboard_bp.route("/api/materials/featured")
def api_featured_materials():
    """Return featured materials for the dashboard cards."""
    session = get_session()
    try:
        materials = session.query(Material).order_by(Material.price_date.desc()).limit(12).all()
        return jsonify([m.to_dict() for m in materials])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()
