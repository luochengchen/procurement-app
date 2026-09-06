"""竞品分析模板库。

每个模板 = 一套主流竞品分析方法论 + 使用说明(guide，告诉用户怎么拿到数据) + 分节字段。
字段类型: text / textarea / number / date / select(options)。sections 内 repeat=True 表示可添加多组
（如多个竞品、多个价格样本、多个候选供应商），报告中会逐组展开编号。
"""

# 常用选项
SITES = ["美国站", "欧洲站(德/英/法)", "日本站", "中东站", "东南亚站", "多站点", "国内1688/内贸"]
MARKET_TOOLS = ["卖家精灵", "Helium 10", "Keepa", "Jungle Scout", "Sorftime/西柚", "卖家后台(自已账号)", "前台手动统计"]
CHANNELS = ["1688", "阿里国际站", "工厂/展会", "跨境B2C平台", "海关数据", "行业报告", "线下档口", "其他"]
PAYMENTS = ["T/T 30%预付", "信用证", "月结", "O/A", "支付宝/线上担保", "其他"]
CERT_OPTS = ["CE", "RoHS", "FCC", "UL", "ISO9001", "BSCI", "SGS报告", "OEKO-TEX", "FDA", "REACH", "无(待确认)"]

TEMPLATES = [
    # ============================================================ 1. Listing 全维度拆解
    {
        "key": "listing-dive",
        "name": "竞品 Listing 全维度拆解",
        "icon": "bi-binoculars-fill",
        "tone": "primary",
        "desc": "选一个对标竞品，逐层拆标题 / 图片 / 五点 / A+ / 评论 / 价格销量，提炼可抄卖点与可打痛点，并同步看采购成本机会。",
        "guide": (
            "【适用】已有或拟定上架的某一款产品，找一个直接竞品做深度拆解。\n\n"
            "【怎么找到竞品】① 类目 BSR 榜前 100 里选人群/场景/价格接近的 1 个；② 核心关键词搜索结果首页；③ 老竞品详情页的 Sponsored 广告位。价格差距建议在 ±15% 内才算「直接竞品」。\n\n"
            "【数据从哪拿】\n"
            "· BSR/排名/上架时间：亚马逊前台 + Keepa(免费插件，看历史曲线)。\n"
            "· 预估月销量/关键词流量：卖家精灵 / Helium10 / Jungle Scout 的「查竞品」「关键词反查」；没工具可用「加购测试法」估日销。\n"
            "· 标题/五点/A+/评论：直接前台逐项记录；评论痛点重点看 1-3 星差评。\n"
            "· 促销/价格波动：Keepa 看降价史（LD/BD 固定天数、手动降价不固定，可区分）。\n"
            "· 成本估算：采购价询 1688/工厂；佣金按类目(约15%)；FBA 费按尺寸重量在亚马逊后台算。"
        ),
        "sections": [
            {
                "id": "obj", "title": "分析对象与市场定位", "repeat": False, "fields": [
                    {"key": "site", "label": "目标站点/市场", "type": "select", "options": SITES},
                    {"key": "category", "label": "目标类目", "type": "text", "placeholder": "如：厨房收纳 / 户外照明"},
                    {"key": "my_product", "label": "我方产品(拟采购/上架)", "type": "text", "placeholder": "如：不锈钢厨房置物架"},
                    {"key": "comp_name", "label": "竞品品牌 / ASIN", "type": "text", "required": True},
                    {"key": "comp_url", "label": "竞品链接", "type": "text"},
                    {"key": "bsr", "label": "大类 / 小类 BSR", "type": "text", "placeholder": "如：#12,345 / #320"},
                    {"key": "est_sales", "label": "预估月销量(单)", "type": "number", "step": "1"},
                    {"key": "price", "label": "竞品售价 (USD/本地币)", "type": "number", "step": "0.01"},
                    {"key": "rating", "label": "评分 / 评论数", "type": "text", "placeholder": "如：4.5★ / 1,200"},
                    {"key": "age", "label": "上架时长 / 生命周期", "type": "text", "placeholder": "如：新品(<180天) / 成熟(>365天)"},
                ],
            },
            {
                "id": "listing", "title": "Listing 拆解：标题/图片/五点/A+", "repeat": False, "fields": [
                    {"key": "title", "label": "标题关键词结构", "type": "textarea", "rows": 3,
                     "placeholder": "拆出：品牌+核心词+卖点词+长尾词顺序；标注竞品漏掉但搜索量高的词(关键词缺口)"},
                    {"key": "images", "label": "图片体系", "type": "textarea", "rows": 3,
                     "placeholder": "主图风格(白底/场景)；副图顺序与每张传达的卖点；为什么把核心卖点放第2张"},
                    {"key": "bullets", "label": "五点卖点高频词", "type": "textarea", "rows": 3,
                     "placeholder": "每条开头词组、使用场景、适用人群，提炼 3-5 个高频卖点词"},
                    {"key": "aplus", "label": "A+/对比表强调点", "type": "textarea", "rows": 3,
                     "placeholder": "竞品在对比表强调什么、刻意回避什么参数（回避处=可攻击的差异化空间）"},
                ],
            },
            {
                "id": "reviews", "title": "用户评价与痛点挖掘", "repeat": False, "fields": [
                    {"key": "good", "label": "好评高频卖点(3-5条)", "type": "textarea", "rows": 3},
                    {"key": "bad", "label": "差评高频痛点(3-5条)", "type": "textarea", "rows": 3,
                     "placeholder": "重点看1-3星，差评痛点=我们的产品机会点"},
                ],
            },
            {
                "id": "ops", "title": "运营动作观察", "repeat": False, "fields": [
                    {"key": "traffic", "label": "流量结构 / 广告位", "type": "text",
                     "placeholder": "自然 vs SP/SB 广告占比；用关键词反查看它是自然还是广告流量词"},
                    {"key": "promo", "label": "促销节奏 / 价格波动", "type": "text",
                     "placeholder": "Coupon / Lightning Deal / Best Deal 频率与折扣；Keepa 降价史结论"},
                    {"key": "gap_kw", "label": "竞品未覆盖的关键词/功能缺口", "type": "text",
                     "placeholder": "高搜索量但无竞品优化的词；评论区/QA被要求但没人满足的功能"},
                ],
            },
            {
                "id": "sourcing", "title": "采购与成本视角", "repeat": False, "fields": [
                    {"key": "cost", "label": "成本测算明细", "type": "textarea", "rows": 2,
                     "placeholder": "采购+头程+佣金15%+FBA费 ≈ 毛利=售价-成本；给出估算毛利与毛利率"},
                    {"key": "sourcing_idea", "label": "供应链优化机会", "type": "textarea", "rows": 2,
                     "placeholder": "哪项用料/工艺可降本、是否可换材料或换供应商、MOQ 建议"},
                ],
            },
            {
                "id": "conclusion", "title": "结论与行动建议", "repeat": False, "fields": [
                    {"key": "summary", "label": "核心发现(3-5条)", "type": "textarea", "rows": 3},
                    {"key": "actions", "label": "落地行动(Listing/定价/采购)", "type": "textarea", "rows": 3},
                ],
            },
        ],
    },

    # ============================================================ 2. SWOT
    {
        "key": "swot",
        "name": "SWOT 竞品 / 选品分析",
        "icon": "bi-grid-1x2-fill",
        "tone": "warning",
        "desc": "把一个产品(或候选供应商)的 优势/劣势/机会/威胁 摆到同一张表，决定「做不做、怎么做、找谁供」。",
        "guide": (
            "【适用】选品立项或供应商取舍时，评估一个机会的相对优劣势。\n\n"
            "【怎么填】S/W 是对自身(或拟采购产品/拟合作供应商)内部的评估；O/T 是外部市场环境。每格写 3-5 条，尽量带数据而非形容词。\n\n"
            "【数据从哪拿】\n"
            "· 自身优势劣势：参考我们成本核算/工厂匹配/认证模块已有数据 + 供应商询价对比。\n"
            "· 机会：Google Trends 看搜索趋势、类目销量增长、新品榜(New Releases)出现的新需求。\n"
            "· 威胁：Keepa/卖家精灵看头部竞品动作、价格战程度、认证/合规新规(可配合本工具认证查询)。"
        ),
        "sections": [
            {
                "id": "obj", "title": "评估对象", "repeat": False, "fields": [
                    {"key": "subject", "label": "被评估对象(产品/供应商/项目)", "type": "text", "required": True},
                    {"key": "market", "label": "目标市场", "type": "select", "options": SITES},
                    {"key": "date", "label": "评估日期", "type": "date"},
                ],
            },
            {
                "id": "swot", "title": "SWOT 四象限", "repeat": False, "fields": [
                    {"key": "s", "label": "S 优势 Strengths(3-5条)", "type": "textarea", "rows": 3},
                    {"key": "w", "label": "W 劣势 Weaknesses(3-5条)", "type": "textarea", "rows": 3},
                    {"key": "o", "label": "O 机会 Opportunities(3-5条)", "type": "textarea", "rows": 3},
                    {"key": "t", "label": "T 威胁 Threats(3-5条)", "type": "textarea", "rows": 3},
                ],
            },
            {
                "id": "conclusion", "title": "结论", "repeat": False, "fields": [
                    {"key": "strategy", "label": "应对策略(SO/WT 组合打法)", "type": "textarea", "rows": 3},
                    {"key": "decision", "label": "决策：做不做 / 选哪家", "type": "select",
                     "options": ["立项推进", "暂缓/放弃", "先小批量试单", "换方案/换供应商", "待补充数据后再定"]},
                    {"key": "notes", "label": "补充说明", "type": "textarea", "rows": 2},
                ],
            },
        ],
    },

    # ============================================================ 3. 4P 营销组合
    {
        "key": "four-p",
        "name": "4P 营销组合分析",
        "icon": "bi-diagram-3-fill",
        "tone": "info",
        "desc": "从 产品(Product)/价格(Price)/渠道(Place)/推广(Promotion) 四个面评估一个市场打法，价格环节含采购与利润测算。",
        "guide": (
            "【适用】已确定要做某产品，系统梳理四要素并和竞品对齐。\n\n"
            "【数据从哪拿】\n"
            "· Product：竞品 Listing + 评论，提炼功能/材质/规格差异。\n"
            "· Price：Keepa 历史价格区间、类目价格带；核算=售价-佣金-头程-FBA-采购。\n"
            "· Place：BSR 榜单结构、类目集中度(头部占比)、新品存活率。\n"
            "· Promotion：前台看 Coupon/LD/BD，卖家精灵看广告流量占比与主投词。"
        ),
        "sections": [
            {
                "id": "obj", "title": "产品与市场背景", "repeat": False, "fields": [
                    {"key": "product", "label": "产品 / 规格 / 目标市场", "type": "text", "required": True},
                ],
            },
            {
                "id": "product", "title": "P1 Product 产品", "repeat": False, "fields": [
                    {"key": "features", "label": "功能 / 材质 / 规格定位", "type": "textarea", "rows": 2},
                    {"key": "diff", "label": "相对竞品的差异化卖点", "type": "textarea", "rows": 2},
                    {"key": "quality", "label": "质量标准 / 认证要求", "type": "select", "options": CERT_OPTS},
                ],
            },
            {
                "id": "price", "title": "P2 Price 价格与利润", "repeat": False, "fields": [
                    {"key": "price_point", "label": "拟定售价 / 价格带", "type": "text", "placeholder": "如：$19.99-$24.99"},
                    {"key": "cogs", "label": "采购成本(出厂价)", "type": "text", "placeholder": "如：¥35 / pcs"},
                    {"key": "fees", "label": "头程+佣金+FBA 估算", "type": "text", "placeholder": "如：头程$2.1+佣金15%+FBA$3.4"},
                    {"key": "margin", "label": "估算毛利 / 毛利率", "type": "text", "placeholder": "如：$4.2 / 21%"},
                ],
            },
            {
                "id": "place", "title": "P3 Place 渠道与布局", "repeat": False, "fields": [
                    {"key": "channel", "label": "销售渠道 / 站点", "type": "select", "options": SITES},
                    {"key": "concentration", "label": "类目集中度 / 头部格局", "type": "textarea", "rows": 2},
                    {"key": "listing_plan", "label": "上架规划(变体/主推款)", "type": "text"},
                ],
            },
            {
                "id": "promotion", "title": "P4 Promotion 推广", "repeat": False, "fields": [
                    {"key": "promo_plan", "label": "推广方案(广告/促销/节奏)", "type": "textarea", "rows": 3},
                    {"key": "keywords", "label": "主投关键词清单", "type": "textarea", "rows": 2},
                ],
            },
            {
                "id": "conclusion", "title": "结论与行动", "repeat": False, "fields": [
                    {"key": "summary", "label": "四要素总结与优先级", "type": "textarea", "rows": 3},
                    {"key": "actions", "label": "下一步行动", "type": "textarea", "rows": 3},
                ],
            },
        ],
    },

    # ============================================================ 4. 波特五力 / 市场进入
    {
        "key": "five-forces",
        "name": "波特五力 · 市场进入分析",
        "icon": "bi-shield-shaded",
        "tone": "danger",
        "desc": "决定要不要进入某个品类：现有竞争、新进入者、替代品、上游议价、下游议价，五股力量 + 市场容量综合打分。",
        "guide": (
            "【适用】拿不准要不要进某品类 / 某站点时做；结论是「进 / 不进 / 怎么进」。\n\n"
            "【数据从哪拿】\n"
            "· 现有竞争强度：头部商品数、价格战程度(Keepa 价格区间)、月销量分布集中度。\n"
            "· 新进入者威胁：New Releases 榜新品数量与起量速度(上架<180天、评论<100 的活跃新品占比)。\n"
            "· 替代品威胁：搜索关键词的周边类目产品、同功能不同形态产品数量。\n"
            "· 上游(供应商)议价能力：1688 同款供应商数量与报价集中度；是否依赖独家模具/独家料。\n"
            "· 下游(买家/平台)议价能力：买家品牌忠诚度、大促折扣常态化程度、平台抽佣与广告成本占比。\n\n"
            "每力按 1-5 分自评(1=弱威胁/有利, 5=强威胁/不利)，综合给判断。"
        ),
        "sections": [
            {
                "id": "obj", "title": "目标品类 / 市场", "repeat": False, "fields": [
                    {"key": "niche", "label": "目标品类", "type": "text", "required": True, "placeholder": "如：便携筋膜枪"},
                    {"key": "market", "label": "目标市场", "type": "select", "options": SITES},
                    {"key": "capacity", "label": "市场容量判断", "type": "textarea", "rows": 2,
                     "placeholder": "搜索量/月销总量/头部月销，判断市场够不够大、有没有空间"},
                ],
            },
            {
                "id": "forces", "title": "五力逐一评估", "repeat": False, "fields": [
                    {"key": "rival", "label": "现有竞争强度 (评分1-5)", "type": "text", "placeholder": "分数 + 依据"},
                    {"key": "entrant", "label": "新进入者威胁 (1-5)", "type": "text"},
                    {"key": "substitute", "label": "替代品威胁 (1-5)", "type": "text"},
                    {"key": "supplier", "label": "上游/供应商议价力 (1-5)", "type": "text", "placeholder": "供应商数量、独家程度"},
                    {"key": "buyer", "label": "下游/平台议价力 (1-5)", "type": "text"},
                ],
            },
            {
                "id": "conclusion", "title": "结论", "repeat": False, "fields": [
                    {"key": "avg", "label": "综合判断 / 平均得分", "type": "text"},
                    {"key": "decision", "label": "进入决策", "type": "select",
                     "options": ["进入", "暂缓(条件不成熟)", "不进入", "换差异化细分再评估"]},
                    {"key": "risk", "label": "主要风险与对策", "type": "textarea", "rows": 3},
                ],
            },
        ],
    },

    # ============================================================ 5. 市场价格带与定价
    {
        "key": "price-band",
        "name": "市场价格带与定价分析",
        "icon": "bi-bar-chart-fill",
        "tone": "success",
        "desc": "收集类目 TOP 竞品的价格/销量/评论样本，画出价格带分布，反推「目标定价 → 目标采购成本」。采购定价闭环。",
        "guide": (
            "【适用】定自己产品的售价区间，并倒推能接受的采购成本(Max COGS)。\n\n"
            "【怎么收集样本】在 BSR 榜/搜索结果页取 8-15 个有代表性的竞品(头部/中部/尾部都覆盖)，逐个记录：售价、预估月销、BSR、评论数。用「＋ 添加价格样本」逐条录入。\n\n"
            "【数据从哪拿】\n"
            "· 售价/评论/BSR：亚马逊前台。\n"
            "· 预估月销：卖家精灵 / Jungle Scout / Helium10，或用加购测试法。\n"
            "· 历史价格区间：Keepa。\n\n"
            "【怎么用】样本填完后填「价格带总结」：主流成交带在哪？目标价取带内偏下以打新品期。再用公式反推：Max 采购成本 = 售价×(1-佣金率) - 头程 - FBA - 目标毛利，去 1688 找满足该成本的产品。"
        ),
        "sections": [
            {
                "id": "obj", "title": "分析对象", "repeat": False, "fields": [
                    {"key": "product", "label": "产品关键词 / 类目", "type": "text", "required": True},
                    {"key": "market", "label": "目标市场", "type": "select", "options": SITES},
                    {"key": "sample_count", "label": "计划样本数", "type": "number", "step": "1", "placeholder": "建议 8-15"},
                ],
            },
            {
                "id": "samples", "title": "价格样本(逐条录入)", "repeat": True, "fields": [
                    {"key": "name", "label": "竞品名称/品牌", "type": "text", "required": True},
                    {"key": "price", "label": "售价", "type": "number", "step": "0.01"},
                    {"key": "monthly", "label": "预估月销", "type": "number", "step": "1"},
                    {"key": "bsr", "label": "BSR 排名", "type": "text"},
                    {"key": "reviews", "label": "评论数", "type": "number", "step": "1"},
                    {"key": "note", "label": "备注(变体/促销等)", "type": "text"},
                ],
            },
            {
                "id": "conclusion", "title": "定价结论", "repeat": False, "fields": [
                    {"key": "band", "label": "主流价格带总结", "type": "textarea", "rows": 2},
                    {"key": "target_price", "label": "目标定价", "type": "text"},
                    {"key": "max_cogs", "label": "倒推最大采购成本(COGS)", "type": "text",
                     "placeholder": "= 售价×(1-佣金) - 头程 - FBA - 目标毛利"},
                    {"key": "supply_check", "label": "1688/供应商匹配结果", "type": "textarea", "rows": 2,
                     "placeholder": "有无该成本档供应商、要降本需改什么(材质/尺寸/MOQ)"},
                ],
            },
        ],
    },

    # ============================================================ 6. 供应商对比(采购视角)
    {
        "key": "supplier-compare",
        "name": "供应商横向对比(采购视角)",
        "icon": "bi-truck-flatbed",
        "tone": "secondary",
        "desc": "同一款产品找多个候选供应商，对比报价/MOQ/交期/认证/质量/产能，输出「选谁、怎么谈、有什么风险」。",
        "guide": (
            "【适用】产品已定，在 1688/工厂/展会/阿里国际站 找到 3-5 家候选供应商后横向比选。\n\n"
            "【怎么找供应商】可配合本工具「工厂匹配/识图搜索」先用关键词找工厂，再去 1688 看同款报价与工厂信息。\n\n"
            "【每组填什么】一家供应商一组，用「＋ 添加供应商」逐家录入。关键数据获取方法：\n"
            "· 报价/MOQ/交期：直接 1688 在线沟通或询盘，报价务必问清「含不含模具/税/运费」。\n"
            "· 认证/验厂报告：要求对方提供证书或 SGS 验厂报告；工商主体可在天眼查/Apizero 核验(本工具工厂模块已接)。\n"
            "· 产能/交期稳定性：问月产能、是否有其他大客户排产。\n"
            "· 样品：付费打样最见真章，要求寄样前确认规格书。\n\n"
            "填完在「结论」里打分排序(质量×报价×交期×配合度)，定首选与备选，并列出谈判要点与风险。"
        ),
        "sections": [
            {
                "id": "obj", "title": "采购需求", "repeat": False, "fields": [
                    {"key": "product", "label": "产品 / 规格书要点", "type": "text", "required": True},
                    {"key": "qty", "label": "目标采购量", "type": "text", "placeholder": "如：首批 5,000 pcs，月返单 2,000"},
                    {"key": "market", "label": "目标市场 / 需证书", "type": "text", "placeholder": "如：美国站，需 FCC/UL"},
                ],
            },
            {
                "id": "suppliers", "title": "候选供应商(逐家录入)", "repeat": True, "fields": [
                    {"key": "name", "label": "供应商名称", "type": "text", "required": True},
                    {"key": "channel", "label": "来源渠道", "type": "select", "options": CHANNELS},
                    {"key": "location", "label": "所在地", "type": "text", "placeholder": "如：浙江 余姚"},
                    {"key": "quote", "label": "报价(币种/单位)", "type": "text", "placeholder": "如：¥3.2/pcs 含税含运"},
                    {"key": "moq", "label": "MOQ", "type": "text"},
                    {"key": "leadtime", "label": "交期", "type": "text", "placeholder": "如：打样7天/量产15天"},
                    {"key": "sample", "label": "样品费 / 是否寄样", "type": "text"},
                    {"key": "payment", "label": "付款方式", "type": "select", "options": PAYMENTS},
                    {"key": "certs", "label": "认证 / 验厂", "type": "select", "options": CERT_OPTS + ["待索要证书"]},
                    {"key": "capacity", "label": "月产能 / 大客户", "type": "text"},
                    {"key": "note", "label": "质量口碑 / 沟通备注", "type": "text"},
                ],
            },
            {
                "id": "conclusion", "title": "结论", "repeat": False, "fields": [
                    {"key": "ranking", "label": "综合排序与理由", "type": "textarea", "rows": 3},
                    {"key": "choice", "label": "首选 / 备选", "type": "text"},
                    {"key": "negotiate", "label": "谈判要点", "type": "textarea", "rows": 2, "placeholder": "降MOQ/锁价期/含检含运/账期"},
                    {"key": "risk", "label": "风险与对策", "type": "textarea", "rows": 2, "placeholder": "产能、质量波动、汇兑、合规"},
                ],
            },
        ],
    },
]

# 便捷查找
TEMPLATE_MAP = {t["key"]: t for t in TEMPLATES}
