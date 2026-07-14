(function () {
  var STORAGE_KEY = 'chistiy_mir_ai_chat';
  var MAX_HISTORY = 12;

  function getCookie(name) {
    var match = document.cookie.match(new RegExp('(?:^|; )' + name.replace(/([.$?*|{}()[\]\\/+^])/g, '\\$1') + '=([^;]*)'));
    return match ? decodeURIComponent(match[1]) : '';
  }

  function getCsrfToken(panel) {
    var cookie = getCookie('csrftoken');
    if (cookie) {
      return cookie;
    }
    var input = panel && panel.querySelector('input[name="csrfmiddlewaretoken"]');
    return input ? input.value : '';
  }

  function loadHistory() {
    try {
      var raw = sessionStorage.getItem(STORAGE_KEY);
      var parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch (e) {
      return [];
    }
  }

  function saveHistory(messages) {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(messages.slice(-MAX_HISTORY)));
    } catch (e) {
      /* ignore quota / private mode */
    }
  }

  function escapeHtml(text) {
    var div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  document.addEventListener('DOMContentLoaded', function () {
    var fab = document.getElementById('aiChatFab');
    var panel = document.getElementById('aiChatPanel');
    var closeBtn = document.getElementById('aiChatClose');
    var clearBtn = document.getElementById('aiChatClear');
    var messagesEl = document.getElementById('aiChatMessages');
    var form = document.getElementById('aiChatForm');
    var input = document.getElementById('aiChatInput');
    var sendBtn = document.getElementById('aiChatSend');
    var endpoint = panel && panel.dataset.endpoint;

    if (!fab || !panel || !form || !input || !messagesEl || !endpoint) {
      return;
    }

    var history = loadHistory();

    function scrollBottom() {
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    function appendBubble(role, text, isError) {
      var bubble = document.createElement('div');
      bubble.className = 'ai-chat-bubble ' + (isError ? 'error' : role === 'user' ? 'user' : 'bot');
      bubble.innerHTML = escapeHtml(text);
      messagesEl.appendChild(bubble);
      scrollBottom();
    }

    function showWelcomeIfEmpty() {
      if (history.length) {
        return;
      }
      appendBubble(
        'assistant',
        'Здравствуйте! Я AI-помощник «Чистый Мир». Спросите про переработку, утилизацию, раздельный сбор или вторичное сырье.'
      );
    }

    function renderHistory() {
      messagesEl.innerHTML = '';
      if (!history.length) {
        showWelcomeIfEmpty();
        return;
      }
      history.forEach(function (msg) {
        appendBubble(msg.role, msg.content);
      });
    }

    function setOpen(open) {
      panel.classList.toggle('is-open', open);
      fab.classList.toggle('is-open', open);
      fab.setAttribute('aria-expanded', open ? 'true' : 'false');
      panel.setAttribute('aria-hidden', open ? 'false' : 'true');
      if (open) {
        scrollBottom();
        setTimeout(function () { input.focus(); }, 150);
      }
    }

    function showTyping(show) {
      var existing = messagesEl.querySelector('.ai-chat-typing');
      if (existing) {
        existing.remove();
      }
      if (!show) {
        return;
      }
      var el = document.createElement('div');
      el.className = 'ai-chat-typing';
      el.innerHTML = '<span></span><span></span><span></span>';
      messagesEl.appendChild(el);
      scrollBottom();
    }

    fab.addEventListener('click', function () {
      setOpen(!panel.classList.contains('is-open'));
    });

    if (closeBtn) {
      closeBtn.addEventListener('click', function () {
        setOpen(false);
      });
    }

    if (clearBtn) {
      clearBtn.addEventListener('click', function () {
        history = [];
        saveHistory(history);
        renderHistory();
      });
    }

    input.addEventListener('keydown', function (event) {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        form.requestSubmit();
      }
    });

    form.addEventListener('submit', function (event) {
      event.preventDefault();
      var text = (input.value || '').trim();
      if (!text || sendBtn.disabled) {
        return;
      }

      history.push({ role: 'user', content: text });
      saveHistory(history);
      appendBubble('user', text);
      input.value = '';
      sendBtn.disabled = true;
      showTyping(true);

      fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(panel),
        },
        body: JSON.stringify({ messages: history }),
        credentials: 'same-origin',
      })
        .then(function (res) {
          return res.json().then(function (data) {
            return { ok: res.ok, status: res.status, data: data };
          }).catch(function () {
            return { ok: res.ok, status: res.status, data: {} };
          });
        })
        .then(function (result) {
          showTyping(false);
          if (!result.ok || !result.data.reply) {
            var err = (result.data && result.data.error) || 'Не удалось получить ответ. Попробуйте ещё раз.';
            appendBubble('assistant', err, true);
            history.pop();
            saveHistory(history);
            return;
          }
          history.push({ role: 'assistant', content: result.data.reply });
          saveHistory(history);
          appendBubble('assistant', result.data.reply);
        })
        .catch(function () {
          showTyping(false);
          appendBubble('assistant', 'Ошибка сети. Проверьте подключение и попробуйте снова.', true);
          history.pop();
          saveHistory(history);
        })
        .finally(function () {
          sendBtn.disabled = false;
          input.focus();
        });
    });

    renderHistory();
  });
})();
