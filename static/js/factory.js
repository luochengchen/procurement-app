// Factory matching — search factories by product/region/scale, view detail.
// 渲染逻辑统一走 window.FactoryUI（static/js/factory_common.js）
window.currentFactories = window.currentFactories || [];   // 供识图页等其他脚本读取

let factoryModal = null;

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("searchBtn").addEventListener("click", searchFactories);
    document.getElementById("searchInput").addEventListener("keydown", (e) => {
        if (e.key === "Enter") searchFactories();
    });
    document.getElementById("onlyManufacturer").addEventListener("change", searchFactories);
    factoryModal = new bootstrap.Modal(document.getElementById("factoryModal"));

    // 热门品类快捷搜索
    document.querySelectorAll(".hot-cat").forEach((el) => {
        el.addEventListener("click", () => {
            document.getElementById("searchInput").value = el.dataset.cat;
            searchFactories();
        });
    });

    // 支持从识图搜索联动跳转：/factory?q=<产品关键词>
    const q = new URLSearchParams(window.location.search).get("q");
    if (q) {
        document.getElementById("searchInput").value = q;
        searchFactories();
    }
});

async function searchFactories() {
    const q = document.getElementById("searchInput").value.trim();
    const region = document.getElementById("regionFilter").value.trim();
    const industry = document.getElementById("industryFilter").value;
    const scale = document.getElementById("scaleFilter").value;
    const sort = document.getElementById("sortBy").value;
    const onlyManufacturer = document.getElementById("onlyManufacturer").checked;

    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (region) params.set("region", region);
    if (industry) params.set("industry", industry);
    if (scale) params.set("scale", scale);
    if (onlyManufacturer) params.set("only_manufacturer", "1");
    params.set("sort", sort);

    const tbody = document.getElementById("factoryTable");
    const countEl = document.getElementById("resultCount");
    const noticeEl = document.getElementById("factoryNotice");
    tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4"><div class="spinner-border spinner-border-sm"></div> 匹配中...</td></tr>';
    noticeEl.classList.add("d-none");

    try {
        const res = await fetch(`/api/factory?${params}`);
        if (!res.ok) throw new Error("查询失败");
        const data = await res.json();

        window.currentFactories = data.results || [];
        const sourceLabel = data.data_source ? ` · 数据源：${data.data_source}` : "";
        countEl.textContent = `共 ${data.total} 家工厂${sourceLabel}`;

        // 数据源降级原因必须让用户看到，否则会误以为「这个功能就是假的」
        if (data.notice) {
            noticeEl.className = "alert alert-warning py-2 small mb-3";
            noticeEl.innerHTML = `<i class="bi bi-exclamation-triangle me-1"></i>${FactoryUI.escapeHtml(data.notice)}`;
            noticeEl.classList.remove("d-none");
        }
        renderKeywordHint(data.keywords, q);

        if (!data.total) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">未找到匹配的工厂，换个关键词或放宽筛选条件试试</td></tr>';
            return;
        }

        tbody.innerHTML = data.results.map(FactoryUI.renderRow).join("");
        tbody.querySelectorAll(".view-detail").forEach((btn) => {
            btn.addEventListener("click", () => openDetail(btn.dataset.id));
        });
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center text-danger py-4">加载失败: ${FactoryUI.escapeHtml(e.message)}</td></tr>`;
    }
}

// 展示本次实际检索了哪些同义词 —— 让用户理解结果为什么变多，也提示可以手动换词
function renderKeywordHint(keywords, q) {
    const el = document.getElementById("keywordHint");
    if (!el) return;
    const extra = (keywords || []).filter((k) => k !== q);
    if (!q || !extra.length) {
        el.classList.add("d-none");
        return;
    }
    el.className = "text-muted small mb-2";
    el.innerHTML = `<i class="bi bi-shuffle me-1"></i>本次同时检索了同义词：${extra.map((k) => `<span class="badge-soft me-1">${FactoryUI.escapeHtml(k)}</span>`).join("")}`;
    el.classList.remove("d-none");
}

function openDetail(id) {
    const f = window.currentFactories.find((x) => String(x.id) === String(id));
    if (!f) return alert("未找到工厂详情");

    document.getElementById("factoryTitle").textContent = f.name;
    document.getElementById("factoryBody").innerHTML = FactoryUI.renderDetail(f);
    factoryModal.show();
}
