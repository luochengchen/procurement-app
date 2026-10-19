// 临时端到端自测（冷启动路径）：后端没起时先给「启动中」页，起来后拿到真页面。
// 用 5128 端口，避免和已经跑着的 5127 实例互相干扰。跑完删除。
import http from 'node:http';
import { apply } from './index.js';

const ROOT = 'F:/Projects/procurement-app';
const PORT = 5128;
let route = null;
const ctx = {
  webServer: { register: (opts) => { route = opts; return () => {}; } },
  effect: (fn) => fn(),
};

apply(ctx, { root: ROOT, path: '/procure', port: PORT });
if (!route) throw new Error('没注册路由');

const server = http.createServer((req, res) => route.handler(req, res));
await new Promise((r) => server.listen(5199, '127.0.0.1', r));

const get = (path) => new Promise((resolve, reject) => {
  http.get({ host: '127.0.0.1', port: 5199, path }, (res) => {
    const chunks = [];
    res.on('data', (c) => chunks.push(c));
    res.on('end', () => resolve({
      status: res.statusCode,
      type: res.headers['content-type'],
      body: Buffer.concat(chunks).toString('utf8'),
    }));
  }).on('error', reject);
});

// 先确认 5128 上是冷的：直接打 ping 应该是 503 JSON（后端启动中）
const cold = await get('/procure/api/ping');
console.log('cold ping', cold.status, cold.type, cold.body.slice(0, 80));

const t0 = Date.now();
const first = await get('/procure/');
const booting = {
  html: first.type?.includes('text/html') && first.body.includes('正在启动采购助手'),
  pollsPing: first.body.includes('/procure/api/ping'),
  elapsed: Date.now() - t0,
};
console.log('first page', first.status, booting);

let ready = null;
for (let i = 0; i < 120; i += 1) {
  const p = await get('/procure/api/ping');
  if (p.status === 200 && p.body.includes('"ok"')) { ready = p; break; }
  await new Promise((r) => setTimeout(r, 500));
}
console.log('ping after boot', ready ? `${ready.status} ${ready.body.slice(0, 60)}` : 'TIMEOUT',
  `${((Date.now() - t0) / 1000).toFixed(1)}s`);

const page = await get('/procure/');
const checks = {
  nav: page.body.includes('href="/procure/materials"'),
  css: page.body.includes('href="/procure/static/css/style.css"'),
  bridge: page.body.includes('window.ProcurementDeskBridge'),
};
console.log('page', page.status, 'len', page.body.length, checks);

// 顺便验一下材料页和工厂页这两条多页路由也能正常改写到挂载点下
const materials = await get('/procure/materials');
const factory = await get('/procure/factory');
const pages = {
  materials: materials.status === 200 && materials.body.includes('href="/procure/calculator"'),
  factory: factory.status === 200 && factory.body.includes('href="/procure/materials"'),
};
console.log('pages', materials.status, factory.status, pages);

const bootLog = await import('node:fs');
const logTail = bootLog.existsSync(`${ROOT}/.dsh/backend.log`)
  ? bootLog.readFileSync(`${ROOT}/.dsh/backend.log`, 'utf8').trim().split('\n').slice(-4).join('\n')
  : '(no log)';
console.log('log tail:\n' + logTail);

server.close();
const ok = (booting.html || first.status === 200)
  && ready && Object.values(checks).every(Boolean) && Object.values(pages).every(Boolean);
process.exit(ok ? 0 : 1);
