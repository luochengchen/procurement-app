"""Factory matching module — search factories by product, scale, region.

数据源降级链：天眼查（主，需 token）→ Apizero（保底，匿名）→ 本地模拟库（兜底）。

本模块负责「筛选/排序/兜底」这一层；字段归一化与经营范围解析在 service.py，
行业推断与产业带知识库在 industry_belt.py。

重要：筛选对**真实数据同样生效**。此前外部数据路径只透传关键词、把
region/industry/scale/sort 全部丢弃，导致用户按行业筛选永远筛不到东西 —— 已修正。
"""
from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request

from modules.factory.industry_belt import (
    BELTS,
    HOT_CATEGORIES,
    INDUSTRY_RULES,
    capital_to_wan,
)

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
        "english_name": "",
        "industry": industry,
        "region": region,
        "city": region.split()[-1] if " " in region else region,
        "district": "",
        "employees": employees,
        "factory_area": area,
        "annual_revenue": revenue,  # 单位：万元
        "reg_capital": "",
        "business_scope": "",
        "legal_person": "",
        "established": "",
        "credit_code": "",
        "phone": "",
        "email": "",
        "reg_status": "存续",
        "company_org_type": "",
        "main_products": products,
        "processes": processes,
        "certifications": certs,
        "export_markets": markets,
        "is_manufacturer": True,   # 模拟库全部是生产型工厂
        "can_export": bool(markets),
        "scale_label": "小型" if employees < 100 else ("中型" if employees < 300 else "大型"),
        "scale_basis": f"员工 {employees} 人",
        "belt": "",
        "verified": True,
        "source": "本地模拟",
        "is_external": False,
    }
    for i, (name, industry, region, employees, area, revenue,
            products, processes, certs, markets) in enumerate(_FACTORY_ROWS, 1)
]

# 行业下拉选项：与 industry_belt 的推断词汇同一套，保证真实数据也能筛到
INDUSTRIES = [name for name, _ in INDUSTRY_RULES]

# 地区选项：省级（来自模拟库）+ 产业带城市（真实数据里 city 是「宁波市」这种）
REGIONS = sorted(
    {r.split()[0] for r in {f["region"] for f in FACTORIES} if " " in r}
    | set(BELTS.keys())
)

SCALES = [
    {"value": "small", "label": "小型（注册资本 < 100 万）"},
    {"value": "medium", "label": "中型（100-1000 万）"},
    {"value": "large", "label": "大型（> 1000 万）"},
]

# 前端排序值 → 说明。mock 库没有注册资本/成立日期，用年销售额与员工规模代理。
SORTS = [
    {"value": "relevance", "label": "相关度"},
    {"value": "capital_desc", "label": "注册资本 ↓"},
    {"value": "established_desc", "label": "成立时间 ↓"},
    {"value": "name", "label": "厂名"},
]


def _match_text(factory: dict, q: str) -> bool:
    """判断工厂是否匹配关键词（厂名/行业/主营产品/工艺/经营范围）。"""
    haystack = " ".join(
        [factory["name"], factory["industry"], factory["region"],
         factory.get("business_scope", "")] +
        factory["main_products"] + factory["processes"]
    ).lower()
    return q in haystack


def _matched_products(factory: dict, q: str) -> list[str]:
    """返回与关键词匹配的主营产品（用于展示「可生产什么」并高亮）。"""
    return [p for p in factory["main_products"] if q.lower() in p.lower()]


@factory_bp.route("/factory")
def page() -> str:
    """Render the factory matching page."""
    return render_template(
        "factory.html",
        regions=REGIONS,
        industries=INDUSTRIES,
        sorts=SORTS,
        hot_categories=HOT_CATEGORIES,
    )


# ---------------------------------------------------------------------------
# 统一筛选/排序：mock 与真实数据走同一套参数语义
# ---------------------------------------------------------------------------
def _scale_bucket(factory: dict) -> str:
    """把规模归一为 small/medium/large（真实数据由注册资本换算）。"""
    label = factory.get("scale_label") or ""
    return {"小型": "small", "中型": "medium", "大型": "large"}.get(label, "")


def _apply_filters(results: list[dict], q: str, region: str, industry: str,
                   scale: str, only_manufacturer: bool,
                   exclude_inactive: bool) -> list[dict]:
    """对（mock 或真实）工厂列表统一施加筛选条件。

    region 用子串匹配而非等值：真实数据的地址是「浙江省宁波市北仑区…」这种长串，
    用户填「宁波」就该命中。
    """
    out = []
    for f in results:
        if exclude_inactive and f.get("reg_status") and f["reg_status"] != "存续":
            continue
        if only_manufacturer and not f.get("is_manufacturer"):
            continue
        if region:
            hay = " ".join([f.get("region", ""), f.get("city", ""),
                            f.get("district", "")])
            if region not in hay:
                continue
        if industry and industry != f.get("industry"):
            continue
        if scale and _scale_bucket(f) != scale:
            continue
        out.append(f)
    return out


def _apply_sort(results: list[dict], sort: str) -> list[dict]:
    """排序。真实数据没有年销售额/员工数，用注册资本与成立日期替代。"""
    if sort == "name":
        results.sort(key=lambda f: f.get("name") or "")
    elif sort == "established_desc":
        results.sort(key=lambda f: f.get("established") or "", reverse=True)
    elif sort == "capital_desc":
        results.sort(key=lambda f: capital_to_wan(f.get("reg_capital") or "")
                     or f.get("annual_revenue") or 0, reverse=True)
    else:  # relevance：真实数据保持 service 打好的相关度序；mock 用年销售额代理
        if results and not results[0].get("is_external"):
            results.sort(key=lambda f: f.get("annual_revenue") or 0, reverse=True)
    return results


@factory_bp.route("/api/factory")
def api_search():
    """Search/match factories. Query params:

    q, region, industry, scale, sort, only_manufacturer, exclude_inactive
    """
    q = request.args.get("q", "").strip()
    region = request.args.get("region", "").strip()
    industry = request.args.get("industry", "").strip()
    scale = request.args.get("scale", "").strip()  # small / medium / large
    sort = request.args.get("sort", "relevance").strip()
    only_manufacturer = request.args.get("only_manufacturer") in ("1", "true", "on")
    # 默认剔除注销/吊销企业 —— 采购拿着一个已注销的主体去谈是纯浪费时间
    exclude_inactive = request.args.get("exclude_inactive", "1") not in ("0", "false", "off")

    # 优先真实外部数据（工商 API 按关键词检索，必须有 q）
    if q:
        try:
            from modules.factory.service import search_external_multi
            external, source, keywords, notice = search_external_multi(q)
            if external:
                for i, f in enumerate(external):
                    f["id"] = 1000 + i  # 稳定 id，供前端详情索引
                filtered = _apply_filters(external, q, region, industry, scale,
                                          only_manufacturer, exclude_inactive)
                filtered = _apply_sort(filtered, sort)
                return jsonify({
                    "total": len(filtered),
                    "results": filtered,
                    "data_source": source,
                    "keywords": keywords,
                    "notice": notice,
                    "external_available": True,
                })
            if notice:
                # 外部源报错（额度用尽等）—— 明确告诉用户为什么看到的是模拟数据
                mock = [dict(f) for f in FACTORIES]
                results = _apply_sort(
                    _apply_filters(mock, q, region, industry, scale,
                                   only_manufacturer, exclude_inactive), sort)
                return jsonify({
                    "total": len(results),
                    "results": results,
                    "data_source": "本地模拟",
                    "keywords": keywords,
                    "notice": notice,
                    "external_available": False,
                })
        except Exception:
            pass  # 外部链路整体异常 → 降级本地模拟

    # 本地兜底：先复制再加工，避免把 matched_products 写回模块级常量污染后续请求
    results = [dict(f) for f in FACTORIES]
    if q:
        for f in results:
            f["matched_products"] = _matched_products(f, q)
    results = _apply_sort(
        _apply_filters(results, q, region, industry, scale,
                       only_manufacturer, exclude_inactive), sort)
    return jsonify({
        "total": len(results),
        "results": results,
        "data_source": "本地模拟",
        "keywords": [q] if q else [],
        "notice": "",
        "external_available": True,
    })


@factory_bp.route("/api/factory/filters")
def api_filters():
    """筛选可选项（地区/行业/规模/排序 + 产业带 + 热门品类），供各页动态填充。"""
    return jsonify({
        "regions": REGIONS,
        "industries": INDUSTRIES,
        "scales": SCALES,
        "sorts": SORTS,
        "belts": [{"city": city, **belt} for city, belt in BELTS.items() if belt["categories"]],
        "hot_categories": HOT_CATEGORIES,
    })


@factory_bp.route("/api/factory/<int:factory_id>")
def api_detail(factory_id: int):
    """Get a single factory's full profile (本地模拟库专用)."""
    factory = next((f for f in FACTORIES if f["id"] == factory_id), None)
    if not factory:
        return jsonify({"error": "工厂不存在"}), 404
    return jsonify(factory)


@factory_bp.route("/api/factory/external")
def api_external():
    """外部工厂数据接入说明（真实字段能力与缺口清单）。"""
    return jsonify({
        "status": "partially_implemented",
        "active_sources": [
            "Apizero 企业工商查询（匿名可用，配置 APIZERO_API_KEY 提升额度）",
            "天眼查开放平台（配置 TIANYANCHA_TOKEN 后作为主源）",
        ],
        "available_fields": [
            "企业名称/英文名/法定代表人/统一社会信用代码",
            "注册地址/城市/区县/注册资本/成立日期/登记状态/企业类型",
            "经营范围（→ 解析出行业、可生产产品、是否生产型、出口资质）",
            "联系电话/邮箱",
        ],
        "missing_fields": {
            "年销售额": "工商数据不提供。需 1688 工厂 API（需企业资质+信息共享协议）",
            "员工数": "工商数据不提供。当前用注册资本换算规模档位并标注口径",
            "厂房面积": "工商数据不提供。同上",
        },
        "planned_integrations": [
            "1688 alibaba.icbu.company.get（主营产品/厂房面积/员工规模/年营业额）",
            "国家企业信用信息公示系统（官方权威数据）",
        ],
        "request_format": {
            "q": "产品/关键词（必填，外部源按关键词检索）",
            "region": "地区（子串匹配 city/district/reg_location）",
            "industry": "行业（取自 industry_belt 推断词汇表）",
            "scale": "规模 small/medium/large（按注册资本换算）",
            "only_manufacturer": "1 = 只看生产型厂家",
            "exclude_inactive": "0 = 保留注销/吊销企业（默认剔除）",
        },
    })
