/* Gently Yonder globe: spin it, pick where you fly from, see where our guides go.
 *
 * Canvas, no libraries. Land is a field of dots baked by build_map.py into
 * data/globe.json (gold where we have destination guides, pale gold where we have
 * prep notes). Distances are great-circle, from approximate city centres, shown
 * rounded to 100 km. Nothing moves unless the reader moves it: no auto-spin.
 * Progressive enhancement: without JavaScript the flat map below stays.
 */
(function () {
  'use strict';
  var root = document.querySelector('.gy-globe');
  if (!root || !window.HTMLCanvasElement || !window.fetch) return;
  var wrap = document.querySelector('.wmap');
  var canvas = root.querySelector('canvas');
  var ctx = canvas.getContext('2d');
  var fromSel = root.querySelector('.gy-globe-from');
  var dateIn = root.querySelector('.gy-globe-date');
  var listEl = root.querySelector('.gy-globe-list');
  var cardEl = root.querySelector('.gy-globe-card');
  var D2R = Math.PI / 180;
  var data = null, origin = null, chosen = null, hover = null;
  var view = { lam: 115, phi: 18 };          // centre of the visible hemisphere
  var zoom = 1, R = 100, W = 0, H = 0, dpr = 1, raf = 0, tween = null;
  var dotsByCls = [[], [], []];

  /* ---------- geometry ---------- */
  function project(lon, lat, k) {             // -> [x, y, z] in units of the globe radius
    k = k || 1;
    var l = (lon - view.lam) * D2R, p = lat * D2R, p0 = view.phi * D2R;
    var cp = Math.cos(p);
    return [k * cp * Math.sin(l),
            k * (Math.cos(p0) * Math.sin(p) - Math.sin(p0) * cp * Math.cos(l)),
            k * (Math.sin(p0) * Math.sin(p) + Math.cos(p0) * cp * Math.cos(l))];
  }
  function screen(v) { return [W / 2 + v[0] * R, H / 2 - v[1] * R]; }
  function visible(v) { return v[2] > 0 || v[0] * v[0] + v[1] * v[1] > 1; }
  function vec(lon, lat) {
    var p = lat * D2R, l = lon * D2R;
    return [Math.cos(p) * Math.cos(l), Math.cos(p) * Math.sin(l), Math.sin(p)];
  }
  function km(a, b) {                          // great-circle distance, Earth radius 6371 km
    var dot = vec(a.lng, a.lat), e = vec(b.lng, b.lat);
    var c = Math.max(-1, Math.min(1, dot[0] * e[0] + dot[1] * e[1] + dot[2] * e[2]));
    return Math.acos(c) * 6371;
  }
  function away(ct) { return !origin || km(origin, ct) > 50; }   // not the city you fly from
  function arc(a, b, n) {                     // points along the great circle, lifted off the surface
    var va = vec(a.lng, a.lat), vb = vec(b.lng, b.lat);
    var w = Math.acos(Math.max(-1, Math.min(1, va[0] * vb[0] + va[1] * vb[1] + va[2] * vb[2])));
    var pts = [], s = Math.sin(w) || 1e-9, lift = 0.04 + 0.22 * (w / Math.PI);
    for (var i = 0; i <= n; i++) {
      var t = i / n, f1 = Math.sin((1 - t) * w) / s, f2 = Math.sin(t * w) / s;
      var x = f1 * va[0] + f2 * vb[0], y = f1 * va[1] + f2 * vb[1], z = f1 * va[2] + f2 * vb[2];
      pts.push([Math.atan2(y, x) / D2R, Math.asin(Math.max(-1, Math.min(1, z))) / D2R,
                1 + lift * Math.sin(Math.PI * t)]);
    }
    return pts;
  }

  /* ---------- drawing ---------- */
  var COL = { sea: '#ebe4d6', rim: '#d6cbb6', grat: 'rgba(255,255,255,.6)',
              land: ['#ab9f88', '#a8721f', '#d3ad66'], ink: '#172033', gold: '#a8721f' };
  function size() {
    var box = canvas.parentNode.getBoundingClientRect();
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = Math.round(box.width); H = Math.round(Math.min(box.width, 620));
    canvas.width = W * dpr; canvas.height = H * dpr;
    canvas.style.width = W + 'px'; canvas.style.height = H + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    R = Math.min(W, H) * 0.46 * zoom;
  }
  function line(points, k) {                  // draw the visible runs of a polyline
    var on = false;
    for (var i = 0; i < points.length; i++) {
      var v = project(points[i][0], points[i][1], points[i][2] || k);
      if (visible(v)) {
        var s = screen(v);
        if (on) ctx.lineTo(s[0], s[1]); else { ctx.moveTo(s[0], s[1]); on = true; }
      } else on = false;
    }
  }
  function draw() {
    raf = 0;
    ctx.clearRect(0, 0, W, H);
    ctx.beginPath(); ctx.arc(W / 2, H / 2, R, 0, 2 * Math.PI);
    ctx.fillStyle = COL.sea; ctx.fill(); ctx.strokeStyle = COL.rim; ctx.lineWidth = 1; ctx.stroke();
    // graticule every 30 degrees
    ctx.beginPath(); ctx.strokeStyle = COL.grat; ctx.lineWidth = 1;
    var lat, lon, pts;
    for (lat = -60; lat <= 60; lat += 30) {
      pts = []; for (lon = -180; lon <= 180; lon += 4) pts.push([lon, lat]);
      line(pts, 1);
    }
    for (lon = -180; lon < 180; lon += 30) {
      pts = []; for (lat = -84; lat <= 84; lat += 4) pts.push([lon, lat]);
      line(pts, 1);
    }
    ctx.stroke();
    // land dots, faded towards the rim
    var sz = Math.max(1.8, R * 0.0145);
    for (var c = 0; c < 3; c++) {
      ctx.fillStyle = COL.land[c];
      var arr = dotsByCls[c];
      for (var i = 0; i < arr.length; i += 2) {
        var v = project(arr[i], arr[i + 1], 1);
        if (v[2] <= 0) continue;
        ctx.globalAlpha = 0.35 + 0.65 * v[2];
        ctx.fillRect(W / 2 + v[0] * R - sz / 2, H / 2 - v[1] * R - sz / 2, sz, sz);
      }
    }
    ctx.globalAlpha = 1;
    // routes from the reader's city
    if (origin) {
      data.cities.filter(away).forEach(function (ct) {
        var on = chosen === ct;
        ctx.beginPath(); line(arc(origin, ct, 48));
        ctx.strokeStyle = on ? COL.gold : 'rgba(23,32,51,.38)';
        ctx.lineWidth = on ? 2.4 : 1.1; ctx.stroke();
      });
    }
    // cities, then their labels on top of every dot
    var labels = [];
    data.cities.forEach(function (ct) {
      var v = project(ct.lng, ct.lat, 1);
      if (v[2] <= 0) return;
      var s = screen(v), on = chosen === ct || hover === ct;
      ctx.beginPath(); ctx.arc(s[0], s[1], on ? 6 : 4, 0, 2 * Math.PI);
      ctx.fillStyle = on ? COL.ink : COL.gold; ctx.fill();
      ctx.lineWidth = 1.5; ctx.strokeStyle = '#fbf8f2'; ctx.stroke();
      if (on || zoom >= 2) labels.push([ct.name, s, on]);
    });
    if (origin) {
      var v = project(origin.lng, origin.lat, 1);
      if (v[2] > 0) {
        var s = screen(v);
        ctx.beginPath(); ctx.arc(s[0], s[1], 7, 0, 2 * Math.PI);
        ctx.fillStyle = '#fbf8f2'; ctx.fill(); ctx.lineWidth = 3; ctx.strokeStyle = COL.ink; ctx.stroke();
        labels.push([origin.name, s, true]);
      }
    }
    labels.forEach(function (l) { label(l[0], l[1], l[2]); });
  }
  function label(text, s, strong) {
    ctx.font = (strong ? '700 ' : '600 ') + '12px "Libre Franklin", Helvetica, Arial, sans-serif';
    ctx.lineWidth = 4; ctx.strokeStyle = '#fbf8f2'; ctx.lineJoin = 'round';
    ctx.strokeText(text, s[0] + 9, s[1] - 7);
    ctx.fillStyle = COL.ink; ctx.fillText(text, s[0] + 9, s[1] - 7);
  }
  function redraw() { if (!raf) raf = requestAnimationFrame(draw); }

  /* ---------- motion (only when the reader asks for it) ---------- */
  function turnTo(lon, lat) {
    var from = { lam: view.lam, phi: view.phi };
    var d = ((lon - from.lam + 540) % 360) - 180;
    var t0 = performance.now(), dur = 650;
    if (tween) cancelAnimationFrame(tween);
    (function step(now) {
      var t = Math.min(1, (now - t0) / dur), e = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
      view.lam = from.lam + d * e;
      view.phi = from.phi + (Math.max(-60, Math.min(60, lat)) - from.phi) * e;
      draw();
      tween = t < 1 ? requestAnimationFrame(step) : null;
    })(t0);
  }

  /* ---------- the panel ---------- */
  function fmt(n) { return '≈ ' + (Math.round(n / 100) * 100).toLocaleString('en-GB') + ' km'; }
  function flightsUrl(ct) {
    var d = dateIn && dateIn.value ? dateIn.value.split('-') : null;
    if (!origin || !d) return null;
    return 'https://www.aviasales.com/search/' + origin.code + d[2] + d[1] + ct.iata + '1?marker=' + data.marker;
  }
  function a(href, text, sponsored) {
    var el = document.createElement('a');
    el.href = href; el.textContent = text;
    if (sponsored) { el.rel = 'nofollow sponsored noopener'; el.target = '_blank'; }
    return el;
  }
  function renderList() {
    var rows = data.cities.filter(away).sort(function (x, y) { return origin ? km(origin, x) - km(origin, y) : 0; });
    listEl.innerHTML = '';
    rows.forEach(function (ct) {
      var li = document.createElement('li'), b = document.createElement('button');
      b.type = 'button'; b.className = chosen === ct ? 'is-on' : '';
      b.innerHTML = '<strong></strong><span class="gy-globe-meta"></span>';
      b.querySelector('strong').textContent = ct.name;
      b.querySelector('.gy-globe-meta').textContent = ct.country + (origin ? ' · ' + fmt(km(origin, ct)) : '');
      b.addEventListener('click', function () { choose(ct, true); });
      li.appendChild(b); listEl.appendChild(li);
    });
  }
  function renderCard() {
    cardEl.innerHTML = '';
    if (!chosen) { cardEl.hidden = true; return; }
    var ct = chosen, L = ct.links, h = document.createElement('p');
    h.className = 'gy-globe-card-h'; h.textContent = ct.name + ', ' + ct.country;
    cardEl.appendChild(h);
    if (origin && away(ct)) {
      var m = document.createElement('p'); m.className = 'gy-globe-card-meta';
      m.textContent = fmt(km(origin, ct)) + ' from ' + origin.name + ' as the crow flies';
      cardEl.appendChild(m);
    }
    var ul = document.createElement('ul');
    function add(el) { var li = document.createElement('li'); li.appendChild(el); ul.appendChild(li); }
    if (L.stay) add(a(L.stay, 'Where to stay in ' + ct.name + ' →'));
    if (L.hotels) add(a(L.hotels, 'Hotels around central ' + ct.name + ' (Stay22) →', true));
    if (L.first) add(a(L.first, ct.name + ' for first-timers →'));
    if (L.todo) add(a(L.todo, 'Things to do in ' + ct.name + ' →'));
    if (L.hub && !L.first) add(a(L.hub, 'Our ' + ct.name + ' guide →'));
    if (L.esim) add(a(L.esim, 'An eSIM for ' + ct.country + ' →'));
    var f = away(ct) ? flightsUrl(ct) : null;
    if (f) add(a(f, 'Search flights ' + origin.code + ' → ' + ct.iata + ' on Aviasales →', true));
    cardEl.appendChild(ul);
    if (ct.note) {
      var n = document.createElement('p'); n.className = 'gy-globe-card-note';
      n.textContent = 'Flights go to ' + ct.iata + ': ' + ct.note + '.';
      cardEl.appendChild(n);
    }
    cardEl.hidden = false;
  }
  function choose(ct, turn) {
    chosen = ct;
    if (turn) turnTo(ct.lng, ct.lat); else redraw();
    renderList(); renderCard();
    if (window.gtag) gtag('event', 'globe_city', { city: ct.name, from: origin ? origin.code : '' });
  }
  function routesCentre() {                  // halfway between the reader and the cities we cover
    var c = [0, 0, 0];
    data.cities.forEach(function (ct) { var v = vec(ct.lng, ct.lat); c[0] += v[0]; c[1] += v[1]; c[2] += v[2]; });
    var o = vec(origin.lng, origin.lat), n = Math.hypot(c[0], c[1], c[2]);
    var m = [o[0] + c[0] / n, o[1] + c[1] / n, o[2] + c[2] / n], k = Math.hypot(m[0], m[1], m[2]);
    if (k < 0.2) m = [c[0] / n, c[1] / n, c[2] / n], k = 1;    // the cities are on the far side of the world
    return [Math.atan2(m[1], m[0]) / D2R, Math.asin(m[2] / k) / D2R];
  }
  function setOrigin(code, turn) {
    origin = data.origins.filter(function (o) { return o.code === code; })[0] || data.origins[0];
    if (fromSel.value !== origin.code) fromSel.value = origin.code;
    var c = routesCentre();
    if (turn) turnTo(c[0], c[1]); else { view.lam = c[0]; view.phi = Math.max(-60, Math.min(60, c[1])); redraw(); }
    renderList(); renderCard();
  }

  /* ---------- input ---------- */
  var drag = null;
  function hit(x, y) {
    var best = null, bd = 196;                // 14 px
    data.cities.forEach(function (ct) {
      var v = project(ct.lng, ct.lat, 1);
      if (v[2] <= 0) return;
      var s = screen(v), d = (s[0] - x) * (s[0] - x) + (s[1] - y) * (s[1] - y);
      if (d < bd) { bd = d; best = ct; }
    });
    return best;
  }
  function pos(e) { var r = canvas.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; }
  canvas.addEventListener('pointerdown', function (e) {
    drag = { p: pos(e), lam: view.lam, phi: view.phi, moved: false };
    canvas.setPointerCapture(e.pointerId);
  });
  canvas.addEventListener('pointermove', function (e) {
    var p = pos(e);
    if (drag) {
      var dx = p[0] - drag.p[0], dy = p[1] - drag.p[1];
      if (Math.abs(dx) + Math.abs(dy) > 4) drag.moved = true;
      var k = 180 / (Math.PI * R);
      view.lam = drag.lam - dx * k;
      view.phi = Math.max(-80, Math.min(80, drag.phi + dy * k));
      redraw();
      return;
    }
    var h = hit(p[0], p[1]);
    if (h !== hover) { hover = h; canvas.style.cursor = h ? 'pointer' : 'grab'; redraw(); }
  });
  canvas.addEventListener('pointerup', function (e) {
    if (drag && !drag.moved) { var h = hit.apply(null, pos(e)); if (h) choose(h, false); }
    drag = null;
  });
  canvas.addEventListener('pointercancel', function () { drag = null; });
  root.querySelectorAll('.gy-globe-zoom button').forEach(function (b) {
    b.addEventListener('click', function () {
      zoom = Math.max(1, Math.min(3, zoom * (b.getAttribute('data-zoom') === 'in' ? 1.4 : 1 / 1.4)));
      size(); redraw();
    });
  });
  fromSel.addEventListener('change', function () {
    setOrigin(fromSel.value, true);
    if (window.gtag) gtag('event', 'globe_origin', { from: fromSel.value });
  });
  if (dateIn) dateIn.addEventListener('change', renderCard);
  window.addEventListener('resize', function () { if (data && !root.hidden) { size(); redraw(); } });

  /* ---------- views: the globe first, the flat map one tap away ---------- */
  function showGlobe(on) {
    root.hidden = !on;
    if (wrap) wrap.classList.toggle('is-hidden-by-globe', on);
    if (on && data) { size(); redraw(); }
  }
  document.querySelectorAll('.wmap-view').forEach(function (b) {
    b.addEventListener('click', function () { showGlobe(b.getAttribute('data-view') === 'globe'); });
  });

  /* ---------- start: load the dots when the map comes near the screen ---------- */
  function guessOrigin() {
    var tz = '';
    try { tz = Intl.DateTimeFormat().resolvedOptions().timeZone || ''; } catch (e) {}
    var o = data.origins.filter(function (x) { return x.tz.indexOf(tz) >= 0; })[0];
    return o ? o.code : 'LON';
  }
  function start() {
    fetch(root.getAttribute('data-src')).then(function (r) { return r.json(); }).then(function (g) {
      data = g;
      for (var i = 0; i < g.dots.length; i += 3) dotsByCls[g.dots[i + 2]].push(g.dots[i] / 10, g.dots[i + 1] / 10);
      g.origins.forEach(function (o) {
        var op = document.createElement('option'); op.value = o.code; op.textContent = o.name + ' (' + o.code + ')';
        fromSel.appendChild(op);
      });
      if (dateIn) {
        var d = new Date(Date.now() + 30 * 864e5), t = new Date();
        dateIn.value = d.toISOString().slice(0, 10);
        dateIn.min = t.toISOString().slice(0, 10);
      }
      var btn = document.querySelector('.wmap-view[data-view="globe"]');
      if (btn) { btn.hidden = false; btn.click(); }
      showGlobe(true);
      setOrigin(guessOrigin(), false);
      size(); draw();
    }).catch(function () { showGlobe(false); });
  }
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (es) {
      if (es.some(function (x) { return x.isIntersecting; })) { io.disconnect(); start(); }
    }, { rootMargin: '600px 0px' });
    io.observe(root.parentNode);
  } else start();
})();
