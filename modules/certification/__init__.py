"""Certification query module — look up product certification requirements."""
from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request
from database import get_session
from models import Certification

certification_bp = Blueprint("certification", __name__, template_folder="../../templates")


# 产品关键词 → 认证产品类别 映射（用于识图/关键词自动匹配）
CATEGORY_KEYWORDS = {
    "运动器材": ["跑步机", "健身", "哑铃", "瑜伽", "杠铃", "单杠", "单车", "椭圆机", "运动", "球", "跳绳", "仰卧板", "拉力器"],
    "户外家具": ["户外", "桌椅", "沙发", "遮阳伞", "凉亭", "躺椅", "藤编", "庭院", "茶几", "遮阳", "露营"],
    "园艺工具": ["园艺", "剪刀", "花盆", "喷壶", "割草机", "铲", "浇花", "植物", "草坪", "篱笆"],
    "玩具": ["玩具", "积木", "娃娃", "毛绒", "拼图", "遥控", "橡皮泥", "玩偶"],
    "电子产品": ["电子", "手机", "耳机", "充电", "蓝牙", "usb", "pcb", "电池", "音箱", "数据线", "适配器", "开关", "连接器", "芯片", "模组"],
    "纺织品": ["纺织", "面料", "毛巾", "床品", "布", "服装", "毯", "摇粒绒", "帆布", "牛津布", "被套"],
    "食品接触材料": ["保温杯", "餐具", "饭盒", "水杯", "厨具", "食品接触", "保鲜盒", "水壶", "婴儿奶瓶"],
    "医疗器械": ["医疗", "口罩", "体温计", "血压计", "器械", "轮椅", "制氧机"],
}


def match_category(keyword: str) -> str:
    """根据产品关键词匹配认证产品类别，无法匹配返回空串。"""
    kw = (keyword or "").lower()
    for category, words in CATEGORY_KEYWORDS.items():
        if any(w in kw for w in words):
            return category
    return ""


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
    """查询认证。参数: product(类别) / country(市场) / q(产品关键词，识图联动)。"""
    session = get_session()
    try:
        product = request.args.get("product", "").strip()
        country = request.args.get("country", "").strip()
        q = request.args.get("q", "").strip()

        # 关键词匹配（识图联动）：q 存在且未显式选类别时，映射到产品类别
        matched_category = ""
        if q and not product:
            matched_category = match_category(q)
            product = matched_category

        query = session.query(Certification)
        if product:
            query = query.filter(Certification.product_category.ilike(f"%{product}%"))
        if country:
            query = query.filter(Certification.target_country.ilike(f"%{country}%"))

        certifications = query.order_by(Certification.target_country, Certification.product_category).all()
        return jsonify({
            "matched_category": matched_category,
            "certifications": [c.to_dict() for c in certifications],
        })
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
