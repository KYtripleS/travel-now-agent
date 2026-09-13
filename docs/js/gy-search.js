/* gy-search.js — client-side site search for Gently Yonder.
 *
 * GitHub Pages is static, so there is no server to query: we ship a ~60KB JSON
 * index (data/search-index.json, built by build_search_index.py) and rank it in
 * the browser. 169 pages is small enough that a hand-rolled scorer beats pulling
 * in a search library, and it keeps us free of a CDN dependency.
 *
 * Drives two surfaces:
 *   1. the nav box on every page — instant dropdown, Enter goes to /search.html
 *   2. search.html itself — full results plus a destination widget rail
 *
 * Every destination below was verified before shipping. WeGoTrip city_ids are
 * only listed where a test-render actually returned tours (Okinawa deliberately
 * has none), and `gocity` is only true for the three cities Go City serves of
 * the ones we cover. Do not add an entry here without checking it the same way.
 */
(function () {
  'use strict';

  var INDEX_PATH = 'data/search-index.json';
  var MAX_DROPDOWN = 7;

  /* destination -> verified widget config (see header note) */
  var DESTINATIONS = {
    'tokyo':      { label: 'Tokyo',      wegotrip: '1850147' },
    'kyoto':      { label: 'Kyoto',      wegotrip: '1857910' },
    'osaka':      { label: 'Osaka',      wegotrip: '1853909' },
    'okinawa':    { label: 'Okinawa' },
    'seoul':      { label: 'Seoul',      wegotrip: '1835848' },
    'bangkok':    { label: 'Bangkok',    wegotrip: '1609350' },
    'chiang mai': { label: 'Chiang Mai', wegotrip: '1153671' },
    'phuket':     { label: 'Phuket',     wegotrip: '1151254' },
    'singapore':  { label: 'Singapore',  wegotrip: '1880252', gocity: true },
    'hong kong':  { label: 'Hong Kong',  wegotrip: '1819729', gocity: true },
    'sydney':     { label: 'Sydney',     wegotrip: '2147714', gocity: true },
    'melbourne':  { label: 'Melbourne',  wegotrip: '2158177' },
    'perth':      { label: 'Perth',      wegotrip: '2063523' },
    'taipei':     { label: 'Taipei',     wegotrip: '1668341' },
    'hanoi':      { label: 'Hanoi',      wegotrip: '1581130' },
    'hoi an':     { label: 'Hoi An',     wegotrip: '1580240' },
    'bali':       { label: 'Bali',       wegotrip: '1645528' },
    'kuala lumpur': { label: 'Kuala Lumpur', wegotrip: '1735161' },
    'penang':     { label: 'Penang',     wegotrip: '1735106' },
    'manila':     { label: 'Manila',     wegotrip: '1701668' },
    'cebu':       { label: 'Cebu',       wegotrip: '1717512' },
    'yogyakarta': { label: 'Yogyakarta', wegotrip: '1621177' }
  };

  var AFFILIATE = {
    wegotrip: 'https://wegotrip.tpx.lu/DCr0TOXx',
    gocity:   'https://gocity.tpx.lu/z5uRRfo8',
    klook:    'https://klook.tpx.lu/TgR5Suzs',
    kkday:    'https://kkday.tpx.lu/99SKEU6d',
    airalo:   'https://airalo.tpx.lu/ctddHmQY',
    ekta:     'https://ektatraveling.tpx.lu/LXmPxVUQ',
    aviasales:'https://aviasales.tpx.lu/dESAKheX'
  };
  var REL = 'rel="nofollow sponsored noopener" target="_blank"';

  var docs = null;
  var loading = null;

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function root() {
    var el = document.querySelector('[data-gy-root]');
    return el ? el.getAttribute('data-gy-root') : '';
  }

  function load() {
    if (docs) return Promise.resolve(docs);
    if (loading) return loading;
    loading = fetch(root() + INDEX_PATH)
      .then(function (r) { return r.json(); })
      .then(function (j) { docs = j.docs || []; return docs; })
      .catch(function () { docs = []; return docs; });
    return loading;
  }

  function tokenize(q) {
    return String(q).toLowerCase().split(/[^a-z0-9]+/).filter(Boolean);
  }

  /* Score one document against the query tokens.
   *
   * The ordering that matters most: searching "tokyo" must return the Tokyo
   * guide first, not a Tokyo luggage-storage article. So a page that IS the
   * destination (title is exactly the query, or the slug is .../tokyo/index)
   * gets a decisive bonus, and the category label is worth almost nothing —
   * scoring it highly was what pushed the hub down, since sibling pages carry
   * categories like "Tokyo City Guide" that repeat the destination name. */
  function score(doc, tokens, normQuery) {
    var slug = doc.u.toLowerCase();
    var title = doc.t.toLowerCase();
    var keys = doc.k || '';
    var desc = (doc.d || '').toLowerCase();
    var cat = (doc.c || '').toLowerCase();
    var total = 0;

    var segs = slug.replace(/\.html$/, '').split('/');
    var leaf = segs[segs.length - 1];
    var parent = segs.length > 1 ? segs[segs.length - 2] : '';
    var isHub = leaf === 'index';

    for (var i = 0; i < tokens.length; i++) {
      var t = tokens[i];
      var hit = 0;
      if (slug.indexOf(t) !== -1) hit += 10;
      /* the page whose own filename/folder IS this place */
      if (leaf === t || (isHub && parent === t)) hit += 8;
      if (new RegExp('(^|[^a-z])' + t, 'i').test(title)) hit += 8;
      else if (title.indexOf(t) !== -1) hit += 5;
      if (new RegExp('(^| )' + t + '($| )').test(keys)) hit += 6;
      else if (keys.indexOf(t) !== -1) hit += 2;
      if (cat.indexOf(t) !== -1) hit += 1;
      if (desc.indexOf(t) !== -1) hit += 2;
      if (!hit) return 0;          // every token must match somewhere
      total += hit;
    }

    /* whole-query shape: an exact title is almost always what was wanted */
    var flatTitle = title.replace(/[^a-z0-9]+/g, ' ').trim();
    if (flatTitle === normQuery) total += 30;
    else if (flatTitle.indexOf(normQuery + ' ') === 0) total += 6;

    /* nudge shorter, more focused titles up when scores tie */
    return total + Math.max(0, 40 - doc.t.length) / 100;
  }

  function search(q) {
    var tokens = tokenize(q);
    if (!tokens.length || !docs) return [];
    var normQuery = tokens.join(' ');
    var out = [];
    for (var i = 0; i < docs.length; i++) {
      var s = score(docs[i], tokens, normQuery);
      if (s > 0) out.push({ doc: docs[i], s: s });
    }
    out.sort(function (a, b) { return b.s - a.s; });
    return out;
  }

  /* Which destination (if any) is this query about? Longest label first so
   * "hong kong" wins over a stray "hong". */
  function destinationFor(q) {
    var norm = ' ' + String(q).toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim() + ' ';
    var best = null;
    for (var key in DESTINATIONS) {
      if (norm.indexOf(' ' + key + ' ') !== -1) {
        if (!best || key.length > best.length) best = key;
      }
    }
    return best ? { key: best, cfg: DESTINATIONS[best] } : null;
  }

  /* ---------------- nav dropdown ---------------- */

  function initNav() {
    var box = document.querySelector('.gy-search-box');
    if (!box) return;
    var input = box.querySelector('input');
    var panel = box.querySelector('.gy-search-panel');
    var active = -1;
    var results = [];

    function close() { panel.hidden = true; active = -1; }

    function render() {
      if (!results.length) {
        panel.innerHTML = '<p class="gy-search-empty">No matches yet</p>';
        panel.hidden = false;
        return;
      }
      var html = results.slice(0, MAX_DROPDOWN).map(function (r, i) {
        return '<a class="gy-search-hit' + (i === active ? ' is-active' : '') +
          '" href="' + root() + esc(r.doc.u) + '">' +
          '<span class="gy-search-hit-t">' + esc(r.doc.t) + '</span>' +
          '<span class="gy-search-hit-c">' + esc(r.doc.c) + '</span></a>';
      }).join('');
      html += '<a class="gy-search-all" href="' + root() + 'search.html?q=' +
        encodeURIComponent(input.value) + '">See all ' + results.length +
        ' results &rarr;</a>';
      panel.innerHTML = html;
      panel.hidden = false;
    }

    input.addEventListener('input', function () {
      var q = input.value.trim();
      if (q.length < 2) { close(); return; }
      load().then(function () { results = search(q); active = -1; render(); });
    });

    input.addEventListener('keydown', function (e) {
      var max = Math.min(results.length, MAX_DROPDOWN);
      if (e.key === 'ArrowDown' && max) { e.preventDefault(); active = (active + 1) % max; render(); }
      else if (e.key === 'ArrowUp' && max) { e.preventDefault(); active = (active - 1 + max) % max; render(); }
      else if (e.key === 'Escape') { close(); input.blur(); }
      else if (e.key === 'Enter') {
        if (active >= 0 && results[active]) {
          e.preventDefault();
          window.location.href = root() + results[active].doc.u;
        }
        /* otherwise let the form submit through to search.html */
      }
    });

    input.addEventListener('focus', function () { if (input.value.trim().length >= 2) render(); });
    document.addEventListener('click', function (e) { if (!box.contains(e.target)) close(); });
    load(); // warm the index so the first keystroke is instant
  }

  /* ---------------- search results page ---------------- */

  function widgetRail(dest, q) {
    var cfg = dest ? dest.cfg : null;
    var name = cfg ? cfg.label : null;
    var parts = [];

    if (cfg && cfg.wegotrip) {
      parts.push(
        '<div class="gy-rail-card">' +
        '<h3 class="gy-rail-h">Self-guided tours in ' + esc(name) + '</h3>' +
        '<div class="gy-rail-frame"><script async src="https://tpemb.com/content' +
        '?trs=547982&shmarker=743846&locale=en&city_id=' + cfg.wegotrip +
        '&tours=2&powered_by=true&campaign_id=150&promo_id=4489" charset="utf-8"><\/script></div>' +
        '</div>');
    }

    var links = [];
    if (cfg && cfg.gocity) {
      links.push('<li><a href="' + AFFILIATE.gocity + '" ' + REL + '>Multi-attraction pass for ' +
        esc(name) + ' on Go City &rarr;</a></li>');
    }
    links.push('<li><a href="' + AFFILIATE.klook + '" ' + REL + '>Tours &amp; tickets' +
      (name ? ' in ' + esc(name) : '') + ' on Klook &rarr;</a></li>');
    links.push('<li><a href="' + AFFILIATE.kkday + '" ' + REL + '>Cross-check prices on KKday &rarr;</a></li>');
    links.push('<li><a href="' + AFFILIATE.airalo + '" ' + REL + '>Travel eSIM for your trip &rarr;</a></li>');
    links.push('<li><a href="' + AFFILIATE.ekta + '" ' + REL + '>Compare travel insurance &rarr;</a></li>');
    links.push('<li><a href="' + AFFILIATE.aviasales + '" ' + REL + '>Check current flight fares &rarr;</a></li>');

    parts.push(
      '<div class="gy-rail-card">' +
      '<h3 class="gy-rail-h">' + (name ? 'Book ' + esc(name) : 'Plan your trip') + '</h3>' +
      '<ul class="gy-rail-links">' + links.join('') + '</ul>' +
      '<p class="gy-rail-note">Affiliate links — Gently Yonder may earn a commission at no ' +
      'extra cost to you.</p></div>');

    return parts.join('');
  }

  /* The WeGoTrip embed writes itself into the page, so it has to be injected as
   * a real script node — innerHTML alone would never execute it. */
  function runScripts(container) {
    var olds = container.querySelectorAll('script');
    for (var i = 0; i < olds.length; i++) {
      var old = olds[i];
      var s = document.createElement('script');
      for (var a = 0; a < old.attributes.length; a++) {
        s.setAttribute(old.attributes[a].name, old.attributes[a].value);
      }
      s.text = old.text;
      old.parentNode.replaceChild(s, old);
    }
  }

  function initPage() {
    var page = document.querySelector('[data-gy-search-page]');
    if (!page) return;
    var input = page.querySelector('.gy-searchpage-input');
    var listEl = page.querySelector('.gy-results');
    var countEl = page.querySelector('.gy-results-count');
    var railEl = page.querySelector('.gy-rail');

    function run(q, push) {
      q = (q || '').trim();
      if (input && input.value !== q) input.value = q;
      document.title = q ? 'Search: ' + q + ' | Gently Yonder' : 'Search | Gently Yonder';

      if (!q) {
        countEl.textContent = '';
        listEl.innerHTML = '<p class="gy-results-hint">Try a destination (Sydney, Tokyo, Bangkok), ' +
          'or a topic like eSIM, insurance, or packing.</p>';
        railEl.innerHTML = '';
        return;
      }

      load().then(function () {
        var res = search(q);
        countEl.textContent = res.length
          ? res.length + ' result' + (res.length === 1 ? '' : 's') + ' for "' + q + '"'
          : 'No results for "' + q + '"';

        listEl.innerHTML = res.length
          ? res.map(function (r) {
              return '<article class="gy-result">' +
                '<a class="gy-result-t" href="' + root() + esc(r.doc.u) + '">' + esc(r.doc.t) + '</a>' +
                '<p class="gy-result-c">' + esc(r.doc.c) + '</p>' +
                '<p class="gy-result-d">' + esc(r.doc.d) + '</p></article>';
            }).join('')
          : '<p class="gy-results-hint">Nothing matched. Try a broader word — a country ' +
            'instead of a town, or "eSIM" instead of a brand name.</p>';

        railEl.innerHTML = widgetRail(destinationFor(q), q);
        runScripts(railEl);

        if (push) {
          var url = q ? '?q=' + encodeURIComponent(q) : location.pathname;
          history.replaceState(null, '', url);
        }
        if (window.gtag) window.gtag('event', 'search', { search_term: q, results: res.length });
      });
    }

    var timer = null;
    if (input) {
      input.addEventListener('input', function () {
        clearTimeout(timer);
        timer = setTimeout(function () { run(input.value, true); }, 180);
      });
    }
    var form = page.querySelector('.gy-searchpage-form');
    if (form) form.addEventListener('submit', function (e) { e.preventDefault(); run(input.value, true); });

    var q = new URLSearchParams(location.search).get('q') || '';
    run(q, false);
  }

  function init() { initNav(); initPage(); }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
