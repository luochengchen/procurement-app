// Competitor analysis — pick a template, fill data, generate a usable report
let currentTemplate = null;
let lastResult = null;
let reportModal = null;

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".pick-tpl").forEach((btn) => {
        btn.addEventListener("click", () => {
            const key = btn.closest(".tpl-card").dataset.key;
            selectTemplate(key);
        });
    });
    document.getElementById("backToPicker").addEventListener("click", () => {
        document.getElementById("tplEditor").classList.add("d-none");
        document.getElementById("tplPicker").classList.remove("d-none");
    });
    document.getElementById("clearFormBtn").addEventListener("click", clearForm);
    document.getElementById("genReportBtn").addEventListener("click", generateReport);

    // 报告弹窗事件
    reportModal = new bootstrap.Modal(document.getElementById("reportModal"));
    document.querySelectorAll(".report-tab").forEach((tab) => {
        tab.addEventListener("click", () => switchTab(tab.dataset.tab));
    });
    document.getElementById("dlHtmlBtn").addEventListener("click", () => download(".html", "text/html", lastResult.html));
    document.getElementById("dlMdBtn").addEventListener("click", () => download(".md", "text/markdown", lastResult.markdown));
    document.getElementById("copyMdBtn").addEventListener("click", copyMarkdown);
    document.getElementById("printBtn").addEventListener("click", () => {
        const fr = document.getElementById("reportFrame");
        if (fr.contentWindow) fr.contentWindow.print();
    });
});

async function selectTemplate(key) {
    // 若编辑器已有内容，切模板前先确认
    if (!document.getElementById("tplEditor").classList.contains("d-none") && hasFormContent()) {
        if (!confirm("当前模板已填写内容，切换将清空，是否继续？")) return;
    }
    try {
        const res = await fetch(`/api/competitor/templates/${encodeURIComponent(key)}`);
        if (!res.ok) throw new Error("模板加载失败");
        currentTemplate = await res.json();
        renderEditor(currentTemplate);
    } catch (e) {
        alert(e.message);
    }
}

function renderEditor(tpl) {
    const icon = document.getElementById("tplIcon");
    icon.className = `bi ${tpl.icon} fs-4 text-${tpl.tone}`;
    document.getElementById("tplName").textContent = tpl.name;
    document.getElementById("tplDesc").textContent = tpl.desc;
    document.getElementById("tplGuide").textContent = tpl.guide;

    const wrap = document.getElementById("formSections");
    wrap.innerHTML = "";
    tpl.sections.forEach((sec) => wrap.appendChild(buildSection(sec)));

    document.getElementById("tplPicker").classList.add("d-none");
    document.getElementById("tplEditor").classList.remove("d-none");
    window.scrollTo({ top: 0, behavior: "smooth" });
}

function buildSection(sec) {
    const card = document.createElement("div");
    card.className = "card mb-3";
    card.dataset.section = sec.id;
    card.dataset.repeat = sec.repeat ? "1" : "0";

    const head = document.createElement("div");
    head.className = "card-header py-2";
    head.innerHTML = `<strong><i class="bi bi-card-list me-1"></i>${sec.title}</strong>`;
    card.appendChild(head);

    const body = document.createElement("div");
    body.className = "card-body";
    card.appendChild(body);

    if (sec.repeat) {
        const groups = document.createElement("div");
        groups.className = "grp-wrap d-flex flex-column gap-2";
        body.appendChild(groups);
        appendGroup(sec, groups);

        const addBtn = document.createElement("button");
        addBtn.type = "button";
        addBtn.className = "btn btn-sm btn-outline-primary mt-2 add-grp";
        addBtn.innerHTML = '<i class="bi bi-plus-lg"></i> 添加一组';
        addBtn.addEventListener("click", () => appendGroup(sec, groups));
        body.appendChild(addBtn);
    } else {
        const row = document.createElement("div");
        row.className = "row g-3";
        body.appendChild(row);
        sec.fields.forEach((f) => {
            const cell = fieldWrap(f, null);
            if (cell) row.appendChild(cell);
        });
    }
    return card;
}

function appendGroup(sec, container) {
    const grp = document.createElement("fieldset");
    grp.className = "border rounded p-3 grp";
    grp.style.borderColor = "var(--border)";
    grp.innerHTML = `
        <div class="d-flex justify-content-between align-items-center mb-2">
            <span class="text-muted small fw-semibold">${container.querySelectorAll(".grp").length + 1}. 记录</span>
            <button type="button" class="btn btn-sm btn-outline-danger remove-grp" title="移除该组">
                <i class="bi bi-x"></i>
            </button>
        </div>`;
    const row = document.createElement("div");
    row.className = "row g-3";
    grp.appendChild(row);
    sec.fields.forEach((f) => {
        const cell = fieldWrap(f, null);
        if (cell) row.appendChild(cell);
    });
    grp.querySelector(".remove-grp").addEventListener("click", () => {
        if (container.querySelectorAll(".grp").length <= 1) {
            grp.querySelectorAll("input,textarea,select").forEach((el) => { el.value = ""; });
        } else {
            grp.remove();
        }
    });
    container.appendChild(grp);
}

// 构造单个字段的 (col > label + control)；value 以 DOM 属性赋值，杜绝注入
function fieldWrap(f, value) {
    const full = f.type === "textarea" || (f.type === "select" && (f.options || []).length > 4);
    const col = document.createElement("div");
    col.className = full ? "col-12" : "col-md-6";

    const label = document.createElement("label");
    label.className = "form-label small mb-1";
    label.innerHTML = f.label + (f.required ? ' <span class="text-danger">*</span>' : "");
    col.appendChild(label);

    let control;
    if (f.type === "select") {
        control = document.createElement("select");
        control.className = "form-select form-select-sm";
        const opt0 = document.createElement("option");
        opt0.value = "";
        opt0.textContent = "— 请选择 —";
        control.appendChild(opt0);
        (f.options || []).forEach((o) => {
            const op = document.createElement("option");
            op.value = o;
            op.textContent = o;
            control.appendChild(op);
        });
    } else if (f.type === "textarea") {
        control = document.createElement("textarea");
        control.className = "form-control form-control-sm";
        control.rows = f.rows || 3;
    } else {
        control = document.createElement("input");
        control.className = "form-control form-control-sm";
        control.type = f.type === "number" ? "number" : f.type === "date" ? "date" : "text";
        if (f.type === "number" && f.step) control.step = f.step;
    }
    control.dataset.fkey = f.key;
    control.placeholder = f.placeholder || "";
    if (value != null) control.value = value;
    col.appendChild(control);
    return col;
}

// 从 DOM 收集答案
function collectAnswers() {
    const answers = {};
    document.querySelectorAll("#formSections .card").forEach((card) => {
        const id = card.dataset.section;
        if (card.dataset.repeat === "1") {
            const arr = [];
            card.querySelectorAll(".grp").forEach((grp) => {
                const item = {};
                grp.querySelectorAll("[data-fkey]").forEach((el) => {
                    item[el.dataset.fkey] = el.value.trim();
                });
                if (Object.values(item).some((v) => v)) arr.push(item);
            });
            answers[id] = arr;
        } else {
            const item = {};
            card.querySelectorAll("[data-fkey]").forEach((el) => {
                item[el.dataset.fkey] = el.value.trim();
            });
            answers[id] = item;
        }
    });
    return answers;
}

function hasAnyAnswer(answers) {
    return Object.values(answers).some((v) => {
        if (Array.isArray(v)) return v.some((it) => Object.values(it).some((x) => x));
        return Object.values(v).some((x) => x);
    });
}

function hasFormContent() {
    const answers = collectAnswers();
    return hasAnyAnswer(answers);
}

function clearForm() {
    document.querySelectorAll("#formSections [data-fkey]").forEach((el) => { el.value = ""; });
}

async function generateReport() {
    if (!currentTemplate) return;
    const answers = collectAnswers();
    if (!hasAnyAnswer(answers)) {
        alert("请先在表单中填写内容（至少一项），再生成报告");
        return;
    }
    try {
        const res = await fetch("/api/competitor/report", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ template_key: currentTemplate.key, answers }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "生成失败");
        lastResult = data;
        showReport(data);
    } catch (e) {
        alert(`报告生成失败: ${e.message}`);
    }
}

function showReport(data) {
    document.getElementById("reportTitle").textContent = `${data.template_name} · 已生成`;
    document.getElementById("reportFrame").srcdoc = data.html;
    document.getElementById("reportMd").value = data.markdown;
    switchTab("preview");
    reportModal.show();
}

function switchTab(tab) {
    document.querySelectorAll(".report-tab").forEach((t) => {
        t.classList.toggle("active", t.dataset.tab === tab);
    });
    document.getElementById("tabPreview").classList.toggle("d-none", tab !== "preview");
    document.getElementById("tabMarkdown").classList.toggle("d-none", tab !== "markdown");
}

function download(ext, mime, content) {
    if (!lastResult) return;
    const blob = new Blob(["﻿" + content], { type: `${mime};charset=utf-8` });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = lastResult.filename + ext;
    a.click();
    URL.revokeObjectURL(a.href);
}

function copyMarkdown() {
    const text = document.getElementById("reportMd").value;
    const done = () => alert("Markdown 已复制，可直接粘贴到 Word/笔记/Typora");
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done).catch(() => fallbackCopy(text, done));
    } else {
        fallbackCopy(text, done);
    }
}

function fallbackCopy(text, done) {
    const ta = document.getElementById("reportMd");
    ta.select();
    document.execCommand("copy");
    done();
}
