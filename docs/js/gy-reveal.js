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

/* Asia-Pacific map — hover/focus tooltip (progressive enhancement) */
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
    metaEl.textContent = node.getAttribute('data-guides') + ' guides · ' + node.getAttribute('data-cities');
    tip.style.left = (r.left - w.left + r.width / 2) + 'px';
    tip.style.top  = (r.top - w.top) + 'px';
    tip.hidden = false;
  }
  function hide() { tip.hidden = true; }
  wrap.querySelectorAll('.apac-node').forEach(function (node) {
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
