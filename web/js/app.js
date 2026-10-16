/* Badminton Doctor - router + chat (vanilla JS, không cần build) */
(function () {
  'use strict';

  // Để rỗng nếu FastAPI phục vụ cả trang web lẫn API cùng một origin.
  // Nếu API chạy ở nơi khác, đặt ví dụ: 'http://localhost:8000'
  var API_BASE = '';
  var CHAT_TIMEOUT_MS = 60000;

  /* ---------- Router ---------- */
  var ROUTES = ['home', 'gear', 'chat', 'video'];

  function currentRoute() {
    var h = (location.hash || '').replace(/^#\/?/, '');
    return ROUTES.indexOf(h) >= 0 ? h : 'home';
  }

  function renderRoute() {
    var route = currentRoute();
    document.querySelectorAll('.view').forEach(function (v) {
      v.hidden = v.getAttribute('data-view') !== route;
    });
    document.querySelectorAll('.nav a').forEach(function (a) {
      if (a.getAttribute('data-route') === route) a.setAttribute('aria-current', 'page');
      else a.removeAttribute('aria-current');
    });
    window.scrollTo(0, 0);
    if (route === 'chat') onChatShown();
    if (route === 'gear' && window.Gear) window.Gear.show();
  }

  window.addEventListener('hashchange', renderRoute);

  /* ---------- Helpers ---------- */
  function store(key, val) {
    try {
      if (val === undefined) return sessionStorage.getItem(key);
      if (val === null) sessionStorage.removeItem(key);
      else sessionStorage.setItem(key, val);
    } catch (e) { /* storage bị chặn: bỏ qua */ }
    return null;
  }

  function escapeHtml(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  // Định dạng nhẹ cho câu trả lời: **đậm**, danh sách "- ", xuống dòng. Luôn escape trước.
  function formatReply(text) {
    var lines = escapeHtml(String(text)).split(/\r?\n/);
    var out = [], inList = false;
    lines.forEach(function (line) {
      var m = line.match(/^\s*[-*•]\s+(.*)$/);
      var inline = function (s) { return s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>'); };
      if (m) {
        if (!inList) { out.push('<ul>'); inList = true; }
        out.push('<li>' + inline(m[1]) + '</li>');
      } else {
        if (inList) { out.push('</ul>'); inList = false; }
        if (line.trim()) out.push('<p>' + inline(line) + '</p>');
      }
    });
    if (inList) out.push('</ul>');
    return out.join('');
  }

  /* ---------- Chat ---------- */
  var els = {
    messages: document.getElementById('messages'),
    form: document.getElementById('composer'),
    input: document.getElementById('chat-input'),
    send: document.getElementById('send-btn'),
    reset: document.getElementById('chat-reset'),
    dot: document.getElementById('status-dot'),
    statusText: document.getElementById('status-text'),
    suggestions: document.getElementById('suggestions')
  };

  // session_id do server cấp ở lượt đầu; chỉ giữ trong biến JS => tải lại trang = hội thoại mới
  var sessionId = null;
  var busy = false;
  var locked = false;   // true khi server báo hết lượt (429)
  var greeted = false;
  var lastUserText = '';

  function addMessage(kind, html) {
    var div = document.createElement('div');
    div.className = 'msg msg-' + kind;
    div.innerHTML = html;
    els.messages.appendChild(div);
    els.messages.scrollTop = els.messages.scrollHeight;
    return div;
  }

  function greet() {
    if (greeted) return;
    greeted = true;
    addMessage('bot',
      '<p>Xin chào, mình là trợ lý của Badminton Doctor.</p>' +
      '<p>Bạn có thể kể về trình độ, ngân sách và cách chơi của mình, mình sẽ gợi ý vợt, giày hoặc quả cầu phù hợp.</p>');
  }

  function setBusy(v) {
    busy = v;
    els.send.disabled = v || locked;
    els.input.disabled = locked;
    els.input.setAttribute('aria-busy', v ? 'true' : 'false');
  }

  function showTyping() {
    return addMessage('bot', '<span class="typing" aria-label="Đang trả lời"><i></i><i></i><i></i></span>');
  }

  function showError(msg, canRetry) {
    var node = addMessage('error',
      '<p>' + escapeHtml(msg) + '</p>' +
      '<button type="button" class="btn btn-ghost btn-sm">' +
      (canRetry ? 'Thử lại' : 'Cuộc trò chuyện mới') + '</button>');
    node.querySelector('button').addEventListener('click', function () {
      if (canRetry) {
        node.remove();
        if (lastUserText) sendMessage(lastUserText, true);
      } else {
        els.reset.click();
      }
    });
  }

  function sendMessage(text, isRetry) {
    text = (text || '').trim();
    if (!text || busy) return;
    lastUserText = text;
    if (!isRetry) addMessage('user', '<p>' + escapeHtml(text) + '</p>');
    setBusy(true);
    var typing = showTyping();

    var ctrl = new AbortController();
    var timer = setTimeout(function () { ctrl.abort(); }, CHAT_TIMEOUT_MS);

    fetch(API_BASE + '/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, session_id: sessionId }),
      signal: ctrl.signal
    })
      .then(function (res) {
        if (res.ok) return res.json();
        return res.json().catch(function () { return {}; }).then(function (body) {
          var e = new Error('HTTP ' + res.status);
          e.status = res.status;
          e.detail = typeof body.detail === 'string' ? body.detail : '';
          throw e;
        });
      })
      .then(function (data) {
        typing.remove();
        if (data.session_id) {
          sessionId = data.session_id;
        }
        addMessage('bot', formatReply(data.reply != null ? data.reply : '(Không có nội dung trả lời)'));
        setStatus(true);
      })
      .catch(function (err) {
        typing.remove();
        if (err.status === 429) {
          locked = true;   // hết lượt: khóa ô nhập, chỉ còn "Cuộc trò chuyện mới"
          showError(err.detail || 'Cuộc trò chuyện đã đạt giới hạn lượt.', false);
          setStatus(true);
        } else if (err.status === 502) {
          showError('Mô hình đang gặp lỗi. Bạn thử lại sau ít giây nhé.', true);
          setStatus(true);
        } else if (err.status) {
          showError('Tin nhắn không hợp lệ hoặc quá dài (tối đa 500 ký tự). Mã lỗi ' + err.status + '.', true);
          setStatus(true);
        } else if (err.name === 'AbortError') {
          showError('Máy chủ phản hồi quá lâu. Bạn thử lại nhé.', true);
        } else {
          showError('Không kết nối được máy chủ. Kiểm tra lại rồi thử lại.', true);
          setStatus(false);
        }
      })
      .then(function () {
        clearTimeout(timer);
        setBusy(false);
        els.input.focus();
      });
  }

  function autoGrow() {
    els.input.style.height = 'auto';
    els.input.style.height = Math.min(els.input.scrollHeight, 140) + 'px';
  }

  els.form.addEventListener('submit', function (e) {
    e.preventDefault();
    var t = els.input.value;
    els.input.value = '';
    autoGrow();
    sendMessage(t);
  });

  els.input.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
      e.preventDefault();
      els.form.requestSubmit();
    }
  });
  els.input.addEventListener('input', autoGrow);

  els.suggestions.addEventListener('click', function (e) {
    var chip = e.target.closest('.chip');
    if (chip) sendMessage(chip.textContent);
  });

  els.reset.addEventListener('click', function () {
    if (busy) return;
    sessionId = null;
    locked = false;
    els.input.disabled = false;
    els.send.disabled = false;
    els.messages.innerHTML = '';
    greeted = false;
    lastUserText = '';
    greet();
    els.input.focus();
  });

  /* ---------- Hỏi chuyên gia (POST /ask-expert) ---------- */
  var ex = {
    open: document.getElementById('expert-open'),
    dlg: document.getElementById('expert-dialog'),
    form: document.getElementById('expert-form'),
    q: document.getElementById('expert-question'),
    did: document.getElementById('expert-discord'),
    consent: document.getElementById('expert-consent'),
    err: document.getElementById('expert-error'),
    cancel: document.getElementById('expert-cancel'),
    submit: document.getElementById('expert-submit')
  };
  var EXPERT_TIMEOUT_MS = 20000;
  var expertBusy = false;

  function expertError(msg) {
    ex.err.textContent = msg;
    ex.err.hidden = !msg;
  }

  ex.open.addEventListener('click', function () {
    if (!sessionId) {   // server chỉ nhận khi phiên chat đã tồn tại
      addMessage('error', '<p>Hãy trò chuyện với AI ít nhất một lượt trước, rồi gửi câu hỏi cho chuyên gia nhé.</p>');
      return;
    }
    expertError('');
    if (!ex.q.value.trim()) ex.q.value = lastUserText.slice(0, 500);
    ex.dlg.showModal();
    ex.q.focus();
  });

  ex.cancel.addEventListener('click', function () { ex.dlg.close(); });

  ex.form.addEventListener('submit', function (e) {
    e.preventDefault();
    if (expertBusy) return;
    var question = ex.q.value.trim();
    var discordId = ex.did.value.trim();
    if (!question) { expertError('Hãy nhập câu hỏi.'); return; }
    expertError('');
    expertBusy = true;
    ex.submit.disabled = true;
    ex.submit.textContent = 'Đang gửi...';

    var ctrl = new AbortController();
    var timer = setTimeout(function () { ctrl.abort(); }, EXPERT_TIMEOUT_MS);

    fetch(API_BASE + '/ask-expert', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: question, discord_id: discordId, session_id: sessionId }),
      signal: ctrl.signal
    })
      .then(function (res) {
        if (res.ok) return res.json();
        return res.json().catch(function () { return {}; }).then(function (body) {
          var err = new Error('HTTP ' + res.status);
          err.status = res.status;
          err.detail = typeof body.detail === 'string' ? body.detail : '';
          throw err;
        });
      })
      .then(function () {
        ex.q.value = '';
        ex.consent.checked = false;
        ex.dlg.close();
        addMessage('bot', '<p>Mình đã chuyển câu hỏi của bạn cho chuyên gia. Hãy tham gia server Discord và theo dõi kênh #hỏi-đáp để xem câu trả lời.</p>');
        setStatus(true);
      })
      .catch(function (err) {
        if (err.status === 404) expertError('Phiên trò chuyện đã hết hạn. Hãy hỏi AI một câu mới rồi gửi lại.');
        else if (err.status === 422) expertError('Discord ID hoặc câu hỏi chưa hợp lệ. ID gồm 17-20 chữ số.');
        else if (err.status === 429) expertError(err.detail || 'Bạn đã gửi tối đa số câu hỏi cho chuyên gia trong phiên này.');
        else if (err.status === 502) expertError('Chưa gửi được câu hỏi. Bạn thử lại sau ít giây nhé.');
        else if (err.status === 503) expertError('Tính năng hỏi chuyên gia tạm thời chưa khả dụng.');
        else if (err.status) expertError('Không gửi được (mã lỗi ' + err.status + ').');
        else if (err.name === 'AbortError') expertError('Máy chủ phản hồi quá lâu. Bạn thử lại nhé.');
        else expertError('Không kết nối được máy chủ. Kiểm tra lại rồi thử lại.');
      })
      .then(function () {
        clearTimeout(timer);
        expertBusy = false;
        ex.submit.disabled = false;
        ex.submit.textContent = 'Gửi';
      });
  });
  
  /* ---------- Trạng thái server (GET /health) ---------- */
  function setStatus(ok) {
    els.dot.className = 'dot ' + (ok ? 'dot-ok' : 'dot-bad');
    els.statusText.textContent = ok ? 'Máy chủ đang hoạt động' : 'Không kết nối được máy chủ';
  }

  function checkHealth() {
    fetch(API_BASE + '/health', { cache: 'no-store' })
      .then(function (r) { setStatus(r.ok); })
      .catch(function () { setStatus(false); });
  }

  function onChatShown() {
    greet();
    checkHealth();
    // Nếu người dùng bấm "Hỏi AI" từ trang gear, điền sẵn câu hỏi (không tự gửi)
    var pre = store('bd_prefill');
    if (pre) {
      store('bd_prefill', null);
      els.input.value = pre;
      autoGrow();
    }
    els.input.focus({ preventScroll: true });
  }

  // Cho các module khác (gear.js) chuyển sang chat với câu hỏi điền sẵn
  window.BD = {
    askAI: function (text) {
      store('bd_prefill', text);
      if (currentRoute() === 'chat') onChatShown();
      else location.hash = '#/chat';
    }
  };

  renderRoute();
})();
