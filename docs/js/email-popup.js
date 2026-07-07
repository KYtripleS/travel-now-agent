/* Gently Yonder — email-capture popup (MailerLite direct)
 * Fires once per visitor on scroll-depth >50% OR after a time delay,
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
  var TIME_DELAY_MS = 35000;     // 35s
  var SCROLL_TRIGGER = 0.5;      // 50% of page
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
      + "#tn-pop-ov{position:fixed;inset:0;background:rgba(23,32,51,.62);z-index:99998;"
      + "display:flex;align-items:center;justify-content:center;padding:20px;opacity:0;"
      + "transition:opacity .25s ease}"
      + "#tn-pop-ov.tn-in{opacity:1}"
      + "#tn-pop{background:#F8F4E9;max-width:420px;width:100%;border-radius:14px;"
      + "box-shadow:0 24px 60px rgba(0,0,0,.35);overflow:hidden;transform:translateY(12px);"
      + "transition:transform .25s ease;font-family:Georgia,'Times New Roman',serif;position:relative}"
      + "#tn-pop-ov.tn-in #tn-pop{transform:translateY(0)}"
      + "#tn-pop .tn-top{padding:30px 28px 22px;text-align:center}"
      + "#tn-pop h2{margin:0 0 10px;font-size:1.5rem;color:#172033;line-height:1.2}"
      + "#tn-pop p{margin:0;color:#475569;font-size:1rem;line-height:1.5}"
      + "#tn-pop .tn-bot{background:#172033;padding:22px 28px 26px;text-align:center}"
      + "#tn-pop .tn-mail{display:block;width:100%;box-sizing:border-box;border:1px solid #3d4a66;"
      + "border-radius:40px;background:#0f1626;color:#f8f4e9;padding:13px 18px;font-size:1rem;"
      + "font-family:inherit;margin-bottom:10px;text-align:center;outline:none}"
      + "#tn-pop .tn-mail:focus{border-color:#C9A84C}"
      + "#tn-pop .tn-mail::placeholder{color:#8a94ab}"
      + "#tn-pop .tn-cta{display:block;width:100%;box-sizing:border-box;background:#C9A84C;"
      + "color:#172033;border:0;border-radius:40px;padding:15px 18px;font-size:1.05rem;"
      + "font-weight:700;font-family:inherit;cursor:pointer;text-decoration:none;letter-spacing:.2px}"
      + "#tn-pop .tn-cta:hover{background:#d8ba61}"
      + "#tn-pop .tn-cta[disabled]{opacity:.6;cursor:default}"
      + "#tn-pop .tn-sub{display:inline-block;margin-top:14px;color:#cfd6e4;font-size:.82rem;"
      + "text-decoration:underline;cursor:pointer}"
      + "#tn-pop .tn-x{position:absolute;top:10px;right:12px;width:32px;height:32px;border:0;"
      + "border-radius:50%;background:rgba(23,32,51,.08);color:#172033;font-size:1.1rem;"
      + "line-height:1;cursor:pointer}"
      + "#tn-pop .tn-x:hover{background:rgba(23,32,51,.16)}"
      + "#tn-pop .tn-note{margin-top:12px;color:#9aa6bd;font-size:.72rem}"
      + "#tn-pop .tn-ok{display:none;padding:6px 0}"
      + "#tn-pop .tn-ok a{color:#C9A84C;font-weight:700}";
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
    ov.setAttribute("role", "dialog");
    ov.setAttribute("aria-modal", "true");
    ov.setAttribute("aria-label", "Get the free Gently Yonder pre-flight checklist");
    ov.innerHTML =
      '<div id="tn-pop">'
      + '<button class="tn-x" aria-label="Close">&times;</button>'
      + '<div class="tn-top">'
      + '<h2>Before you fly &mdash; get the checklist</h2>'
      + '<p>Our free printable <strong>Pre-Flight Checklist</strong> (PDF): documents, '
      + 'eSIM, carry-on, and the security rules people trip over. Plus one useful '
      + 'travel-prep tip a week.</p>'
      + '</div>'
      + '<div class="tn-bot">'
      + '<iframe name="tn-ml-sink" style="display:none" title="hidden"></iframe>'
      + '<form id="tn-pop-form" action="' + ML_ACTION + '" method="post" target="tn-ml-sink">'
      + '<input class="tn-mail" type="email" name="fields[email]" required '
      + 'placeholder="your@email.com" aria-label="Email address" autocomplete="email" />'
      + '<input type="hidden" name="ml-submit" value="1" />'
      + '<input type="hidden" name="anticsrf" value="true" />'
      + '<button class="tn-cta" type="submit">Get the free checklist &rarr;</button>'
      + '</form>'
      + '<div class="tn-ok" id="tn-pop-ok">'
      + '<p style="color:#f8f4e9">Sent! Your checklist: '
      + '<a href="' + pdf + '" target="_blank" rel="noopener">download the PDF &rarr;</a><br/>'
      + '<span style="font-size:.85rem;color:#cfd6e4">A copy is also on its way to your inbox.</span></p>'
      + '</div>'
      + '<span class="tn-sub" id="tn-pop-no">No thanks</span>'
      + '<div class="tn-note">Free. Unsubscribe anytime. No spam.</div>'
      + '</div>'
      + '</div>';
    document.body.appendChild(ov);
    _overlay = ov;
    requestAnimationFrame(function () { ov.classList.add("tn-in"); });

    ov.querySelector(".tn-x").addEventListener("click", function () { close(ov); });
    ov.querySelector("#tn-pop-no").addEventListener("click", function () { close(ov); });
    ov.addEventListener("click", function (e) { if (e.target === ov) close(ov); });
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
