/* Gently Yonder — scroll reveal (dependency-free, fail-safe).
   Fades content blocks in as they enter the viewport. Design rules:
   - Elements already in the first viewport are never hidden.
   - A sentinel verifies IntersectionObserver actually fires in this
     environment; if it doesn't within 1.5s, everything is revealed.
   - prefers-reduced-motion disables the effect entirely (CSS also guards). */
(function () {
  "use strict";
  if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  if (!("IntersectionObserver" in window)) return;

  var candidates = document.querySelectorAll(
    "main h2, .article-figure, .tip-box, .product-card, .faq details, .related-articles, .prep-table"
  );
  if (!candidates.length) return;

  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add("gy-in");
        io.unobserve(entry.target);
      }
    });
  }, { rootMargin: "0px", threshold: 0 });

  var hidden = [];
  candidates.forEach(function (el) {
    // Skip the homepage's own data-reveal system.
    if (el.closest("[data-reveal]")) return;
    // Never hide anything the visitor can already see.
    var r = el.getBoundingClientRect();
    if (r.top < window.innerHeight && r.bottom > 0) return;
    el.classList.add("gy-reveal");
    hidden.push(el);
    io.observe(el);
  });
  if (!hidden.length) return;

  // Sentinel: the root element always intersects, so a working observer
  // fires immediately. If it hasn't fired in 1.5s, fail open.
  var ioAlive = false;
  var sentinel = new IntersectionObserver(function () {
    ioAlive = true;
    sentinel.disconnect();
  });
  sentinel.observe(document.documentElement);
  setTimeout(function () {
    if (!ioAlive) {
      hidden.forEach(function (el) { el.classList.add("gy-in"); });
      io.disconnect();
      sentinel.disconnect();
    }
  }, 1500);
})();

/* World map — hover/focus tooltip and the close-up toggle (progressive enhancement) */
(function () {
  var wrap = document.querySelector('.apac-map-wrap');
  if (!wrap) return;
  var tip = wrap.querySelector('.apac-tooltip');
  if (!tip) return;
  var nameEl = tip.querySelector('.apac-tt-name');
  var metaEl = tip.querySelector('.apac-tt-meta');
  function show(node) {
    var r = node.getBoundingClientRect(), w = wrap.getBoundingClientRect();
    nameEl.textContent = node.getAttribute('data-country');
    metaEl.textContent = node.getAttribute('data-meta') ||
      (node.getAttribute('data-guides') + ' guides · ' + node.getAttribute('data-cities'));
    tip.style.left = (r.left - w.left + r.width / 2) + 'px';
    tip.style.top  = (r.top - w.top) + 'px';
    tip.hidden = false;
  }
  function hide() { tip.hidden = true; }
  /* World / close-up: the same drawing, re-framed (no animation) */
  var svg = wrap.querySelector('svg');
  wrap.querySelectorAll('.wmap-view').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var view = btn.getAttribute('data-view');
      var narrow = view === 'apac' && window.matchMedia('(max-width: 640px)').matches &&
                   wrap.hasAttribute('data-apac-narrow');
      svg.setAttribute('viewBox', wrap.getAttribute(view !== 'apac' ? 'data-world'
                                                     : narrow ? 'data-apac-narrow' : 'data-apac'));
      wrap.classList.toggle('is-apac', view === 'apac');
      wrap.classList.toggle('is-narrow', narrow);
      wrap.querySelectorAll('.wmap-view').forEach(function (b) {
        var on = b === btn;
        b.classList.toggle('is-on', on);
        b.setAttribute('aria-pressed', on ? 'true' : 'false');
      });
      hide();
      if (window.gtag) gtag('event', 'map_view', { view: view });
    });
  });
  wrap.querySelectorAll('.apac-node, .wmap-c').forEach(function (node) {
    node.addEventListener('mouseenter', function () { show(node); });
    node.addEventListener('mouseleave', hide);
    node.addEventListener('focus', function () { show(node); });
    node.addEventListener('blur', hide);
    node.addEventListener('click', function () {
      if (window.gtag) gtag('event', 'map_country_click', { country: node.getAttribute('data-country') || '' });
    });
  });
  document.querySelectorAll('.apac-legend .apac-chip').forEach(function (chip) {
    chip.addEventListener('click', function () {
      var n = chip.querySelector('.apac-chip-name');
      if (window.gtag) gtag('event', 'map_country_click', { country: n ? n.textContent : '', via: 'legend' });
    });
  });
})();

/* Revenue-funnel instrumentation: affiliate + newsletter clicks (aggregate only) */
(function () {
  function onClick(e) {
    if (!e.target.closest) return;
    if (e.type === 'auxclick' && e.button !== 1) return;   /* middle click opens a tab too */
    var a = e.target.closest('a[rel~="sponsored"]');
    if (a) {
      var partner = '';
      try { partner = new URL(a.href).hostname.replace(/^www\./, ''); } catch (err) {}
      /* Which placement earned the click: the verdict box, a table, the link
       * under a partner heading, a widget, or ordinary prose. Tells us whether
       * the answer-first layout (add_aeo.py) converts better than the old
       * end-of-article links. */
      var placement = a.closest('.gy-verdict') ? 'verdict'
        : a.closest('table') ? 'table'
        : a.closest('.gy-section-link') ? 'section'
        : a.closest('.gy-pick') ? 'pick'
        : a.closest('.gy-rates') ? 'hotel'
        : a.closest('.gy-city-rates') ? 'city'
        : a.closest('.gy-quick-picks') ? 'quickpick'
        : a.closest('.gy-globe') ? 'globe'
        : a.closest('.gy-promo') ? 'promo'
        : a.closest('.gy-finder') ? 'finder'
        : a.closest('.gy-widget, .gy-cta') ? 'widget'
        : 'prose';
      /* Travelpayouts short links take ?sub_id= (letters, digits, _), and its
       * dashboard then splits clicks and bookings by it: which page and which
       * placement. It is added only on a real click, so a link a crawler
       * follows arrives without one, and untagged clicks are the bots. */
      try {
        var u = new URL(a.href);
        var page = location.pathname.replace(/^\/(articles\/)?/, '').replace(/(\/index)?\.html$|\/$/, '') || 'home';
        if (/(^|\.)(tpx\.lu|tp\.st|tp\.media)$/.test(u.hostname) && !u.searchParams.has('sub_id')) {
          u.searchParams.set('sub_id', (page + '__' + placement).replace(/[^A-Za-z0-9]+/g, '_'));
          a.href = u.toString();
        } else if (/(^|\.)sjv\.io$/.test(u.hostname) && !u.searchParams.has('subId1')) {
          /* Impact (Holafly) reports subId1-3; it wants letters and digits only */
          u.searchParams.set('subId1', page.replace(/[^A-Za-z0-9]+/g, ''));
          u.searchParams.set('subId2', placement);
          a.href = u.toString();
        } else if (/(^|\.)stay22\.com$/.test(u.hostname) && /^\/allez\//.test(u.pathname)
                   && (!u.searchParams.has('campaign') || /^gentlyyonder-/.test(u.searchParams.get('campaign')))) {
          /* Stay22 (hotels, GetYourGuide) splits its stats by campaign; it wants _ not -.
             Its LetMeAllez script stamps "gentlyyonder-<page>" on our links when the page
             loads, which hides the placement, so that stamp is replaced at click time. */
          u.searchParams.set('campaign', (page + '__' + placement).replace(/[^A-Za-z0-9]+/g, '_'));
          a.href = u.toString();
        }
      } catch (err) {}
      if (window.gtag) gtag('event', 'affiliate_click', { partner: partner, page: location.pathname, placement: placement });
    }
    var b = e.target.closest('.newsletter-btn, [data-tally-open]');
    if (b && window.gtag) gtag('event', 'newsletter_click', { page: location.pathname });
    /* a related guide sending its reader on to a stay guide (add_aeo.STAY_POINTERS):
       tells us which pages feed the hotel pages */
    var sp = e.target.closest('.gy-stay-pointer a');
    if (sp && window.gtag) gtag('event', 'stay_pointer_click', { page: location.pathname, target: sp.getAttribute('href') });
    /* a broad comparison sending its reader to the page for their own trip
       (add_aeo.PICKERS, and the city list's "our area guide" links) */
    var pk = e.target.closest('.gy-picker a, .gy-city-rates-list a[href$=".html"]');
    if (pk && window.gtag) gtag('event', 'picker_click', { page: location.pathname, target: pk.getAttribute('href') });
  }
  document.addEventListener('click', onClick, true);
  document.addEventListener('auxclick', onClick, true);
})();

/* "In this guide" (add_aeo.py): open beside the text on wide screens, where it
   sits in the empty margin; one line on phones. Marks the section being read,
   and on phones folds itself away after a jump so it doesn't cover the text. */
(function () {
  var toc = document.querySelector('.gy-toc');
  if (!toc) return;
  var wide = window.matchMedia ? window.matchMedia('(min-width: 1240px)') : null;
  function isWide() { return !!(wide && wide.matches); }
  function sync() { toc.open = isWide(); }
  sync();
  if (wide) {
    if (wide.addEventListener) wide.addEventListener('change', sync);
    else if (wide.addListener) wide.addListener(sync);
  }

  var links = Array.prototype.slice.call(toc.querySelectorAll('a.gy-toc-link'));
  var heads = links.map(function (a) {
    return document.getElementById(decodeURIComponent(a.getAttribute('href').slice(1)));
  });

  toc.addEventListener('click', function (e) {
    var a = e.target.closest ? e.target.closest('a.gy-toc-link') : null;
    if (!a) return;
    var target = heads[links.indexOf(a)];
    if (window.gtag) gtag('event', 'toc_click', { page: location.pathname, section: a.getAttribute('href') });
    if (!target || isWide()) return;               /* wide: an ordinary anchor jump */
    e.preventDefault();                            /* phone: fold first, then jump, */
    toc.open = false;                              /* so the landing spot is right  */
    target.scrollIntoView();
    if (history.pushState) history.pushState(null, '', a.getAttribute('href'));
  });

  var current = -1, queued = false;
  function mark() {
    queued = false;
    if (!isWide()) return;
    var idx = -1;
    for (var i = 0; i < heads.length; i++) {
      if (heads[i] && heads[i].getBoundingClientRect().top < 140) idx = i; else if (heads[i]) break;
    }
    if (idx === current) return;
    if (current >= 0) { links[current].classList.remove('is-current'); links[current].removeAttribute('aria-current'); }
    if (idx >= 0) { links[idx].classList.add('is-current'); links[idx].setAttribute('aria-current', 'location'); }
    current = idx;
  }
  window.addEventListener('scroll', function () {
    if (!queued) { queued = true; requestAnimationFrame(mark); }
  }, { passive: true });
  mark();
})();

/* Time-limited offers (promotions.py). The deadline is the fixed data-ends in
   the markup, never computed in the browser, so a reload cannot reset it. An
   offer past its deadline is replaced by a plain "ended" line; one not yet
   started says when it starts. Impressions are counted once per offer per
   page view, when half of the box is on screen. */
(function () {
  var boxes = document.querySelectorAll('.gy-promo[data-ends]');
  if (!boxes.length) return;
  function ev(name, box, extra) {
    if (!window.gtag) return;
    var p = { promo_id: box.getAttribute('data-promo') || '', page: location.pathname };
    for (var k in extra) p[k] = extra[k];
    gtag('event', name, p);
  }
  function left(ms, precise) {
    var m = Math.floor(ms / 60000), d = Math.floor(m / 1440), h = Math.floor(m % 1440 / 60);
    if (!precise) return d >= 2 ? d + ' days left' : (d * 24 + h) + 'h ' + (m % 60) + 'm left';
    var s = Math.floor(ms / 1000) % 60;
    return (d ? d + 'd ' : '') + h + 'h ' + (m % 60) + 'm ' + s + 's left';
  }
  function tick() {
    var now = Date.now(), live = false;
    for (var i = 0; i < boxes.length; i++) {
      var b = boxes[i], end = Date.parse(b.getAttribute('data-ends')),
          start = Date.parse(b.getAttribute('data-starts') || '');
      if (isNaN(end) || now >= end) {                 /* no valid deadline, or past it */
        if (!b.classList.contains('is-ended')) {
          b.classList.add('is-ended');
          var t = b.querySelector('.gy-promo-title strong');
          b.innerHTML = '<p class="gy-promo-label">Ended</p><p class="gy-promo-title">'
            + (t ? t.textContent : 'This offer') + ': this offer has ended.</p>';
        }
        continue;
      }
      var out = b.querySelector('.gy-promo-left');
      if (!isNaN(start) && now < start) {
        if (out) { out.hidden = false; out.textContent = ' Not started yet.'; }
        b.classList.add('is-upcoming');
        live = true; continue;
      }
      b.classList.remove('is-upcoming');
      b.classList.toggle('is-soon', end - now <= 7 * 864e5);   /* the last week: stronger rule */
      if (out && b.getAttribute('data-countdown') === '1') {
        out.hidden = false;
        out.textContent = ' ' + (b.getAttribute('data-left-prefix') || '')
          + left(end - now, b.getAttribute('data-precision') === 'time');
        live = true;
      } else if (now + 6e4 > end) live = true;
    }
    bar(now);
    return live;
  }
  /* Phones: in an offer's last 14 days, a bar at the foot of the screen keeps
     the real deadline in view while the box itself is scrolled away. */
  var barEl = null, barBox = null, boxInView = false, hidden = false;
  try { hidden = sessionStorage.getItem('gy_promo_bar') === '0'; } catch (e) {}
  function bar(now) {
    if (hidden || !window.matchMedia || !matchMedia('(max-width: 640px)').matches) return;
    if (!barBox) {
      for (var i = 0; i < boxes.length; i++) {
        var e = Date.parse(boxes[i].getAttribute('data-ends'));
        if (!boxes[i].classList.contains('is-ended') && !boxes[i].classList.contains('is-upcoming')
            && e - now <= 14 * 864e5) { barBox = boxes[i]; break; }
      }
      if (!barBox) return;
      if (!barBox.id) barBox.id = 'offer-' + barBox.getAttribute('data-promo');
      barEl = document.createElement('div');
      barEl.className = 'gy-promo-bar';
      barEl.setAttribute('role', 'region');
      barEl.setAttribute('aria-label', 'Time-limited offer');
      barEl.innerHTML = '<a href="#' + barBox.id + '"></a><button type="button" aria-label="Hide this bar">\u00d7</button>';
      barEl.querySelector('button').addEventListener('click', function () {
        hidden = true; barEl.hidden = true;
        try { sessionStorage.setItem('gy_promo_bar', '0'); } catch (e) {}
      });
      barEl.querySelector('a').addEventListener('click', function () { ev('promo_bar_click', barBox, {}); });
      document.body.appendChild(barEl);
      if ('IntersectionObserver' in window) {
        new IntersectionObserver(function (es) { boxInView = es[0].isIntersecting; bar(Date.now()); }).observe(barBox);
      }
    }
    var end = Date.parse(barBox.getAttribute('data-ends')), t = barBox.querySelector('.gy-promo-title strong');
    if (barBox.classList.contains('is-ended') || now >= end) { barEl.hidden = true; return; }
    barEl.querySelector('a').textContent = (t ? t.textContent : 'Offer') + ' \u00b7 '
      + (barBox.getAttribute('data-left-prefix') || '') + left(end - now, false) + ' \u2192';
    barEl.hidden = boxInView;
  }
  if (tick()) var timer = setInterval(function () { if (!tick()) clearInterval(timer); }, 1000);
  else setInterval(tick, 60000);                    /* keep the phone bar's count current */
  for (var k = 0; k < boxes.length; k++) {         /* a tab left open past a deadline */
    var ms = Date.parse(boxes[k].getAttribute('data-ends')) - Date.now();
    if (ms > 0 && ms < 2147483000) setTimeout(tick, ms + 50);
  }
  var seen = {};
  function shown(b) {
    var id = b.getAttribute('data-promo');
    if (seen[id] || b.classList.contains('is-ended')) return;
    seen[id] = 1; ev('promo_impression', b, {});
  }
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { shown(e.target); io.unobserve(e.target); } });
    }, { threshold: 0.5 });
    for (var j = 0; j < boxes.length; j++) io.observe(boxes[j]);
  }
  document.addEventListener('click', function (e) {
    if (!e.target.closest) return;
    var b = e.target.closest('.gy-promo');
    if (!b || b.classList.contains('is-ended')) return;
    var copy = e.target.closest('.gy-promo-copy');
    if (copy) {
      var code = copy.getAttribute('data-code') || '';
      try { navigator.clipboard.writeText(code); copy.textContent = 'Copied'; } catch (err) {}
      ev('coupon_copy', b, {});
      return;
    }
    if (e.target.closest('.gy-promo-cta')) ev('promo_click', b, {});
  }, true);
})();
