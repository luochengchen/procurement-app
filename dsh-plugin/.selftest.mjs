// 临时自测：用假的 Host ctx 装载插件，把 /procure 前缀挂到一个临时 HTTP 服务器上，
// 验证反代、HTML/JS 路径改写与数据口注入。验证完即删。
import http from 'node:http';
import { apply } from './index.js';

const ROOT = 'F:/Projects/procurement-app';
let route = null;
const ctx = {
  webServer: { register: (opts) => { route = opts; return () => {}; } },
  effect: (fn) => fn(),
};

apply(ctx, { root: ROOT, path: '/procure', port: 5127 });
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

// 第一次请求只会拿到 503（插件有意不等后端），随后页面自己轮询就绪。
// 自测要验的是「就绪之后」的产物，所以这里先像浏览器那样轮询到 ping 通。
const deadline = Date.now() + 60000;
let ping;
for (;;) {
  ping = await get('/procure/api/ping');
  if (ping.status === 200) break;
  if (Date.now() > deadline) throw new Error(`后端 60 秒未就绪：${ping.status} ${ping.body.slice(0, 120)}`);
  await new Promise((r) => setTimeout(r, 500));
}
console.log('ping  ', ping.status, ping.type, ping.body.slice(0, 80));

const page = await get('/procure/');
const html = page.body;
console.log('page  ', page.status, page.type, 'len', html.length);
const checks = {
  nav: html.includes('href="/procure/materials"') && html.includes('href="/procure/calculator"'),
  rootHref: html.includes('href="/procure/"'),
  css: html.includes('href="/procure/static/css/style.css"'),
  staticJs: html.includes('src="/procure/static/js/dashboard.js"'),
  noLeftoverHref: !/href="\/(materials|calculator|image-search|factory|certification|competitor)"/.test(html),
  noDoublePrefix: !html.includes('/procure/procure'),
  shimEarly: html.indexOf('window.__procurementBase') > 0
    && html.indexOf('window.__procurementBase') < html.indexOf('/procure/static/js/'),
  bridge: html.includes('window.ProcurementDeskBridge'),
  bridgeBase: html.includes('fetch("/procure/api"+p,init)'),
  beforeBodyEnd: /window\.ProcurementDeskBridge[\s\S]*<\/script>\s*<\/body>\s*(<\/html>\s*)?$/.test(html),
};

const js = await get('/procure/static/js/dashboard.js');
const jsChecks = {
  status: js.status === 200 && /javascript/.test(js.type || ''),
  prefixed: js.body.includes('"/procure/api/materials/stats"'),
  noLeftover: !js.body.includes('"/api/materials/stats"'),
  noDouble: !js.body.includes('/procure/procure'),
};
console.log('js    ', js.status, js.type, 'len', js.body.length, jsChecks);

const stats = await get('/procure/api/materials/stats');
console.log('stats ', stats.status, stats.type, stats.body.slice(0, 100));

server.close();
const ok = ping.status === 200
  && Object.values(checks).every(Boolean)
  && Object.values(jsChecks).every(Boolean)
  && stats.status === 200;
console.log('RESULT', ok ? 'PASS' : 'FAIL', Object.entries({ ...checks, ...jsChecks })
  .filter(([, v]) => !v).map(([k]) => k));
process.exit(ok ? 0 : 1);
