"""Seed the database with initial material, certification, and cost template data."""
from __future__ import annotations

from datetime import date, timedelta

from database import get_session, init_db
from models import (Certification, CostItem, CostTemplate, Material,
                    MaterialCategory, PriceHistory)


def seed_categories(session) -> dict[str, int]:
    """Insert 6 material categories. Returns {name: id} mapping."""
    categories = [
        ("塑料原料", "🧪", 1),
        ("金属材料", "🔩", 2),
        ("电子元器件", "💻", 3),
        ("包装材料", "📦", 4),
        ("纺织面料", "🧵", 5),
        ("五金配件", "🔧", 6),
    ]
    cat_ids = {}
    for name, icon, order in categories:
        cat = session.query(MaterialCategory).filter_by(name=name).first()
        if not cat:
            cat = MaterialCategory(name=name, icon=icon, sort_order=order)
            session.add(cat)
            session.flush()
        cat_ids[name] = cat.id
    session.commit()
    return cat_ids


# 塑料原料主要市场（系数相对基准价，反映地区运费/供需差异）
PLASTIC_REGIONS = {"余姚": 1.00, "东莞": 1.04, "天津": 1.02}
# 五金配件主要市场
HARDWARE_REGIONS = {"永康": 1.00, "东莞": 1.05, "温州": 1.02}

# 塑料原料：(name, spec, unit, 基准价, 趋势)
PLASTICS = [
    ("ABS 757", "台湾奇美", "kg", 18.50, "up"),
    ("PC 110", "韩国乐天", "kg", 22.00, "stable"),
    ("PP K8303", "燕山石化", "kg", 9.80, "down"),
    ("PE 7042", "大庆石化", "kg", 8.50, "stable"),
    ("PVC SG-5", "新疆天业", "kg", 6.20, "down"),
    ("PA66 101L", "杜邦", "kg", 32.00, "up"),
    ("POM 500P", "杜邦", "kg", 28.00, "stable"),
    ("PET 水瓶级", "华润化学", "kg", 7.80, "down"),
    ("PS 525", "湛江新中美", "kg", 9.50, "stable"),
    ("TPU 85A", "万华化学", "kg", 25.00, "up"),
    ("PMMA 8N", "三菱丽阳", "kg", 20.00, "stable"),
    ("HDPE 5000S", "燕山石化", "kg", 8.80, "down"),
    ("PC/ABS C1200HF", "沙比克", "kg", 24.00, "stable"),
    ("LDPE 2426H", "大庆石化", "kg", 9.20, "down"),
]

# 五金配件：(name, spec, unit, 基准价, 趋势)
HARDWARE = [
    ("十字沉头螺丝 M4×20", "304不锈钢", "千只", 35.00, "stable"),
    ("拉伸弹簧", "线径1.2×外径8×长50", "pcs", 1.20, "up"),
    ("微型轴承 608ZZ", "8×22×7mm", "pcs", 1.80, "down"),
    ("锌合金拉手", "128mm 孔距", "pcs", 5.50, "stable"),
    ("模具顶针", "SKD61 φ4×150", "pcs", 15.00, "up"),
    ("六角螺母 M8", "304不锈钢", "千只", 60.00, "stable"),
    ("平垫片 M6", "镀锌", "千只", 12.00, "down"),
    ("不锈钢合页 4寸", "304 轴承款", "pcs", 8.50, "stable"),
    ("抽屉滑轨 45cm", "三节静音", "副", 12.00, "stable"),
    ("万向脚轮 2寸", "带刹车", "pcs", 6.80, "down"),
    ("挂锁 32mm", "铜芯", "pcs", 9.50, "stable"),
    ("角码支架", "38×38 不锈钢", "pcs", 2.50, "down"),
    ("抽芯铆钉 4×12", "铝", "千只", 18.00, "stable"),
    ("气撑杆 300N", "400mm", "pcs", 15.00, "up"),
]

# 其他品类（单地区「全国」）：(category, name, spec, unit, price, trend)
OTHERS = [
    ("电子元器件", "STM32F103C8T6", "LQFP48", "pcs", 8.50, "up"),
    ("电子元器件", "ESP32-WROOM-32E", "SMD", "pcs", 15.00, "stable"),
    ("电子元器件", "PCB 双面板 FR-4", "1.6mm 1oz", "cm²", 0.08, "stable"),
    ("电子元器件", "USB-C 连接器 16P", "SMT 沉板", "pcs", 0.85, "down"),
    ("电子元器件", "18650锂电池", "3.7V 2600mAh", "pcs", 12.50, "up"),
    ("包装材料", "三层瓦楞纸箱", "50×40×30cm", "pcs", 3.50, "stable"),
    ("包装材料", "气泡袋", "40×50cm 大泡", "pcs", 0.45, "down"),
    ("包装材料", "PE缠绕膜", "50cm×300m", "卷", 55.00, "stable"),
    ("包装材料", "透明胶带", "48mm×100m", "卷", 3.80, "stable"),
    ("包装材料", "EPE珍珠棉", "3mm×1m×2m", "张", 12.00, "up"),
    ("纺织面料", "全棉平纹布 40S", "150cm 幅宽", "米", 15.00, "stable"),
    ("纺织面料", "涤纶牛津布 600D", "150cm 幅宽", "米", 8.50, "down"),
    ("纺织面料", "尼龙塔丝隆 210T", "150cm 幅宽", "米", 10.00, "stable"),
    ("纺织面料", "帆布 16安", "150cm 幅宽", "米", 22.00, "up"),
    ("纺织面料", "摇粒绒 280g", "160cm 幅宽", "米", 18.00, "stable"),
]


def _add_material(session, cat_id, name, spec, unit, region, price, pdate, source, trend):
    existing = session.query(Material).filter_by(name=name, spec=spec, region=region).first()
    if existing:
        return
    mat = Material(
        category_id=cat_id, name=name, spec=spec, unit=unit, region=region,
        current_price=price, price_date=pdate, price_source=source, trend=trend,
    )
    session.add(mat)
    session.flush()
    session.add(PriceHistory(material_id=mat.id, price=round(price * 0.94, 2), recorded_date=pdate - timedelta(days=30)))
    session.add(PriceHistory(material_id=mat.id, price=round(price * 0.97, 2), recorded_date=pdate - timedelta(days=15)))
    session.add(PriceHistory(material_id=mat.id, price=price, recorded_date=pdate))


def seed_materials(session, cat_ids: dict[str, int]) -> None:
    """Insert materials, plastic & hardware get multi-region pricing."""
    today = date.today()

    # 塑料原料：3 个地区
    for name, spec, unit, base, trend in PLASTICS:
        for region, factor in PLASTIC_REGIONS.items():
            _add_material(session, cat_ids["塑料原料"], name, spec, unit, region,
                          round(base * factor, 2), today - timedelta(days=1), "中国塑料城", trend)

    # 五金配件：3 个地区
    for name, spec, unit, base, trend in HARDWARE:
        for region, factor in HARDWARE_REGIONS.items():
            _add_material(session, cat_ids["五金配件"], name, spec, unit, region,
                          round(base * factor, 2), today - timedelta(days=1), "1688五金市场", trend)

    # 其他品类：单地区
    for cat_name, name, spec, unit, price, trend in OTHERS:
        _add_material(session, cat_ids[cat_name], name, spec, unit, "全国", price,
                      today - timedelta(days=1), "1688", trend)

    session.commit()


def seed_certifications(session) -> None:
    """Insert certification requirements for major markets."""
    if session.query(Certification).first():
        return  # Already seeded

    certs = [
        # === 欧盟 ===
        ("电子产品", "欧盟", "CE", "制造商自我声明/公告机构", True, "¥3,000-50,000", 30, "欧盟强制性安全认证"),
        ("电子产品", "欧盟", "RoHS", "第三方检测机构", True, "¥2,000-8,000", 15, "限制有害物质指令"),
        ("电子产品", "欧盟", "REACH", "ECHA", True, "¥5,000-30,000", 30, "化学品注册评估授权"),
        ("玩具", "欧盟", "EN 71", "公告机构", True, "¥5,000-20,000", 20, "玩具安全标准"),
        ("纺织品", "欧盟", "OEKO-TEX Standard 100", "OEKO-TEX协会", False, "¥3,000-10,000", 15, "纺织品有害物质检测"),
        ("食品接触材料", "欧盟", "EU 1935/2004", "第三方实验室", True, "¥3,000-15,000", 20, "食品接触材料框架法规"),

        # === 美国 ===
        ("电子产品", "美国", "FCC", "FCC认可实验室", True, "¥2,000-15,000", 20, "无线电频率设备认证"),
        ("电子产品", "美国", "UL", "UL LLC", False, "¥20,000-100,000", 60, "安全认证，零售商普遍要求"),
        ("食品接触材料", "美国", "FDA 21 CFR", "第三方实验室", True, "¥5,000-20,000", 30, "食品接触物质法规"),
        ("玩具", "美国", "ASTM F963", "CPSC认可实验室", True, "¥5,000-15,000", 15, "美国玩具安全标准"),
        ("医疗器械", "美国", "FDA 510(k)", "FDA", True, "$5,000-50,000", 90, "医疗器械上市前通知"),

        # === 日本 ===
        ("电子产品", "日本", "PSE", "METI认可机构", True, "¥10,000-50,000", 45, "电气用品安全法"),
        ("食品接触材料", "日本", "JFSL 370", "日本食品卫生协会", True, "¥5,000-15,000", 20, "食品卫生法材质检测"),
        ("纺织品", "日本", "JIS", "JIS认证机构", False, "¥10,000-30,000", 30, "日本工业标准"),

        # === 中东 ===
        ("通用消费品", "沙特阿拉伯", "SABER", "SASO", True, "¥3,000-10,000", 15, "沙特产品安全计划"),
        ("电子产品", "沙特阿拉伯", "SASO IECEE", "SASO认可实验室", True, "¥5,000-20,000", 30, "沙特电子电器能效认证"),
        ("通用消费品", "阿联酋", "ESMA", "ESMA", True, "¥3,000-12,000", 15, "阿联酋标准化认证"),

        # === 东南亚 ===
        ("电子产品", "泰国", "TISI", "TISI", True, "¥8,000-30,000", 45, "泰国工业标准协会认证"),
        ("通用消费品", "印度尼西亚", "SNI", "BSN", True, "¥5,000-20,000", 30, "印度尼西亚国家标准"),
        ("食品", "菲律宾", "FDA Philippines", "菲律宾FDA", True, "¥3,000-10,000", 20, "菲律宾食品药品注册"),
        ("电子产品", "越南", "CR Mark", "QUACERT/QUATEST", True, "¥5,000-15,000", 25, "越南符合性标志"),

        # === 运动器材（新增）===
        ("运动器材", "欧盟", "CE", "制造商自我声明/公告机构", True, "¥3,000-30,000", 30, "通用安全认证"),
        ("运动器材", "欧盟", "EN ISO 20957", "公告机构", True, "¥10,000-40,000", 40, "固定式健身器材安全标准（原EN 957）"),
        ("运动器材", "美国", "ASTM F2276", "CPSC认可实验室", True, "¥8,000-25,000", 30, "健身器材安全规范"),
        ("运动器材", "美国", "ASTM F2115", "CPSC认可实验室", True, "¥8,000-25,000", 30, "跑步机安全规范"),
        ("运动器材", "日本", "SG认证", "一般财团法人制品安全协会", False, "¥5,000-20,000", 25, "日本安全制品认证（非强制）"),
        ("运动器材", "澳大利亚", "AS 1663", "NATA认可实验室", False, "¥8,000-25,000", 30, "健身器材澳标（部分州要求）"),

        # === 户外家具（新增）===
        ("户外家具", "欧盟", "EN 581", "公告机构", True, "¥5,000-20,000", 25, "户外家具安全、强度与耐久性标准"),
        ("户外家具", "欧盟", "EN 1022", "公告机构", True, "¥3,000-12,000", 15, "座椅稳定性与倾倒测试"),
        ("户外家具", "美国", "ASTM F1988", "CPSC认可实验室", True, "¥5,000-18,000", 20, "户外家具性能与安全规范"),
        ("户外家具", "沙特阿拉伯", "SABER", "SASO", True, "¥3,000-10,000", 15, "沙特产品安全计划"),
        ("户外家具", "澳大利亚", "AS 4688", "NATA认可实验室", False, "¥6,000-20,000", 25, "户外家具澳标"),

        # === 园艺产品（新增）===
        ("园艺工具", "欧盟", "CE 机械指令 2006/42/EC", "公告机构", True, "¥8,000-35,000", 35, "园艺机械强制安全认证"),
        ("园艺工具", "欧盟", "2000/14/EC 噪音指令", "公告机构", True, "¥3,000-15,000", 20, "户外设备噪音排放限值"),
        ("园艺工具", "美国", "ANSI/OPEI", "OPEI认可实验室", True, "¥8,000-30,000", 35, "户外动力设备安全标准"),
        ("园艺工具", "美国", "EPA 排放认证", "EPA", True, "¥5,000-20,000", 30, "发动机排放合规（非道路设备）"),
        ("园艺工具", "日本", "METI", "METI认可机构", False, "¥5,000-18,000", 25, "日本经济产业省要求（电动园艺工具）"),
        ("园艺工具", "澳大利亚", "RCM", "ACMA认可机构", True, "¥3,000-12,000", 15, "电气产品符合性标志"),
    ]

    for product_cat, country, cert_name, cert_body, mandatory, cost, lead_days, desc in certs:
        session.add(Certification(
            product_category=product_cat,
            target_country=country,
            cert_name=cert_name,
            cert_body=cert_body,
            is_mandatory=mandatory,
            estimated_cost=cost,
            lead_time_days=lead_days,
            description=desc,
        ))

    session.commit()


# 预设成本模板：(模板名, 描述, [(类型, 项目名, 单位, 单价, 数量), ...])
COST_TEMPLATES = [
    ("注塑件成本模板", "塑料制品注塑成型，含模具摊销",
     [("material", "塑料粒子 ABS", "kg", 18.50, 0.12),
      ("labor", "注塑操作工", "小时", 35.00, 0.05),
      ("utility", "水电气", "件", 0.30, 1.0),
      ("processing_out", "委外注塑加工", "模次", 2000.00, 0.001),
      ("mold", "模具摊销", "件", 0.80, 1.0),
      ("packaging", "包装费", "件", 0.50, 1.0)]),
    ("五金冲压件模板", "金属冲压件，含模具摊销与运费",
     [("material", "冷轧钢板 SPCC", "吨", 5200.00, 0.0008),
      ("labor", "冲压操作工", "小时", 35.00, 0.06),
      ("utility", "水电气", "件", 0.20, 1.0),
      ("processing_out", "委外冲压加工", "冲次", 500.00, 0.002),
      ("mold", "模具摊销", "件", 0.60, 1.0),
      ("freight", "运费", "件", 0.25, 1.0)]),
    ("户外家具模板", "铝制户外家具，焊接+喷涂+包装",
     [("material", "铝型材 6063", "吨", 24500.00, 0.003),
      ("labor", "组装工", "小时", 35.00, 0.08),
      ("utility", "水电气", "件", 0.50, 1.0),
      ("processing_out", "焊接+喷涂加工", "件", 18.00, 1.0),
      ("packaging", "包装费", "件", 8.00, 1.0),
      ("freight", "运费", "件", 6.00, 1.0)]),
    ("运动器材模板", "钢管类健身器材，焊接+电镀+包装",
     [("material", "钢管 Q235", "吨", 8500.00, 0.006),
      ("labor", "焊接打磨工", "小时", 40.00, 0.1),
      ("utility", "水电气", "件", 0.60, 1.0),
      ("processing_out", "焊接+电镀加工", "件", 25.00, 1.0),
      ("mold", "模具摊销", "件", 1.20, 1.0),
      ("packaging", "包装费", "件", 5.00, 1.0)]),
]


def seed_cost_templates(session) -> None:
    """Insert preset cost templates for typical products."""
    if session.query(CostTemplate).first():
        return

    for name, desc, items in COST_TEMPLATES:
        tpl = CostTemplate(name=name, description=desc)
        session.add(tpl)
        session.flush()
        for item_type, item_name, unit, unit_price, qty in items:
            session.add(CostItem(
                template_id=tpl.id, item_type=item_type, name=item_name,
                unit=unit, unit_price=unit_price, quantity=qty,
                subtotal=round(unit_price * qty, 2),
            ))
    session.commit()


def main():
    init_db()
    session = get_session()
    try:
        print("Seeding categories...")
        cat_ids = seed_categories(session)
        print(f"  {len(cat_ids)} categories")

        print("Seeding materials...")
        seed_materials(session, cat_ids)
        print(f"  {session.query(Material).count()} materials")

        print("Seeding certifications...")
        seed_certifications(session)
        print(f"  {session.query(Certification).count()} certifications")

        print("Seeding cost templates...")
        seed_cost_templates(session)
        print(f"  {session.query(CostTemplate).count()} cost templates")

        print("\nSeed complete!")
    finally:
        session.close()


if __name__ == "__main__":
    main()
