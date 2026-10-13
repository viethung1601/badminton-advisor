/* Trang tra cứu gear: tab, bộ lọc, thẻ sản phẩm. */
(function () {
  'use strict';

  var LABELS = {
    balance:   { head_light: 'Nhẹ đầu', even: 'Cân bằng', head_heavy: 'Nặng đầu' },
    stiffness: { flexible: 'Dẻo', medium: 'Trung bình', stiff: 'Cứng' },
    level:     { beginner: 'Mới chơi', intermediate: 'Trung cấp', advanced: 'Nâng cao' },
    play:      { attack: 'Tấn công', speed: 'Tốc độ', control: 'Kiểm soát', allround: 'Toàn diện' }
  };

  function lab(group, v) { return LABELS[group][v] || v; }   // mã lạ thì hiện nguyên mã, không mất dữ liệu

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

  var ICONS = {
    racket:  '<svg viewBox="0 0 24 24" aria-hidden="true"><ellipse cx="9" cy="9" rx="5.5" ry="6.5" transform="rotate(-35 9 9)"/><path d="m13 14 7 7"/><path d="M5 6.5l5 5M7 4.5l5 5"/></svg>',
    shoe:    '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 16v-4l5-1 3 3h5c3 0 5 1 5 3v1H3z"/><path d="M8 11l1-4"/></svg>',
    shuttle: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="18.5" r="2.5"/><path d="M10 17 6 5M14 17l4-12M12 16V4M8.5 5h7"/></svg>'
  };
  var CAT_WORD = { racket: 'vợt', shoe: 'giày', shuttle: 'quả cầu' };

  var els = {
    tabs: document.getElementById('gear-tabs'),
    groups: document.getElementById('filter-groups'),
    cards: document.getElementById('gear-cards'),
    count: document.getElementById('gear-count'),
    search: document.getElementById('gear-search'),
    clear: document.getElementById('filters-clear')
  };

  var state = { cat: 'racket', data: null, selected: {}, maxPrice: null, query: '' };

  /* ĐIỂM THAY THẾ: khi backend có endpoint, đổi hàm này, ví dụ
     return fetch('/gear').then(function (r) { return r.json(); });
     Dữ liệu cần có dạng { racket: [...], shoe: [...], shuttle: [...] } như GEAR_SAMPLE. */
  function loadGear() {
    return fetch('/rackets?limit=100&sort=price_asc').then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    }).then(function (d) {
      return { racket: d.items.map(toRacket), shoe: [], shuttle: [] };
    });
  }

  function fmtPrice(n) {
    return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR',
      minimumFractionDigits: 0, maximumFractionDigits: 2 }).format(n)
  }

  function items() { return (state.data && state.data[state.cat]) || []; }

  function uniq(key) {
    var seen = {}, out = [];
    items().forEach(function (it) {
      if (it[key] != null && !seen[it[key]]) { seen[it[key]] = 1; out.push(it[key]); }
    });
    return out.sort(function (a, b) { return String(a).localeCompare(String(b), 'vi', { numeric: true }); });
  }

  function priceCeil() {
    var m = 0;
    items().forEach(function (it) { if (it.price > m) m = it.price; });
    return Math.ceil(m / 10) * 10 || 10;
  }

  /* ----- Bộ lọc ----- */
  function resetFilters() {
    state.selected = {};
    state.maxPrice = priceCeil();
    state.query = '';
    els.search.value = '';
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
    });
    els.groups.innerHTML = html;
  }

  function matches(it) {
    if (it.price > state.maxPrice) return false;
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

  /* ----- Thẻ sản phẩm ----- */
  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function renderCards() {
    var list = items().filter(matches);
    if (!items().length) {
      els.count.textContent = '';
      els.cards.innerHTML = '<div class="empty">Chưa có dữ liệu ' + CAT_WORD[state.cat] + '.</div>';
      return;
    }
    els.count.textContent = list.length + ' ' + CAT_WORD[state.cat] + ' phù hợp';
    if (!list.length) {
      els.cards.innerHTML = '<div class="empty">Chưa có sản phẩm nào khớp bộ lọc. Thử bỏ bớt tiêu chí, hoặc hỏi AI để được gợi ý.</div>';
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
          (it.style ? '<p class="muted small">Phù hợp: ' + esc(it.style) + '</p>' : '') +
          '<div class="price">' + fmtPrice(it.price) + '</div>' +
          (it.checked ? '<p class="muted small">Giá kiểm ngày ' + esc(it.checked) + '</p>' : '') +
          (it.url && /^https?:\/\//.test(it.url)
            ? '<p class="small"><a href="' + esc(it.url) + '" target="_blank" rel="noopener">Nguồn</a></p>' : '') +
          '<button type="button" class="btn btn-ghost btn-sm" data-ask="' + esc(it.name) + '">Hỏi AI về món này</button>' +
        '</div></article>';
    }).join('');
  }

  function render() { renderFilters(); renderCards(); }

  /* ----- Sự kiện ----- */
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
    if (e.target.id !== 'price-range') return;
    state.maxPrice = Number(e.target.value);
    document.getElementById('price-val').textContent = fmtPrice(state.maxPrice);
    renderCards();
  });

  els.search.addEventListener('input', function () {
    state.query = els.search.value.trim();
    renderCards();
  });

  els.clear.addEventListener('click', function () { resetFilters(); render(); });

  els.cards.addEventListener('click', function (e) {
    var b = e.target.closest('button[data-ask]');
    if (b && window.BD) window.BD.askAI('Cho mình hỏi thêm về ' + b.getAttribute('data-ask') + ': có hợp với mình không?');
  });

  /* ----- Khởi tạo (tải dữ liệu lần đầu khi mở tab) ----- */
  var loaded = false;
  window.Gear = {
    show: function () {
      if (loaded) return;
      loaded = true;
      els.cards.innerHTML = '<div class="empty">Đang tải dữ liệu...</div>';
      loadGear().then(function (d) {
        state.data = d;
        resetFilters();
        render();
      }).catch(function () {
        loaded = false;
        els.cards.innerHTML = '<div class="empty">Không tải được dữ liệu gear. Thử tải lại trang.</div>';
      });
    }
  };
})();
