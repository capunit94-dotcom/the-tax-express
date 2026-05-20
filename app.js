/* ============================================================
   TAX AXIS  —  Application Logic
   ============================================================ */

// ── Date ─────────────────────────────────────────────────────
const dateEl = document.getElementById('js-date');
if (dateEl) {
  dateEl.textContent = new Date().toLocaleDateString('en-IN', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
  });
}

// ── Ticker: duplicate for seamless loop ──────────────────────
const belt = document.getElementById('js-ticker');
if (belt) belt.innerHTML += belt.innerHTML;

// ── Section navigation ───────────────────────────────────────
function navClick(link) {
  const id = link.dataset.section;
  document.querySelectorAll('.page-section').forEach(s => s.classList.remove('is-active'));
  document.querySelectorAll('.nav__link').forEach(l => l.classList.remove('is-active'));
  const section = document.getElementById(id);
  if (section) section.classList.add('is-active');
  link.classList.add('is-active');
  document.getElementById('js-nav-list').classList.remove('is-open');
  window.scrollTo({ top: 0, behavior: 'smooth' });
  return false;
}

function showSection(id, _el) {
  const fakeLink = document.querySelector(`.nav__link[data-section="${id}"]`);
  if (fakeLink) navClick(fakeLink);
}

// ── Mobile nav ───────────────────────────────────────────────
function toggleMobileNav() {
  document.getElementById('js-nav-list').classList.toggle('is-open');
}

// ── Search bar ───────────────────────────────────────────────
function toggleSearch() {
  document.getElementById('js-search-bar').classList.toggle('is-open');
  if (document.getElementById('js-search-bar').classList.contains('is-open')) {
    setTimeout(() => document.getElementById('js-search-input')?.focus(), 60);
  }
}
function doSearch() {
  const q = document.getElementById('js-search-input')?.value.trim();
  if (!q) return;
  toast(`Searching for: "${q}" — Full search coming soon.`);
  document.getElementById('js-search-bar').classList.remove('is-open');
  document.getElementById('js-search-input').value = '';
}
document.getElementById('js-search-input')?.addEventListener('keydown', e => {
  if (e.key === 'Enter') doSearch();
  if (e.key === 'Escape') toggleSearch();
});
document.addEventListener('keydown', e => {
  if (e.key === '/' && !['INPUT','TEXTAREA'].includes(document.activeElement.tagName)) {
    e.preventDefault(); toggleSearch();
  }
});

// ── Bare Acts tab ────────────────────────────────────────────
function switchAct(id, btn) {
  document.querySelectorAll('.act-tab').forEach(b => b.classList.remove('is-active'));
  document.querySelectorAll('.act-panel').forEach(p => p.classList.remove('is-active'));
  btn.classList.add('is-active');
  const panel = document.getElementById(id);
  if (panel) panel.classList.add('is-active');
}

function navToAct(actId) {
  showSection('bare', null);
  setTimeout(() => {
    const btn = document.querySelector(`.act-tab[data-act="${actId}"]`);
    if (btn) switchAct(actId, btn);
  }, 80);
  return false;
}

// ── Provision search ─────────────────────────────────────────
function filterSections(input, panelId) {
  const q = input.value.toLowerCase().trim();
  const panel = document.getElementById(panelId);
  if (!panel) return;
  panel.querySelectorAll('.provision').forEach(p => {
    const hay = (p.dataset.text + ' ' + p.innerText).toLowerCase();
    p.classList.toggle('hidden', q.length > 1 && !hay.includes(q));
  });
}

// ── Modals ───────────────────────────────────────────────────
function openModal(id) {
  document.getElementById(id)?.classList.add('is-open');
  document.body.style.overflow = 'hidden';
}
function closeModal(id) {
  document.getElementById(id)?.classList.remove('is-open');
  document.body.style.overflow = '';
}
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-backdrop.is-open').forEach(m => {
      m.classList.remove('is-open');
    });
    document.body.style.overflow = '';
  }
});

// ── Newsletter ───────────────────────────────────────────────
function handleSubscribe() {
  const input = document.querySelector('.newsletter-input');
  const email = input?.value.trim();
  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    toast('Please enter a valid email address.'); return;
  }
  input.value = '';
  toast('Subscribed! Daily Tax Digest will be delivered to your inbox.');
}

// ── Live Feed (news.json) ─────────────────────────────────────
const CAT_FLAG = {
  it:    { label: 'Income Tax', cls: 'story-flag--blue'   },
  gst:   { label: 'GST',        cls: 'story-flag--green'  },
  itat:  { label: 'ITAT',       cls: 'story-flag--purple' },
  court: { label: 'Courts',     cls: 'story-flag--teal'   },
};

// Global store so openStory() can look up full body content
let _newsItems = [];

async function loadLiveFeed() {
  const container = document.getElementById('js-live-feed');
  const updatedEl = document.getElementById('js-live-updated');
  if (!container) return;
  try {
    const res  = await fetch('news.json?v=' + Date.now());
    const data = await res.json();

    if (updatedEl && data.last_updated) {
      updatedEl.textContent = 'Updated: ' + data.last_updated;
    }

    if (!data.items || !data.items.length) {
      container.innerHTML = '<p class="live-feed-loading">No updates yet.</p>';
      return;
    }

    // Store items globally for lookup
    _newsItems = data.items;

    // FIFO: populate lead [0], secondary [1-2], three-col [3-5]
    _populateHomeStories(data.items);

    // ── Live feed: items[6–15] — latest 10 stories ─────────────
    const _liveFeedTpl = item => {
      const flag = CAT_FLAG[item.category] || { label: item.category.toUpperCase(), cls: 'story-flag--dark' };
      return `<article class="live-item" data-cat="${item.category}" onclick="openStory('${item.id}')">
          <span class="story-flag ${flag.cls}">${flag.label}</span>
          <h4 class="live-item__hed">${item.title}</h4>
          <p class="live-item__summary">${item.summary}</p>
          <div class="story-byline">
            <span class="byline__author">${item.source}</span>
            <span class="byline__sep">&bull;</span>
            <time>${item.date}</time>
          </div>
        </article>`;
    };

    container.innerHTML = data.items.slice(6, 16).map(_liveFeedTpl).join('');

    // ── Show More: items[16+] — pre-rendered, collapsed ─────────
    const moreItems  = data.items.slice(16);
    const moreWrap   = document.getElementById('js-show-more-wrap');
    const moreGrid   = document.getElementById('js-more-stories');
    const moreBtn    = document.getElementById('js-show-more-btn');
    if (moreWrap && moreGrid && moreBtn) {
      if (moreItems.length > 0) {
        moreGrid.innerHTML = moreItems.map(_liveFeedTpl).join('');
        moreBtn.textContent = `Show More Stories (${moreItems.length})`;
        moreWrap.style.display = 'block';
      } else {
        moreWrap.style.display = 'none';
      }
    }

  } catch (e) {
    container.innerHTML = '<p class="live-feed-loading">Could not load updates.</p>';
  }
}

function filterLive(cat, btn) {
  document.querySelectorAll('.lf-btn').forEach(b => b.classList.remove('is-active'));
  btn.classList.add('is-active');
  // Filter covers both live-feed and show-more grids
  document.querySelectorAll('.live-item').forEach(item => {
    item.classList.toggle('is-hidden', cat !== 'all' && item.dataset.cat !== cat);
  });
}

// ── Show More Stories toggle ─────────────────────────────────
function showMoreStories() {
  const grid = document.getElementById('js-more-stories');
  const btn  = document.getElementById('js-show-more-btn');
  if (!grid || !btn) return;
  const isOpen = grid.classList.toggle('is-open');
  const count  = grid.querySelectorAll('.live-item').length;
  btn.textContent = isOpen ? 'Show Fewer Stories ▲' : `Show More Stories (${count}) ▼`;
  if (isOpen) grid.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ── Dynamic home page population ─────────────────────────────
const _CAT_IMG_LG = {
  it:    'https://images.unsplash.com/photo-1554224155-6726b3ff858f?auto=format&fit=crop&w=900&q=80',
  gst:   'https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=900&q=80',
  itat:  'https://images.unsplash.com/photo-1589829545856-d10d557cf95f?auto=format&fit=crop&w=900&q=80',
  court: 'https://images.unsplash.com/photo-1521791136064-7986c2920216?auto=format&fit=crop&w=900&q=80',
};
const _COL_IMGS = [
  'https://images.unsplash.com/photo-1589829545856-d10d557cf95f?auto=format&fit=crop&w=500&q=80',
  'https://images.unsplash.com/photo-1521791136064-7986c2920216?auto=format&fit=crop&w=500&q=80',
  'https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=500&q=80',
];
// Small images for the 2 secondary h-stories
const _CAT_IMG_SM = {
  it:    'https://images.unsplash.com/photo-1568234928966-359c35dd8327?auto=format&fit=crop&w=400&q=80',
  gst:   'https://images.unsplash.com/photo-1507679799987-c73779587ccf?auto=format&fit=crop&w=400&q=80',
  itat:  'https://images.unsplash.com/photo-1589829545856-d10d557cf95f?auto=format&fit=crop&w=400&q=80',
  court: 'https://images.unsplash.com/photo-1521791136064-7986c2920216?auto=format&fit=crop&w=400&q=80',
};

/*
 * FIFO Home Layout (items from news.json, newest first):
 *  [0]     → Lead story (full-width)
 *  [1–2]   → Secondary h-stories (fills the 2-story row beside sidebar)
 *  [3–5]   → Three-col cards
 *  [6–15]  → Live feed (10 stories)
 *  [16+]   → Show More Stories (pre-rendered, collapsed)
 */
function _populateHomeStories(items) {
  if (!items || !items.length) return;

  // ── [0] Lead story ───────────────────────────────────────────
  const lead = items[0];
  const lf = CAT_FLAG[lead.category] || { label: lead.category.toUpperCase(), cls: 'story-flag--dark' };
  const leadEl = document.querySelector('.lead-story');
  if (leadEl) {
    leadEl.onclick = () => openStory(lead.id);
    leadEl.style.cursor = 'pointer';
    const img = leadEl.querySelector('.story-img');
    if (img) img.src = lead.image || _CAT_IMG_LG[lead.category] || _CAT_IMG_LG.it;
    const flag = leadEl.querySelector('.story-flag');
    if (flag) { flag.className = `story-flag ${lf.cls}`; flag.textContent = lf.label; }
    const hed = leadEl.querySelector('.lead-story__hed');
    if (hed) hed.textContent = lead.title;
    const deck = leadEl.querySelector('.lead-story__deck');
    if (deck) deck.textContent = lead.summary;
    const t = leadEl.querySelector('time');
    if (t) t.textContent = lead.date;
  }

  // ── [1–2] Secondary h-stories (fills blank row beside sidebar) ─
  const secStack = document.querySelector('.secondary-stack');
  if (secStack && items.length > 1) {
    secStack.innerHTML = items.slice(1, 3).map(item => {
      const f = CAT_FLAG[item.category] || { label: item.category.toUpperCase(), cls: 'story-flag--dark' };
      const sm = item.image || _CAT_IMG_SM[item.category] || _CAT_IMG_SM.it;
      return `<article class="h-story border-top" style="cursor:pointer" onclick="openStory('${item.id}')">
        <div class="h-story__img">
          <img class="story-img story-img--sm" src="${sm}" alt="${f.label} update" />
        </div>
        <div class="h-story__body">
          <span class="story-flag ${f.cls}">${f.label}</span>
          <h3 class="h-story__hed">${item.title}</h3>
          <p class="h-story__deck">${item.summary}</p>
          <div class="story-byline">
            <span class="byline__author">${item.source}</span>
            <span class="byline__sep">&bull;</span>
            <time>${item.date}</time>
          </div>
        </div>
      </article>`;
    }).join('');
  }

  // ── [3–5] Three-col cards ────────────────────────────────────
  const threeCol = document.querySelector('.three-col');
  if (threeCol && items.length > 3) {
    threeCol.innerHTML = items.slice(3, 6).map((item, i) => {
      const f = CAT_FLAG[item.category] || { label: item.category.toUpperCase(), cls: 'story-flag--dark' };
      return `<article class="v-story" style="cursor:pointer" onclick="openStory('${item.id}')">
        <img class="story-img story-img--med" src="${item.image || _COL_IMGS[i]}" alt="${f.label} update" />
        <span class="story-flag ${f.cls}">${f.label}</span>
        <h3 class="v-story__hed">${item.title}</h3>
        <p class="v-story__deck">${item.summary}</p>
        <div class="story-byline"><time>${item.date}</time></div>
      </article>`;
    }).join('');
  }
}

// ── Story Reader (live feed items) ───────────────────────────
function openStory(id) {
  const item = _newsItems.find(n => n.id === id);
  if (!item) return;

  const flag = CAT_FLAG[item.category] || { label: item.category.toUpperCase(), cls: 'story-flag--dark' };

  document.getElementById('modal-story-flag').innerHTML =
    `<span class="story-flag ${flag.cls}">${flag.label}</span>`;
  document.getElementById('modal-story-title').textContent = item.title;
  document.getElementById('modal-story-meta').textContent =
    `${item.source}  •  ${item.date}`;
  document.getElementById('modal-story-body').innerHTML =
    item.body || `<p>${item.summary}</p>`;

  openModal('modal-story');
}

// ── View Full Story — opens branded full-page article ────────
function viewFullStory() {
  const title = document.getElementById('modal-story-title')?.textContent || 'Report';
  const body  = document.getElementById('modal-story-body')?.innerHTML   || '';
  const meta  = document.getElementById('modal-story-meta')?.textContent || '';
  const date  = new Date().toLocaleDateString('en-IN', { year: 'numeric', month: 'long', day: 'numeric' });

  const w = window.open('', '_blank');
  if (!w) { toast('Please allow pop-ups to open the full story.'); return; }
  w.document.write(`<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>${title.replace(/</g,'&lt;')} — Tax Axis</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet"/>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Inter', Arial, sans-serif; color: #33302E; background: #fff; font-size: 15px; line-height: 1.8; }
  .page { max-width: 780px; margin: 0 auto; padding: 40px 28px 60px; }
  .top-bar {
    position: sticky; top: 0; background: #FFF1E5; border-bottom: 2px solid #0F5499;
    display: flex; align-items: center; justify-content: space-between;
    padding: 10px 24px; z-index: 100;
  }
  .top-logo { display: flex; align-items: stretch; gap: 0; text-decoration: none; }
  .logo-tax  { background: #0F5499; color: #fff; font-family: 'Inter', sans-serif; font-weight: 900; font-size: 18px; letter-spacing: 2px; padding: 7px 13px; line-height: 1; display: flex; align-items: center; }
  .logo-axis { background: #1a1a1a; color: #fff; font-family: 'Inter', sans-serif; font-weight: 900; font-size: 18px; letter-spacing: 2px; padding: 7px 13px; line-height: 1; display: flex; align-items: center; }
  .top-btns { display: flex; gap: 10px; }
  .btn {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 8px 16px; font-size: 11px; font-weight: 700; font-family: 'Inter', sans-serif;
    letter-spacing: 0.5px; text-transform: uppercase; cursor: pointer;
    border-radius: 2px; border: none;
  }
  .btn-print { background: #0F5499; color: #fff; }
  .btn-print:hover { background: #0a3d6b; }
  .btn-dl { background: #fff; color: #33302E; border: 1.5px solid #CFC5BA; }
  .btn-dl:hover { border-color: #0F5499; color: #0F5499; }
  .label { font-size: 10px; font-weight: 800; letter-spacing: 1.5px; text-transform: uppercase; background: #0F5499; color: #fff; padding: 3px 10px; border-radius: 2px; display: inline-block; margin: 32px 0 14px; }
  h1 { font-family: 'Playfair Display', Georgia, serif; font-size: 28px; font-weight: 900; line-height: 1.3; color: #33302E; margin-bottom: 10px; }
  .meta { font-size: 13px; color: #66605A; margin-bottom: 20px; }
  hr { border: none; border-top: 1px solid #CFC5BA; margin: 20px 0; }
  h3, h4 { font-size: 10px; font-weight: 800; letter-spacing: 1.2px; text-transform: uppercase; color: #0F5499; margin: 26px 0 8px; font-family: 'Inter', sans-serif; }
  p { font-size: 15px; line-height: 1.85; color: #33302E; margin-bottom: 14px; }
  .foot { margin-top: 48px; padding-top: 14px; border-top: 1px solid #CFC5BA; font-size: 11px; color: #66605A; display: flex; justify-content: space-between; }
  @media print {
    .top-bar { display: none; }
    body { font-size: 13px; }
    @page { margin: 18mm; }
  }
</style>
</head><body>
<div class="top-bar">
  <div class="top-logo">
    <div class="logo-tax">TAX</div>
    <div class="logo-axis">AXIS</div>
  </div>
  <div class="top-btns">
    <button class="btn btn-print" onclick="window.print()">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/></svg>
      Print
    </button>
    <button class="btn btn-dl" onclick="window.print()">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
      Download PDF
    </button>
  </div>
</div>
<div class="page">
  <div class="label">Tax Axis — Exclusive Report</div>
  <h1>${title}</h1>
  <p class="meta">${meta}</p>
  <hr/>
  ${body}
  <div class="foot">
    <span>&copy; Tax Axis &nbsp;|&nbsp; taxaxis.in</span>
    <span>Viewed: ${date}</span>
  </div>
</div>
</body></html>`);
  w.document.close();
}

// ── PDF Download — story reader modal ────────────────────────
function downloadStoryPDF() {
  const title = document.getElementById('modal-story-title')?.textContent || 'Report';
  const body  = document.getElementById('modal-story-body')?.innerHTML   || '';
  const meta  = document.getElementById('modal-story-meta')?.textContent || '';
  _openPDFWindow(title, meta, body);
}

// ── PDF Download — static article modals (lead/1/2) ──────────
function downloadArticlePDF(modalId) {
  const modal = document.getElementById(modalId);
  if (!modal) return;
  const title = modal.querySelector('h2')?.textContent || 'Article';
  const meta  = modal.querySelector('.modal__meta')?.textContent || '';
  // Grab everything after the <hr> as the body
  const hr    = modal.querySelector('hr');
  let body    = '';
  if (hr) {
    let el = hr.nextElementSibling;
    while (el && !el.classList.contains('modal__actions')) {
      body += el.outerHTML;
      el = el.nextElementSibling;
    }
  }
  _openPDFWindow(title, meta, body);
}

// ── Shared PDF window builder ─────────────────────────────────
function _openPDFWindow(title, meta, bodyHTML) {
  const date = new Date().toLocaleDateString('en-IN', {
    year: 'numeric', month: 'long', day: 'numeric'
  });
  const w = window.open('', '_blank');
  if (!w) { toast('Please allow pop-ups to download PDF.'); return; }
  w.document.write(`<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"/>
<title>${title.replace(/</g,'&lt;')} — Tax Axis</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet"/>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Inter', Arial, sans-serif;
    color: #33302E; background: #fff;
    padding: 52px 56px; max-width: 800px; margin: 0 auto;
    font-size: 14px; line-height: 1.8;
  }
  .pdf-head {
    display: flex; flex-direction: column; align-items: flex-start;
    padding-bottom: 18px; border-bottom: 3px solid #0F5499; margin-bottom: 28px;
  }
  .pdf-logo { display: flex; align-items: stretch; gap: 0; margin-bottom: 6px; }
  .logo-tax  { background: #0F5499; color: #fff; font-family: 'Inter', sans-serif; font-weight: 900; font-size: 22px; letter-spacing: 2px; padding: 7px 14px; line-height: 1; display: flex; align-items: center; }
  .logo-axis { background: #1a1a1a; color: #fff; font-family: 'Inter', sans-serif; font-weight: 900; font-size: 22px; letter-spacing: 2px; padding: 7px 14px; line-height: 1; display: flex; align-items: center; }
  .pdf-tagline {
    font-size: 10px; letter-spacing: 2px; text-transform: uppercase;
    color: #66605A; margin-top: 4px;
  }
  .pdf-label {
    display: inline-block; font-size: 10px; font-weight: 800;
    letter-spacing: 1.5px; text-transform: uppercase;
    background: #0F5499; color: #fff;
    padding: 3px 10px; border-radius: 2px; margin-bottom: 14px;
  }
  h1 {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 24px; font-weight: 900; line-height: 1.35;
    color: #33302E; margin-bottom: 10px;
  }
  .pdf-meta { font-size: 12px; color: #66605A; margin-bottom: 18px; }
  hr { border: none; border-top: 1px solid #CFC5BA; margin: 18px 0; }
  h3, h4 {
    font-family: 'Inter', sans-serif;
    font-size: 10px; font-weight: 800; letter-spacing: 1.2px;
    text-transform: uppercase; color: #0F5499; margin: 22px 0 8px;
  }
  p { font-size: 14px; line-height: 1.8; color: #33302E; margin-bottom: 13px; }
  .pdf-foot {
    margin-top: 44px; padding-top: 14px;
    border-top: 1px solid #CFC5BA; font-size: 11px; color: #66605A;
    display: flex; justify-content: space-between;
  }
  @media print {
    body { padding: 0; }
    @page { margin: 20mm 18mm; }
  }
</style>
</head><body>
<div class="pdf-head">
  <div class="pdf-logo">
    <div class="logo-tax">TAX</div>
    <div class="logo-axis">AXIS</div>
  </div>
  <div class="pdf-tagline">Income Tax &nbsp;&middot;&nbsp; GST &nbsp;&middot;&nbsp; Case Laws &nbsp;&middot;&nbsp; Bare Acts</div>
</div>
<div class="pdf-label">Tax Axis &mdash; Exclusive Report</div>
<h1>${title}</h1>
<p class="pdf-meta">${meta}</p>
<hr/>
${bodyHTML}
<div class="pdf-foot">
  <span>&copy; Tax Axis &nbsp;|&nbsp; taxaxis.in</span>
  <span>Downloaded: ${date}</span>
</div>
</body></html>`);
  w.document.close();
  setTimeout(() => { w.focus(); w.print(); }, 700);
}

// Load live feed on page ready
loadLiveFeed();

// ── Toast ─────────────────────────────────────────────────────
let _toastTimer;
function toast(msg) {
  const el = document.getElementById('js-toast');
  if (!el) return;
  el.textContent = msg;
  el.classList.add('is-visible');
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => el.classList.remove('is-visible'), 4000);
}
