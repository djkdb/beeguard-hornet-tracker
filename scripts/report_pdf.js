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
const best = exps.slice().sort((a, b) => b['mAP50-95'] - a['mAP50-95'])[0];
const cm = csv(R('results', 'test_confusion_counts.csv'));
const row = name => cm.find(r => Object.values(r)[0] === `정답:${name}`);
const rate = (t, p) => { const r = row(t); const tot = Object.values(r).slice(1).reduce((s, v) => s + +v, 0); return `${(100 * r[`예측:${p}`] / tot).toFixed(1)}%`; };
const summary = JSON.parse(fs.readFileSync(R('logs', 'summary.json'), 'utf8'));
const f3 = v => (+v).toFixed(3);

const cover = `
<section class="cover">
  <div class="eyebrow">머신러닝 과제 · 결과보고서</div>
  <h1 class="title">YOLOv8 기반 꿀벌·장수말벌·등검은말벌<br>탐지 및 추적</h1>
  <div class="subtitle">양봉장 말벌 방어 시스템 BeeGuard 1단계: 데이터 구축과 모델 개발</div>
  <table class="meta">
    <tr><th>학번 · 이름</th><td>2022041067 이성준</td><th>소속</th><td>충북대학교 소프트웨어학부</td></tr>
    <tr><th>GitHub</th><td colspan="3"><a href="${GITHUB}">${GITHUB}</a></td></tr>
  </table>
  <div class="kpis">
    <div class="kpi"><div class="v">1,423<small>장</small></div><div class="l">직접 수집·라벨링한 학습 이미지<br>(7,583장 수집 → 정제 → 검수)</div></div>
    <div class="kpi"><div class="v">${f3(best.mAP50)}</div><div class="l">테스트 mAP50 (${best.exp})<br>mAP50-95 ${f3(best['mAP50-95'])}</div></div>
    <div class="kpi"><div class="v">${rate('giant_hornet', 'yellow_legged_hornet')}<small> / </small>${rate('yellow_legged_hornet', 'giant_hornet')}</div><div class="l">장수말벌→등검은말벌 /<br>등검은말벌→장수말벌 오인율</div></div>
    <div class="kpi"><div class="v">${summary.duration_s}<small>초</small></div><div class="l">탐지·추적 영상, 세 부류 등장<br>궤적은 logs/tracks.csv로 저장</div></div>
  </div>
  <div class="abstract"><b>요약</b><br>
    한국 양봉장의 두 위협종인 장수말벌과 등검은말벌을 꿀벌과 구분해 탐지·추적하는 YOLOv8 모델을 만들었습니다.
    공개 데이터셋을 쓰지 않고 9개 경로에서 7,583장을 모아 1,536장으로 정제했고, Grounding DINO로 초기 박스를 만든 뒤
    번호를 붙인 검수 시트로 AI 검수를 거쳐 라벨을 다듬었습니다. 무료 GPU를 쓸 수 없어 CPU에서 입력 크기 320과 640을 비교 학습했고,
    테스트 세트에서 두 말벌 종의 오인율과 실패 사례를 분석했습니다. 추적은 ByteTrack으로 하고, 강의 예제와 달리 궤적을 파일로 따로 저장했으며,
    말벌의 정지비행(HOVER)을 표시했습니다. 웹 사진(접사)과 실제 영상(작은 객체)의 차이가 가장 큰 한계로 드러났습니다.</div>
  <table class="req">
    <tr><th>과제 요구사항</th><th>이 보고서 / 저장소</th></tr>
    <tr><td>3개 부류, 부류마다 100장 이상 수집</td><td>꿀벌 397 · 장수말벌 489 · 등검은말벌 347장 (1.2절)</td></tr>
    <tr><td>3개 부류 학습</td><td>YOLOv8n 전이학습, 입력 크기 비교 실험 (1.4~1.6절)</td></tr>
    <tr><td>감지·추적 결과 동영상 (5초 이상)</td><td><code>videos/beeguard_tracking.mp4</code>, 15초 (1.7절)</td></tr>
    <tr><td>GitHub에 학습 모델과 동영상 공개</td><td><code>models/best.pt</code>, 공개 저장소 (2장)</td></tr>
    <tr><td>보고서: 학습 과정·성능 / GitHub 링크 / 경험</td><td>1장 / 2장 / 3장</td></tr>
  </table>
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

/* 표지 */
.cover { page-break-after: always; padding-top: 8mm; }
.eyebrow { color: var(--accent); font-weight: 700; letter-spacing: .08em; font-size: 9pt; }
.title { font-size: 23pt; line-height: 1.32; margin: 6px 0 8px; border: 0; color: var(--dark); }
.subtitle { color: var(--muted); font-size: 11pt; margin-bottom: 18px; }
table.meta { width: 100%; border-collapse: collapse; margin: 0 0 18px; font-size: 9.2pt; }
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
table { border-collapse: collapse; width: 100%; font-size: 8.3pt; margin: 6px 0 12px; page-break-inside: avoid; line-height: 1.5; }
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
