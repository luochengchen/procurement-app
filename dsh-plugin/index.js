/**
 * Host half of the 跨境采购助手 entry.
 *
 * procurement-app 是一个 Flask 多页应用（app.py + templates + static + SQLite），
 * 所以 Host 半要干两件事：
 *
 *   1. 按需把后端拉起来（`<root>/.venv/Scripts/pythonw.exe dsh-plugin/serve.py`，
 *      端口由 config 决定），等 /api/ping 真的通；已经有人跑着就直接复用。
 *   2. 在 Harness Web 服务器上挂 /procure 前缀，把请求反代到本地 Flask。
 *
 * 为什么反代而不是让 iframe 直连 `http://127.0.0.1:<port>/`：
 *   - 和 Web UI 同 origin，宿主能读 iframe 的 contentDocument（Esc、主题、数据口），
 *     也没有跨域限制；
 *   - 同 origin 才能共用宿主的鉴权与地址栏入口。
 *
 * 和股票分析最大的不同：那个应用是单页 + 全部绝对路径 fetch("/api/...")，
 * 只要改一个前缀；这里是**多页应用**，页面里的 href="/materials"、
 * src="/static/..."、JS 里的 window.location.href = "/factory?q=..." 全是根绝对
 * 路径，所以要把 HTML 里的引用、静态 JS 里的字符串常量都改写到挂载点下，
 * 并在页面最早执行的位置注入一个 fetch/XHR/点击拦截的补丁，兜住运行时拼出来的路径。
 * 这些都只在**响应里**做，项目源码一行不改。
 */
import http from 'node:http';
import { spawn } from 'node:child_process';
import { existsSync, mkdirSync, openSync, readFileSync, statSync, truncateSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

export const inject = ['webServer'];

const DEFAULTS = {
  /** 项目根目录：app.py / templates / static / data.db 都在这里。 */
  root: 'F:/Projects/procurement-app',
  /** Harness Web 服务器上的挂载点。 */
  path: '/procure',
  /** Flask 端口。改这里要同时改 cordis.patch.yml。 */
  port: 5127,
  /** 等待后端就绪的上限（毫秒）。SQLite + 种子数据都在 import 时完成，通常 1–3 秒。 */
  bootTimeoutMs: 30000,
};

/** 插件自己的目录（serve.py 在这里）。 */
const HERE = path.dirname(fileURLToPath(import.meta.url));

const LOG_FILE = '.dsh/backend.log';
const LOG_MAX_BYTES = 2 * 1024 * 1024;

function htmlText(value) {
  return String(value).replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' })[c]);
}

export function apply(ctx, config) {
  const cfg = { ...DEFAULTS, ...(config || {}) };
  const root = cfg.root;
  const routePath = cfg.path.replace(/\/+$/, '');
  const port = Number(cfg.port);
  const base = `http://127.0.0.1:${port}`;
  const mountName = routePath.replace(/^\//, '');

  // -------------------------------------------------------------- 路径改写
  //
  // 只改「以单个斜杠开头、后面紧跟标识符」的字符串：`"/api/x"`、`"/static/x.css"`、
  // `"/factory"` 都要加前缀；`"//cdn..."`（协议相对）、已经是 `"/procure/..."` 的
  // 不动。根路径 `href="/"` 单独按属性改，避免误伤 JS 里的 `split("/")`。

  const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const refRe = new RegExp(`(["'])\\/(?!\\/|${escapeRe(mountName)}(?:[/"']|$))(?=[A-Za-z_])`, 'g');
  const rootAttrRe = /((?:href|action|src|data-goto)\s*=\s*["'])\/(?=["'])/g;

  /** 把响应体里的根绝对路径改写到挂载点下。HTML 与静态 JS 共用。 */
  function rewriteRefs(text) {
    return text
      .replace(rootAttrRe, `$1${routePath}/`)
      .replace(refRe, (_m, quote) => `${quote}${routePath}/`);
  }

  // ---------------------------------------------------------------- 进程管理

  /** 后端是不是我们认识的那个后端：/api/ping 返回 {"status":"ok"}。 */
  const ping = () => new Promise((resolve) => {
    const req = http.get(`${base}/api/ping`, { timeout: 1500 }, (res) => {
      let text = '';
      res.setEncoding('utf8');
      res.on('data', (chunk) => { text += chunk; });
      res.on('end', () => {
        try {
          resolve(JSON.parse(text).status === 'ok');
        } catch {
          resolve(false);
        }
      });
    });
    req.on('timeout', () => { req.destroy(); resolve(false); });
    req.on('error', () => resolve(false));
  });

  /**
   * 用哪个解释器。
   *
   * Windows 上必须用 `pythonw.exe`：venv 里的 `python.exe` 不是本体，而是一个
   * 274KB 的启动器，它会用 *基础解释器* 再 CreateProcess 一次，那个孙进程会拿到
   * 一个**新的控制台窗口** —— 父进程传的 `windowsHide` 管不到它。实测 `python.exe`
   * 会弹出黑窗，`pythonw.exe` 完全无窗口（详见记忆库 windows-venv-console-window）。
   */
  function pythonCommand() {
    const scripts = path.join(root, '.venv', 'Scripts');
    const win = path.join(scripts, 'pythonw.exe');
    if (process.platform === 'win32' && existsSync(win)) return { cmd: win };
    const exe = path.join(scripts, 'python.exe');
    if (existsSync(exe)) return { cmd: exe };
    return { cmd: process.platform === 'win32' ? 'python' : 'python3' };
  }

  function openLog() {
    const dir = path.join(root, '.dsh');
    mkdirSync(dir, { recursive: true });
    const file = path.join(dir, 'backend.log');
    try {
      if (existsSync(file) && statSync(file).size > LOG_MAX_BYTES) truncateSync(file, 0);
    } catch {
      /* 日志裁不掉不影响启动 */
    }
    return { file, fd: openSync(file, 'a') };
  }

  function spawnBackend() {
    const { cmd } = pythonCommand();
    const { file, fd } = openLog();
    const child = spawn(cmd, [path.join(HERE, 'serve.py')], {
      cwd: root,
      env: {
        ...process.env,
        PORT: String(port),
        PROCUREMENT_ROOT: root,
        PYTHONUNBUFFERED: '1',
        PYTHONIOENCODING: 'utf-8',
      },
      // detached：DSH 重启/插件重载时不连带杀掉后端，下次进入直接复用。
      detached: true,
      windowsHide: true,
      stdio: ['ignore', fd, fd],
    });
    child.unref();
    return { pid: child.pid, cmd, file };
  }

  let booting = null;

  /** 拉起后端（幂等）。返回的 Promise 只会 resolve，不会 reject。 */
  function startBoot() {
    if (booting) return booting;
    booting = (async () => {
      let spawned;
      try {
        spawned = spawnBackend();
      } catch (error) {
        return { error: `启动 Python 后端失败：${error && error.message ? error.message : String(error)}` };
      }
      const deadline = Date.now() + cfg.bootTimeoutMs;
      while (Date.now() < deadline) {
        await new Promise((r) => setTimeout(r, 400));
        if (await ping()) return { ok: true, pid: spawned.pid };
        if (spawned.pid == null) break;
      }
      return {
        error: `后端 ${cfg.bootTimeoutMs / 1000} 秒内没有响应 ${base}/api/ping（python: ${spawned.cmd}）。`
          + `\n日志：${spawned.file}`,
      };
    })().finally(() => { booting = null; });
    return booting;
  }

  /**
   * 后端没起来就拉起来。`waitMs` 是愿意同步等的时间：请求进来时只等一小会，
   * 等不到就先回一张「启动中」页面让浏览器自己轮询 —— 比让窗口空白几秒好，
   * 也避免了在插件加载时预热（那样每开一次 DSH 就白起一个 Python 进程）。
   */
  async function ensureBackend(waitMs = 0) {
    if (await ping()) return { ok: true };
    const boot = startBoot();
    if (!waitMs) return { booting: true };
    return new Promise((resolve) => {
      const timer = setTimeout(() => resolve({ booting: true }), waitMs);
      boot.then((result) => { clearTimeout(timer); resolve(result); });
    });
  }

  function logTail(lines = 15) {
    try {
      const file = path.join(root, LOG_FILE);
      if (!existsSync(file)) return '';
      const text = readFileSync(file, 'utf8');
      return text.trim().split('\n').slice(-lines).join('\n');
    } catch {
      return '';
    }
  }

  // ------------------------------------------------------------------ 反代

  /** 把 `/procure/api/x?y` 映射成上游的 `/api/x?y`。 */
  function upstreamPath(url) {
    const rest = url.startsWith(routePath) ? url.slice(routePath.length) : url;
    if (!rest || rest === '/') return '/';
    return rest.startsWith('/') ? rest : `/${rest}`;
  }

  /** 挂载点前缀补丁：页面最早执行的脚本，兜住运行时拼出来的根绝对路径。 */
  function prefixShim() {
    const P = JSON.stringify(routePath);
    return '<script>(function(){var P=' + P + ';'
      + 'function fix(u){if(typeof u!=="string")return u;'
      + 'if(u.charAt(0)!=="/"||u.charAt(1)==="/")return u;'
      + 'if(u===P||u.indexOf(P+"/")===0)return u;return P+u}'
      + 'window.__procurementBase=P;window.__procurementFix=fix;'
      + 'var of=window.fetch;'
      + 'if(typeof of==="function"){window.fetch=function(input,init){'
      + 'if(typeof input==="string"){input=fix(input)}'
      + 'else if(input&&typeof input.url==="string"){var nu=fix(input.url);'
      + 'if(nu!==input.url){try{input=new Request(nu,input)}catch(e){}}}'
      + 'return of.call(this,input,init)}}'
      + 'if(window.XMLHttpRequest){var xo=XMLHttpRequest.prototype.open;'
      + 'XMLHttpRequest.prototype.open=function(m,u){var a=[].slice.call(arguments);'
      + 'if(a.length>1)a[1]=fix(u);return xo.apply(this,a)}}'
      // 动态生成的 <a href="/xxx"> 也留在挂载点里，不要跳出到宿主根
      + 'document.addEventListener("click",function(e){'
      + 'var t=e.target;var a=t&&t.closest?t.closest("a[href]"):null;if(!a)return;'
      + 'var h=a.getAttribute("href");if(!h||h.charAt(0)!=="/"||h.charAt(1)==="/")return;'
      + 'if(h===P||h.indexOf(P+"/")===0)return;e.preventDefault();window.location.href=P+h'
      + '},true);'
      + '})();<\/script>';
  }

  /**
   * 数据口：页面的每个 `/api/` 响应复制一份，进页面 events，并 postMessage 给宿主
   * （浮窗 iframe 走 `window.parent`，独立标签页走 `window.opener`）。
   * 这样 DSH 侧读 `window.__procureDesk` 就能拿到材料/工厂/成本核算的结果，
   * 不必抓 DOM，也不必改项目模板。
   */
  function bridgeScript(apiBase) {
    return '<script>(function(){'
      + 'if(window.ProcurementDeskBridge)return;'
      + 'var ev=[],ls=[],MAX=200;'
      + 'function emit(e){ev.push(e);if(ev.length>MAX)ev.shift();'
      + 'for(var i=0;i<ls.length;i++){try{ls[i](e)}catch(x){}}'
      + 'try{var t=[window.parent,window.opener];for(var k=0;k<t.length;k++){'
      + "var w=t[k];if(w&&w!==window&&!w.closed)w.postMessage({source:'procurement-desk',kind:'api',url:e.url,data:e.data,at:e.at},'*')}"
      + '}catch(x){}}'
      + 'function rec(u,d){emit({url:String(u),data:d,at:Date.now()})}'
      + 'var of=window.fetch;'
      + 'if(typeof of==="function"){window.fetch=function(){'
      + 'var u=typeof arguments[0]==="string"?arguments[0]:((arguments[0]&&arguments[0].url)||"");'
      + 'var p=of.apply(this,arguments);'
      + 'if(String(u).indexOf("/api/")>=0){p.then(function(r){'
      + 'try{r.clone().json().then(function(d){rec(u,d)}).catch(function(){})}catch(x){}'
      + '}).catch(function(){})}'
      + 'return p}}'
      + 'window.ProcurementDeskBridge={version:1,events:ev,'
      + 'last:function(){return ev[ev.length-1]||null},'
      + 'onData:function(f){if(typeof f==="function")ls.push(f);'
      + 'return function(){var i=ls.indexOf(f);if(i>=0)ls.splice(i,1)}},'
      + 'call:function(p,init){return fetch("' + apiBase + '"+p,init).then(function(r){return r.json()})}};'
      + "window.addEventListener('message',function(e){try{"
      + "if(e.data&&e.data.source==='procurement-desk-host')"
      + "window.dispatchEvent(new CustomEvent('procurement-desk:host',{detail:e.data.payload}))"
      + '}catch(x){}})'
      + '})();<\/script>';
  }

  /** HTML：先改写引用，再在第 <head> 之后塞路径补丁、</body> 前塞数据口。 */
  function rewriteHtml(body) {
    let out = rewriteRefs(body);
    const shim = prefixShim();
    const head = out.match(/<head[^>]*>/i);
    if (head) {
      const at = head.index + head[0].length;
      out = out.slice(0, at) + shim + out.slice(at);
    } else {
      out = shim + out;
    }
    const tag = bridgeScript(`${routePath}/api`);
    const at = out.lastIndexOf('</body>');
    return at >= 0 ? out.slice(0, at) + tag + out.slice(at) : out + tag;
  }

  const isScript = (type) => /javascript|ecmascript/i.test(type);

  /** 浅色/深色都能看的提示页（跟随系统偏好）。 */
  function noticePage(title, message, detailHtml = '') {
    return '<!doctype html><meta charset="utf-8"><title>' + htmlText(title) + '</title>'
      + '<style>'
      + ':root{--page:#f8fafc;--surface:#fff;--ink:#0f172a;--muted:#64748b;--line:#e2e8f0;--brand:#0369a1}'
      + '@media (prefers-color-scheme:dark){:root{--page:#0b1220;--surface:#131c2e;--ink:#f8fafc;'
      + '--muted:#94a3b8;--line:#26334a;--brand:#38bdf8}}'
      + '*{box-sizing:border-box}'
      + 'body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;'
      + 'background:var(--page);color:var(--ink);font:14px/1.7 system-ui,"Microsoft YaHei",sans-serif}'
      + '.box{max-width:520px;padding:0 24px;text-align:center}'
      + '.spin{width:28px;height:28px;margin:0 auto 14px;border:3px solid var(--line);'
      + 'border-top-color:var(--brand);border-radius:50%;animation:spin 900ms linear infinite}'
      + '@keyframes spin{to{transform:rotate(360deg)}}'
      + 'h1{margin:0 0 6px;font-size:16px;font-weight:600}'
      + 'p{margin:0;color:var(--muted);font-size:12.5px}'
      + 'pre{white-space:pre-wrap;text-align:left;background:var(--surface);border:1px solid var(--line);'
      + 'border-radius:8px;padding:12px;font-size:12px;color:var(--ink);overflow:auto}'
      + 'code{background:var(--surface);border:1px solid var(--line);border-radius:4px;padding:1px 5px}'
      + '</style><body><div class="box">' + detailHtml + '</div></body>';
  }

  /**
   * 「后端正在启动」页：轮询 `/procure/api/ping`，通了就换成真正的页面。
   * 轮询用的是 JSON 接口，所以「启动中」的 503 不会被误当成就绪。
   */
  function renderBooting(res, target) {
    const pingUrl = `${routePath}/api/ping`;
    const script = '<script>(function(){var n=0;'
      + 'function poll(){if(++n>120){document.getElementById("msg").textContent="启动超时，见 .dsh/backend.log";return}'
      + `fetch(${JSON.stringify(pingUrl)},{cache:"no-store"}).then(function(r){return r.ok?r.json():null})`
      + '.then(function(d){if(d&&d.status==="ok"){location.replace(' + JSON.stringify(target) + ');return}'
      + 'setTimeout(poll,800)}).catch(function(){setTimeout(poll,800)})}'
      + 'setTimeout(poll,600)})();<\/script>';
    const detail = '<div class="spin"></div>'
      + '<h1>正在启动采购助手…</h1>'
      + '<p>首次启动要初始化 SQLite，通常 1–3 秒，之后就复用同一个进程。</p>'
      + `<p id="msg" style="margin-top:10px">${htmlText(base)}</p>` + script;
    const body = noticePage('跨境采购助手启动中', '', detail);
    res.statusCode = 200;
    res.setHeader('content-type', 'text/html; charset=utf-8');
    res.setHeader('cache-control', 'no-store');
    res.setHeader('content-length', Buffer.byteLength(body));
    res.end(body);
  }

  function renderError(res, message, status = 503) {
    const detail = logTail();
    const inner = '<h1>采购助手后端没起来</h1>'
      + '<p style="margin-bottom:10px">' + htmlText(message).replace(/\n/g, '<br>') + '</p>'
      + (detail ? '<p style="margin:12px 0 6px">后端日志末尾：</p><pre>' + htmlText(detail) + '</pre>' : '')
      + '<p style="margin-top:12px">手动排查：<code>' + htmlText(root) + '</code>，'
      + '<code>.venv\\Scripts\\python.exe dsh-plugin\\serve.py</code></p>';
    const body = noticePage('跨境采购助手后端未就绪', '', inner);
    res.statusCode = status;
    res.setHeader('content-type', 'text/html; charset=utf-8');
    res.setHeader('cache-control', 'no-store');
    res.setHeader('content-length', Buffer.byteLength(body));
    res.end(body);
  }

  function forward(req, res) {
    // accept-encoding 固定成 identity：HTML/JS 要在内存里改写，上游要是压过
    // （gzip/br）就成了一堆二进制，长度也对不上。Flask 开发服务器默认不压缩，
    // 但别指望它一直如此。
    const headers = { ...req.headers, host: `127.0.0.1:${port}`, 'accept-encoding': 'identity' };
    let upstream;
    try {
      upstream = http.request({
        host: '127.0.0.1',
        port,
        method: req.method,
        path: upstreamPath(req.url || '/'),
        headers,
      }, (up) => {
        const type = String(up.headers['content-type'] || '');
        const outHeaders = { ...up.headers };
        delete outHeaders.connection;
        delete outHeaders['transfer-encoding'];
        delete outHeaders['content-encoding']; // 改写后的长度对不上，也不再是压缩体
        outHeaders['cache-control'] = outHeaders['cache-control'] || 'no-store';

        // 上游 3xx 的 Location 也是根绝对路径，同样要落回挂载点。
        const loc = outHeaders.location;
        if (typeof loc === 'string' && loc.startsWith('/') && !loc.startsWith('//')
          && loc !== routePath && !loc.startsWith(`${routePath}/`)) {
          outHeaders.location = routePath + loc;
        }

        if (type.includes('text/html') || isScript(type)) {
          delete outHeaders.etag;
          const chunks = [];
          up.on('data', (c) => chunks.push(c));
          up.on('end', () => {
            if (res.writableEnded) return;
            const raw = Buffer.concat(chunks).toString('utf8');
            const body = type.includes('text/html') ? rewriteHtml(raw) : rewriteRefs(raw);
            const buf = Buffer.from(body, 'utf8');
            res.writeHead(up.statusCode || 200, { ...outHeaders, 'content-length': buf.length });
            res.end(buf);
          });
          up.on('error', () => { if (!res.headersSent) renderError(res, '上游响应中断'); });
          return;
        }

        res.writeHead(up.statusCode || 200, outHeaders);
        up.pipe(res);
      });
    } catch (error) {
      renderError(res, `请求后端失败：${error && error.message ? error.message : String(error)}`);
      return;
    }

    // 报表导出/Excel 模板生成可能要几秒：不要给上游设短超时。
    upstream.setTimeout(0);
    upstream.on('error', (error) => {
      if (res.headersSent) { res.end(); return; }
      renderError(res, `连接 ${base} 失败：${error && error.message ? error.message : String(error)}`);
    });
    req.on('aborted', () => upstream.destroy());
    req.pipe(upstream);
  }

  // ---------------------------------------------------------------- 注册路由

  ctx.effect(() => ctx.webServer.register({
    kind: 'prefix',
    path: routePath,
    async handler(req, res) {
      const ready = await ensureBackend(1500);
      if (ready.ok) {
        forward(req, res);
        return;
      }
      // API 调用方（页面自己、数据口、外脚本）要 JSON，不能塞 HTML 进去。
      if (upstreamPath(req.url || '/').startsWith('/api/')) {
        const body = JSON.stringify({ error: 'backend-booting', base });
        res.statusCode = 503;
        res.setHeader('content-type', 'application/json; charset=utf-8');
        res.setHeader('retry-after', '1');
        res.end(body);
        return;
      }
      if (ready.booting) {
        renderBooting(res, req.url || routePath);
        return;
      }
      renderError(res, ready.error || '后端未就绪');
    },
  }));

  // 故意不在插件加载时预热：那等于每次打开 DSH 都白起一个 Python 进程，
  // 也正是「一开 DSH 就冒出 python 窗口」的来源。现在只在你点开入口时才启动。
}
