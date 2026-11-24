// report/report_draft.md → report/result_report.pdf
// 사용법: node scripts/report_pdf.js   (pandoc과 Playwright Chromium 필요, 한글은 Google Fonts의 Noto Sans KR)
const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const repo = path.resolve(__dirname, '..');
const md = fs.readFileSync(path.join(repo, 'report', 'report_draft.md'), 'utf8')
  .split('\n').filter(l => !l.startsWith('> ')).join('\n')   // 초안 안내문 제거
  .replace(' — 결과보고서 (초안)', ' — 결과보고서');
const tmpMd = path.join(repo, 'report', '_build.md');
const html = path.join(repo, 'report', '_build.html');
fs.writeFileSync(tmpMd, md);
const css = `
@page { size: A4; margin: 16mm 14mm; }
body { font-family: 'Noto Sans KR', sans-serif; font-size: 10pt; line-height: 1.6; color: #111; max-width: none; }
h1 { font-size: 17pt; margin: 0 0 8px; } h2 { font-size: 13.5pt; border-bottom: 1px solid #999; padding-bottom: 3px; margin-top: 22px; }
h3 { font-size: 11pt; margin: 16px 0 6px; }
table { border-collapse: collapse; width: 100%; font-size: 8.6pt; margin: 6px 0 10px; page-break-inside: avoid; }
th, td { border: 1px solid #bbb; padding: 3px 5px; text-align: left; vertical-align: top; } th { background: #f0f0f0; }
img { max-width: 100%; display: block; margin: 6px auto; page-break-inside: avoid; }
code { font-size: 8.8pt; background: #f4f4f4; padding: 0 3px; } hr { display: none; }
figure { margin: 6px 0; } figcaption { font-size: 8.5pt; color: #555; text-align: center; }`;
const header = path.join(repo, 'report', '_head.html');
fs.writeFileSync(header, `<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap" rel="stylesheet"><style>${css}</style>`);
execFileSync('pandoc', [tmpMd, '-f', 'gfm', '-t', 'html5', '-s', '--metadata', 'title=결과보고서', '-H', header, '-o', html]);
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.goto('file://' + html, { waitUntil: 'networkidle' });
  await p.evaluate(() => document.fonts.ready);
  await p.addStyleTag({ content: 'header#title-block-header{display:none}' });
  await p.pdf({ path: path.join(repo, 'report', 'result_report.pdf'), format: 'A4', printBackground: true });
  await b.close();
  for (const f of [tmpMd, html, header]) fs.unlinkSync(f);
  console.log('report/result_report.pdf 생성');
})();
