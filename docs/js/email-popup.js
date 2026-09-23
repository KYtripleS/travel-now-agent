/* Gently Yonder — email-capture card (MailerLite direct)
 * A quiet card that slides in at the corner of the page — no dark overlay, no
 * locked page, nothing between the reader and the article. (It was a
 * full-screen modal; a modal on a first visit reads as a content farm, and
 * affiliate-network reviewers judge exactly that.)
 * Fires once per visitor on scroll-depth >60% OR after a time delay,
 * whichever comes first. Dismissals are remembered for 30 days
 * (localStorage), so it never nags a returning reader.
 *
 * The form POSTs straight to MailerLite's subscribe endpoint via a
 * hidden iframe (no CORS, no third-party script), then shows a success
 * state with the Pre-Flight Checklist PDF. Honest + on-brand
 * (navy/gold/cream, easy to dismiss, no fake urgency).
 */
(function () {
  "use strict";
  // The injector stamps data-root with the correct relative climb to site
  // root for this page's depth — robust across nesting and a domain move.
  var ME = document.currentScript;
  var ROOT = (ME && ME.getAttribute("data-root")) || "";
  var SEEN_KEY = "tn_popup_seen_at";
  var SUPPRESS_DAYS = 30;
  var TIME_DELAY_MS = 45000;     // 45s
  var SCROLL_TRIGGER = 0.6;      // 60% of page
  var ML_ACTION = "https://assets.mailerlite.com/jsonp/2495161/forms/192338701516277591/subscribe";
  var PDF_PATH = "downloads/travel-now-preflight-checklist.pdf"; // resolved below

  // Don't show if recently seen/dismissed/subscribed.
  try {
    var seen = parseInt(localStorage.getItem(SEEN_KEY) || "0", 10);
    if (seen && (Date.now() - seen) / 86400000 < SUPPRESS_DAYS) return;
  } catch (e) { /* localStorage blocked — show once this session via flag below */ }

  var shown = false;
  function markSeen() { try { localStorage.setItem(SEEN_KEY, String(Date.now())); } catch (e) {} }

  function injectStyles() {
    var css = ""
      + "#tn-pop-ov{position:fixed;right:20px;bottom:20px;z-index:9990;width:360px;max-width:calc(100vw - 40px);"
      + "opacity:0;transform:translateY(16px);transition:opacity .3s ease,transform .3s ease;pointer-events:none}"
      + "#tn-pop-ov.tn-in{opacity:1;transform:none;pointer-events:auto}"
      + "#tn-pop{background:#fff;border:1px solid #e4dccd;border-radius:12px;"
      + "box-shadow:0 12px 40px rgba(23,32,51,.16);padding:20px 20px 16px;position:relative;"
      + "font-family:Inter,ui-sans-serif,system-ui,-apple-system,sans-serif}"
      + "#tn-pop h2{margin:0 28px 6px 0;font-family:Georgia,'Times New Roman',serif;font-size:1.12rem;"
      + "line-height:1.3;color:#172033}"
      + "#tn-pop p{margin:0 0 12px;color:#5b6576;font-size:.9rem;line-height:1.5}"
      + "#tn-pop form{display:flex;gap:8px}"
      + "#tn-pop .tn-mail{flex:1;min-width:0;border:1px solid #d7cbbb;border-radius:999px;padding:10px 14px;"
      + "font:inherit;font-size:.92rem;color:#172033;background:#fbfaf7;outline:none}"
      + "#tn-pop .tn-mail:focus{border-color:#b8945f}"
      + "#tn-pop .tn-cta{border:0;border-radius:999px;background:#172033;color:#fff;padding:10px 16px;"
      + "font:inherit;font-size:.9rem;font-weight:700;cursor:pointer;white-space:nowrap}"
      + "#tn-pop .tn-cta:hover{background:#26324a}"
      + "#tn-pop .tn-cta[disabled]{opacity:.6;cursor:default}"
      + "#tn-pop .tn-x{position:absolute;top:10px;right:10px;width:28px;height:28px;border:0;border-radius:50%;"
      + "background:transparent;color:#5b6576;font-size:1.2rem;line-height:1;cursor:pointer}"
      + "#tn-pop .tn-x:hover{background:#f6f2ea;color:#172033}"
      + "#tn-pop .tn-note{margin:10px 0 0;color:#8a93a3;font-size:.74rem}"
      + "#tn-pop .tn-ok{display:none}"
      + "#tn-pop .tn-ok a{color:#8a6a3a;font-weight:700}"
      + "@media (max-width:560px){#tn-pop-ov{right:12px;left:12px;bottom:12px;width:auto;max-width:none}}";
    var s = document.createElement("style");
    s.id = "tn-pop-style";
    s.textContent = css;
    document.head.appendChild(s);
  }

  function close(overlay) {
    markSeen();
    overlay.classList.remove("tn-in");
    setTimeout(function () { if (overlay.parentNode) overlay.parentNode.removeChild(overlay); }, 250);
    document.removeEventListener("keydown", onKey);
  }

  var _overlay = null;
  function onKey(e) { if (e.key === "Escape" && _overlay) close(_overlay); }

  function show() {
    if (shown) return;
    shown = true;
    injectStyles();
    var root = ROOT;
    var pdf = root + PDF_PATH;

    var ov = document.createElement("div");
    ov.id = "tn-pop-ov";
    ov.setAttribute("role", "complementary");
    ov.setAttribute("aria-label", "Get the free Gently Yonder pre-flight checklist");
    ov.innerHTML =
      '<div id="tn-pop">'
      + '<button class="tn-x" aria-label="Close">&times;</button>'
      + '<h2>The pre-flight checklist, free</h2>'
      + '<p>Documents, eSIM, carry-on and the security rules people trip over &mdash; '
      + 'as a printable PDF, plus one useful travel-prep note a week.</p>'
      + '<iframe name="tn-ml-sink" style="display:none" title="hidden"></iframe>'
      + '<form id="tn-pop-form" action="' + ML_ACTION + '" method="post" target="tn-ml-sink">'
      + '<input class="tn-mail" type="email" name="fields[email]" required '
      + 'placeholder="your@email.com" aria-label="Email address" autocomplete="email" />'
      + '<input type="hidden" name="ml-submit" value="1" />'
      + '<input type="hidden" name="anticsrf" value="true" />'
      + '<button class="tn-cta" type="submit">Send it</button>'
      + '</form>'
      + '<div class="tn-ok" id="tn-pop-ok">'
      + '<p>Sent. <a href="' + pdf + '" target="_blank" rel="noopener">Download the PDF &rarr;</a> '
      + 'A copy is on its way to your inbox too.</p>'
      + '</div>'
      + '<p class="tn-note">Free. Unsubscribe in one click.</p>'
      + '</div>';
    document.body.appendChild(ov);
    _overlay = ov;
    setTimeout(function () { ov.classList.add("tn-in"); }, 30);  // rAF stalls in background tabs

    ov.querySelector(".tn-x").addEventListener("click", function () { close(ov); });
    document.addEventListener("keydown", onKey);

    // Submit posts to MailerLite in the hidden iframe; we swap to the
    // success state locally (the response is cross-origin by design).
    var form = ov.querySelector("#tn-pop-form");
    form.addEventListener("submit", function () {
      var btn = form.querySelector(".tn-cta");
      btn.disabled = true;
      btn.textContent = "Sending…";
      setTimeout(function () {
        form.style.display = "none";
        ov.querySelector("#tn-pop-ok").style.display = "block";
        markSeen();
        if (window.gtag) gtag("event", "newsletter_signup", { source: "popup" });
      }, 700);
    });
  }

  // Triggers: time delay OR scroll depth, whichever first.
  setTimeout(show, TIME_DELAY_MS);
  function onScroll() {
    var h = document.documentElement;
    var scrolled = (window.scrollY + window.innerHeight) / (h.scrollHeight || 1);
    if (scrolled >= SCROLL_TRIGGER) { show(); window.removeEventListener("scroll", onScroll); }
  }
  window.addEventListener("scroll", onScroll, { passive: true });
})();
