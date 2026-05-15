/* ============================================================
   THE TAX EXPRESS  —  Application Logic
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

    // Dynamically populate lead story and three-column section
    _populateHomeStories(data.items);

    container.innerHTML = data.items.map(item => {
      const flag = CAT_FLAG[item.category] || { label: item.category.toUpperCase(), cls: 'story-flag--dark' };
      return `
        <article class="live-item" data-cat="${item.category}" onclick="openStory('${item.id}')">
          <span class="story-flag ${flag.cls}">${flag.label}</span>
          <h4 class="live-item__hed">${item.title}</h4>
          <p class="live-item__summary">${item.summary}</p>
          <div class="story-byline">
            <span class="byline__author">${item.source}</span>
            <span class="byline__sep">&bull;</span>
            <time>${item.date}</time>
          </div>
        </article>`;
    }).join('');

  } catch (e) {
    container.innerHTML = '<p class="live-feed-loading">Could not load updates.</p>';
  }
}

function filterLive(cat, btn) {
  document.querySelectorAll('.lf-btn').forEach(b => b.classList.remove('is-active'));
  btn.classList.add('is-active');
  document.querySelectorAll('.live-item').forEach(item => {
    item.classList.toggle('is-hidden', cat !== 'all' && item.dataset.cat !== cat);
  });
}

// ── Home page dynamic population ─────────────────────────────
const CAT_IMAGES = {
  it:    'https://images.unsplash.com/photo-1554224155-6726b3ff858f?auto=format&fit=crop&w=900&q=80',
  gst:   'https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=900&q=80',
  itat:  'https://images.unsplash.com/photo-1589829545856-d10d557cf95f?auto=format&fit=crop&w=900&q=80',
  court: 'https://images.unsplash.com/photo-1521791136064-7986c2920216?auto=format&fit=crop&w=900&q=80',
};
const COL_IMAGES = [
  'https://images.unsplash.com/photo-1589829545856-d10d557cf95f?auto=format&fit=crop&w=500&q=80',
  'https://images.unsplash.com/photo-1521791136064-7986c2920216?auto=format&fit=crop&w=500&q=80',
  'https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=500&q=80',
];

function _populateHomeStories(items) {
  if (!items || !items.length) return;

  // ── Lead story: most recent item ──────────────────────────
  const lead = items[0];
  const leadFlag = CAT_FLAG[lead.category] || { label: lead.category.toUpperCase(), cls: 'story-flag--dark' };
  const leadEl = document.querySelector('.lead-story');
  if (leadEl) {
    leadEl.setAttribute('onclick', `openStory('${lead.id}')`);
    const imgEl = leadEl.querySelector('.story-img');
    if (imgEl) imgEl.src = CAT_IMAGES[lead.category] || CAT_IMAGES.it;
    const flagEl = leadEl.querySelector('.story-flag');
    if (flagEl) { flagEl.className = `story-flag ${leadFlag.cls}`; flagEl.textContent = leadFlag.label; }
    const hedEl = leadEl.querySelector('.lead-story__hed');
    if (hedEl) hedEl.textContent = lead.title;
    const deckEl = leadEl.querySelector('.lead-story__deck');
    if (deckEl) deckEl.textContent = lead.summary;
    const timeEl = leadEl.querySelector('time');
    if (timeEl) timeEl.textContent = lead.date;
  }

  // ── Three-column row: items 1–3 ───────────────────────────
  const threeCol = document.querySelector('.three-col');
  if (threeCol && items.length > 1) {
    const colItems = items.slice(1, 4);
    threeCol.innerHTML = colItems.map((item, i) => {
      const flag = CAT_FLAG[item.category] || { label: item.category.toUpperCase(), cls: 'story-flag--dark' };
      return `
        <article class="v-story" style="cursor:pointer" onclick="openStory('${item.id}')">
          <img class="story-img story-img--med" src="${COL_IMAGES[i]}" alt="${flag.label} update" />
          <span class="story-flag ${flag.cls}">${flag.label}</span>
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

  // Wire up "View Original Source" link — opens in new tab
  const srcLink = document.getElementById('modal-story-source-link');
  if (srcLink) {
    if (item.url && item.url !== '#') {
      srcLink.href = item.url;
      srcLink.style.display = 'inline-flex';
    } else {
      srcLink.style.display = 'none';
    }
  }

  openModal('modal-story');
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
<title>${title.replace(/</g,'&lt;')} — The Tax Express</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Merriweather:ital,wght@0,400;0,700;0,900;1,400&family=Source+Sans+3:wght@400;600;700&display=swap');
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Source Sans 3', Arial, sans-serif;
    color: #111; background: #fff;
    padding: 52px 56px; max-width: 800px; margin: 0 auto;
    font-size: 14px; line-height: 1.8;
  }
  .pdf-head {
    text-align: center; padding-bottom: 18px;
    border-bottom: 3px solid #cc0000; margin-bottom: 28px;
  }
  .pdf-logo {
    font-family: 'Merriweather', Georgia, serif;
    font-size: 30px; font-weight: 900; color: #cc0000; letter-spacing: -0.5px;
  }
  .pdf-tagline {
    font-size: 10px; letter-spacing: 2px; text-transform: uppercase;
    color: #888; margin-top: 5px;
  }
  .pdf-label {
    display: inline-block; font-size: 10px; font-weight: 800;
    letter-spacing: 1.5px; text-transform: uppercase;
    background: #cc0000; color: #fff;
    padding: 3px 10px; border-radius: 2px; margin-bottom: 14px;
  }
  h1 {
    font-family: 'Merriweather', Georgia, serif;
    font-size: 22px; font-weight: 900; line-height: 1.4;
    color: #0a0a0a; margin-bottom: 10px;
  }
  .pdf-meta { font-size: 12px; color: #777; margin-bottom: 18px; }
  hr { border: none; border-top: 1px solid #ddd; margin: 18px 0; }
  h3, h4 {
    font-family: 'Source Sans 3', sans-serif;
    font-size: 10px; font-weight: 800; letter-spacing: 1.2px;
    text-transform: uppercase; color: #cc0000; margin: 22px 0 8px;
  }
  p { font-size: 14px; line-height: 1.8; color: #222; margin-bottom: 13px; }
  .pdf-foot {
    margin-top: 44px; padding-top: 14px;
    border-top: 1px solid #ddd; font-size: 11px; color: #aaa;
    display: flex; justify-content: space-between;
  }
  @media print {
    body { padding: 0; }
    @page { margin: 20mm 18mm; }
  }
</style>
</head><body>
<div class="pdf-head">
  <div class="pdf-logo">The Tax Express</div>
  <div class="pdf-tagline">Income Tax &nbsp;&middot;&nbsp; GST &nbsp;&middot;&nbsp; Case Laws &nbsp;&middot;&nbsp; Bare Acts</div>
</div>
<div class="pdf-label">The Tax Express &mdash; Exclusive Report</div>
<h1>${title}</h1>
<p class="pdf-meta">${meta}</p>
<hr/>
${bodyHTML}
<div class="pdf-foot">
  <span>&copy; The Tax Express &nbsp;|&nbsp; thetaxexpress.in</span>
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
