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
