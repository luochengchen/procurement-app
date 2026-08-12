"""Certification query module — look up product certification requirements."""
from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request
from database import get_session
from models import Certification

certification_bp = Blueprint("certification", __name__, template_folder="../../templates")


@certification_bp.route("/certification")
def page() -> str:
    session = get_session()
    try:
        from sqlalchemy import distinct
        categories = [row[0] for row in session.query(distinct(Certification.product_category)).all()]
        countries = [row[0] for row in session.query(distinct(Certification.target_country)).all()]
        return render_template("certification.html", categories=categories, countries=countries)
    finally:
        session.close()


@certification_bp.route("/api/certification")
def api_query():
    session = get_session()
    try:
        product = request.args.get("product", "").strip()
        country = request.args.get("country", "").strip()

        query = session.query(Certification)
        if product:
            query = query.filter(Certification.product_category.ilike(f"%{product}%"))
        if country:
            query = query.filter(Certification.target_country.ilike(f"%{country}%"))

        certifications = query.order_by(Certification.target_country, Certification.product_category).all()
        return jsonify([c.to_dict() for c in certifications])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()


@certification_bp.route("/api/certification/external")
def api_external():
    return jsonify({
        "error": "外部认证API尚未接入",
        "message": "此接口预留给第三方认证数据库/监管API集成",
        "planned_integrations": [
            "欧盟 CE/RoHS/REACH 官方数据库",
            "美国 FCC/FDA/UL 产品分类查询",
            "日本 PSE/METI 认证要求",
            "沙特 SABER/SASO 认证平台",
            "海关 HS Code → 认证要求映射",
        ],
        "request_format": {"product": "产品名称/类别", "country": "目标市场国家", "hs_code": "海关编码 (optional)"},
        "response_format": {"certifications": [{"name": "认证名称", "body": "认证机构", "mandatory": True}]},
        "status": "not_implemented",
    }), 501
