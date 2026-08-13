// Materials query + price history chart
let historyChart = null;
let historyModal = null;

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("searchBtn").addEventListener("click", searchMaterials);
    document.getElementById("searchInput").addEventListener("keydown", (e) => {
        if (e.key === "Enter") searchMaterials();
    });
    historyModal = new bootstrap.Modal(document.getElementById("historyModal"));
    searchMaterials();
});

// 主题切换重绘
window.redrawCharts = () => {
    if (historyChart) renderHistoryChart(historyChart._data);
};

async function searchMaterials() {
    const q = document.getElementById("searchInput").value.trim();
    const category = document.getElementById("categoryFilter").value;
    const region = document.getElementById("regionFilter").value;
    const sort = document.getElementById("sortBy").value;

    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (category) params.set("category", category);
    if (region) params.set("region", region);
    params.set("sort", sort);

    const tbody = document.getElementById("materialsTable");
    const countEl = document.getElementById("resultCount");
    tbody.innerHTML = '<tr><td colspan="9" class="text-center py-4"><div class="spinner-border spinner-border-sm"></div> 查询中...</td></tr>';

    try {
        const res = await fetch(`/api/materials?${params}`);
        if (!res.ok) throw new Error("查询失败");
        const materials = await res.json();

        countEl.textContent = `共 ${materials.length} 条`;
        if (!materials.length) {
            tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted py-4">未找到匹配材料</td></tr>';
            return;
        }

        const trend = { up: ["↑", "trend-up"], down: ["↓", "trend-down"], stable: ["→", "trend-stable"] };
        tbody.innerHTML = materials
            .map((m) => {
                const [arrow, cls] = trend[m.trend] || trend.stable;
                return `
                <tr>
                    <td><span class="badge-soft">${m.category_name}</span></td>
                    <td><strong>${m.name}</strong></td>
                    <td class="text-muted">${m.spec}</td>
                    <td><span class="badge-soft">${m.region}</span></td>
                    <td>${m.unit}</td>
                    <td><strong style="font-variant-numeric: tabular-nums">${m.currency} ${m.current_price.toFixed(2)}</strong></td>
                    <td><span class="${cls} fw-bold">${arrow}</span></td>
                    <td class="text-muted">${m.price_date}</td>
                    <td class="text-end">
                        <button class="btn btn-sm btn-outline-primary view-history"
                            data-id="${m.id}" data-name="${m.name}" data-unit="${m.unit}">
                            <i class="bi bi-graph-up"></i>
                        </button>
                    </td>
                </tr>`;
            })
            .join("");

        // 绑定历史按钮
        tbody.querySelectorAll(".view-history").forEach((btn) => {
            btn.addEventListener("click", () => loadHistory(btn));
        });
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="9" class="text-center text-danger py-4">加载失败: ${e.message}</td></tr>`;
    }
}

async function loadHistory(btn) {
    const id = btn.dataset.id;
    const name = btn.dataset.name;
    const unit = btn.dataset.unit;

    document.getElementById("historyTitle").textContent = `${name} 价格历史 (${unit})`;
    historyModal.show();

    try {
        const res = await fetch(`/api/materials/${id}/history`);
        if (!res.ok) throw new Error("加载历史失败");
        const history = await res.json();
        // 按日期正序
        history.sort((a, b) => a.recorded_date.localeCompare(b.recorded_date));
        renderHistoryChart(history);
        renderHistoryTable(history);
    } catch (e) {
        alert(e.message);
    }
}

function renderHistoryChart(history) {
    const canvas = document.getElementById("historyChart");
    if (!canvas || !history || !history.length) return;

    const colors = window.chartColors();
    const labels = history.map((h) => h.recorded_date);
    const values = history.map((h) => h.price);

    if (historyChart) historyChart.destroy();

    historyChart = new Chart(canvas, {
        type: "line",
        data: {
            labels,
            datasets: [
                {
                    data: values,
                    borderColor: colors.series1,
                    backgroundColor: colors.series1,
                    borderWidth: 2,
                    pointRadius: 3,
                    pointHoverRadius: 6,
                    tension: 0.3,
                    fill: false,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: "index", intersect: false },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: colors.surface,
                    titleColor: colors.ink,
                    bodyColor: colors.ink,
                    borderColor: colors.gridline,
                    borderWidth: 1,
                    callbacks: {
                        label: (ctx) => ` ${ctx.parsed.y.toFixed(2)}`,
                    },
                },
            },
            scales: {
                x: {
                    ticks: { color: colors.muted, font: { size: 11 }, maxRotation: 45 },
                    grid: { display: false },
                    border: { display: false },
                },
                y: {
                    ticks: { color: colors.muted, font: { size: 11 } },
                    grid: { color: colors.gridline, drawTicks: false },
                    border: { display: false },
                },
            },
        },
    });
    // 缓存数据供主题切换重绘
    historyChart._data = history;
}

function renderHistoryTable(history) {
    const tbody = document.querySelector("#historyTable tbody");
    tbody.innerHTML = history
        .map((h, i) => {
            let delta = "";
            if (i > 0) {
                const diff = h.price - history[i - 1].price;
                const pct = ((diff / history[i - 1].price) * 100).toFixed(1);
                const cls = diff > 0 ? "trend-up" : diff < 0 ? "trend-down" : "trend-stable";
                const arrow = diff > 0 ? "↑" : diff < 0 ? "↓" : "→";
                delta = `<span class="${cls}">${arrow} ${diff.toFixed(2)} (${pct}%)</span>`;
            }
            return `
            <tr>
                <td>${h.recorded_date}</td>
                <td style="font-variant-numeric: tabular-nums">${h.price.toFixed(2)}</td>
                <td>${delta || "-"}</td>
            </tr>`;
        })
        .join("");
}
