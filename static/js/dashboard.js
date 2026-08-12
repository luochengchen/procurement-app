// Dashboard — stats, category chart, featured materials
let statsChart = null;
let statsData = [];

document.addEventListener("DOMContentLoaded", () => {
    loadFeatured();
    loadStats();
});

// 主题切换时重绘图表
window.redrawCharts = renderStatsChart;

// ---- 分类分布柱状图 ----
async function loadStats() {
    try {
        const res = await fetch("/api/materials/stats");
        if (!res.ok) return;
        statsData = await res.json();
        renderStatsChart();
    } catch (e) {
        /* 静默：图表失败不影响主数据 */
    }
}

function renderStatsChart() {
    const canvas = document.getElementById("statsChart");
    if (!canvas || !statsData.length) return;

    const colors = window.chartColors();
    const sorted = [...statsData].sort((a, b) => b.count - a.count);

    if (statsChart) statsChart.destroy();

    statsChart = new Chart(canvas, {
        type: "bar",
        data: {
            labels: sorted.map((d) => `${d.icon} ${d.category}`),
            datasets: [
                {
                    data: sorted.map((d) => d.count),
                    backgroundColor: colors.series1,
                    borderRadius: 4,
                    barThickness: 18,
                },
            ],
        },
        options: {
            indexAxis: "y",
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: colors.surface,
                    titleColor: colors.ink,
                    bodyColor: colors.ink,
                    borderColor: colors.gridline,
                    borderWidth: 1,
                    callbacks: {
                        label: (ctx) => ` ${ctx.parsed.x} 种材料`,
                    },
                },
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0,
                        color: colors.muted,
                        font: { size: 11 },
                    },
                    grid: { color: colors.gridline, drawTicks: false },
                    border: { display: false },
                },
                y: {
                    ticks: {
                        color: colors.ink,
                        font: { size: 12 },
                    },
                    grid: { display: false },
                    border: { display: false },
                },
            },
        },
    });
}

// ---- 精选材料卡片 ----
async function loadFeatured() {
    const container = document.getElementById("featuredMaterials");
    try {
        const res = await fetch("/api/materials/featured");
        if (!res.ok) throw new Error("加载失败");
        const materials = await res.json();

        // 统计
        const categories = new Set(materials.map((m) => m.category_name));
        const up = materials.filter((m) => m.trend === "up").length;
        const down = materials.filter((m) => m.trend === "down").length;
        document.getElementById("statCategories").textContent = categories.size;
        document.getElementById("statUpdated").textContent = materials.length;
        document.getElementById("statUp").textContent = up;
        document.getElementById("statDown").textContent = down;

        if (!materials.length) {
            container.innerHTML =
                '<p class="text-muted text-center py-4">暂无数据</p>';
            return;
        }

        const trend = { up: ["↑", "trend-up"], down: ["↓", "trend-down"], stable: ["→", "trend-stable"] };
        container.innerHTML = `<div class="row g-2">${materials
            .slice(0, 9)
            .map((m) => {
                const [arrow, cls] = trend[m.trend] || trend.stable;
                return `
                <div class="col-md-6 col-xl-4">
                    <div class="d-flex align-items-center justify-content-between p-2 rounded-3" style="background: color-mix(in srgb, var(--gridline) 40%, transparent)">
                        <div class="text-truncate me-2">
                            <div class="fw-semibold text-truncate" style="font-size:0.88rem">${m.name}</div>
                            <small class="text-muted">${m.spec || m.unit}</small>
                        </div>
                        <div class="text-end flex-shrink-0">
                            <div class="fw-bold" style="font-size:0.9rem; font-variant-numeric: tabular-nums">${m.current_price.toFixed(2)}</div>
                            <small class="${cls}" style="font-size:0.78rem">${arrow} ${m.unit}</small>
                        </div>
                    </div>
                </div>`;
            })
            .join("")}</div>`;
    } catch (e) {
        container.innerHTML = `<p class="text-danger text-center py-4">${e.message}</p>`;
    }
}
