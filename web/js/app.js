/* Badminton Doctor - router + chat (vanilla JS, no build step needed) */
(function () {
  'use strict';

  // Leave empty if FastAPI serves both the web page and the API from the same origin.
  // If the API runs elsewhere, set e.g.: 'http://localhost:8000'
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
    } catch (e) { /* storage is blocked: ignore */ }
    return null;
  }

  function escapeHtml(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  // Light formatting for replies: **bold**, "- " lists, line breaks. Always escape first.
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

  // session_id is issued by the server on the first turn; kept only in a JS variable => reloading the page = a new conversation
  var sessionId = null;
  var busy = false;
  var locked = false;   // true when the server reports the turn limit (429)
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
      '<p>Hello, I\'m the Badminton Doctor assistant.</p>' +
      '<p>Tell me about your skill level, budget and play style, and I\'ll suggest suitable rackets, shoes or shuttlecocks.</p>');
  }

  function setBusy(v) {
    busy = v;
    els.send.disabled = v || locked;
    els.input.disabled = locked;
    els.input.setAttribute('aria-busy', v ? 'true' : 'false');
  }

  function showTyping() {
    return addMessage('bot', '<span class="typing" aria-label="Replying"><i></i><i></i><i></i></span>');
  }

  function showError(msg, canRetry) {
    var node = addMessage('error',
      '<p>' + escapeHtml(msg) + '</p>' +
      '<button type="button" class="btn btn-ghost btn-sm">' +
      (canRetry ? 'Retry' : 'New conversation') + '</button>');
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
        addMessage('bot', formatReply(data.reply != null ? data.reply : '(No reply content)'));
        setStatus(true);
      })
      .catch(function (err) {
        typing.remove();
        if (err.status === 429) {
          locked = true;   // turn limit reached: lock the input, only "New conversation" remains
          showError(err.detail || 'This conversation has reached its turn limit.', false);
          setStatus(true);
        } else if (err.status === 502) {
          showError('The model ran into an error. Please try again in a few seconds.', true);
          setStatus(true);
        } else if (err.status) {
          showError('The message is invalid or too long (max 500 characters). Error code ' + err.status + '.', true);
          setStatus(true);
        } else if (err.name === 'AbortError') {
          showError('The server took too long to respond. Please try again.', true);
        } else {
          showError('Could not connect to the server. Check your connection and try again.', true);
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

  /* ---------- Ask an expert (POST /ask-expert) ---------- */
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
    if (!sessionId) {   // the server only accepts this once a chat session exists
      addMessage('error', '<p>Please chat with the AI for at least one turn first, then send your question to the expert.</p>');
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
    if (!question) { expertError('Please enter a question.'); return; }
    expertError('');
    expertBusy = true;
    ex.submit.disabled = true;
    ex.submit.textContent = 'Sending...';

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
        addMessage('bot', '<p>I\'ve passed your question on to the expert. Join the Discord server and follow the #hỏi-đáp channel to see the answer.</p>');
        setStatus(true);
      })
      .catch(function (err) {
        if (err.status === 404) expertError('The chat session has expired. Ask the AI a new question, then send again.');
        else if (err.status === 422) expertError('The Discord ID or the question is invalid. An ID has 17-20 digits.');
        else if (err.status === 429) expertError(err.detail || 'You have reached the maximum number of expert questions for this session.');
        else if (err.status === 502) expertError('Could not send the question. Please try again in a few seconds.');
        else if (err.status === 503) expertError('The ask-an-expert feature is temporarily unavailable.');
        else if (err.status) expertError('Could not send (error code ' + err.status + ').');
        else if (err.name === 'AbortError') expertError('The server took too long to respond. Please try again.');
        else expertError('Could not connect to the server. Check your connection and try again.');
      })
      .then(function () {
        clearTimeout(timer);
        expertBusy = false;
        ex.submit.disabled = false;
        ex.submit.textContent = 'Send';
      });
  });
  
  /* ---------- Server status (GET /health) ---------- */
  function setStatus(ok) {
    els.dot.className = 'dot ' + (ok ? 'dot-ok' : 'dot-bad');
    els.statusText.textContent = ok ? 'Server is running' : 'Cannot connect to the server';
  }

  function checkHealth() {
    fetch(API_BASE + '/health', { cache: 'no-store' })
      .then(function (r) { setStatus(r.ok); })
      .catch(function () { setStatus(false); });
  }

  function onChatShown() {
    greet();
    checkHealth();
    // If the user clicked "Ask AI" from the gear page, prefill the question (do not send automatically)
    var pre = store('bd_prefill');
    if (pre) {
      store('bd_prefill', null);
      els.input.value = pre;
      autoGrow();
    }
    els.input.focus({ preventScroll: true });
  }

  // Lets other modules (gear.js) jump to the chat with a prefilled question
  window.BD = {
    askAI: function (text) {
      store('bd_prefill', text);
      if (currentRoute() === 'chat') onChatShown();
      else location.hash = '#/chat';
    }
  };

  renderRoute();
})();