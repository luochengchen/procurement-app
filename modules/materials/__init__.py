"""Materials query module — search, filter, and browse material prices."""
from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request
from database import get_session
from models import Material, MaterialCategory, PriceHistory

materials_bp = Blueprint("materials", __name__, template_folder="../../templates")


@materials_bp.route("/materials")
def page() -> str:
    """Render the materials query page."""
    session = get_session()
    try:
        categories = session.query(MaterialCategory).order_by(MaterialCategory.sort_order).all()
        return render_template("materials.html", categories=[c.to_dict() for c in categories])
    finally:
        session.close()


@materials_bp.route("/api/materials")
def api_list():
    """Search/filter materials. Query params: q, category, sort."""
    session = get_session()
    try:
        q = request.args.get("q", "").strip()
        category = request.args.get("category", "").strip()
        sort = request.args.get("sort", "name")  # name / price_asc / price_desc / date

        query = session.query(Material)

        if q:
            query = query.filter(
                Material.name.ilike(f"%{q}%") | Material.spec.ilike(f"%{q}%")
            )
        if category:
            query = query.join(MaterialCategory).filter(MaterialCategory.name == category)

        if sort == "price_asc":
            query = query.order_by(Material.current_price.asc())
        elif sort == "price_desc":
            query = query.order_by(Material.current_price.desc())
        elif sort == "date":
            query = query.order_by(Material.price_date.desc())
        else:
            query = query.order_by(Material.name.asc())

        materials = query.limit(100).all()
        return jsonify([m.to_dict() for m in materials])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()


@materials_bp.route("/api/materials/stats")
def api_stats():
    """Aggregate material count and avg price by category."""
    session = get_session()
    try:
        from sqlalchemy import func
        rows = (
            session.query(
                MaterialCategory.name, MaterialCategory.icon,
                func.count(Material.id), func.avg(Material.current_price),
            )
            .outerjoin(Material, Material.category_id == MaterialCategory.id)
            .group_by(MaterialCategory.id)
            .order_by(MaterialCategory.sort_order)
            .all()
        )
        return jsonify([
            {
                "category": name,
                "icon": icon,
                "count": count,
                "avg_price": round(avg or 0, 2),
            }
            for name, icon, count, avg in rows
        ])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()


@materials_bp.route("/api/materials/<int:material_id>/history")
def api_price_history(material_id: int):
    """Get price history for a specific material."""
    session = get_session()
    try:
        history = (
            session.query(PriceHistory)
            .filter(PriceHistory.material_id == material_id)
            .order_by(PriceHistory.recorded_date.desc())
            .limit(30)
            .all()
        )
        return jsonify([h.to_dict() for h in history])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()
