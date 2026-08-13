"""Factory matching module — search factories by product, scale, region, revenue.

数据源（预留）：当前为内置模拟数据。后续接入：
  - 1688 工厂 API `alibaba.icbu.company.get`（item_get_factory）：主营产品、厂房面积、
    员工规模、年营业额、产能、认证 —— 唯一同时覆盖「规模/地址/年销售额/产品」四字段。
  - 天眼查/企查查工商 API：经营范围、注册地址、注册资本（主体校验补充）。
"""
from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request

factory_bp = Blueprint("factory", __name__, template_folder="../../templates")


# 模拟工厂库：(厂名, 行业, 地区, 员工数, 厂房面积㎡, 年销售额万元, 主营产品, 工艺, 认证, 出口市场)
_FACTORY_ROWS = [
    ("宁波精工五金制造有限公司", "五金配件", "浙江 宁波", 150, 8000, 12000,
     ["螺丝", "螺母", "垫片", "铆钉", "角码"], ["冷镦", "冲压", "搓丝", "电镀"],
     ["ISO9001", "SGS", "深度验厂"], ["欧盟", "美国", "东南亚"]),
    ("永康市五金配件厂", "五金配件", "浙江 金华", 80, 3500, 5000,
     ["合页", "滑轨", "脚轮", "拉手", "锁具"], ["冲压", "压铸", "抛光"],
     ["ISO9001"], ["东南亚", "中东"]),
    ("东莞市精密五金有限公司", "五金配件", "广东 东莞", 220, 12000, 18000,
     ["螺丝", "弹簧", "轴承", "顶针", "气撑杆"], ["冷镦", "热处理", "CNC", "电镀"],
     ["ISO9001", "IATF16949", "SGS"], ["欧盟", "美国", "日本"]),
    ("余姚市塑业科技有限公司", "塑料制品", "浙江 宁波", 180, 10000, 15000,
     ["ABS", "PC", "PP", "PE", "注塑件"], ["注塑", "挤出", "吹塑"],
     ["ISO9001", "深度验厂"], ["欧盟", "美国"]),
    ("台州塑料制品有限公司", "塑料制品", "浙江 台州", 100, 6000, 8000,
     ["TPU", "TPE", "PVC制品", "硅胶件"], ["注塑", "包胶", "硫化"],
     ["ISO9001"], ["东南亚", "中东"]),
    ("佛山塑料包装制品厂", "塑料制品", "广东 佛山", 90, 5000, 6500,
     ["PET瓶", "HDPE桶", "PP编织袋"], ["吹瓶", "吹膜", "注塑"],
     ["QS", "ISO9001"], ["国内", "东南亚"]),
    ("深圳华兴电子有限公司", "电子元器件", "广东 深圳", 300, 15000, 25000,
     ["PCB", "连接器", "锂电池组", "USB-C"], ["SMT", "插件", "组装", "测试"],
     ["ISO9001", "UL", "FCC"], ["欧盟", "美国", "日本"]),
    ("东莞市恒宇电子科技有限公司", "电子元器件", "广东 东莞", 120, 8000, 9000,
     ["微控制器模块", "传感器", "蓝牙模组"], ["SMT", "DIP", "烧录", "测试"],
     ["ISO9001", "CE"], ["欧盟", "东南亚"]),
    ("绍兴柯桥纺织有限公司", "纺织面料", "浙江 绍兴", 200, 20000, 16000,
     ["牛津布", "塔丝隆", "帆布", "摇粒绒"], ["织造", "染整", "涂层"],
     ["OEKO-TEX", "ISO9001"], ["欧盟", "美国"]),
    ("南通家纺制品有限公司", "纺织面料", "江苏 南通", 160, 12000, 11000,
     ["全棉平纹布", "床品", "毛巾"], ["织造", "印染", "缝制"],
     ["OEKO-TEX"], ["欧盟", "日本"]),
    ("临海市户外家具有限公司", "户外家具", "浙江 台州", 250, 18000, 20000,
     ["铝制户外桌椅", "遮阳伞", "凉亭"], ["铝型材", "焊接", "喷涂", "藤编"],
     ["ISO9001", "BSCI", "SGS"], ["欧盟", "美国", "澳大利亚"]),
    ("佛山顺德户外家具制造厂", "户外家具", "广东 佛山", 180, 15000, 14000,
     ["户外沙发", "躺椅", "茶几"], ["焊接", "喷涂", "组装"],
     ["ISO9001", "Sedex"], ["欧盟", "中东"]),
    ("厦门体育用品有限公司", "运动器材", "福建 厦门", 320, 20000, 28000,
     ["跑步机", "健身车", "哑铃", "单杠"], ["焊接", "电镀", "喷涂", "组装"],
     ["ISO9001", "CE", "EN ISO 20957"], ["欧盟", "美国", "日本"]),
    ("宁波运动器材制造有限公司", "运动器材", "浙江 宁波", 140, 10000, 12000,
     ["健身器材配件", "杠铃片", "仰卧板"], ["冲压", "焊接", "注塑"],
     ["ISO9001", "CE"], ["欧盟", "美国"]),
    ("常州园艺工具有限公司", "园艺工具", "江苏 常州", 110, 8000, 7500,
     ["园艺剪刀", "花盆", "喷壶", "割草机配件"], ["冲压", "注塑", "组装"],
     ["CE", "ANSI/OPEI", "ISO9001"], ["欧盟", "美国", "澳大利亚"]),
]

FACTORIES = [
    {
        "id": i,
        "name": name,
        "industry": industry,
        "region": region,
        "employees": employees,
        "factory_area": area,
        "annual_revenue": revenue,  # 单位：万元
        "main_products": products,
        "processes": processes,
        "certifications": certs,
        "export_markets": markets,
        "verified": True,
        "source": "1688",
    }
    for i, (name, industry, region, employees, area, revenue,
            products, processes, certs, markets) in enumerate(_FACTORY_ROWS, 1)
]


def _match_text(factory: dict, q: str) -> bool:
    """判断工厂是否匹配关键词（厂名/行业/主营产品/工艺）。"""
    haystack = " ".join(
        [factory["name"], factory["industry"], factory["region"]] +
        factory["main_products"] + factory["processes"]
    ).lower()
    return q in haystack


def _matched_products(factory: dict, q: str) -> list[str]:
    """返回与关键词匹配的主营产品（用于展示「可生产什么」）。"""
    return [p for p in factory["main_products"] if q.lower() in p.lower()]


@factory_bp.route("/factory")
def page() -> str:
    """Render the factory matching page."""
    regions = sorted({f["region"] for f in FACTORIES})
    industries = sorted({f["industry"] for f in FACTORIES})
    return render_template("factory.html", regions=regions, industries=industries)


@factory_bp.route("/api/factory")
def api_search():
    """Search/match factories. Query params: q, region, industry, scale, sort."""
    q = request.args.get("q", "").strip()
    region = request.args.get("region", "").strip()
    industry = request.args.get("industry", "").strip()
    scale = request.args.get("scale", "").strip()  # small / medium / large
    sort = request.args.get("sort", "revenue_desc")  # revenue_desc / employees_desc / name

    results = []
    for f in FACTORIES:
        if q and not _match_text(f, q):
            continue
        if region and f["region"] != region:
            continue
        if industry and f["industry"] != industry:
            continue
        if scale == "small" and f["employees"] >= 100:
            continue
        if scale == "medium" and not (100 <= f["employees"] < 300):
            continue
        if scale == "large" and f["employees"] < 300:
            continue

        item = dict(f)
        if q:
            item["matched_products"] = _matched_products(f, q)
        results.append(item)

    if sort == "employees_desc":
        results.sort(key=lambda f: f["employees"], reverse=True)
    elif sort == "name":
        results.sort(key=lambda f: f["name"])
    else:
        results.sort(key=lambda f: f["annual_revenue"], reverse=True)

    return jsonify({"total": len(results), "results": results})


@factory_bp.route("/api/factory/<int:factory_id>")
def api_detail(factory_id: int):
    """Get a single factory's full profile."""
    factory = next((f for f in FACTORIES if f["id"] == factory_id), None)
    if not factory:
        return jsonify({"error": "工厂不存在"}), 404
    return jsonify(factory)


@factory_bp.route("/api/factory/external")
def api_external():
    """预留外部工厂数据接口。"""
    return jsonify({
        "error": "外部工厂数据API尚未接入",
        "message": "此接口预留给 1688 工厂 API / 工商数据 API 集成",
        "planned_integrations": [
            "1688 alibaba.icbu.company.get（主营产品/厂房面积/员工规模/年营业额）",
            "1688 item_search_factory（按关键词/类目/地区/产能筛选）",
            "天眼查/企查查工商API（经营范围/注册地址/注册资本主体校验）",
            "国家企业信用信息公示系统（官方权威数据）",
        ],
        "request_format": {
            "product": "产品/关键词（用于匹配可生产该产品的工厂）",
            "region": "地区 (optional)",
            "industry": "行业 (optional)",
            "scale": "规模 small/medium/large (optional)",
        },
        "response_format": {
            "factories": [{
                "name": "工厂名称", "region": "地址",
                "employees": "员工规模", "factory_area": "厂房面积",
                "annual_revenue": "年销售额", "main_products": ["可生产产品"],
            }],
        },
        "status": "not_implemented",
    }), 501
