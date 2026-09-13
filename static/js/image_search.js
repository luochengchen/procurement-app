// 识图搜索页 —— 图片识别 + 真实工厂匹配。
//
// 图片上传/识别统一走 window.ImageDrop（static/js/image_drop.js），
// 工厂表格与详情统一走 window.FactoryUI（static/js/factory_common.js）。
// 本文件只负责「识别完之后干什么」以及工厂筛选面板。
let imgFactories = [];
let imgFactoryModal = null;

document.addEventListener("DOMContentLoaded", () => {
    imgFactoryModal = new bootstrap.Modal(document.getElementById("imgFactoryModal"));

    document.getElementById("imgFactoryBtn").addEventListener("click", searchImgFactories);
    document.getElementById("imgFactoryQ").addEventListener("keydown", (e) => {
        if (e.key === "Enter") searchImgFactories();
    });

    // 自定义识别回调：图片识别出的关键词直接驱动工厂匹配
    const dropRoot = document.getElementById("imgDrop");
    if (dropRoot) {
        ImageDrop.mount(dropRoot, { onRecognized: onRecognized });
    }

    loadImgFactoryFilters();

    // 支持 /image-search?q= 直接带关键词进来
    const q = new URLSearchParams(window.location.search).get("q");
    if (q) {
        document.getElementById("imgFactoryQ").value = q;
    }
    searchImgFactories();
});

// 识别完成：展示识别详情 + 触发工厂匹配
function onRecognized(keyword, data) {
    renderRecognition(data);
    document.getElementById("imgFactoryQ").value = keyword;
    searchImgFactories();
}

function renderRecognition(data) {
    const box = document.getElementById("recogBox");
    const engineLabel = data.engine === "keyword"
        ? '<span class="badge-soft text-warning">未启用 AI 识图 · 按关键词检索</span>'
        : `<span class="badge-soft text-success">识别引擎 ${FactoryUI.escapeHtml(data.engine)}</span>`;

    const chips = (data.candidates || []).map((c) =>
        `<button type="button" class="badge-soft me-1 use-candidate" data-kw="${FactoryUI.escapeHtml(c)}">${FactoryUI.escapeHtml(c)}</button>`
    ).join("");

    box.innerHTML = `
        <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
            ${engineLabel}
            ${data.category ? `<span class="badge-soft">品类：${FactoryUI.escapeHtml(data.category)}</span>` : ""}
            ${data.material ? `<span class="badge-soft">材质：${FactoryUI.escapeHtml(data.material)}</span>` : ""}
        </div>
        <div class="fw-semibold mb-1">检索关键词：${FactoryUI.escapeHtml(data.keyword || "—")}</div>
        ${data.desc ? `<div class="text-muted small mb-2">${FactoryUI.escapeHtml(data.desc)}</div>` : ""}
        ${chips ? `<div class="mb-2 small text-muted">同义检索词：${chips}</div>` : ""}
        ${data.note ? `<div class="alert alert-warning py-2 small mb-0">${FactoryUI.escapeHtml(data.note)}</div>` : ""}
    `;
    box.classList.remove("d-none");
    const ph = document.getElementById("recogPlaceholder");
    if (ph) ph.classList.add("d-none");

    box.querySelectorAll(".use-candidate").forEach((el) => {
        el.addEventListener("click", () => {
            document.getElementById("imgFactoryQ").value = el.dataset.kw;
            searchImgFactories();
        });
    });
}

async function loadImgFactoryFilters() {
    try {
        const res = await fetch("/api/factory/filters");
        const data = await res.json();
        const fill = (id, items, placeholder, valueKey) => {
            const sel = document.getElementById(id);
            if (!sel) return;
            sel.innerHTML = (placeholder ? `<option value="">${placeholder}</option>` : "") +
                items.map((it) => {
                    const v = valueKey ? it[valueKey] : it;
                    const label = valueKey ? it.label : it;
                    return `<option value="${FactoryUI.escapeHtml(v)}">${FactoryUI.escapeHtml(label)}</option>`;
                }).join("");
        };
        // 地区用 datalist：真实地址是「浙江省宁波市北仑区…」，等值下拉筛不出东西，得能自由输入
        const regionList = document.getElementById("imgRegionList");
        if (regionList) {
            regionList.innerHTML = (data.regions || [])
                .map((r) => `<option value="${FactoryUI.escapeHtml(r)}"></option>`).join("");
        }
        fill("imgFactoryIndustry", data.industries || [], "全部行业");
        fill("imgFactoryScale", data.scales || [], "不限规模", "value");
        fill("imgFactorySort", data.sorts || [], "", "value");

        // 热门品类快捷入口
        const hot = document.getElementById("imgHotCats");
        if (hot) {
            hot.innerHTML = (data.hot_categories || []).map((c) =>
                `<button type="button" class="badge-soft me-1 use-hot" data-kw="${FactoryUI.escapeHtml(c)}">${FactoryUI.escapeHtml(c)}</button>`
            ).join("");
            hot.querySelectorAll(".use-hot").forEach((el) => {
                el.addEventListener("click", () => {
                    document.getElementById("imgFactoryQ").value = el.dataset.kw;
                    searchImgFactories();
                });
            });
        }
    } catch (e) {
        /* 筛选项加载失败不阻断主流程 */
    }
}

async function searchImgFactories() {
    const q = document.getElementById("imgFactoryQ").value.trim();
    const region = document.getElementById("imgFactoryRegion").value.trim();
    const industry = document.getElementById("imgFactoryIndustry").value;
    const scale = document.getElementById("imgFactoryScale").value;
    const sort = document.getElementById("imgFactorySort").value;
    const onlyMfr = document.getElementById("imgOnlyManufacturer").checked;

    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (region) params.set("region", region);
    if (industry) params.set("industry", industry);
    if (scale) params.set("scale", scale);
    if (onlyMfr) params.set("only_manufacturer", "1");
    params.set("sort", sort || "relevance");

    const tbody = document.getElementById("imgFactoryTable");
    const countEl = document.getElementById("imgFactoryCount");
    const noticeEl = document.getElementById("imgFactoryNotice");
    tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4"><div class="spinner-border spinner-border-sm"></div> 匹配中...</td></tr>';
    noticeEl.classList.add("d-none");

    try {
        const res = await fetch(`/api/factory?${params}`);
        if (!res.ok) throw new Error("查询失败");
        const data = await res.json();

        imgFactories = data.results || [];
        countEl.textContent = `共 ${data.total} 家${data.data_source ? " · 数据源：" + data.data_source : ""}`;

        if (data.notice) {
            noticeEl.className = "alert alert-warning py-2 small mb-2";
            noticeEl.innerHTML = `<i class="bi bi-exclamation-triangle me-1"></i>${FactoryUI.escapeHtml(data.notice)}`;
            noticeEl.classList.remove("d-none");
        }

        if (!data.total) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">没有匹配到工厂，换个关键词或放宽筛选条件</td></tr>';
            return;
        }

        tbody.innerHTML = data.results.map(FactoryUI.renderRow).join("");
        tbody.querySelectorAll(".view-detail").forEach((btn) => {
            btn.addEventListener("click", () => openImgFactoryDetail(btn.dataset.id));
        });
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center text-danger py-4">加载失败: ${FactoryUI.escapeHtml(e.message)}</td></tr>`;
    }
}

function openImgFactoryDetail(id) {
    const f = imgFactories.find((x) => String(x.id) === String(id));
    if (!f) return alert("未找到工厂详情");
    document.getElementById("imgFactoryTitle").textContent = f.name;
    document.getElementById("imgFactoryBody").innerHTML = FactoryUI.renderDetail(f);
    imgFactoryModal.show();
}
