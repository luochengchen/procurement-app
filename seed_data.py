"""Seed the database with initial material and certification data."""
from __future__ import annotations

from datetime import date, timedelta

from database import get_session, init_db
from models import (Certification, Material, MaterialCategory, PriceHistory)


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


def seed_materials(session, cat_ids: dict[str, int]) -> None:
    """Insert ~30 materials across all categories."""
    today = date.today()

    materials_data = [
        # 塑料原料
        ("塑料原料", "ABS 757", "台湾奇美", "kg", 18.50, today - timedelta(days=2), "1688", "up"),
        ("塑料原料", "PC 110", "韩国乐天", "kg", 22.00, today - timedelta(days=1), "1688", "stable"),
        ("塑料原料", "PP K8303", "燕山石化", "kg", 9.80, today - timedelta(days=3), "金联创", "down"),
        ("塑料原料", "PE 7042", "大庆石化", "kg", 8.50, today - timedelta(days=1), "卓创资讯", "stable"),
        ("塑料原料", "PVC SG-5", "新疆天业", "kg", 6.20, today - timedelta(days=5), "生意社", "down"),
        # 金属材料
        ("金属材料", "不锈钢板 304/2B", "2.0×1219×2438mm", "吨", 16800, today - timedelta(days=2), "我的钢铁网", "up"),
        ("金属材料", "铝合金板 6061-T6", "3.0×1250×2500mm", "吨", 24500, today - timedelta(days=1), "上海有色网", "stable"),
        ("金属材料", "冷轧钢板 SPCC", "1.0×1250×C", "吨", 5200, today - timedelta(days=3), "找钢网", "down"),
        ("金属材料", "铜带 T2", "0.5×200mm", "吨", 72000, today - timedelta(days=1), "长江有色", "up"),
        ("金属材料", "镀锌管 DN15", "2.75mm×6m", "根", 85.00, today - timedelta(days=4), "钢铁王国", "stable"),
        # 电子元器件
        ("电子元器件", "STM32F103C8T6", "LQFP48", "pcs", 8.50, today - timedelta(days=1), "华强北指数", "up"),
        ("电子元器件", "ESP32-WROOM-32E", "SMD", "pcs", 15.00, today - timedelta(days=2), "立创商城", "stable"),
        ("电子元器件", "PCB 双面板 FR-4", "1.6mm 1oz", "cm²", 0.08, today - timedelta(days=5), "嘉立创", "stable"),
        ("电子元器件", "USB-C 连接器 16P", "SMT 沉板", "pcs", 0.85, today - timedelta(days=1), "1688", "down"),
        ("电子元器件", "18650锂电池", "3.7V 2600mAh", "pcs", 12.50, today - timedelta(days=3), "阿里巴巴", "up"),
        # 包装材料
        ("包装材料", "三层瓦楞纸箱", "50×40×30cm", "pcs", 3.50, today - timedelta(days=2), "纸箱网", "stable"),
        ("包装材料", "气泡袋", "40×50cm 大泡", "pcs", 0.45, today - timedelta(days=1), "1688", "down"),
        ("包装材料", "PE缠绕膜", "50cm×300m", "卷", 55.00, today - timedelta(days=4), "1688", "stable"),
        ("包装材料", "透明胶带", "48mm×100m", "卷", 3.80, today - timedelta(days=1), "1688", "stable"),
        ("包装材料", "EPE珍珠棉", "3mm×1m×2m", "张", 12.00, today - timedelta(days=3), "1688", "up"),
        # 纺织面料
        ("纺织面料", "全棉平纹布 40S", "150cm 幅宽", "米", 15.00, today - timedelta(days=2), "柯桥纺织指数", "stable"),
        ("纺织面料", "涤纶牛津布 600D", "150cm 幅宽", "米", 8.50, today - timedelta(days=1), "1688", "down"),
        ("纺织面料", "尼龙塔丝隆 210T", "150cm 幅宽", "米", 10.00, today - timedelta(days=3), "盛泽指数", "stable"),
        ("纺织面料", "帆布 16安", "150cm 幅宽", "米", 22.00, today - timedelta(days=1), "1688", "up"),
        ("纺织面料", "摇粒绒 280g", "160cm 幅宽", "米", 18.00, today - timedelta(days=4), "绍兴轻纺城", "stable"),
        # 五金配件
        ("五金配件", "十字沉头螺丝 M4×20", "304不锈钢", "千只", 35.00, today - timedelta(days=1), "1688", "stable"),
        ("五金配件", "拉伸弹簧", "线径1.2×外径8×长50", "pcs", 1.20, today - timedelta(days=2), "1688", "up"),
        ("五金配件", "微型轴承 608ZZ", "8×22×7mm", "pcs", 1.80, today - timedelta(days=1), "1688", "down"),
        ("五金配件", "锌合金拉手", "128mm 孔距", "pcs", 5.50, today - timedelta(days=3), "1688", "stable"),
        ("五金配件", "模具顶针", "SKD61 φ4×150", "pcs", 15.00, today - timedelta(days=1), "模具钢网", "up"),
    ]

    for cat_name, name, spec, unit, price, pdate, source, trend in materials_data:
        existing = session.query(Material).filter_by(name=name, spec=spec).first()
        if existing:
            continue
        mat = Material(
            category_id=cat_ids[cat_name],
            name=name, spec=spec, unit=unit,
            current_price=price, price_date=pdate,
            price_source=source, trend=trend,
        )
        session.add(mat)
        session.flush()

        # Add price history (3 entries per material)
        session.add(PriceHistory(material_id=mat.id, price=round(price * 0.95, 2), recorded_date=pdate - timedelta(days=30)))
        session.add(PriceHistory(material_id=mat.id, price=round(price * 0.97, 2), recorded_date=pdate - timedelta(days=15)))
        session.add(PriceHistory(material_id=mat.id, price=price, recorded_date=pdate))

    session.commit()


def seed_certifications(session) -> None:
    """Insert certification requirements for major markets."""
    if session.query(Certification).first():
        return  # Already seeded

    certs = [
        # 欧盟
        ("电子产品", "欧盟", "CE", "制造商自我声明/公告机构", True, "¥3,000-50,000", 30, "欧盟强制性安全认证，适用几乎所有电子电器产品"),
        ("电子产品", "欧盟", "RoHS", "第三方检测机构", True, "¥2,000-8,000", 15, "限制有害物质指令，电子电器产品必须合规"),
        ("电子产品", "欧盟", "REACH", "ECHA", True, "¥5,000-30,000", 30, "化学品注册评估授权，含SVHC物质检测"),
        ("玩具", "欧盟", "EN 71", "公告机构", True, "¥5,000-20,000", 20, "玩具安全标准，物理+化学+阻燃测试"),
        ("纺织品", "欧盟", "OEKO-TEX Standard 100", "OEKO-TEX协会", False, "¥3,000-10,000", 15, "纺织品有害物质检测，非强制但买家普遍要求"),
        ("食品接触材料", "欧盟", "EU 1935/2004", "第三方实验室", True, "¥3,000-15,000", 20, "食品接触材料框架法规"),

        # 美国
        ("电子产品", "美国", "FCC", "FCC认可实验室", True, "¥2,000-15,000", 20, "无线电频率设备强制性认证"),
        ("电子产品", "美国", "UL", "UL LLC", False, "¥20,000-100,000", 60, "安全认证，非强制但零售商（亚马逊/沃尔玛）普遍要求"),
        ("食品接触材料", "美国", "FDA 21 CFR", "第三方实验室", True, "¥5,000-20,000", 30, "食品接触物质法规"),
        ("玩具", "美国", "ASTM F963", "CPSC认可实验室", True, "¥5,000-15,000", 15, "美国玩具安全标准，含CPSIA追踪标签"),
        ("医疗器械", "美国", "FDA 510(k)", "FDA", True, "$5,000-50,000", 90, "医疗器械上市前通知"),

        # 日本
        ("电子产品", "日本", "PSE", "METI认可机构", True, "¥10,000-50,000", 45, "电气用品安全法，分菱形PSE(指定产品)和圆形PSE(非指定)"),
        ("食品接触材料", "日本", "JFSL 370", "日本食品卫生协会", True, "¥5,000-15,000", 20, "食品卫生法材质检测"),
        ("纺织品", "日本", "JIS", "JIS认证机构", False, "¥10,000-30,000", 30, "日本工业标准，部分品类非强制但要求标注"),

        # 沙特/中东
        ("通用消费品", "沙特阿拉伯", "SABER", "SASO", True, "¥3,000-10,000", 15, "沙特产品安全计划，几乎所有产品均需注册"),
        ("电子产品", "沙特阿拉伯", "SASO IECEE", "SASO认可实验室", True, "¥5,000-20,000", 30, "沙特电子电器能效与安全认证"),
        ("通用消费品", "阿联酋", "ESMA", "ESMA", True, "¥3,000-12,000", 15, "阿联酋标准化与计量局认证"),

        # 东南亚
        ("电子产品", "泰国", "TISI", "TISI", True, "¥8,000-30,000", 45, "泰国工业标准协会强制认证"),
        ("通用消费品", "印度尼西亚", "SNI", "BSN", True, "¥5,000-20,000", 30, "印度尼西亚国家标准强制认证"),
        ("食品", "菲律宾", "FDA Philippines", "菲律宾FDA", True, "¥3,000-10,000", 20, "菲律宾食品与药品管理局注册"),
        ("电子产品", "越南", "CR Mark", "QUACERT/QUATEST", True, "¥5,000-15,000", 25, "越南符合性标志，适用电子电器及电信设备"),
    ]

    for product_cat, country, cert_name, cert_body, mandatory, cost, lead_days, desc in certs:
        cert = Certification(
            product_category=product_cat,
            target_country=country,
            cert_name=cert_name,
            cert_body=cert_body,
            is_mandatory=mandatory,
            estimated_cost=cost,
            lead_time_days=lead_days,
            description=desc,
        )
        session.add(cert)

    session.commit()


def main():
    init_db()
    session = get_session()
    try:
        print("Seeding categories...")
        cat_ids = seed_categories(session)
        print(f"  Created {len(cat_ids)} categories")

        print("Seeding materials...")
        seed_materials(session, cat_ids)
        count = session.query(Material).count()
        print(f"  Total materials: {count}")

        print("Seeding certifications...")
        seed_certifications(session)
        cert_count = session.query(Certification).count()
        print(f"  Total certifications: {cert_count}")

        print("\nSeed complete!")
    finally:
        session.close()


if __name__ == "__main__":
    main()
