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

    container.innerHTML = data.items.map(item => {
      const flag = CAT_FLAG[item.category] || { label: item.category.toUpperCase(), cls: 'story-flag--dark' };
      return `
        <article class="live-item" data-cat="${item.category}" onclick="window.open('${item.url}','_blank')">
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
