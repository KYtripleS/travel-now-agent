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
        : a.closest('.gy-esim-plans') ? 'plans'
        : a.closest('table') ? 'table'
        : a.closest('.gy-section-link') ? 'section'
        : a.closest('.gy-pick') ? 'pick'
        : a.closest('.gy-rates') ? 'hotel'
        : a.closest('.gy-city-rates') ? 'city'
        : a.closest('.gy-quick-picks') ? 'quickpick'
        : a.closest('.gy-globe') ? 'globe'
        : a.closest('.gy-promo') ? 'promo'
        : a.closest('.gy-aff-bar') ? 'stickybar'
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
    /* a hotel's name opens the hotel's own website (no commission, by design): counts
       how much hotel intent leaves that way, next to the "Check rates" clicks */
    var hn = e.target.closest('a.gy-hotel-name');
    if (hn && window.gtag) gtag('event', 'hotel_site_click', { page: location.pathname,
      placement: hn.closest('.gy-quick-picks') ? 'quickpick' : hn.closest('table') ? 'table' : 'prose' });
  }
  document.addEventListener('click', onClick, true);
  document.addEventListener('auxclick', onClick, true);
})();

/* Exposure and map use, the denominators the click counts lack.
   aff_view: a commercial block was at least half on screen (or filled half the
   screen), once per block type per page view, so affiliate_click by placement can be
   read per reader who saw the block rather than per page view.
   map_interact: the reader tapped or clicked into a hotel map. Clicks inside the
   Stay22 iframe are cross-origin and invisible here; the iframe taking focus is the
   one signal the page gets. Once per page view. Nothing about the reader is sent. */
(function () {
  var BLOCKS = [['.gy-verdict', 'verdict'], ['.gy-quick-picks', 'quickpick'], ['.gy-stay-map', 'map'],
                ['.gy-city-rates', 'city'], ['.gy-esim-plans', 'plans'], ['.gy-flightmap', 'flightmap'], ['.gy-trip', 'trip'], ['.gy-rates', 'hotel'], ['.gy-cta', 'widget']];
  var seen = {};
  function send(name, p) { if (window.gtag) gtag('event', name, p); }
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        var kind = e.target.getAttribute('data-gy-view');
        if (seen[kind] || !e.isIntersecting) return;
        if (e.intersectionRatio < 0.5 && e.intersectionRect.height < innerHeight * 0.5) return;
        seen[kind] = true;
        send('aff_view', { page: location.pathname, placement: kind });
        Array.prototype.forEach.call(document.querySelectorAll('[data-gy-view="' + kind + '"]'), function (el) { io.unobserve(el); });
      });
    }, { threshold: [0, 0.25, 0.5] });
    BLOCKS.forEach(function (b) {
      Array.prototype.forEach.call(document.querySelectorAll(b[0]), function (el) {
        if (el.hasAttribute('data-gy-view')) return;   /* a block matching two selectors counts once */
        el.setAttribute('data-gy-view', b[1]);
        io.observe(el);
      });
    });
  }
  if (!document.querySelector('.gy-stay-map iframe')) return;
  var used = false;
  addEventListener('blur', function () {
    setTimeout(function () {
      var f = document.activeElement;
      if (used || !f || f.tagName !== 'IFRAME' || !f.closest('.gy-stay-map')) return;
      used = true;
      send('map_interact', { page: location.pathname });
    }, 0);
  });
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

/* eSIM pages: a bar at the foot of the screen with the partner link for the
   provider whose section is being read (Airalo until the Saily section, and so
   on). It appears once the verdict has scrolled away, hides over the footer and
   under a time-limited offer's bar, and can be closed for the visit. */
(function () {
  if (!/esim|pocket-wifi|staying-connected|sim-card|roaming/.test(location.pathname)) return;
  var BRANDS = { 'airalo.tpx.lu': 'Airalo', 'saily.tpx.lu': 'Saily', 'holafly.sjv.io': 'Holafly' };
  try { if (sessionStorage.getItem('gy_aff_bar') === '0') return; } catch (e) {}
  var main = document.getElementById('main');
  if (!main) return;
  function brandOf(a) {
    try { return BRANDS[new URL(a.href).hostname] ? a : null; } catch (e) { return null; }
  }
  /* the page's partner links, and each h2 with the first one in its section; read
     afresh each time, because partner scripts rewrite links after load */
  function scan() {
    var links = Array.prototype.filter.call(main.querySelectorAll('a[rel~="sponsored"]'), brandOf);
    var hs = main.querySelectorAll('h2'), marks = [];
    links.forEach(function (a) {
      var h = null;
      for (var i = 0; i < hs.length && (hs[i].compareDocumentPosition(a) & Node.DOCUMENT_POSITION_FOLLOWING); i++) h = hs[i];
      if (h && (!marks.length || marks[marks.length - 1].h !== h)) marks.push({ h: h, a: a });
    });
    return { links: links, hs: hs, marks: marks };
  }
  if (!scan().links.length) return;
  var bar = document.createElement('div');
  bar.className = 'gy-aff-bar';
  bar.setAttribute('role', 'region');
  bar.setAttribute('aria-label', 'Partner link');
  bar.hidden = true;
  bar.innerHTML = '<span class="gy-aff-bar-tag">Partner link</span><a rel="nofollow sponsored noopener" target="_blank"></a>'
    + '<button type="button" aria-label="Hide this bar">\u00d7</button>';
  bar.querySelector('button').addEventListener('click', function () {
    bar.hidden = true; off = true;
    document.body.classList.remove('gy-has-aff-bar');
    try { sessionStorage.setItem('gy_aff_bar', '0'); } catch (e) {}
  });
  document.body.appendChild(bar);
  var off = false, footer = document.querySelector('.gy-footer'), verdict = main.querySelector('.gy-verdict');
  function update() {
    if (off) return;
    /* the section being read; past the last provider's section, back to the top pick */
    var p = scan(), links = p.links, hs = p.hs, marks = p.marks;
    if (!links.length) { bar.hidden = true; return; }
    var y = innerHeight * 0.4, cur = links[0], h = null;
    for (var i = 0; i < hs.length && hs[i].getBoundingClientRect().top < y; i++) h = hs[i];
    for (var j = 0; j < marks.length && marks[j].h.getBoundingClientRect().top < y; j++) cur = marks[j].a;
    if (h && marks.length && j === marks.length && h !== marks[j - 1].h) cur = links[0];
    /* other scripts may rewrite or replace partner links, so look the link up each
       time and remember which source it was copied from */
    var link = bar.querySelector('a'), src = cur.getAttribute('href');
    if (link.getAttribute('data-src') !== src) {
      link.setAttribute('data-src', src);
      link.href = cur.href;
      link.textContent = 'See ' + BRANDS[new URL(cur.href).hostname] + ' plans \u2192';
    }
    var past = verdict ? verdict.getBoundingClientRect().bottom < 0 : scrollY > 600;
    var atFoot = footer && footer.getBoundingClientRect().top < innerHeight;
    var promo = document.querySelector('.gy-promo-bar:not([hidden])');
    bar.hidden = !past || atFoot || !!promo;
    document.body.classList.toggle('gy-has-aff-bar', !bar.hidden);
  }
  var queued = false;
  addEventListener('scroll', function () {
    if (queued) return;
    queued = true;
    requestAnimationFrame(function () { queued = false; update(); });
  }, { passive: true });
  addEventListener('resize', update);
  update();
})();

/* Hotel maps: the reader's dates. Stay22's map shows live prices and availability
   once it has check-in and check-out; the dates are kept for the visit, so the
   next guide's map opens on them too. */
(function () {
  var forms = document.querySelectorAll('form.gy-map-dates');
  if (!forms.length) return;
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function iso(d) { return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
  function plus(day, n) { var p = day.split('-'); return iso(new Date(+p[0], +p[1] - 1, +p[2] + n)); }
  var today = iso(new Date()), saved = null;
  try { saved = JSON.parse(sessionStorage.getItem('gy_trip') || 'null'); } catch (e) {}
  if (saved && !(saved.in >= today)) saved = null;
  function apply(form, t) {
    var frame = form.parentNode.querySelector('iframe');
    if (!frame) return;
    var u = new URL(frame.src);
    u.searchParams.set('checkin', t.in);
    u.searchParams.set('checkout', plus(t.in, +t.n));
    u.searchParams.set('adults', t.a);
    if (frame.src !== u.toString()) frame.src = u.toString();
  }
  Array.prototype.forEach.call(forms, function (form) {
    form.hidden = false;
    form.elements['in'].min = today;
    if (saved) {
      form.elements['in'].value = saved.in;
      form.elements['n'].value = saved.n;
      form.elements['a'].value = saved.a;
      apply(form, saved);
    }
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var t = { in: form.elements['in'].value, n: form.elements['n'].value, a: form.elements['a'].value };
      if (!t.in) { form.elements['in'].focus(); return; }
      try { sessionStorage.setItem('gy_trip', JSON.stringify(t)); } catch (err) {}
      apply(form, t);
      if (window.gtag) gtag('event', 'map_dates', { page: location.pathname, nights: +t.n, lead_days: Math.round((new Date(t.in) - new Date(today)) / 864e5) });
    });
  });
})();

/* Flight fares to the city (add_aeo.add_flight_map): Aviasales' fare map from a hub the
   reader picks. The first hub is guessed from the browser's time zone, never sent anywhere;
   a hub the reader picks is kept for the visit. The widget loads only when the box nears the
   screen. On touch screens the map does not pan, so a finger scrolling the guide never gets
   caught in it (the zoom buttons still work). Its links live in a shadow root, so a click is
   counted from the composed path, and only when the widget did not cancel it (pins that just
   open a price card). */
(function () {
  var boxes = document.querySelectorAll('.gy-flightmap');
  if (!boxes.length) return;
  var page = location.pathname;
  function guess() {
    var tz = '';
    try { tz = Intl.DateTimeFormat().resolvedOptions().timeZone || ''; } catch (e) {}
    if (/^America\/(Toronto|Montreal|Halifax|Winnipeg)/.test(tz)) return 'YTO';
    if (/^America\/(Los_Angeles|Vancouver|Denver|Phoenix|Boise|Anchorage)|^Pacific\/Honolulu/.test(tz)) return 'LAX';
    if (/^America\//.test(tz)) return 'NYC';
    if (/^(Australia|Pacific\/Auckland)/.test(tz)) return 'SYD';
    if (/^Asia\/(Kolkata|Calcutta|Dhaka|Karachi|Kathmandu|Colombo)/.test(tz)) return 'DEL';
    if (/^Asia\/(Tokyo|Seoul|Shanghai|Taipei|Hong_Kong)/.test(tz)) return 'TYO';
    if (/^Asia\//.test(tz)) return 'SIN';
    return 'LON';
  }
  var saved = null;
  try { saved = sessionStorage.getItem('gy_from'); } catch (e) {}
  var coarse = window.matchMedia && matchMedia('(pointer: coarse)').matches;
  Array.prototype.forEach.call(boxes, function (box) {
    var btns = Array.prototype.slice.call(box.querySelectorAll('[data-from]'));
    var frame = box.querySelector('.gy-flightmap-frame');
    if (!btns.length || !frame) return;
    box.hidden = false;
    var cur = null, loaded = false;
    function load() {
      loaded = true;
      frame.innerHTML = '';
      var w = Math.round(frame.clientWidth) || 600, h = w < 560 ? 360 : 440;
      var q = 'currency=usd&trs=547982&shmarker=743846.' + box.getAttribute('data-sub')
        + '&lat=' + box.getAttribute('data-lat') + '&lng=' + box.getAttribute('data-lng')
        + '&powered_by=true&search_host=www.aviasales.com%2Fsearch&locale=en&origin=' + cur
        + '&value_min=0&value_max=1000000&round_trip=true&only_direct=false&radius=1'
        + '&draggable=' + (coarse ? 'false' : 'true') + '&disable_zoom=false&show_logo=false&scrollwheel=false'
        + '&primary=%230B63D6&secondary=%230B63D6&light=%23ffffff&width=' + w + '&height=' + h
        + '&zoom=3&promo_id=4054&campaign_id=100';
      var s = document.createElement('script');
      s.async = true; s.charset = 'utf-8';
      s.src = 'https://tpemb.com/content?' + q;
      frame.appendChild(s);
    }
    function pick(code) {
      cur = code;
      btns.forEach(function (b) { b.setAttribute('aria-pressed', b.getAttribute('data-from') === code ? 'true' : 'false'); });
    }
    var first = saved || guess();
    pick(btns.some(function (b) { return b.getAttribute('data-from') === first; }) ? first : btns[0].getAttribute('data-from'));
    box.addEventListener('click', function (e) {
      var b = e.target.closest ? e.target.closest('[data-from]') : null;
      if (!b || b.getAttribute('data-from') === cur) return;
      pick(b.getAttribute('data-from'));
      try { sessionStorage.setItem('gy_from', cur); } catch (err) {}
      if (window.gtag) gtag('event', 'flightmap_from', { page: page, from: cur });
      load();
    });
    if ('IntersectionObserver' in window) {
      var io = new IntersectionObserver(function (en) {
        if (en[0].isIntersecting && !loaded) { io.disconnect(); load(); }
      }, { rootMargin: '400px 0px' });
      io.observe(box);
    } else {
      load();
    }
  });
  document.addEventListener('click', function (e) {
    var box = e.target.closest ? e.target.closest('.gy-flightmap') : null;
    if (!box || e.defaultPrevented || !e.composedPath) return;
    var a = e.composedPath().filter(function (n) { return n.tagName === 'A' && /^https:\/\/tp\.media\/r/.test(n.href || ''); })[0];
    if (a && window.gtag) gtag('event', 'affiliate_click', { partner: 'aviasales', page: page, placement: 'flightmap' });
  });
})();

/* eSIM plans with a destination picker (add_aeo.add_esim_multi): one table per destination,
   the picker shows one. Without JavaScript the first destination shows. */
(function () {
  Array.prototype.forEach.call(document.querySelectorAll('.gy-esim-multi'), function (box) {
    var pick = box.querySelector('.gy-esim-pick'), sel = pick && pick.querySelector('select');
    if (!sel) return;
    pick.hidden = false;
    sel.addEventListener('change', function () {
      Array.prototype.forEach.call(box.querySelectorAll('.gy-esim-dest'), function (p) {
        p.hidden = p.getAttribute('data-dest') !== sel.value;
      });
      if (window.gtag) gtag('event', 'plans_dest', { page: location.pathname, dest: sel.value });
    });
  });
})();

/* Trip-prep reminders (add_aeo.add_trip_reminders): from a departure date, a calendar file of
   timed reminders, one per job, each linking back to the page for it (utm_source=calendar).
   Built in the browser; nothing is sent anywhere. The date the reader gave a hotel map is
   offered first. */
(function () {
  var boxes = document.querySelectorAll('.gy-trip');
  if (!boxes.length) return;
  var BASE = 'https://gentlyyonder.com/articles/';
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function ymd(d) { return d.getFullYear() + pad(d.getMonth() + 1) + pad(d.getDate()); }
  function esc(s) { return String(s).replace(/\\/g, '\\\\').replace(/([,;])/g, '\\$1').replace(/\n/g, '\\n'); }
  function fold(line) {                         /* RFC 5545: lines of at most 75 octets */
    var out = '';
    while (line.length > 73) { out += line.slice(0, 73) + '\r\n '; line = line.slice(73); }
    return out + line;
  }
  var today = new Date(); today.setHours(0, 0, 0, 0);
  var saved = null;
  try { saved = JSON.parse(sessionStorage.getItem('gy_trip') || 'null'); } catch (e) {}
  Array.prototype.forEach.call(boxes, function (box) {
    var form = box.querySelector('form'), list = box.querySelector('.gy-trip-list');
    if (!form) return;
    box.hidden = false;
    var input = form.elements.d, t = new Date(today.getTime() + 864e5);
    input.min = t.getFullYear() + '-' + pad(t.getMonth() + 1) + '-' + pad(t.getDate());
    if (saved && saved.in && saved.in >= input.min) input.value = saved.in;
    var city = box.getAttribute('data-city');
    var JOBS = [
      [60, 19, 'Book your room in ' + city, box.getAttribute('data-stay'), 'room'],
      [45, 19, 'Check flight fares to ' + city, box.getAttribute('data-page'), 'flights'],
      [21, 19, 'Sort travel insurance for ' + city, box.getAttribute('data-ins'), 'insurance'],
      [7, 19, 'Set up your eSIM for ' + city, box.getAttribute('data-esim'), 'esim'],
      [3, 19, 'Pack for ' + city, box.getAttribute('data-pack'), 'packing'],
      [1, 18, 'Tomorrow you fly: the last checks', 'pre-flight-checklist-48-hours.html', 'lastchecks']
    ];
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      if (!input.value) { input.focus(); return; }
      var p = input.value.split('-'), dep = new Date(+p[0], +p[1] - 1, +p[2]);
      var stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d+Z$/, 'Z');
      var ev = [], items = [];
      JOBS.forEach(function (j, i) {
        var d = new Date(dep.getTime() - j[0] * 864e5);
        if (d <= today) return;                   /* that moment has passed: no reminder */
        var url = BASE + j[3] + '?utm_source=calendar&utm_medium=reminder&utm_campaign=trip_prep&utm_content=' + j[4];
        var day = ymd(d), hh = pad(j[1]);
        ev.push(['BEGIN:VEVENT', 'UID:' + day + '-' + j[4] + '-' + Math.random().toString(36).slice(2) + '@gentlyyonder.com',
          'DTSTAMP:' + stamp, 'DTSTART:' + day + 'T' + hh + '0000', 'DTEND:' + day + 'T' + hh + '1500',
          'SUMMARY:' + esc(j[2]), 'DESCRIPTION:' + esc(j[2] + ' (' + j[0] + ' days before you fly). Open: ' + url),
          'URL:' + url, 'BEGIN:VALARM', 'ACTION:DISPLAY', 'DESCRIPTION:' + esc(j[2]), 'TRIGGER:PT0M', 'END:VALARM',
          'END:VEVENT'].map(fold).join('\r\n'));
        items.push('<li><strong>' + d.toLocaleDateString(undefined, { day: 'numeric', month: 'short' }) + ', '
          + hh + ':00</strong> <a href="' + url + '">' + j[2] + '</a></li>');
      });
      if (!ev.length) { list.hidden = false; list.innerHTML = '<li>That date is too close for reminders: the jobs are all due now.</li>'; return; }
      var ics = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Gently Yonder//Trip prep//EN', 'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH', 'X-WR-CALNAME:Trip to ' + esc(city)].join('\r\n') + '\r\n' + ev.join('\r\n') + '\r\nEND:VCALENDAR\r\n';
      var name = 'trip-to-' + city.toLowerCase().replace(/[^a-z0-9]+/g, '-') + '.ics';
      if (/iPhone|iPad|iPod/.test(navigator.userAgent)) {
        location.href = 'data:text/calendar;charset=utf-8,' + encodeURIComponent(ics);   /* iOS opens Calendar */
      } else {
        var a = document.createElement('a');
        a.href = URL.createObjectURL(new Blob([ics], { type: 'text/calendar' }));
        a.download = name; document.body.appendChild(a); a.click();
        setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
      }
      list.innerHTML = items.join(''); list.hidden = false;
      try { sessionStorage.setItem('gy_trip', JSON.stringify({ in: input.value, n: (saved && saved.n) || '3', a: (saved && saved.a) || '2' })); } catch (err) {}
      if (window.gtag) gtag('event', 'trip_reminders', { page: location.pathname, count: ev.length,
        lead_days: Math.round((dep - today) / 864e5) });
    });
  });
})();
