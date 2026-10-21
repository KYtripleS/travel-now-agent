/* Plugs and voltage by country: adapter checker and table filter.
   Reads the rows of #gp-table (data-t types, data-v volts, data-h hertz), so the
   page needs no extra data request. */
(function () {
  var table = document.getElementById('gp-table');
  if (!table) return;
  var rows = Array.prototype.slice.call(table.tBodies[0].rows);
  var byCode = {};
  rows.forEach(function (tr) {
    byCode[tr.getAttribute('data-c')] = {
      name: tr.cells[0].textContent,
      types: tr.getAttribute('data-t').split(' '),
      volts: tr.getAttribute('data-v').split(' ').map(Number),
      hz: tr.getAttribute('data-h').split(' ')
    };
  });

  // where the IEC listing alone would mislead a traveller: the sockets the
  // checker counts, and a line it adds
  var SOCKETS = { JP: ['A'] };
  var NOTES = {
    JP: 'Most sockets in Japan are two-pin, and some older ones will not take a plug with one wider pin.'
  };

  // sockets each plug fits, besides its own type
  var FITS = { A: ['B'], C: ['E', 'F', 'J', 'K', 'L', 'N'], E: ['F'], F: ['E'] };
  function fits(plug, sockets) {
    return sockets.some(function (s) { return s === plug || (FITS[plug] || []).indexOf(s) > -1; });
  }
  function band(v) { return v < 180 ? 'low' : 'high'; }
  function bands(c) {
    var b = {};
    c.volts.forEach(function (v) { b[band(v)] = 1; });
    return Object.keys(b);
  }
  function list(a) {
    return a.length < 2 ? a.join('') : a.slice(0, -1).join(', ') + ' and ' + a[a.length - 1];
  }
  function the(name) {
    return /^(United |Netherlands|Philippines|Bahamas|Gambia|Maldives|Marshall|Solomon|Cayman|Falkland|Faroe|US |Turks|Cook |Comoros|Seychelles|Central African|Dominican Republic)/.test(name) ? 'the ' + name : name;
  }
  function esc(s) {
    return s.replace(/[&<>"]/g, function (ch) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]; });
  }

  var from = document.getElementById('gp-from');
  var to = document.getElementById('gp-to');
  var out = document.getElementById('gp-out');

  function check() {
    var a = byCode[from.value], b = byCode[to.value];
    if (!a || !b) return;
    var sockets = SOCKETS[to.value] || b.types;
    var ok = a.types.filter(function (t) { return fits(t, sockets); });
    var no = a.types.filter(function (t) { return ok.indexOf(t) < 0; });
    var html = '<p class="gp-verdict">';
    if (a === b) {
      html += 'Same country: no adapter needed.</p>';
      out.innerHTML = html;
      return;
    }
    if (!no.length) html += '<strong>No plug adapter needed.</strong> ';
    else if (!ok.length) html += '<strong>You need a plug adapter.</strong> ';
    else html += '<strong>Some of your plugs fit.</strong> ';
    html += esc(b.name) + ' uses Type ' + list(b.types) + ' sockets';
    if (ok.length && no.length) {
      html += ': your Type ' + list(ok) + ' plugs fit, Type ' + list(no) + ' plugs need an adapter';
    } else if (no.length) {
      html += ', and plugs from ' + esc(a.name) + ' are Type ' + list(a.types);
    }
    html += '.';
    if (NOTES[to.value]) html += ' ' + NOTES[to.value];
    html += '</p><p>';
    var ba = bands(a), bb = bands(b);
    var volts = b.volts.join(' / ') + ' V';
    if (ba.length === 1 && bb.length === 1 && ba[0] !== bb[0]) {
      html += '<strong>Different voltage (' + volts + ').</strong> Chargers marked 100–240 V are fine with just a plug adapter; a single-voltage appliance, such as many hair dryers, needs a converter or a local replacement.';
    } else if (ba.length > 1 || bb.length > 1) {
      html += '<strong>Mixed voltage (' + volts + ').</strong> Some sockets differ from others, so check the label on anything that is not marked 100–240 V before you plug it in.';
    } else {
      html += '<strong>Same voltage range (' + volts + ').</strong> Your devices will work as they do at home';
      html += a.volts.join() !== b.volts.join() ? '; heating appliances may run a little warmer or weaker.' : '.';
    }
    if (a.hz.join() !== b.hz.join()) {
      html += ' The frequency is ' + b.hz.join(' / ') + ' Hz rather than ' + a.hz.join(' / ') + ' Hz, which does not matter for chargers.';
    }
    html += '</p>';
    out.innerHTML = html;
  }
  from.addEventListener('change', check);
  to.addEventListener('change', check);
  check();

  var filter = document.getElementById('gp-filter');
  filter.addEventListener('input', function () {
    var q = filter.value.trim().toLowerCase();
    var type = /^type\s*[a-o]$/.test(q) ? q.slice(-1).toUpperCase() : '';
    rows.forEach(function (tr) {
      var c = byCode[tr.getAttribute('data-c')];
      var hit = type ? c.types.indexOf(type) > -1 : !q || c.name.toLowerCase().indexOf(q) > -1;
      tr.hidden = !hit;
    });
  });
})();
