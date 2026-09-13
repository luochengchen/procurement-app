// 全站「放图片」组件 —— 材料/成本/认证/工厂/竞品/识图 六个页面共用同一个实现。
//
// 关键设计：
//  1. 不声明任何顶层全局变量，只挂 window.ImageDrop，避免与各页现有全局 const 撞名。
//  2. 每个实例的 DOM 查询都走 root.querySelector，支持同页多实例。
//  3. 上传前用 canvas 在浏览器端压缩（长边 1280 / q0.85）—— 不引入服务端 Pillow 依赖。
//  4. 识别结果由页面自己的 onRecognized 回调决定怎么用（填搜索框 / 跳转 / 预填）。
//
// 自动挂载：页面里放好 partial 后，本脚本会在 DOMContentLoaded 时扫描 .img-drop，
// 从 data-target 读取行为类型；也可以手动调 window.ImageDrop.mount(el, opts)。
(function () {
    "use strict";

    const MAX_SIDE = 1280;
    const QUALITY = 0.85;

    let lastActive = null;   // 鼠标悬停/聚焦过的实例，供 Ctrl+V 粘贴定向投递

    // ---- 页面行为表：data-target → onRecognized ----
    const TARGETS = {
        // 填入页面上的某个输入框并触发它的搜索（details 见各页挂载点）
        fillSearch(el, kw, data) {
            const inputId = el.dataset.input || "searchInput";
            const input = document.getElementById(inputId);
            if (!input) return false;
            input.value = kw;
            input.dispatchEvent(new Event("input", { bubbles: true }));
            const btn = document.getElementById(el.dataset.trigger || "searchBtn");
            if (btn) btn.click();
            return true;
        },
        // 跳到指定页面并带上关键词
        goto(el, kw) {
            const base = el.dataset.goto || "/factory";
            window.location.href = `${base}?q=${encodeURIComponent(kw)}`;
            return true;
        },
        // 只把关键词交给页面自定义逻辑（由页面自己 mount 并提供回调）
        manual() { return false; },
    };

    function defaultHandler(el, kw, data, opts) {
        if (opts && opts.onRecognized) return opts.onRecognized(kw, data);
        const kind = el.dataset.target || "manual";
        const fn = TARGETS[kind] || TARGETS.manual;
        return fn(el, kw, data);
    }

    // ---------------------------------------------------------------
    // 图片压缩：canvas 重绘，避免手机原图 5-10MB 直接打满上传
    // ---------------------------------------------------------------
    function compress(file) {
        return new Promise((resolve) => {
            const url = URL.createObjectURL(file);
            const img = new Image();
            img.onload = () => {
                URL.revokeObjectURL(url);
                let { width, height } = img;
                const scale = Math.min(1, MAX_SIDE / Math.max(width, height));
                width = Math.round(width * scale);
                height = Math.round(height * scale);
                const canvas = document.createElement("canvas");
                canvas.width = width;
                canvas.height = height;
                canvas.getContext("2d").drawImage(img, 0, 0, width, height);
                canvas.toBlob(
                    (blob) => resolve(blob ? { blob, url: canvas.toDataURL("image/jpeg", QUALITY) } : { blob: file, url }),
                    "image/jpeg",
                    QUALITY
                );
            };
            // 解码失败（非图片/损坏文件）时退回原文件，交给后端报错
            img.onerror = () => { URL.revokeObjectURL(url); resolve({ blob: file, url: "" }); };
            img.src = url;
        });
    }

    function mount(root, opts) {
        opts = opts || {};
        const zone = root.querySelector('[data-role="zone"]');
        const fileInput = root.querySelector('[data-role="file"]');
        const preview = root.querySelector('[data-role="preview"]');
        const imgEl = root.querySelector('[data-role="img"]');
        const kwInput = root.querySelector('[data-role="kw"]');
        const goBtn = root.querySelector('[data-role="go"]');
        const resetBtn = root.querySelector('[data-role="reset"]');
        const noteEl = root.querySelector('[data-role="note"]');
        if (!zone || !fileInput) return null;

        let picked = null;   // { blob, url }

        function reset() {
            picked = null;
            fileInput.value = "";
            preview.classList.add("d-none");
            zone.classList.remove("d-none");
            noteEl.textContent = "";
            if (kwInput) kwInput.value = "";
        }

        function note(text, tone) {
            noteEl.className = "img-drop-note small " + (tone === "error" ? "text-danger" : "text-muted");
            noteEl.textContent = text || "";
        }

        async function accept(file) {
            if (!file) return;
            if (!file.type.startsWith("image/")) {
                note("请选择图片文件（JPG / PNG / WebP）", "error");
                return;
            }
            note("正在处理图片…");
            picked = await compress(file);
            imgEl.src = picked.url || URL.createObjectURL(picked.blob);
            preview.classList.remove("d-none");
            zone.classList.add("d-none");
            note("图片已就绪，点「识别并搜索」继续");
            if (root.dataset.auto === "1") run();
        }

        async function run() {
            if (!picked) return;
            goBtn.disabled = true;
            note("正在识别…");
            try {
                const fd = new FormData();
                fd.append("image", picked.blob, "upload.jpg");
                fd.append("keyword", (kwInput && kwInput.value.trim()) || "");
                const res = await fetch("/api/image-search/upload", { method: "POST", body: fd });
                const data = await res.json();
                if (!res.ok) throw new Error(data.error || "识别失败");

                const kw = (data.keyword || "").trim();
                if (!kw) {
                    note("没得到可用关键词，请在上方手动补充后重试", "error");
                    return;
                }
                // 明确告诉用户这次到底是「AI 视觉识别」还是「按你填的关键词搜索」
                const engineLabel = data.engine === "keyword"
                    ? "未启用 AI 视觉识别，按关键词搜索"
                    : `识别引擎：${data.engine}`;
                note(`${engineLabel} · 关键词「${kw}」`);

                const handled = defaultHandler(root, kw, data, opts);
                if (!handled) note(`关键词「${kw}」已就绪${data.note ? " · " + data.note : ""}`);
            } catch (e) {
                note(`失败：${e.message}`, "error");
            } finally {
                goBtn.disabled = false;
            }
        }

        zone.addEventListener("click", () => fileInput.click());
        zone.addEventListener("keydown", (e) => {
            if (e.key === "Enter" || e.key === " ") { e.preventDefault(); fileInput.click(); }
        });
        fileInput.addEventListener("change", (e) => accept(e.target.files[0]));
        resetBtn.addEventListener("click", reset);
        goBtn.addEventListener("click", run);

        ["dragenter", "dragover"].forEach((ev) =>
            zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.add("drag-over"); }));
        ["dragleave", "drop"].forEach((ev) =>
            zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.remove("drag-over"); }));
        zone.addEventListener("drop", (e) => accept(e.dataTransfer.files[0]));

        // Ctrl+V 粘贴：记录最近交互过的实例，把图片投给它
        zone.addEventListener("mouseenter", () => { lastActive = api; });
        zone.addEventListener("focus", () => { lastActive = api; });

        const api = { root, accept, reset, run };
        return api;
    }

    // 页面里所有 .img-drop 自动挂载；同页多实例时粘贴投给最近悬停的那个
    document.addEventListener("DOMContentLoaded", () => {
        // data-manual="1" 的实例由页面脚本自行 mount（需要自定义回调），这里跳过避免重复绑定
        const all = Array.from(document.querySelectorAll('.img-drop:not([data-manual="1"])'));
        all.forEach((el) => {
            const api = mount(el, { onRecognized: window.ImageDropHandlers && window.ImageDropHandlers[el.id] });
            if (api && !lastActive) lastActive = api;
        });

        document.addEventListener("paste", (e) => {
            const items = (e.clipboardData || {}).items || [];
            for (const it of items) {
                if (it.type && it.type.startsWith("image/")) {
                    e.preventDefault();
                    const target = lastActive || (all[0] ? mount(all[0], {}) : null);
                    if (target) target.accept(it.getAsFile());
                    return;
                }
            }
        });
    });

    window.ImageDrop = { mount };
})();
