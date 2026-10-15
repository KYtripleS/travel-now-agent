/* Stay Finder (tools/stay-finder.html). Ranks a city's areas for one trip from
   what our stay guides already say, with open rules: every point on screen
   names the words in the guide that earned it. Data: data/stay-finder.json,
   built by build_stay_finder.py. No live prices, ratings or availability. */
(function () {
  var root = document.getElementById('gy-finder');
  if (!root) return;
  var $ = function (id) { return document.getElementById(id); };
  var DATA = null, MAX = 3;
  var TIER_WORD = { 4: 'splurge', 3: 'comfortable', 2: 'good value', 1: 'budget' };
  var BUDGET = {
    any: { label: 'Any budget', ok: function () { return true; } },
    low: { label: 'Budget or good value', ok: function (t) { return t <= 2; } },
    mid: { label: 'Comfortable', ok: function (t) { return t === 3; } },
    high: { label: 'Splurge', ok: function (t) { return t === 4; } }
  };
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function track(name, p) { if (window.gtag) gtag('event', name, p); }

  function chosen() {
    var ps = [].slice.call(root.querySelectorAll('input[name="p"]:checked')).map(function (x) { return x.value; });
    var b = root.querySelector('input[name="budget"]:checked');
    return { city: $('gf-city').value, budget: b ? b.value : 'any', ps: ps };
  }

  function rank(city, budget, ps) {
    var ok = BUDGET[budget].ok;
    return city.areas.map(function (a, i) {
      var pts = [], score = 0;
      ps.forEach(function (p) {
        var t = a.tags[p];
        if (t) {
          score += t[0];
          pts.push({ n: t[0], text: DATA.rules[p].label + ': the guide says “' + t[1] + '”'
            + (t[0] === 3 ? ' in who the area suits' : ' about the area') });
        }
      });
      if (i === 0 && (!ps.length || ps.indexOf('first') >= 0)) {
        score += 1; pts.push({ n: 1, text: 'Listed first in our guide’s short answer' });
      }
      var fit = a.hotels.filter(function (h) { return ok(h.tier); });
      if (budget !== 'any') {
        if (fit.length) { score += 2; pts.push({ n: 2, text: (fit.length === 1 ? 'One of our picks here is ' : fit.length + ' of our picks here are ') + BUDGET[budget].label.toLowerCase() }); }
        else pts.push({ n: 0, text: 'None of our picks here are ' + BUDGET[budget].label.toLowerCase() });
      }
      var hotels = fit.concat(a.hotels.filter(function (h) { return !ok(h.tier); }));
      return { a: a, i: i, score: score, pts: pts, hotels: hotels, fit: fit.length };
    }).sort(function (x, y) { return y.score - x.score || x.i - y.i; });
  }

  function render(fire) {
    var c = chosen(), city = null;
    for (var k = 0; k < DATA.cities.length; k++) if (DATA.cities[k].slug === c.city) city = DATA.cities[k];
    if (!city) { $('gf-out').innerHTML = ''; return; }
    var rows = rank(city, c.budget, c.ps), guide = '../' + city.url;
    var html = '<p class="gf-meta">' + rows.length + ' areas from our guide, <a href="' + esc(guide) + '">'
      + esc('Where to Stay in ' + city.city) + '</a>, updated ' + esc(city.checked)
      + '. Scores come only from the guide’s own words; they know nothing about prices or rooms on your dates.</p><ol class="gf-list">';
    rows.forEach(function (r, n) {
      var a = r.a;
      html += '<li class="gf-area"><h3><span class="gf-rank">' + (n + 1) + '</span> ' + esc(a.name)
        + ' <span class="gf-score">' + r.score + ' pts</span></h3>'
        + '<p class="gf-why"><strong>' + esc(city.lead || 'If you want') + '</strong> ' + esc(a.want) + ': ' + esc(a.why) + '.</p>';
      if (r.pts.length) {
        html += '<ul class="gf-pts">' + r.pts.map(function (p) {
          return '<li><span class="gf-n">' + (p.n ? '+' + p.n : '0') + '</span> ' + esc(p.text) + '</li>';
        }).join('') + '</ul>';
      } else if (c.ps.length) {
        html += '<p class="gf-none">Nothing in the guide matches your priorities here.</p>';
      }
      if (r.hotels.length) {
        html += '<ul class="gf-hotels">' + r.hotels.slice(0, 3).map(function (h) {
          return '<li><strong>' + esc(h.name) + '</strong>, ' + esc(TIER_WORD[h.tier])
            + (h.best ? '. Best for: ' + esc(h.best) : '') + (h.watch ? '. <em>Watch out:</em> ' + esc(h.watch) : '') + '.'
            + (h.rates ? ' <a class="gf-rates" href="' + esc(h.rates) + '" rel="nofollow sponsored noopener" target="_blank">View current prices →</a>' : '')
            + '</li>';
        }).join('') + '</ul>';
      }
      html += '<p class="gf-more"><a class="gf-guide" href="' + esc(guide + (a.anchor ? '#' + a.anchor : '')) + '">Read about '
        + esc(a.name) + ' in the guide</a></p></li>';
    });
    html += '</ol><p class="gf-foot">'
      + (city.tax_anchor ? 'Count the city’s hotel tax too: <a href="' + esc(guide + '#' + city.tax_anchor) + '">the rates are in the guide</a>. ' : '')
      + 'Price links go to Booking.com through our partner Stay22; we may earn a commission if you book, at no cost to you, and it never changes the order above.</p>';
    $('gf-out').innerHTML = html;
    try {
      var q = '?city=' + encodeURIComponent(c.city) + (c.budget !== 'any' ? '&budget=' + c.budget : '')
        + (c.ps.length ? '&p=' + c.ps.join(',') : '');
      history.replaceState(null, '', location.pathname + q);
    } catch (e) {}
    if (fire) track('finder_result', { city: c.city, budget: c.budget, priorities: c.ps.join(',') || 'none', top_area: rows[0] ? rows[0].a.name : '' });
  }

  function limit() {
    var on = root.querySelectorAll('input[name="p"]:checked').length;
    [].forEach.call(root.querySelectorAll('input[name="p"]'), function (x) { x.disabled = !x.checked && on >= MAX; });
  }

  function setup(data) {
    DATA = data;
    var sel = $('gf-city');
    sel.innerHTML = '<option value="">Choose a city</option>' + data.cities.map(function (c) {
      return '<option value="' + esc(c.slug) + '">' + esc(c.city) + '</option>';
    }).join('');
    $('gf-ps').innerHTML = Object.keys(data.rules).map(function (k) {
      return '<label><input name="p" type="checkbox" value="' + k + '"> ' + esc(data.rules[k].label) + '</label>';
    }).join('');
    var q = new URLSearchParams(location.search);
    var city = q.get('city'), b = q.get('budget'), ps = (q.get('p') || '').split(',');
    if (city && data.cities.some(function (c) { return c.slug === city; })) sel.value = city;
    if (b && BUDGET[b]) root.querySelector('input[name="budget"][value="' + b + '"]').checked = true;
    ps.slice(0, MAX).forEach(function (p) {
      var x = root.querySelector('input[name="p"][value="' + p.replace(/[^a-z]/g, '') + '"]');
      if (x) x.checked = true;
    });
    limit();
    if (sel.value) render(false);
    root.addEventListener('change', function (e) {
      if (e.target.name === 'p') limit();
      if (sel.value) render(false);
    });
    $('gf-form').addEventListener('submit', function (e) {
      e.preventDefault();
      if (!sel.value) { sel.focus(); return; }
      render(true);
      $('gf-out').focus();
    });
    $('gf-out').addEventListener('click', function (e) {
      var a = e.target.closest && e.target.closest('a.gf-guide');
      if (a) track('finder_guide_click', { city: sel.value, target: a.getAttribute('href') });
    });
  }

  fetch(root.getAttribute('data-src')).then(function (r) { return r.json(); }).then(setup).catch(function () {
    $('gf-out').innerHTML = '<p>The finder could not load. Our <a href="../stay/index.html">stay guides</a> have the same information.</p>';
  });
})();
