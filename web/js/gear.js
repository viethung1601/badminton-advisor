/* Gear lookup page: tabs, filters, product cards. */
(function () {
  'use strict';

  var LABELS = {
    balance: { head_light: 'Head light', even: 'Even', head_heavy: 'Head heavy' },
    stiffness: { flexible: 'Flexible', medium: 'Medium', stiff: 'Stiff' },
    level: { beginner: 'Beginner', intermediate: 'Intermediate', advanced: 'Advanced' },
    play: { attack: 'Attack', speed: 'Speed', control: 'Control', allround: 'All-round' }
  };

  var SHOE_LABELS = {
    gender: { men: 'Men', women: 'Women', unisex: 'Unisex' },
    width: { narrow: 'Narrow', standard: 'Standard', wide: 'Wide' }
  };

  function lab(group, v) { return LABELS[group][v] || v; }   // unknown code: show the raw code, don't lose data

  function toRacket(r) {
    return {
      id: 'r' + r.racket_id,
      name: r.name,
      brand: r.brand,
      price: r.price_eur,
      balance: lab('balance', r.balance),
      flex: lab('stiffness', r.stiffness),
      weight: r.weight_class,
      level: lab('level', r.level),
      play: lab('play', r.play_style),
      style: lab('level', r.level) + ' · ' + lab('play', r.play_style),
      checked: r.price_checked_at,
      url: r.source_url
    };
  }

  function toShoe(r) {
    var w = r.width ? (SHOE_LABELS.width[r.width] || r.width) : null;
    return {
      id: 's' + r.shoe_id,
      name: r.name,
      brand: r.brand,
      price: r.price_eur,
      gender: SHOE_LABELS.gender[r.gender] || r.gender,
      width: w,                                   // null = no data yet (not included in the filter)
      widthTag: w ? w + ' fit' : 'Fit: no data yet',
      sizeMin: r.size_min_eu,
      sizeMax: r.size_max_eu,
      sizeText: 'EU ' + r.size_min_eu + '–' + r.size_max_eu,
      weightText: r.weight_g != null
        ? Math.round(r.weight_g) + ' g (measured at size ' + r.weight_ref_size_eu + ')'
        : 'Weight: no data yet',
      style: null
    };
  }

  var ICONS = {
    racket: '<svg viewBox="0 0 24 24" aria-hidden="true"><ellipse cx="9" cy="9" rx="5.5" ry="6.5" transform="rotate(-35 9 9)"/><path d="m13 14 7 7"/><path d="M5 6.5l5 5M7 4.5l5 5"/></svg>',
    shoe: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 16v-4l5-1 3 3h5c3 0 5 1 5 3v1H3z"/><path d="M8 11l1-4"/></svg>',
    shuttle: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="18.5" r="2.5"/><path d="M10 17 6 5M14 17l4-12M12 16V4M8.5 5h7"/></svg>'
  };
  var CAT_WORD = { racket: 'racket', shoe: 'shoe', shuttle: 'shuttlecock' };

  var els = {
    tabs: document.getElementById('gear-tabs'),
    groups: document.getElementById('filter-groups'),
    cards: document.getElementById('gear-cards'),
    count: document.getElementById('gear-count'),
    search: document.getElementById('gear-search'),
    clear: document.getElementById('filters-clear')
  };

  var state = { cat: 'racket', data: null, selected: {}, maxPrice: null, query: '', size: null };

  /* REPLACEMENT POINT: when the backend has an endpoint, change this function, e.g.
     return fetch('/gear').then(function (r) { return r.json(); });
     The data must have the shape { racket: [...], shoe: [...], shuttle: [...] } like GEAR_SAMPLE. */
  function getJSON(url) {
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    });
  }

  function loadGear() {
    return Promise.all([
      getJSON('/rackets?limit=100&sort=price_asc'),
      getJSON('/shoes?limit=100&sort=price_asc')
    ]).then(function (res) {
      return { racket: res[0].items.map(toRacket), shoe: res[1].items.map(toShoe), shuttle: [] };
    });
  }

  function fmtPrice(n) {
    return new Intl.NumberFormat('de-DE', {
      style: 'currency', currency: 'EUR',
      minimumFractionDigits: 0, maximumFractionDigits: 2
    }).format(n)
  }

  function items() { return (state.data && state.data[state.cat]) || []; }

  function uniq(key) {
    var seen = {}, out = [];
    items().forEach(function (it) {
      if (it[key] != null && !seen[it[key]]) { seen[it[key]] = 1; out.push(it[key]); }
    });
    return out.sort(function (a, b) { return String(a).localeCompare(String(b), 'en', { numeric: true }); });
  }

  function priceCeil() {
    var m = 0;
    items().forEach(function (it) { if (it.price > m) m = it.price; });
    return Math.ceil(m / 10) * 10 || 10;
  }

  /* ----- Filters ----- */
  function resetFilters() {
    state.selected = {};
    state.maxPrice = priceCeil();
    state.query = '';
    els.search.value = '';
    state.size = null;
  }

  function renderFilters() {
    var html = '';
    (window.GEAR_FILTERS[state.cat] || []).forEach(function (f) {
      if (f.type === 'check') {
        html += '<fieldset class="fgroup"><legend>' + f.label + '</legend>';
        uniq(f.key).forEach(function (v) {
          var checked = (state.selected[f.key] || []).indexOf(v) >= 0 ? ' checked' : '';
          html += '<label class="fopt"><input type="checkbox" data-key="' + f.key + '" value="' + String(v).replace(/"/g, '&quot;') + '"' + checked + '> ' + v + '</label>';
        });
        html += '</fieldset>';
      } else if (f.type === 'price') {
        var max = priceCeil();
        html += '<div class="fgroup"><label class="flabel" for="price-range">' + f.label + '</label>' +
          '<div class="range-val" id="price-val">' + fmtPrice(state.maxPrice) + '</div>' +
          '<input class="range" id="price-range" type="range" min="0" max="' + max + '" step="5" value="' + state.maxPrice + '"></div>';
      }
      else if (f.type === 'size') {
        html += '<div class="fgroup"><label class="flabel" for="size-input">' + f.label + '</label>' +
          '<input type="number" id="size-input" min="30" max="55" step="0.5" placeholder="e.g. 42"' +
          (state.size != null ? ' value="' + state.size + '"' : '') + '></div>';
      }
    });
    els.groups.innerHTML = html;
  }

  function matches(it) {
    if (it.price > state.maxPrice) return false;
    if (state.size != null && it.sizeMin != null &&
      (state.size < it.sizeMin || state.size > it.sizeMax)) return false;
    if (state.query) {
      var hay = (it.name + ' ' + it.brand).toLowerCase();
      if (hay.indexOf(state.query.toLowerCase()) < 0) return false;
    }
    for (var k in state.selected) {
      var sel = state.selected[k];
      if (sel.length && sel.indexOf(it[k]) < 0) return false;
    }
    return true;
  }

  /* ----- Product cards ----- */
  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function renderCards() {
    var list = items().filter(matches);
    if (!items().length) {
      els.count.textContent = '';
      els.cards.innerHTML = '<div class="empty">No ' + CAT_WORD[state.cat] + ' data yet.</div>';
      return;
    }
    els.count.textContent = list.length + ' ' + CAT_WORD[state.cat] + (list.length === 1 ? '' : 's') + ' found';
    if (!list.length) {
      els.cards.innerHTML = '<div class="empty">No products match the filters. Try removing some criteria, or ask the AI for a suggestion.</div>';
      return;
    }
    var tagKeys = window.GEAR_TAGS[state.cat] || [];
    els.cards.innerHTML = list.map(function (it) {
      var tags = tagKeys.map(function (k) { return it[k] ? '<span class="tag">' + esc(it[k]) + '</span>' : ''; }).join('');
      return '<article class="card">' +
        '<div class="card-media">' + ICONS[state.cat] + '</div>' +
        '<div class="card-body">' +
        '<span class="card-brand">' + esc(it.brand) + '</span>' +
        '<h4>' + esc(it.name) + '</h4>' +
        '<div class="tags">' + tags + '</div>' +
        (it.style ? '<p class="muted small">Suitable for: ' + esc(it.style) + '</p>' : '') +
        '<div class="price">' + fmtPrice(it.price) + '</div>' +
        (it.checked ? '<p class="muted small">Price checked on ' + esc(it.checked) + '</p>' : '') +
        (it.url && /^https?:\/\//.test(it.url)
          ? '<p class="small"><a href="' + esc(it.url) + '" target="_blank" rel="noopener">Source</a></p>' : '') +
        '<button type="button" class="btn btn-ghost btn-sm" data-ask="' + esc(it.name) + '">Ask AI about this</button>' +
        '</div></article>';
    }).join('');
  }

  function render() { renderFilters(); renderCards(); }

  /* ----- Events ----- */
  els.tabs.addEventListener('click', function (e) {
    var b = e.target.closest('button[data-cat]');
    if (!b || b.getAttribute('data-cat') === state.cat) return;
    state.cat = b.getAttribute('data-cat');
    els.tabs.querySelectorAll('button').forEach(function (x) {
      x.setAttribute('aria-selected', x === b ? 'true' : 'false');
    });
    resetFilters();
    render();
  });

  els.groups.addEventListener('change', function (e) {
    var t = e.target;
    if (t.type !== 'checkbox') return;
    var k = t.getAttribute('data-key');
    var arr = state.selected[k] || (state.selected[k] = []);
    var i = arr.indexOf(t.value);
    if (t.checked && i < 0) arr.push(t.value);
    if (!t.checked && i >= 0) arr.splice(i, 1);
    renderCards();
  });

  els.groups.addEventListener('input', function (e) {
    if (e.target.id === 'price-range') {
      state.maxPrice = Number(e.target.value);
      document.getElementById('price-val').textContent = fmtPrice(state.maxPrice);
      renderCards();
    } else if (e.target.id === 'size-input') {
      state.size = e.target.value === '' ? null : Number(e.target.value);
      renderCards();
    }
  });

  els.search.addEventListener('input', function () {
    state.query = els.search.value.trim();
    renderCards();
  });

  els.clear.addEventListener('click', function () { resetFilters(); render(); });

  els.cards.addEventListener('click', function (e) {
    var b = e.target.closest('button[data-ask]');
    if (b && window.BD) window.BD.askAI('Tell me more about ' + b.getAttribute('data-ask') + ': is it suitable for me?');
  });

  /* ----- Initialization (load data the first time the tab opens) ----- */
  var loaded = false;
  window.Gear = {
    show: function () {
      if (loaded) return;
      loaded = true;
      els.cards.innerHTML = '<div class="empty">Loading data...</div>';
      loadGear().then(function (d) {
        state.data = d;
        resetFilters();
        render();
      }).catch(function () {
        loaded = false;
        els.cards.innerHTML = '<div class="empty">Could not load the gear data. Try reloading the page.</div>';
      });
    }
  };
})();