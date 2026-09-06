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
        regions = [r[0] for r in session.query(Material.region).distinct().order_by(Material.region).all()]
        return render_template(
            "materials.html",
            categories=[c.to_dict() for c in categories],
            regions=regions,
        )
    finally:
        session.close()


@materials_bp.route("/api/materials")
def api_list():
    """Search/filter materials. Query params: q, category, region, sort."""
    session = get_session()
    try:
        q = request.args.get("q", "").strip()
        category = request.args.get("category", "").strip()
        region = request.args.get("region", "").strip()
        sort = request.args.get("sort", "name")  # name / price_asc / price_desc / date

        query = session.query(Material)

        if q:
            query = query.filter(
                Material.name.ilike(f"%{q}%") | Material.spec.ilike(f"%{q}%")
            )
        if category:
            query = query.join(MaterialCategory).filter(MaterialCategory.name == category)
        if region:
            query = query.filter(Material.region == region)

        if sort == "price_asc":
            query = query.order_by(Material.current_price.asc())
        elif sort == "price_desc":
            query = query.order_by(Material.current_price.desc())
        elif sort == "date":
            query = query.order_by(Material.price_date.desc())
        else:
            query = query.order_by(Material.name.asc())

        materials = query.limit(500).all()
        ids = [m.id for m in materials]

        # 一次性取这些材料的最近走势（升序，每材料保留末 6 期），避免 N+1 查询
        spark: dict[int, list[float]] = {}
        if ids:
            rows = (
                session.query(PriceHistory.material_id, PriceHistory.price)
                .filter(PriceHistory.material_id.in_(ids))
                .order_by(PriceHistory.recorded_date.asc())
                .all()
            )
            for mid, price in rows:
                bucket = spark.setdefault(mid, [])
                bucket.append(price)
                if len(bucket) > 6:
                    bucket.pop(0)

        result = []
        for m in materials:
            d = m.to_dict()
            d["spark"] = spark.get(m.id, [])
            result.append(d)
        return jsonify(result)
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
