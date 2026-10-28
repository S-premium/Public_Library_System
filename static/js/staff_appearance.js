/**
 * staff_appearance.js — theme + language for ADMIN and LIBRARIAN pages
 * ─────────────────────────────────────────────────────────────────────
 * Drop in:  /static/js/staff_appearance.js
 * Include on every admin / librarian page (the shared sidebar template
 * is the easiest place):
 *   <script src="/static/js/staff_appearance.js"></script>
 *
 * Backend:  GET/POST /api/staff/appearance  ->  table `staff_appearance`
 *           theme must be one of: 'default' | 'dark' | 'light'
 *
 * SELECT NOW, SAVE LATER
 *   Clicking a swatch / choosing a language only PREVIEWS it
 *   (selectTheme / selectLanguage). Nothing is written to the database
 *   until StaffAppearance.saveDraft() is called (the "Save Changes" button).
 *   StaffAppearance.discard() reverts the preview to the saved values.
 *
 * LIGHT THEME
 *   1. A stronger light palette (CSS variables).
 *   2. LIGHT_CSS: scoped rules (html[data-theme="light"]) for the settings
 *      page plus common elements (tables, modals, dropdowns, inputs...).
 *   3. fixContrast(): scans the page and turns white / near-white text that
 *      sits on a LIGHT background into dark text, on every page. Text on dark
 *      backgrounds (dark sidebar, blue buttons) is left alone. Switching back
 *      to Default / Dark restores every colour.
 *   Default and Dark are not touched by any of this.
 *
 * TRANSLATION
 *   PHRASES is a list of [english, filipino, hiligaynon] rows. A text node
 *   (or placeholder / title) is translated only when its whole trimmed text
 *   EXACTLY equals an English phrase. Add rows to PHRASES or call
 *     StaffAppearance.addPhrases([['Save Book', 'I-save ang Libro', 'I-save ang Libro']]);
 *   Add class="notranslate" to exclude an element.
 */
(function () {
  'use strict';

  var API_URL     = '/api/staff/appearance';
  var CACHE_KEY   = 'staff_appearance';
  var DEFAULTS    = { theme: 'default', language: 'english' };
  var LANGS       = ['english', 'filipino', 'hiligaynon'];

  /* ═══════════════ THEMES: default · dark · light ═══════════════ */
  var THEMES = {
    default: {
      '--bg1': '#1e2d3d', '--bg2': '#2f3f4d', '--bg3': '#42586b',
      '--accent': '#9fc1e1', '--accent2': '#48c78e',
      '--card': 'rgba(255,255,255,0.06)', '--card-b': 'rgba(255,255,255,0.10)',
      '--border': 'rgba(255,255,255,0.08)', '--tl': '#dae8f5'
    },
    dark: {
      '--bg1': '#0d1117', '--bg2': '#141a22', '--bg3': '#1c2430',
      '--accent': '#9fc1e1', '--accent2': '#48c78e',
      '--card': 'rgba(255,255,255,0.05)', '--card-b': 'rgba(255,255,255,0.09)',
      '--border': 'rgba(255,255,255,0.08)', '--tl': '#c9d6e3'
    },
    light: {
      '--bg1': '#f7f9fc', '--bg2': '#eff4fa', '--bg3': '#e4edf7',
      '--accent': '#236aa3', '--accent2': '#16895a',
      '--card': 'rgba(255,255,255,0.92)', '--card-b': '#ffffff',
      '--border': 'rgba(27,42,58,0.13)', '--tl': '#3d566d'
    }
  };

  var THEME_LABELS = { default: 'Default', dark: 'Dark', light: 'Light' };

  /* Values saved by the old 6-theme version map onto the new three. */
  var LEGACY = { ocean: 'default', forest: 'default', amber: 'default', cobalt: 'dark', midnight: 'dark', slate: 'dark' };
  function normalizeTheme(t) {
    if (THEMES[t]) return t;
    return LEGACY[t] || DEFAULTS.theme;
  }

  /* Light-theme rules (all scoped, so Default / Dark are untouched). */
  var L = 'html[data-theme="light"] ';
  var LIGHT_CSS = [
    /* ── base ── */
    L + 'body{color:#1b2a3a}',
    L + '::selection{background:rgba(35,106,163,.22)}',
    L + '*::-webkit-scrollbar-thumb{background:rgba(27,42,58,.25);border-radius:8px}',
    L + '*::-webkit-scrollbar-track{background:transparent}',
    L + 'hr{border-color:rgba(27,42,58,.14);opacity:1}',
    L + '.text-muted,' + L + '.text-white-50{color:rgba(27,42,58,.6)!important}',

    /* ── settings page: shell ── */
    L + '.settings-sidebar{background:rgba(255,255,255,.92);box-shadow:2px 0 18px rgba(27,42,58,.06)}',
    L + '.main-topbar{background:rgba(255,255,255,.92);box-shadow:0 1px 10px rgba(27,42,58,.06)}',
    L + '.sidebar-back{color:rgba(27,42,58,.7)}',
    L + '.sidebar-back .back-circle{background:rgba(35,106,163,.1);border-color:rgba(35,106,163,.28)}',
    L + '.profile-email,' + L + '.sr-sub{color:rgba(27,42,58,.6)}',
    L + '.nav-section-label,' + L + '.wk-head,' + L + '.pw-req-title{color:rgba(27,42,58,.48)}',
    L + '.nav-item{color:rgba(27,42,58,.75)}',
    L + '.nav-item:hover{background:rgba(27,42,58,.06);color:#1b2a3a}',
    L + '.nav-item.active,' + L + 'body:not(:has(.settings-section:target)) .nav-item[href="#sec-overview"],' + L + 'body:has(#sec-personal:target) .nav-item[href="#sec-personal"],' + L + 'body:has(#sec-security:target) .nav-item[href="#sec-security"],' + L + 'body:has(#sec-appearance:target) .nav-item[href="#sec-appearance"]{background:rgba(35,106,163,.13);color:var(--accent)}',
    L + 'body:has(#sec-personal:target) .nav-item[href="#sec-overview"],' + L + 'body:has(#sec-security:target) .nav-item[href="#sec-overview"],' + L + 'body:has(#sec-appearance:target) .nav-item[href="#sec-overview"]{background:none;color:rgba(27,42,58,.75)}',
    L + '.qc-label,' + L + '.sr-label,' + L + '.act-text,' + L + '.ls-num{color:#1b2a3a}',
    L + '.ls-num small,' + L + '.ls-lbl,' + L + '.hm-mon,' + L + '.hm-daylbl-col span,' + L + '.hm-legend-note,' + L + '.hm-lg,' + L + '.wk-bar-val,' + L + '.wk-bar-day{color:rgba(27,42,58,.6)}',
    L + '.ls-stat{background:rgba(255,255,255,.85)}',
    L + '.block,' + L + '.quick-card{box-shadow:0 2px 12px rgba(27,42,58,.07)}',
    L + '.block-action,' + L + '.sr-btn{background:rgba(35,106,163,.1);border-color:rgba(35,106,163,.28)}',
    L + 'button.sr-btn:hover:not(:disabled){background:rgba(35,106,163,.18)}',
    L + '.setting-row{border-bottom-color:rgba(27,42,58,.08)}',
    L + '.sr-value{color:var(--tl)}',
    L + '.toggle-track{background:rgba(27,42,58,.2)}',
    L + '.sr-select,' + L + '.sr-input,' + L + '.pw-input-wrap input,' + L + '.settings-search input{background:#fff;border-color:rgba(27,42,58,.2);color:#1b2a3a}',
    L + '.sr-select option{background:#fff;color:#1b2a3a}',
    L + '.settings-search input::placeholder,' + L + '.pw-input-wrap input::placeholder{color:rgba(27,42,58,.45)}',
    L + '.pw-eye{color:rgba(27,42,58,.45)}',
    L + '.pw-strength,' + L + '.wk-bar-track{background:rgba(27,42,58,.09)}',
    L + '.pw-requirements{background:rgba(27,42,58,.04);border-top-color:rgba(27,42,58,.08)}',
    L + '.pw-req-item{color:rgba(27,42,58,.55)}',
    L + '.pw-req-item.met{color:var(--accent2)}',
    L + '.req-dot{border-color:rgba(27,42,58,.28)}',
    L + '.personal-tabs{background:rgba(27,42,58,.06);border-color:rgba(27,42,58,.09)}',
    L + '.personal-tab{color:rgba(27,42,58,.6)}',
    L + '.personal-tab:hover{color:#1b2a3a;background:rgba(27,42,58,.05)}',
    L + '#pt-info:checked ~ .personal-tabs label[for="pt-info"],' + L + '#pt-contact:checked ~ .personal-tabs label[for="pt-contact"]{background:#fff;color:var(--accent);box-shadow:0 2px 8px rgba(27,42,58,.14)}',
    L + '.gender-pill span{background:#fff;border-color:rgba(27,42,58,.2);color:rgba(27,42,58,.72)}',
    L + '.gender-pill span.on{background:rgba(35,106,163,.13);border-color:var(--accent);color:var(--accent)}',
    L + '.l0{background:rgba(27,42,58,.09)}',
    L + '.l1{background:#BBDEFB}',
    L + '.toast-item{background:#fff;color:#1b2a3a;border-color:rgba(27,42,58,.13);box-shadow:0 8px 24px rgba(27,42,58,.2)}',
    L + '.theme-swatch{border-color:rgba(27,42,58,.18)}',
    L + '.theme-swatch.active{border-color:var(--accent)}',
    L + '.theme-swatch.active::after{color:#1b2a3a;text-shadow:none}',
    L + '.avatar-circle{border-color:rgba(255,255,255,.8)}',

    /* ── common elements on every admin / librarian page ── */
    L + '.table{--bs-table-color:#1b2a3a;--bs-table-bg:transparent;--bs-table-striped-bg:rgba(27,42,58,.03);--bs-table-hover-bg:rgba(35,106,163,.06);--bs-table-border-color:rgba(27,42,58,.1);color:#1b2a3a}',
    L + '.card{background:#fff;color:#1b2a3a;border-color:rgba(27,42,58,.12);box-shadow:0 2px 12px rgba(27,42,58,.07)}',
    L + '.modal-content{background:#fff;color:#1b2a3a;border-color:rgba(27,42,58,.13);box-shadow:0 18px 50px rgba(27,42,58,.22)}',
    L + '.modal-header,' + L + '.modal-footer{border-color:rgba(27,42,58,.1)}',
    L + '.dropdown-menu{background:#fff;color:#1b2a3a;border-color:rgba(27,42,58,.13);box-shadow:0 10px 30px rgba(27,42,58,.16)}',
    L + '.dropdown-item{color:#1b2a3a}',
    L + '.dropdown-item:hover{background:rgba(35,106,163,.09);color:#1b2a3a}',
    L + '.form-control,' + L + '.form-select,' + L + 'textarea,' + L + 'select,' +
      L + 'input:not([type=checkbox]):not([type=radio]):not([type=range]):not([type=file]):not([type=color]):not([type=submit]):not([type=button]){background-color:#fff;border-color:rgba(27,42,58,.2);color:#1b2a3a}',
    L + '.form-control:focus,' + L + '.form-select:focus,' + L + 'textarea:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(35,106,163,.15)}',
    L + '.form-control::placeholder,' + L + 'textarea::placeholder,' + L + 'input::placeholder{color:rgba(27,42,58,.45)}',
    L + 'select option{background:#fff;color:#1b2a3a}',

    /* all themes: selectable swatches feel clickable */
    '.theme-swatch,[data-theme-value]{cursor:pointer}'
  ].join('\n');

  function injectStyles() {
    if (document.getElementById('staff-appearance-css')) return;
    var st = document.createElement('style');
    st.id = 'staff-appearance-css';
    st.textContent = LIGHT_CSS;
    (document.head || document.documentElement).appendChild(st);
  }

  /* ═══════════════ LANGUAGE PACK  [english, filipino, hiligaynon] ═══════════════ */
  var PHRASES = [
    /* ── Sidebar / topbar ── */
    ['Admin Panel',            'Panel ng Admin',              'Panel sang Admin'],
    ['Main',                   'Pangunahin',                  'Pangunahon'],
    ['Home',                   'Tahanan',                     'Balay'],
    ['Announcement',           'Anunsyo',                     'Pahibalo'],
    ['Management',             'Pamamahala',                  'Pagdumala'],
    ['User Management',        'Pamamahala ng User',          'Pagdumala sang User'],
    ['Admins',                 'Mga Admin',                   'Mga Admin'],
    ['Librarians',             'Mga Librarian',               'Mga Librarian'],
    ['Users / Members',        'Mga User / Miyembro',         'Mga User / Miyembro'],
    ['Add Management',         'Magdagdag ng Account',        'Magdugang sang Account'],
    ['Add Admin',              'Magdagdag ng Admin',          'Magdugang sang Admin'],
    ['Add Librarian',          'Magdagdag ng Librarian',      'Magdugang sang Librarian'],
    ['Borrow Management',      'Pamamahala ng Paghiram',      'Pagdumala sang Pagpanghulam'],
    ['Borrowing Form',         'Porma ng Paghiram',           'Porma sang Pagpanghulam'],
    ['Borrow History',         'Kasaysayan ng Paghiram',      'Kasaysayan sang Pagpanghulam'],
    ['Book Management',        'Pamamahala ng Libro',         'Pagdumala sang Libro'],
    ['Event Calendar',         'Kalendaryo ng Kaganapan',     'Kalendaryo sang Hitabo'],
    ['Account Requests',       'Mga Kahilingan sa Account',   'Mga Hangyo sa Account'],
    ['System Settings',        'Mga Setting ng Sistema',      'Mga Setting sang Sistema'],
    ['Account settings',       'Mga setting ng account',      'Mga setting sang account'],
    ['Search for...',          'Maghanap ng...',              'Pangitaa ang...'],
    ['Collapse sidebar',       'I-collapse ang sidebar',      'I-collapse ang sidebar'],
    ['Expand sidebar',         'I-expand ang sidebar',        'I-expand ang sidebar'],
    ['Open menu',              'Buksan ang menu',             'Buksi ang menu'],
    ['Logout',                 'Mag-logout',                  'Mag-log out'],
    ['Clear',                  'Burahin',                     'Limpyoha'],

    /* ── Settings page: shell ── */
    ['Settings',               'Mga Setting',                 'Mga Setting'],
    ['Back to Home',           'Bumalik sa Tahanan',          'Balik sa Balay'],
    ['Administrator',          'Tagapangasiwa',               'Manugdumala'],
    ['General',                'Pangkalahatan',               'Pangkabilugan'],
    ['Overview',               'Pangkalahatang-tanaw',        'Pangkabilugan nga Talan-awon'],
    ['Personal Details',       'Personal na Detalye',         'Personal nga Detalye'],
    ['Password & Security',    'Password at Seguridad',       'Password kag Seguridad'],
    ['Preferences',            'Mga Kagustuhan',              'Mga Ginapili'],
    ['Appearance',             'Hitsura',                     'Hitsura'],
    ['Sign Out',               'Mag-sign Out',                'Mag-log out'],
    ['Save Changes',           'I-save ang Pagbabago',        'I-save ang Pagbag-o'],
    ['Find a setting… (e.g. password, theme)',
                               'Maghanap ng setting… (hal. password, tema)',
                               'Pangitaa ang setting… (pananglitan password, tema)'],

    /* ── Settings page: overview ── */
    ['Good to see you,',       'Ikinagagalak kitang makita,', 'Nalipay kami nga makita ka,'],
    ['Manage everything about your account from here.',
                               'Pamahalaan ang lahat tungkol sa iyong account dito.',
                               'Dumalahan ang tanan parte sa imo account diri.'],
    ['Account Summary',        'Buod ng Account',             'Sumaryo sang Account'],
    ['Edit',                   'I-edit',                      'I-edit'],
    ['Username / Email',       'Username / Email',            'Username / Email'],
    ['Account Status',         'Katayuan ng Account',         'Kahimtangan sang Account'],
    ['Active & Verified',      'Aktibo at Na-verify',         'Aktibo kag Na-verify'],
    ['Pending approval',       'Naghihintay ng Pag-apruba',   'Nagahulat sang Pag-aprobar'],
    ['Deactivated',            'Na-deactivate',               'Na-deactivate'],
    ['● Active',               '● Aktibo',                    '● Aktibo'],
    ['● Inactive',             '● Hindi Aktibo',              '● Indi Aktibo'],
    ['Admin Since',            'Admin Mula',                  'Admin Halin Pa'],
    ['Login Activity',         'Aktibidad sa Pag-login',      'Aktibidad sang Pag-login'],
    ['Last 6 months',          'Nakaraang 6 na buwan',        'Nagligad nga 6 ka bulan'],

    /* ── Settings page: personal details ── */
    ['Update your profile information.', 'I-update ang impormasyon ng iyong profile.', 'I-update ang impormasyon sang imo profile.'],
    ['Personal',               'Personal na',                 'Personal nga'],
    ['Details',                'Detalye',                     'Detalye'],
    ['Profile Info',           'Impormasyon ng Profile',      'Impormasyon sang Profile'],
    ['Contact',                'Kontak',                      'Kontak'],
    ['Basic Info',             'Batayang Impormasyon',        'Basehan nga Impormasyon'],
    ['First Name',             'Unang Pangalan',              'Ngalan'],
    ['Last Name',              'Apelyido',                    'Apelyido'],
    ['Gender',                 'Kasarian',                    'Sekso'],
    ['Male',                   'Lalaki',                      'Lalaki'],
    ['Female',                 'Babae',                       'Babayi'],
    ['Others',                 'Iba pa',                      'Iban pa'],
    ['Email / Username',       'Email / Username',            'Email / Username'],
    ['Read-only',              'Basahin lamang',              'Mabasa lang'],
    ['Phone Number',           'Numero ng Telepono',          'Numero sang Telepono'],
    ['Save',                   'I-save',                      'I-save'],
    ['Cancel',                 'Ikansela',                    'Kanselahon'],
    ['First name',             'Unang pangalan',              'Ngalan'],
    ['Last name',              'Apelyido',                    'Apelyido'],
    ['e.g. 0917 123 4567',     'hal. 0917 123 4567',          'pananglitan 0917 123 4567'],

    /* ── Settings page: security (labels only) ── */
    ['Keep your account secure.', 'Panatilihing ligtas ang iyong account.', 'Pabilinon nga luwas ang imo account.'],
    ['& Security',             'at Seguridad',                'kag Seguridad'],
    ['Change Password',        'Palitan ang Password',        'Ilisan ang Password'],
    ['Current Password',       'Kasalukuyang Password',       'Karon nga Password'],
    ['New Password',           'Bagong Password',             'Bag-o nga Password'],
    ['Confirm New Password',   'Kumpirmahin ang Bagong Password', 'Kumpirmahon ang Bag-o nga Password'],
    ['Update Password',        'I-update ang Password',       'I-update ang Password'],

    /* ── Settings page: appearance ── */
    ['Customize how the library looks for you.', 'I-customize ang hitsura ng aklatan para sa iyo.', 'I-customize ang hitsura sang librarya para sa imo.'],
    ['Color Theme',            'Kulay ng Tema',               'Kulay sang Tema'],
    ['Default',                'Default',                     'Default'],
    ['Dark',                   'Madilim',                     'Madulom'],
    ['Light',                  'Maliwanag',                   'Masanag'],
    ['Selected:',              'Napili:',                     'Napili:'],
    ['Language',               'Wika',                        'Pulong'],
    ['Interface Language',     'Wika ng Interface',           'Pulong sang Interface'],
    ['Changes labeled navigation and UI text', 'Binabago ang navigation at mga teksto ng UI', 'Ginabag-o ang navigation kag mga teksto sang UI'],
    ['Changes saved',          'Nai-save ang pagbabago',      'Naka-save na'],
    ['Unsaved changes — click Save Changes to apply.',
                               'Hindi pa nai-save — i-click ang I-save ang Pagbabago.',
                               'Wala pa na-save — i-click ang I-save ang Pagbag-o.']
  ];

  /* Context-specific rows: [css selector of an ancestor, english, filipino, hiligaynon]. */
  var SCOPED = [
    ['.sec-heading h2',      'Appearance', 'Mga Setting ng', 'Mga Setting sang'],
    ['.sec-heading h2 span', 'Settings',   'Hitsura',        'Hitsura']
  ];

  /* ═══════════════ LOOKUP ═══════════════ */
  var MAP = {};        // english -> { filipino, hiligaynon }
  var SCOPED_MAP = []; // [{ sel, en, filipino, hiligaynon }]

  function build() {
    MAP = {};
    PHRASES.forEach(function (row) {
      MAP[row[0]] = { filipino: row[1], hiligaynon: row[2] };
    });
    SCOPED_MAP = SCOPED.map(function (r) {
      return { sel: r[0], en: r[1], filipino: r[2], hiligaynon: r[3] };
    });
  }
  build();

  function lookup(el, trimmed, lang) {
    for (var i = 0; i < SCOPED_MAP.length; i++) {
      var r = SCOPED_MAP[i];
      if (r.en === trimmed && el && el.closest && el.closest(r.sel) &&
          (r.sel.indexOf(' span') === -1 || el.matches('span') || el.closest('span'))) {
        var inSpan = !!el.closest('.sec-heading h2 span');
        var wantsSpan = r.sel.slice(-4) === 'span';
        if (inSpan === wantsSpan) return r[lang];
      }
    }
    var hit = MAP[trimmed];
    return hit ? hit[lang] : null;
  }

  /* ═══════════════ DOM WALK ═══════════════ */
  var SKIP = { SCRIPT: 1, STYLE: 1, NOSCRIPT: 1, CODE: 1, PRE: 1, TEXTAREA: 1, SVG: 1, CANVAS: 1, IFRAME: 1, INPUT: 1, SELECT: 1, OPTION: 1 };
  var TEXT_STATE = new WeakMap(); // Text node -> { orig, applied }
  var ATTR_STATE = new WeakMap(); // Element   -> { attr: { orig, applied } }
  var ATTRS      = ['placeholder', 'title'];
  var currentLang = 'english';
  var observer = null;

  function skipped(el) {
    for (var p = el; p; p = p.parentElement) {
      if (SKIP[p.tagName] || (p.classList && p.classList.contains('notranslate'))) return true;
    }
    return false;
  }

  function translateTextNode(node, lang) {
    var el = node.parentElement;
    if (!el || skipped(el)) return;
    var st = TEXT_STATE.get(node);
    var cur = node.nodeValue;

    if (!st) { st = { orig: cur, applied: null }; TEXT_STATE.set(node, st); }
    else if (st.applied !== null && cur !== st.applied) { st.orig = cur; st.applied = null; } // page changed it

    if (lang === 'english') {
      if (st.applied !== null) { node.nodeValue = st.orig; st.applied = null; }
      return;
    }
    var trimmed = st.orig.trim();
    if (!trimmed) return;
    var tr = lookup(el, trimmed, lang);
    if (tr) {
      var lead = st.orig.match(/^\s*/)[0], trail = st.orig.match(/\s*$/)[0];
      var next = lead + tr + trail;
      if (node.nodeValue !== next) node.nodeValue = next;
      st.applied = next;
    } else if (st.applied !== null) {
      node.nodeValue = st.orig; st.applied = null;
    }
  }

  function translateAttrs(el, lang) {
    if (skipped(el) && el.tagName !== 'INPUT') { if (el.closest && el.closest('.notranslate')) return; }
    var states = ATTR_STATE.get(el) || {};
    ATTRS.forEach(function (attr) {
      if (!el.hasAttribute(attr)) return;
      var cur = el.getAttribute(attr);
      var st  = states[attr];
      if (!st) { st = states[attr] = { orig: cur, applied: null }; }
      else if (st.applied !== null && cur !== st.applied) { st.orig = cur; st.applied = null; }

      if (lang === 'english') {
        if (st.applied !== null) { el.setAttribute(attr, st.orig); st.applied = null; }
        return;
      }
      var tr = lookup(el, st.orig.trim(), lang);
      if (tr) { el.setAttribute(attr, tr); st.applied = tr; }
      else if (st.applied !== null) { el.setAttribute(attr, st.orig); st.applied = null; }
    });
    ATTR_STATE.set(el, states);
  }

  function walk(root, lang) {
    if (!root) return;
    if (root.nodeType === 3) { translateTextNode(root, lang); return; }
    if (root.nodeType !== 1) return;

    var tw = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
    var n;
    while ((n = tw.nextNode())) translateTextNode(n, lang);

    if (root.matches && root.matches('[placeholder],[title]')) translateAttrs(root, lang);
    var els = root.querySelectorAll('[placeholder],[title]');
    for (var i = 0; i < els.length; i++) translateAttrs(els[i], lang);
  }

  function pause()  { if (observer) observer.disconnect(); }
  function resume() {
    if (!observer || !document.body) return;
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
  }

  function applyLanguage(lang) {
    if (LANGS.indexOf(lang) === -1) lang = 'english';
    currentLang = lang;
    document.documentElement.lang = lang === 'filipino' ? 'fil' : lang === 'hiligaynon' ? 'hil' : 'en';
    document.documentElement.dataset.language = lang;

    function run() {
      pause();
      walk(document.body, lang);
      resume();
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run, { once: true });
    else run();
  }

  /* Translate content the page adds later (tables, modals, toasts…) */
  var queue = [], timer = null;
  function startObserver() {
    if (observer || !window.MutationObserver) return;
    observer = new MutationObserver(function (muts) {
      if (currentLang === 'english') return;
      muts.forEach(function (m) {
        if (m.type === 'characterData') queue.push(m.target);
        else m.addedNodes.forEach(function (nd) { queue.push(nd); });
      });
      if (timer) return;
      timer = setTimeout(function () {
        timer = null;
        var items = queue; queue = [];
        pause();
        items.forEach(function (nd) { if (nd.isConnected) walk(nd, currentLang); });
        resume();
      }, 60);
    });
    resume();
  }

  /* ═══════════════ THEME ═══════════════ */
  var currentTheme = DEFAULTS.theme;

  function applyTheme(theme) {
    theme = normalizeTheme(theme);
    currentTheme = theme;
    var vars = THEMES[theme];
    Object.keys(vars).forEach(function (k) { document.documentElement.style.setProperty(k, vars[k]); });
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme === 'light' ? 'light' : 'dark';
    syncPicker();
    scheduleContrast();
  }

  /* ── Theme picker wiring (settings page) ── */
  function pickerKey(el) {
    var k = el.getAttribute('data-theme-value');
    if (k) return THEMES[k] ? k : null;
    var st = ATTR_STATE.get(el);
    var t = ((st && st.title && st.title.orig) || el.getAttribute('title') || '').trim().toLowerCase();
    return THEMES[t] ? t : null;
  }

  function pickers() {
    if (!document.body) return [];
    return Array.prototype.slice.call(document.querySelectorAll('[data-theme-value], .theme-swatch'));
  }

  function syncPicker() {
    pickers().forEach(function (el) {
      var k = pickerKey(el);
      if (k) el.classList.toggle('active', k === currentTheme);
    });
    var label = document.querySelector('#sec-appearance .theme-row + div span');
    if (label && label.textContent.trim() !== THEME_LABELS[currentTheme]) {
      label.childNodes.forEach(function (n) { if (n.nodeType === 3) TEXT_STATE.delete(n); });
      label.textContent = THEME_LABELS[currentTheme];
      if (currentLang !== 'english') walk(label, currentLang);
    }
  }

  /* Click on any swatch -> PREVIEW only. Saved later by saveDraft(). */
  function wirePickers() {
    document.addEventListener('click', function (e) {
      var el = e.target.closest && e.target.closest('[data-theme-value], .theme-swatch');
      if (!el) return;
      var key = pickerKey(el);
      if (!key) return;
      window.StaffAppearance.selectTheme(key);
    });
  }

  /* ═══════════════ CACHE + API ═══════════════ */
  function readCache() {
    var out = Object.assign({}, DEFAULTS);
    try {
      var c = sessionStorage.getItem(CACHE_KEY);
      if (c) out = Object.assign(out, JSON.parse(c));
    } catch (_) {}
    out.theme = normalizeTheme(out.theme);
    if (LANGS.indexOf(out.language) === -1) out.language = DEFAULTS.language;
    return out;
  }
  function writeCache(p) { try { sessionStorage.setItem(CACHE_KEY, JSON.stringify(p)); } catch (_) {} }

  /* ═══════════════ DRAFT: select now, save later ═══════════════ */
  var pending = { theme: null, language: null };

  function hasPending() { return pending.theme !== null || pending.language !== null; }
  function emitDraft() {
    document.dispatchEvent(new CustomEvent('appearanceDraftChanged', { detail: { dirty: hasPending() } }));
  }

  window.StaffAppearance = {
    THEMES: THEMES,

    /** Current saved prefs (from cache). */
    get: readCache,

    /** Save to the database, then apply. Resolves to the server JSON ({success:…}). */
    save: async function (prefs) {
      var merged = Object.assign({}, readCache(), prefs);
      merged.theme = normalizeTheme(merged.theme);
      var data;
      try {
        var res = await fetch(API_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(merged)
        });
        data = await res.json();
      } catch (_) {
        return { success: false, message: 'Network error' };
      }
      if (data && data.success) {
        merged = { theme: normalizeTheme(data.theme), language: data.language };
        writeCache(merged);
        applyTheme(merged.theme);
        applyLanguage(merged.language);
      }
      return data || { success: false };
    },

    /** Add more translations at runtime: rows of [english, filipino, hiligaynon]. */
    addPhrases: function (rows) {
      (rows || []).forEach(function (r) { if (r && r.length >= 3) PHRASES.push(r); });
      build();
      if (currentLang !== 'english') applyLanguage(currentLang);
    },

    applyTheme: applyTheme,
    applyLanguage: applyLanguage,

    /** Preview a theme WITHOUT saving. */
    selectTheme: function (key) {
      key = normalizeTheme(key);
      applyTheme(key);
      pending.theme = (key !== readCache().theme) ? key : null;
      emitDraft();
    },

    /** Preview a language WITHOUT saving. */
    selectLanguage: function (lang) {
      if (LANGS.indexOf(lang) === -1) return;
      applyLanguage(lang);
      pending.language = (lang !== readCache().language) ? lang : null;
      emitDraft();
    },

    /** True when a theme/language has been previewed but not saved yet. */
    hasPending: hasPending,

    /** Save the previewed theme/language to the database. */
    saveDraft: async function () {
      if (!hasPending()) return { success: true, unchanged: true };
      var res = await window.StaffAppearance.save({
        theme:    pending.theme    || currentTheme,
        language: pending.language || currentLang
      });
      if (res && res.success) {
        pending = { theme: null, language: null };
        emitDraft();
      }
      return res;
    },

    /** Throw away the preview and go back to the saved values. */
    discard: function () {
      var saved = readCache();
      pending = { theme: null, language: null };
      applyTheme(saved.theme);
      applyLanguage(saved.language);
      emitDraft();
    },

    /** Instant save (no preview step). */
    setTheme: async function (key) {
      key = normalizeTheme(key);
      if (!THEMES[key] || key === currentTheme) return;
      var prev = currentTheme;
      applyTheme(key);
      var res = await window.StaffAppearance.save({ theme: key });
      if (!res || !res.success) applyTheme(prev);
      document.dispatchEvent(new CustomEvent('appearanceSaved', { detail: res || { success: false } }));
    }
  };

  /* ═══════════════ LIGHT THEME: auto-fix white text on light backgrounds ═══════════════ */
  var contrastTimer = null;
  var CONTRAST_SKIP = { SCRIPT: 1, STYLE: 1, NOSCRIPT: 1, SVG: 1, CANVAS: 1, IFRAME: 1, PATH: 1 };

  function parseColor(str) {
    var m = (str || '').match(/[\d.]+/g);
    if (!m || m.length < 3) return null;
    return { r: +m[0], g: +m[1], b: +m[2], a: m.length > 3 ? +m[3] : 1 };
  }
  function lum(c) { return (0.299 * c.r + 0.587 * c.g + 0.114 * c.b) / 255; }

  /* First visible background above the element; 'unknown' for gradients / images. */
  function effectiveBg(el) {
    for (var p = el; p && p !== document.body && p !== document.documentElement; p = p.parentElement) {
      var cs = getComputedStyle(p);
      if (cs.backgroundImage && cs.backgroundImage !== 'none') return 'unknown';
      var bg = parseColor(cs.backgroundColor);
      if (bg && bg.a > 0.5) return bg;
    }
    return { r: 247, g: 249, b: 252, a: 1 };   // Light theme page background
  }

  function fixContrast() {
    if (currentTheme !== 'light' || !document.body) return;
    var els = document.body.querySelectorAll('*');
    for (var i = 0; i < els.length; i++) {
      var el = els[i];
      if (CONTRAST_SKIP[el.tagName.toUpperCase()] || el.hasAttribute('data-sa-fixed')) continue;

      var hasText = el.tagName === 'I' || Array.prototype.some.call(el.childNodes, function (n) {
        return n.nodeType === 3 && n.nodeValue.trim();
      });
      if (!hasText) continue;

      var c = parseColor(getComputedStyle(el).color);
      if (!c || c.a < 0.05 || lum(c) < 0.72) continue;        // not white-ish

      var bg = effectiveBg(el);
      if (bg === 'unknown' || lum(bg) < 0.6) continue;         // dark background: white text is correct

      el.setAttribute('data-sa-fixed', '1');
      el.setAttribute('data-sa-orig', el.style.getPropertyValue('color'));
      // keep faint (semi-transparent) text readable: never go below 0.62 opacity
      el.style.setProperty('color', 'rgba(27,42,58,' + Math.max(c.a, 0.62) + ')', 'important');
    }
  }

  function clearContrast() {
    var fixed = document.querySelectorAll('[data-sa-fixed]');
    for (var i = 0; i < fixed.length; i++) {
      var el = fixed[i], orig = el.getAttribute('data-sa-orig');
      if (orig) el.style.setProperty('color', orig); else el.style.removeProperty('color');
      el.removeAttribute('data-sa-fixed');
      el.removeAttribute('data-sa-orig');
    }
  }

  function scheduleContrast() {
    clearTimeout(contrastTimer);
    contrastTimer = setTimeout(function () {
      if (!document.body) return;
      if (currentTheme === 'light') fixContrast(); else clearContrast();
    }, 250);   // wait for CSS colour transitions to finish
  }

  function startContrastWatcher() {
    if (!window.MutationObserver || !document.body) return;
    new MutationObserver(function () { if (currentTheme === 'light') scheduleContrast(); })
      .observe(document.body, { childList: true, subtree: true });
  }

  /* ═══════════════ BOOT ═══════════════ */
  injectStyles();
  var cached = readCache();
  applyTheme(cached.theme);            // instant, before first paint where possible
  startObserver();
  wirePickers();
  if (cached.language !== 'english') applyLanguage(cached.language);
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', syncPicker);
  else syncPicker();

  function loadFromServer() {
    fetch(API_URL, { headers: { 'Accept': 'application/json' } })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(); })
      .then(function (d) {
        var prefs = {
          theme:    normalizeTheme(d.theme),
          language: LANGS.indexOf(d.language) !== -1 ? d.language : DEFAULTS.language
        };
        writeCache(prefs);
        if (!hasPending()) {            // don't overwrite an unsaved preview
          applyTheme(prefs.theme);
          applyLanguage(prefs.language);
        }
        document.dispatchEvent(new CustomEvent('appearanceLoaded', { detail: prefs }));
      })
      .catch(function () { /* not logged in / offline: keep cached values */ });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', loadFromServer);
  else loadFromServer();

  window.addEventListener('load', scheduleContrast);
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { startContrastWatcher(); scheduleContrast(); });
  } else { startContrastWatcher(); scheduleContrast(); }
})();