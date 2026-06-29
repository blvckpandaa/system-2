(function () {
  function lockForm(form) {
    if (form.dataset.submitLocked === '1') {
      return;
    }
    form.dataset.submitLocked = '1';

    form.querySelectorAll('button, input, select, textarea').forEach(function (el) {
      if (el.type !== 'hidden') {
        el.disabled = true;
      }
    });

    var submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
    if (submitBtn && submitBtn.dataset.loadingPrepared !== '1') {
      submitBtn.dataset.loadingPrepared = '1';
      submitBtn.dataset.originalHtml = submitBtn.innerHTML;
      var label = form.dataset.loadingMessage || 'Загрузка...';
      submitBtn.innerHTML =
        '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>' +
        label;
    }
  }

  function showOverlay(wrap, message) {
    var overlay = wrap.querySelector('.form-loading-overlay');
    if (!overlay) {
      return;
    }
    var msgEl = overlay.querySelector('.form-loading-message');
    if (msgEl) {
      msgEl.textContent = message;
    }
    overlay.classList.remove('d-none');
    overlay.setAttribute('aria-busy', 'true');

    wrap.querySelectorAll('a').forEach(function (link) {
      link.classList.add('pe-none');
      link.setAttribute('aria-disabled', 'true');
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('form[data-loading-form]').forEach(function (form) {
      form.addEventListener('submit', function (event) {
        if (form.dataset.submitLocked === '1') {
          event.preventDefault();
          return false;
        }

        var wrap = form.closest('[data-form-wrap]');
        var message = form.dataset.loadingMessage || 'Загрузка...';

        if (wrap) {
          wrap.querySelectorAll('form').forEach(lockForm);
          showOverlay(wrap, message);
        } else {
          lockForm(form);
        }
      });
    });
  });
})();
