// report/report_draft.md → report/result_report.pdf
// 사용법: node scripts/report_pdf.js   (pandoc, Playwright Chromium 필요. 한글 글꼴은 Google Fonts의 Noto Sans KR)
// 표지와 요약 숫자는 results/experiments.csv, results/test_confusion_counts.csv, logs/summary.json에서 읽어 채운다.
const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const repo = path.resolve(__dirname, '..');
const R = (...p) => path.join(repo, ...p);
const GITHUB = 'https://github.com/djkdb/beeguard-hornet-tracker';

// ---------- 요약 숫자 ----------
function csv(file) {
  const [head, ...rows] = fs.readFileSync(file, 'utf8').replace(/^﻿/, '').trim().split('\n').map(l => l.split(','));
  return rows.map(r => Object.fromEntries(head.map((h, i) => [h, r[i]])));
}
const exps = csv(R('results', 'experiments.csv'));
const FINAL = 'n640';   // models/best.pt로 쓰는 최종 모델
const best = exps.find(e => e.exp === FINAL) || exps.slice().sort((a, b) => b['mAP50-95'] - a['mAP50-95'])[0];
const cm = csv(R('results', 'test_confusion_counts.csv'));
const row = name => cm.find(r => Object.values(r)[0] === `정답:${name}`);
const rate = (t, p) => { const r = row(t); const tot = Object.values(r).slice(1).reduce((s, v) => s + +v, 0); return `${(100 * r[`예측:${p}`] / tot).toFixed(1)}%`; };
const summary = JSON.parse(fs.readFileSync(R('logs', 'summary.json'), 'utf8'));
const f3 = v => (+v).toFixed(3);

const cover = `
<section class="cover">
  <div class="eyebrow">머신러닝 과제 결과보고서</div>
  <h1 class="title">YOLOv8 기반 꿀벌·장수말벌·등검은말벌 탐지 및 추적</h1>
  <table class="meta">
    <tr><th>학번 · 이름</th><td>2022041067 이성준</td><th>소속</th><td>충북대학교 소프트웨어학부</td></tr>
    <tr><th>GitHub</th><td colspan="3"><a href="${GITHUB}">${GITHUB}</a></td></tr>
  </table>
  <div class="abstract"><b>요약</b><br>
    양봉장에 피해를 주는 장수말벌과 등검은말벌을 꿀벌과 구분해 찾아내는 YOLOv8 모델을 학습하고, 영상에서 추적해 보았다.
    9개 경로에서 사진 7,583장을 모아 1,536장으로 추렸고, Grounding DINO로 만든 초기 박스를 AI 검수로 다듬어 1,423장(박스 1,432개)을 학습에 썼다.
    GPU를 쓸 수 없어 CPU에서 입력 크기 320과 640을 비교했고, ${best.exp} 모델이 테스트 세트에서 mAP50 ${f3(best.mAP50)}, mAP50-95 ${f3(best['mAP50-95'])}를 기록했다.
    두 말벌 종의 오인율은 ${rate('giant_hornet', 'yellow_legged_hornet')}(장수말벌→등검은말벌), ${rate('yellow_legged_hornet', 'giant_hornet')}(반대)였다.
    추적은 ByteTrack으로 했고, 궤적을 파일로 저장하고 말벌의 정지비행을 표시하도록 코드를 고쳤다. 점수가 잘 나오는 쉬운 주제 대신, 여름에 구상한 프로젝트의 첫 단계를 직접 만들어 보는 데 의미를 두었다.</div>
</section>`;

// ---------- 본문 ----------
const md = fs.readFileSync(R('report', 'report_draft.md'), 'utf8').split('\n')
  .filter(l => !l.startsWith('> ') && !l.startsWith('# ') && !/^- (학번·이름|과목|배경):/.test(l))
  .join('\n');
const tmpMd = R('report', '_build.md');
const html = R('report', '_build.html');
const head = R('report', '_head.html');
fs.writeFileSync(tmpMd, md);

const css = `
:root { --ink:#1b1f24; --muted:#5b6470; --line:#d9dde3; --soft:#f5f6f8; --accent:#b45309; --accent-soft:#fff4e5; --dark:#1f2a37; }
@page { size: A4; margin: 15mm 15mm 16mm; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family: 'Noto Sans KR', sans-serif; font-size: 9.4pt; line-height: 1.72; color: var(--ink); margin: 0; max-width: none; padding: 0; word-break: keep-all; }
a { color: var(--accent); text-decoration: none; }
p { margin: 4px 0 8px; }
ul, ol { margin: 4px 0 10px; padding-left: 18px; } li { margin: 2px 0; } li > ul { margin: 2px 0; }
strong { font-weight: 700; }
code { font-family: 'Noto Sans KR', monospace; font-size: 8.4pt; background: var(--soft); border: 1px solid var(--line); border-radius: 3px; padding: 0 3px; }
hr { display: none; }
.keep { break-inside: avoid; page-break-inside: avoid; }
td code { border: 0; background: none; padding: 0; font-size: 8.3pt; }

/* 표지 */
.cover { padding-top: 4mm; margin-bottom: 18px; }
.eyebrow { color: var(--accent); font-weight: 700; letter-spacing: .08em; font-size: 9pt; }
.title { font-size: 21pt; white-space: nowrap; letter-spacing: -0.01em; line-height: 1.35; margin: 8px 0 22px; border: 0; color: var(--dark); }
.subtitle { color: var(--muted); font-size: 11pt; margin-bottom: 18px; }
table.meta { display: table !important; width: 100% !important; border-collapse: collapse; margin: 0 0 18px; font-size: 9.2pt; }
table.meta th { width: 16%; text-align: left; color: var(--muted); font-weight: 400; background: none; border: 0; border-bottom: 1px solid var(--line); padding: 6px 4px; }
table.meta td { border: 0; border-bottom: 1px solid var(--line); padding: 6px 4px; font-weight: 700; }
.kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin: 0 0 20px; }
.kpi { background: var(--accent-soft); border: 1px solid #f3d9b5; border-radius: 8px; padding: 10px 11px; }
.kpi .v { font-size: 17pt; font-weight: 700; color: var(--accent); line-height: 1.2; font-variant-numeric: tabular-nums; }
.kpi .v small { font-size: 9.5pt; font-weight: 400; }
.kpi .l { font-size: 8pt; color: var(--muted); line-height: 1.5; margin-top: 4px; }
table.req { margin-top: 4px; }

/* 제목 */
h2 { font-size: 14pt; color: var(--dark); margin: 0 0 10px; padding: 6px 0 6px 10px; border-left: 5px solid var(--accent); background: var(--soft); break-after: avoid; }
h2 { margin-top: 22px; }
h3 { font-size: 11pt; color: var(--dark); margin: 18px 0 6px; padding-bottom: 3px; border-bottom: 1px solid var(--line); break-after: avoid; }
h2 + p, h3 + p, h3 + ul, h3 + table { break-before: avoid; }

/* 표 */
table { display: table !important; table-layout: auto; border-collapse: collapse; width: 100% !important; font-size: 8.3pt; margin: 6px 0 12px; page-break-inside: avoid; line-height: 1.5; }
th { background: var(--dark); color: #fff; font-weight: 700; text-align: left; padding: 5px 6px; border: 1px solid var(--dark); }
td { padding: 4px 6px; border: 1px solid var(--line); vertical-align: top; font-variant-numeric: tabular-nums; }
tbody tr:nth-child(even) td { background: #fafbfc; }

/* 그림 */
figure { margin: 8px 0 14px; page-break-inside: avoid; text-align: center; }
figure img { max-width: 100%; max-height: 112mm; border: 1px solid var(--line); border-radius: 4px; }
figcaption { font-size: 8pt; color: var(--muted); margin-top: 4px; }

/* 1장 첫 부분 머리말 */
.abstract { font-size: 9.2pt; line-height: 1.8; background: var(--soft); border-radius: 8px; padding: 12px 14px; margin: 0 0 18px; }
.abstract b { color: var(--dark); }
.lead { background: var(--accent-soft); border-left: 3px solid var(--accent); padding: 8px 12px; border-radius: 0 6px 6px 0; margin: 0 0 12px; font-size: 9pt; }
`;
fs.writeFileSync(head, `<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap" rel="stylesheet"><style>${css}</style>`);
execFileSync('pandoc', [tmpMd, '-f', 'gfm', '-t', 'html5', '-s', '--metadata', 'title=BeeGuard 결과보고서', '-H', head, '-o', html]);

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.goto('file://' + html, { waitUntil: 'networkidle' });
  await p.evaluate(coverHtml => {
    document.querySelector('header#title-block-header')?.remove();
    document.body.insertAdjacentHTML('afterbegin', coverHtml);
    // 그림 → figure + 설명
    document.querySelectorAll('p > img').forEach(img => {
      const par = img.parentElement;
      if (par.children.length !== 1) return;
      const fig = document.createElement('figure');
      fig.appendChild(img.cloneNode());
      const cap = document.createElement('figcaption');
      cap.textContent = img.alt; fig.appendChild(cap);
      par.replaceWith(fig);
    });
    // 제목이 쪽 끝에 홀로 남지 않도록 제목과 바로 뒤 내용을 한 덩어리로 묶는다
    const kids = [...document.body.children];
    const isH = el => el && (el.tagName === 'H2' || el.tagName === 'H3');
    for (let i = 0; i < kids.length; i++) {
      const el = kids[i];
      if (!isH(el)) continue;
      const group = [el];
      let j = i + 1;
      if (el.tagName === 'H2') {
        if (kids[j] && kids[j].tagName === 'H3') { group.push(kids[j]); j++; if (kids[j] && !isH(kids[j])) { group.push(kids[j]); j++; } }
        else while (kids[j] && !isH(kids[j])) { group.push(kids[j]); j++; }
      } else if (kids[j] && !isH(kids[j])) { group.push(kids[j]); j++; }
      const box = document.createElement('div');
      box.className = 'keep';
      el.before(box);
      group.forEach(g => box.appendChild(g));
      i = j - 1;
    }
    // 숫자 칸 오른쪽 정렬
    document.querySelectorAll('td').forEach(td => { if (/^[\s\d.,%()~·/msFPS]+$/.test(td.textContent.trim()) && /\d/.test(td.textContent)) td.style.textAlign = 'right'; });
  }, cover);
  await p.evaluate(() => document.fonts.ready);
  await p.waitForTimeout(300);
  await p.pdf({
    path: R('report', 'result_report.pdf'), format: 'A4', printBackground: true, displayHeaderFooter: true,
    headerTemplate: '<span></span>',
    footerTemplate: `<div style="width:100%;font-size:7.5pt;color:#8a929c;padding:0 15mm;display:flex;justify-content:space-between;font-family:sans-serif">
      <span>BeeGuard Step 1 Report · 2022041067</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>`,
    margin: { top: '15mm', bottom: '16mm', left: '15mm', right: '15mm' },
  });
  await b.close();
  for (const f of [tmpMd, html, head]) fs.unlinkSync(f);
  console.log('report/result_report.pdf 생성');
})();
